"""Settings router — account, block/report, and logout endpoints.

Endpoints (Design §3, prefix ``/users``):
  DELETE /users/providers/{provider} — unlink an OAuth provider
  POST   /users/block                — block a friend (silent)
  DELETE /users/block/{user_id}      — unblock (idempotent)
  GET    /users/block                — list blocked users
  POST   /users/report               — report a user
  POST   /users/logout               — clear the device token

The caller is resolved from ``firebase_uid`` via ``_get_user_id``
(DL-F10-08, like ``routers/friends.py``); guards live in the service
layer and the router only maps exceptions → error codes (Design §5).

Refs: Design §3, §4.1, §5; FR-3, FR-4, FR-6, FR-9;
AC-F10-2, AC-F10-3, AC-F10-4, AC-F10-5, AC-F10-6; DL-F10-08
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.user import User
from app.routers.auth import get_db
from app.schemas.settings import (
    BlockListResponse,
    BlockRequest,
    ReportRequest,
)
from app.services.account_service import (
    LastProviderError,
    ProviderNotLinkedError,
    clear_device_token,
    unlink_provider,
)
from app.services.block_service import (
    NotFriendsError,
    SelfBlockError,
    block_user,
    list_blocked,
    unblock_user,
)
from app.services.friend_service import UserNotFoundError
from app.services.report_service import (
    InvalidReasonError,
    SelfReportError,
    report_user,
)

router = APIRouter(prefix="/users", tags=["settings"])


def _get_user_id(request: Request, db: Session) -> str:
    """Resolve firebase_uid → internal user UUID string (DL-F10-08)."""
    firebase_uid: str = request.state.firebase_uid
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user is None:
        raise UserNotFoundError(f"No user for firebase_uid={firebase_uid!r}")
    return str(user.id)


def _error(status_code: int, error_code: str, message: str) -> JSONResponse:
    """Build a standard error JSON response."""
    return JSONResponse(
        status_code=status_code,
        content={"error_code": error_code, "message": message},
    )


def _user_not_found() -> JSONResponse:
    """Standard 404 response when the caller has no user row."""
    return _error(404, "USER_NOT_FOUND", "Người dùng không tồn tại")


@router.delete("/providers/{provider}", status_code=204)
def unlink_provider_endpoint(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Unlink an OAuth provider from the authenticated user (FR-3)."""
    try:
        user_id = _get_user_id(request, db)
    except UserNotFoundError:
        return _user_not_found()

    try:
        unlink_provider(db, user_id=user_id, provider=provider)
    except LastProviderError:
        return _error(
            422,
            "LAST_PROVIDER",
            "Không thể hủy liên kết provider duy nhất",
        )
    except (ProviderNotLinkedError, ValueError):
        return _error(
            404,
            "PROVIDER_NOT_LINKED",
            "Provider chưa được liên kết",
        )
    return JSONResponse(status_code=204, content=None)


@router.post("/block", status_code=201)
def block_endpoint(
    payload: BlockRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Block a friend (silent — no notification, FR-4, FR-5)."""
    try:
        user_id = _get_user_id(request, db)
    except UserNotFoundError:
        return _user_not_found()

    try:
        block_user(db, blocker_id=user_id, blocked_id=payload.user_id)
    except SelfBlockError:
        return _error(422, "SELF_BLOCK", "Không thể chặn chính mình")
    except NotFriendsError:
        return _error(
            422, "NOT_FRIENDS", "Chỉ có thể chặn người trong danh sách bạn bè"
        )
    return JSONResponse(
        status_code=201, content={"blocked_user_id": payload.user_id}
    )


@router.delete("/block/{user_id}", status_code=204)
def unblock_endpoint(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Unblock a user (idempotent — DL-F10-05)."""
    try:
        caller_id = _get_user_id(request, db)
    except UserNotFoundError:
        return _user_not_found()

    unblock_user(db, blocker_id=caller_id, blocked_id=user_id)
    return JSONResponse(status_code=204, content=None)


@router.get("/block", response_model=BlockListResponse)
def list_blocked_endpoint(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Return the caller's blocked-user list (DL-F10-09)."""
    try:
        caller_id = _get_user_id(request, db)
    except UserNotFoundError:
        return _user_not_found()

    blocked = list_blocked(db, caller_id)
    items = [
        {
            "user_id": b["user_id"],
            "display_name": b.get("display_name"),
            "avatar_url": b.get("avatar_url"),
            "blocked_at": (
                b["blocked_at"].isoformat()
                if hasattr(b["blocked_at"], "isoformat")
                else b["blocked_at"]
            ),
        }
        for b in blocked
    ]
    return JSONResponse(content={"blocked": items, "total": len(items)})


@router.post("/report", status_code=201)
def report_endpoint(
    payload: ReportRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Report a user; stores a moderation record only (AC-F10-5)."""
    try:
        caller_id = _get_user_id(request, db)
    except UserNotFoundError:
        return _user_not_found()

    try:
        report = report_user(
            db,
            reporter_id=caller_id,
            reported_user_id=payload.user_id,
            reason=payload.reason,
        )
    except SelfReportError:
        return _error(422, "SELF_REPORT", "Không thể báo cáo chính mình")
    except InvalidReasonError:
        return _error(422, "INVALID_REASON", "Lý do báo cáo không hợp lệ")
    return JSONResponse(status_code=201, content={"report_id": str(report.id)})


@router.post("/logout", status_code=204)
def logout_endpoint(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Clear the caller's device token on logout (DL-F10-07)."""
    try:
        caller_id = _get_user_id(request, db)
    except UserNotFoundError:
        return _user_not_found()

    clear_device_token(db, caller_id)
    return JSONResponse(status_code=204, content=None)
