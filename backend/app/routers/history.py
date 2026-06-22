"""History router — list the viewer's sent/received photos (F08).

Endpoints (Design §3.1, §3.2), both under the ``/history`` prefix and
requiring a Firebase ID token (middleware):
  GET /history/sent      — authored posts within 24h, newest first
  GET /history/received  — received posts within 24h, newest first

``firebase_uid`` is resolved to the internal user UUID exactly as in
``routers/feed.py``; an unknown user yields 404 ``USER_NOT_FOUND``
(DL-F08-07). A malformed cursor yields 400 ``INVALID_CURSOR``
(DL-F08-04).

Refs: Design §3.1, §3.2, §4.1, §5; FR-1, FR-2;
AC-F08-2, AC-F08-4; DL-F08-04, DL-F08-07
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.user import User
from app.routers.auth import get_db
from app.schemas.history import ReceivedHistoryResponse, SentHistoryResponse
from app.services import history_service

router = APIRouter(prefix="/history", tags=["history"])


def _get_user_id(request: Request, db: Session) -> str | None:
    """Resolve firebase_uid → internal user UUID string, or None."""
    firebase_uid: str = request.state.firebase_uid
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    return str(user.id) if user is not None else None


def _user_not_found() -> JSONResponse:
    """Return the shared 404 USER_NOT_FOUND payload (DL-F08-07)."""
    return JSONResponse(
        status_code=404,
        content={
            "error_code": "USER_NOT_FOUND",
            "message": "Người dùng không tồn tại",
        },
    )


def _invalid_cursor() -> JSONResponse:
    """Return the shared 400 INVALID_CURSOR payload (DL-F08-04)."""
    return JSONResponse(
        status_code=400,
        content={
            "error_code": "INVALID_CURSOR",
            "message": "Con trỏ phân trang không hợp lệ",
        },
    )


@router.get("/sent", response_model=SentHistoryResponse)
def get_sent(
    request: Request,
    cursor: str | None = None,
    limit: int | None = None,
    db: Session = Depends(get_db),
) -> SentHistoryResponse | JSONResponse:
    """Return one page of the viewer's sent history.

    Returns:
        ``SentHistoryResponse`` (200) on success; JSON 404
        ``USER_NOT_FOUND`` when the viewer has no user row (DL-F08-07);
        JSON 400 ``INVALID_CURSOR`` when the cursor is malformed
        (DL-F08-04).
    """
    viewer_id = _get_user_id(request, db)
    if viewer_id is None:
        return _user_not_found()

    page_size = limit if limit is not None else history_service.FEED_PAGE_SIZE
    try:
        items, next_cursor = history_service.get_sent(
            db,
            viewer_id=viewer_id,
            cursor=cursor,
            limit=page_size,
        )
    except history_service.InvalidCursorError:
        return _invalid_cursor()

    return SentHistoryResponse(items=items, next_cursor=next_cursor)


@router.get("/received", response_model=ReceivedHistoryResponse)
def get_received(
    request: Request,
    cursor: str | None = None,
    limit: int | None = None,
    db: Session = Depends(get_db),
) -> ReceivedHistoryResponse | JSONResponse:
    """Return one page of the viewer's received history.

    Returns:
        ``ReceivedHistoryResponse`` (200) on success; JSON 404
        ``USER_NOT_FOUND`` when the viewer has no user row (DL-F08-07);
        JSON 400 ``INVALID_CURSOR`` when the cursor is malformed
        (DL-F08-04).
    """
    viewer_id = _get_user_id(request, db)
    if viewer_id is None:
        return _user_not_found()

    page_size = limit if limit is not None else history_service.FEED_PAGE_SIZE
    try:
        items, next_cursor = history_service.get_received(
            db,
            viewer_id=viewer_id,
            cursor=cursor,
            limit=page_size,
        )
    except history_service.InvalidCursorError:
        return _invalid_cursor()

    return ReceivedHistoryResponse(items=items, next_cursor=next_cursor)
