"""Posts router — presigned upload URL and post creation (F05).

Endpoints (Design §3.1, §3.2):
  POST /posts/upload-url  — presigned S3 PUT URL (server-issued key)
  POST /posts             — create a post + recipient edges

Both require a Firebase ID token (middleware). ``firebase_uid`` is
resolved to the internal user UUID exactly as in ``routers/friends.py``.

Refs: Design §3.1, §3.2, §5; FR-4, FR-5, FR-9;
AC-F05-4; DL-F05-02, DL-F05-05, DL-F05-07; F11 §3.1, AC-F11-3
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.user import User
from app.routers.auth import get_db
from app.schemas.post import (
    CreatePostRequest,
    CreatePostResponse,
    PostUploadUrlRequest,
)
from app.schemas.profile import PresignedUrlResponse
from app.services import post_service, storage_service

router = APIRouter(prefix="/posts", tags=["posts"])


def _get_user_id(request: Request, db: Session) -> str | None:
    """Resolve firebase_uid → internal user UUID string, or None."""
    firebase_uid: str = request.state.firebase_uid
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    return str(user.id) if user is not None else None


@router.post("/upload-url", response_model=PresignedUrlResponse)
def create_post_upload_url(
    request: Request,
    payload: PostUploadUrlRequest,
) -> PresignedUrlResponse | JSONResponse:
    """Return a presigned S3 PUT URL under the ``posts/`` prefix.

    Returns:
        ``PresignedUrlResponse`` (200) on success; JSON 400
        ``INVALID_CONTENT_TYPE`` for unsupported MIME types.
    """
    firebase_uid: str = request.state.firebase_uid
    try:
        return storage_service.generate_upload_url(
            user_id=firebase_uid,
            prefix="posts",
            content_type=payload.content_type,
        )
    except storage_service.InvalidContentTypeError:
        return JSONResponse(
            status_code=400,
            content={
                "error": "INVALID_CONTENT_TYPE",
                "message": "Unsupported content type.",
            },
        )


@router.post("", status_code=201)
def create_post(
    payload: CreatePostRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Create a post and its recipient edges.

    Returns 201 with ``CreatePostResponse``; 422 ``INVALID_RECIPIENT``
    when a recipient is not a friend of the sender (DL-F05-07).
    """
    user_id = _get_user_id(request, db)
    if user_id is None:
        return JSONResponse(
            status_code=404,
            content={
                "error_code": "USER_NOT_FOUND",
                "message": "Người dùng không tồn tại",
            },
        )

    try:
        post, recipient_count = post_service.create_post(
            db,
            user_id=user_id,
            s3_key=payload.s3_key,
            cdn_url=payload.cdn_url,
            recipient_ids=[str(rid) for rid in payload.recipient_ids],
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
    except post_service.InvalidRecipientError:
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "INVALID_RECIPIENT",
                "message": "Người nhận không phải bạn bè",
            },
        )

    # F09 hook lives in post_service.create_post (after commit); the
    # router does not send notifications (DL-F05-05).

    body = CreatePostResponse(
        post_id=post.id,
        expires_at=post.expires_at.isoformat(),
        recipient_count=recipient_count,
        created_at=post.created_at.isoformat(),
    )
    return JSONResponse(status_code=201, content=body.model_dump(mode="json"))
