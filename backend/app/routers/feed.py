"""Feed router — list the viewer's received photos (F06).

Endpoint (Design §3.1):
  GET /feed  — received posts within 24h, newest first, cursor-paginated

Requires a Firebase ID token (middleware). ``firebase_uid`` is resolved
to the internal user UUID exactly as in ``routers/posts.py``; an unknown
user yields 404 ``USER_NOT_FOUND`` (DL-F06-05). A malformed cursor
yields 400 ``INVALID_CURSOR`` (DL-F06-08).

Refs: Design §3.1, §4.1, §5; FR-1; AC-F06-4; DL-F06-05, DL-F06-08
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.user import User
from app.routers.auth import get_db
from app.schemas.feed import FeedResponse
from app.services import feed_service

router = APIRouter(prefix="/feed", tags=["feed"])


def _get_user_id(request: Request, db: Session) -> str | None:
    """Resolve firebase_uid → internal user UUID string, or None."""
    firebase_uid: str = request.state.firebase_uid
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    return str(user.id) if user is not None else None


@router.get("", response_model=FeedResponse)
def get_feed(
    request: Request,
    cursor: str | None = None,
    limit: int | None = None,
    db: Session = Depends(get_db),
) -> FeedResponse | JSONResponse:
    """Return one page of the viewer's received feed.

    Returns:
        ``FeedResponse`` (200) on success; JSON 404 ``USER_NOT_FOUND``
        when the viewer has no user row (DL-F06-05); JSON 400
        ``INVALID_CURSOR`` when the cursor is malformed (DL-F06-08).
    """
    viewer_id = _get_user_id(request, db)
    if viewer_id is None:
        return JSONResponse(
            status_code=404,
            content={
                "error_code": "USER_NOT_FOUND",
                "message": "Người dùng không tồn tại",
            },
        )

    page_size = limit if limit is not None else feed_service.FEED_PAGE_SIZE
    try:
        items, next_cursor = feed_service.get_feed(
            db,
            viewer_id=viewer_id,
            cursor=cursor,
            limit=page_size,
        )
    except feed_service.InvalidCursorError:
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "INVALID_CURSOR",
                "message": "Con trỏ phân trang không hợp lệ",
            },
        )

    return FeedResponse(items=items, next_cursor=next_cursor)
