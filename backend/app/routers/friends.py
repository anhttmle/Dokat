"""Friends router — QR-based friend management endpoints.

Endpoints (Design §3):
  POST /friends/qr/generate        — create a new QR OTP
  POST /friends/qr/scan            — scan QR and create friendship
  GET  /friends                    — list current user's friends
  DELETE /friends/{friend_user_id} — remove a friend
  PUT  /friends/fcm-token          — register / update FCM device token

Refs: Design §3, §5.1
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.redis import get_redis_client
from app.models.user import User
from app.routers.auth import get_db
from app.schemas.friend import (
    FCMTokenRequest,
    GenerateQRResponse,
    ScanQRRequest,
)
from app.services.friend_service import (
    AlreadyFriendsError,
    FriendLimitError,
    SelfFriendError,
    UserNotFoundError,
    create_friendship,
    delete_friendship,
    get_friend_profile,
    list_friends,
    save_fcm_token,
)
from app.services.notification_service import NotificationService
from app.services.otp_service import (
    OTPExpiredError,
    OTPService,
    OTPUsedError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/friends", tags=["friends"])


def _get_user_id(request: Request, db: Session) -> str:
    """Resolve firebase_uid → internal user UUID string."""
    firebase_uid: str = request.state.firebase_uid
    user = (
        db.query(User)
        .filter(User.firebase_uid == firebase_uid)
        .first()
    )
    if user is None:
        raise UserNotFoundError(
            f"No user for firebase_uid={firebase_uid!r}"
        )
    return str(user.id)


@router.post("/qr/generate", response_model=GenerateQRResponse)
async def generate_qr(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Generate a new QR OTP for the authenticated user."""
    user_id = _get_user_id(request, db)
    svc = OTPService(get_redis_client())
    result = await svc.generate(initiator_id=user_id)
    return JSONResponse(content=result.model_dump())


@router.post("/qr/scan", status_code=201)
async def scan_qr(
    payload: ScanQRRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Scan a QR token and create a friendship if valid."""
    scanner_id = _get_user_id(request, db)
    svc = OTPService(get_redis_client())

    try:
        otp_data = await svc.consume(payload.token)
    except OTPExpiredError:
        return JSONResponse(
            status_code=410,
            content={
                "error_code": "QR_EXPIRED",
                "message": "QR đã hết hạn",
            },
        )
    except OTPUsedError:
        return JSONResponse(
            status_code=410,
            content={
                "error_code": "QR_USED",
                "message": "QR đã được sử dụng",
            },
        )

    initiator_id: str = otp_data.initiator_id

    try:
        friendship = create_friendship(
            db, initiator_id=initiator_id, scanner_id=scanner_id
        )
    except SelfFriendError:
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "SELF_FRIEND",
                "message": "Không thể kết bạn với chính mình",
            },
        )
    except AlreadyFriendsError:
        return JSONResponse(
            status_code=409,
            content={
                "error_code": "ALREADY_FRIENDS",
                "message": "Hai người đã là bạn bè",
            },
        )
    except FriendLimitError as exc:
        error_code = (
            "FRIEND_LIMIT_INITIATOR"
            if exc.side == "initiator"
            else "FRIEND_LIMIT_SCANNER"
        )
        return JSONResponse(
            status_code=422,
            content={
                "error_code": error_code,
                "message": "Đã đạt giới hạn 20 bạn bè",
            },
        )

    friend_profile = get_friend_profile(db, initiator_id)
    scanner_profile = get_friend_profile(db, scanner_id)
    notif_svc = NotificationService(db)
    try:
        notif_svc.send_new_friend(
            initiator_id=initiator_id,
            scanner_name=scanner_profile.get("display_name"),
        )
    except Exception:
        logger.warning("FCM notification failed for scan", exc_info=True)

    return JSONResponse(
        status_code=201,
        content={
            "friendship_id": str(friendship.id),
            "friend": friend_profile,
            "created_at": friendship.created_at.isoformat(),
        },
    )


@router.get("")
def get_friends(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Return the authenticated user's friend list."""
    user_id = _get_user_id(request, db)
    friends = list_friends(db, user_id)

    items = [
        {
            "user_id": f["user_id"],
            "display_name": f.get("display_name"),
            "avatar_url": f.get("avatar_url"),
            "friendship_created_at": (
                f["friendship_created_at"].isoformat()
                if hasattr(f["friendship_created_at"], "isoformat")
                else f["friendship_created_at"]
            ),
        }
        for f in friends
    ]

    return JSONResponse(content={"friends": items, "total": len(items)})


@router.delete("/{friend_user_id}", status_code=204)
def remove_friend(
    friend_user_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Remove a friendship edge (idempotent).

    Returns 404 if friend_user_id does not correspond to a known user.
    Returns 204 whether or not the friendship row exists (idempotent).
    """
    user_id = _get_user_id(request, db)
    try:
        get_friend_profile(db, friend_user_id)
    except UserNotFoundError:
        return JSONResponse(
            status_code=404,
            content={
                "error_code": "USER_NOT_FOUND",
                "message": "Người dùng không tồn tại",
            },
        )
    delete_friendship(db, user_id, friend_user_id)
    return JSONResponse(status_code=204, content=None)


@router.put("/fcm-token", status_code=204)
def update_fcm_token(
    payload: FCMTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Register or update the FCM device token for the current user."""
    user_id = _get_user_id(request, db)
    try:
        save_fcm_token(db, user_id, payload.fcm_token)
    except UserNotFoundError:
        return JSONResponse(
            status_code=404,
            content={
                "error_code": "USER_NOT_FOUND",
                "message": "Người dùng không tồn tại",
            },
        )
    return JSONResponse(status_code=204, content=None)
