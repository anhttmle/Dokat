"""Seen router — mark a post seen and list its viewers (F07).

Endpoints (Design §3.1, §3.2), both under the ``/posts`` prefix and
requiring a Firebase ID token (middleware):
  POST /posts/{post_id}/seen     — recipient marks a post seen
  GET  /posts/{post_id}/seen-by  — sender lists who has seen the post

``firebase_uid`` is resolved to the internal user UUID exactly as in
``routers/posts.py``; an unknown user yields 404 ``USER_NOT_FOUND``
(DL-F07-09). A malformed ``post_id`` is rejected by FastAPI path
validation (422).

Refs: Design §3.1, §3.2, §4.1, §5;
AC-F07-1, AC-F07-2, AC-F07-3;
DL-F07-03, DL-F07-04, DL-F07-09
"""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.user import User
from app.routers.auth import get_db
from app.schemas.seen import SeenByResponse, SeenResponse
from app.services import seen_service

router = APIRouter(prefix="/posts", tags=["seen"])


def _get_user_id(request: Request, db: Session) -> str | None:
    """Resolve firebase_uid → internal user UUID string, or None."""
    firebase_uid: str = request.state.firebase_uid
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    return str(user.id) if user is not None else None


def _user_not_found() -> JSONResponse:
    """Return the shared 404 USER_NOT_FOUND payload (DL-F07-09)."""
    return JSONResponse(
        status_code=404,
        content={
            "error_code": "USER_NOT_FOUND",
            "message": "Người dùng không tồn tại",
        },
    )


def _post_not_found() -> JSONResponse:
    """Return the shared 404 POST_NOT_FOUND payload."""
    return JSONResponse(
        status_code=404,
        content={
            "error_code": "POST_NOT_FOUND",
            "message": "Bài đăng không tồn tại",
        },
    )


@router.post("/{post_id}/seen", response_model=SeenResponse)
def mark_post_seen(
    post_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> SeenResponse | JSONResponse:
    """Mark a post seen for the current recipient (idempotent).

    Returns:
        ``SeenResponse`` (200) with the first-seen ``seen_at``; JSON 404
        ``USER_NOT_FOUND`` / ``POST_NOT_FOUND`` or 403 ``NOT_RECIPIENT``
        on the error paths (Design §3.1, §5).
    """
    viewer_id = _get_user_id(request, db)
    if viewer_id is None:
        return _user_not_found()

    try:
        seen_at = seen_service.mark_seen(
            db,
            post_id=str(post_id),
            viewer_id=viewer_id,
        )
    except seen_service.PostNotFoundError:
        return _post_not_found()
    except seen_service.NotRecipientError:
        return JSONResponse(
            status_code=403,
            content={
                "error_code": "NOT_RECIPIENT",
                "message": "Bạn không phải người nhận ảnh này",
            },
        )

    return SeenResponse(post_id=str(post_id), seen_at=seen_at.isoformat())


@router.get("/{post_id}/seen-by", response_model=SeenByResponse)
def get_post_seen_by(
    post_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> SeenByResponse | JSONResponse:
    """List the recipients who have seen the post (sender only).

    Returns:
        ``SeenByResponse`` (200) with ``seen_count`` + ``viewers``; JSON
        404 ``USER_NOT_FOUND`` / ``POST_NOT_FOUND`` or 403 ``FORBIDDEN``
        on the error paths (Design §3.2, §5).
    """
    viewer_id = _get_user_id(request, db)
    if viewer_id is None:
        return _user_not_found()

    try:
        viewers, seen_count = seen_service.get_seen_by(
            db,
            post_id=str(post_id),
            viewer_id=viewer_id,
        )
    except seen_service.PostNotFoundError:
        return _post_not_found()
    except seen_service.NotSenderError:
        return JSONResponse(
            status_code=403,
            content={
                "error_code": "FORBIDDEN",
                "message": "Chỉ người gửi mới xem được danh sách này",
            },
        )

    return SeenByResponse(
        post_id=str(post_id),
        seen_count=seen_count,
        viewers=viewers,
    )
