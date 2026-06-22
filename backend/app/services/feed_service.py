"""Feed service — read received posts for a viewer (F06).

F06 is a **read-only** feature over the data F05 created (DL-F06-01):
it never INSERTs/UPDATEs. ``get_feed`` returns the posts a viewer has
**received** within the last 24h (``expires_at > now()`` — DL-F06-04),
newest first, with a derived ``seen`` flag (``seen_at IS NOT NULL`` —
DL-F06-09) and sender/pet metadata (FR-4).

Pagination is cursor-based over ``(created_at, post_id)`` encoded as an
opaque base64 JSON string (DL-F06-08). Block exclusion goes through the
``_blocked_sender_ids`` hook, which returns an empty set until F10 fills
it in (DL-F06-03).

Refs: Design §1.1, §1.3, §2, §4.1; FR-2, FR-3, FR-4, FR-6, FR-10;
AC-F06-1, AC-F06-2, AC-F06-4, AC-F06-6;
DL-F06-01, DL-F06-03, DL-F06-04, DL-F06-08, DL-F06-09
"""

import base64
import binascii
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.pet_profile import PetProfile
from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import User

FEED_PAGE_SIZE = 20
FEED_MAX_PAGE_SIZE = 50


class InvalidCursorError(Exception):
    """Raised when an opaque feed cursor cannot be decoded (DL-F06-08)."""


def _blocked_sender_ids(db: Session, viewer_id: uuid.UUID) -> set[uuid.UUID]:
    """Return sender IDs hidden from the viewer's feed by a block.

    Delegates to ``block_service.get_blocked_user_ids``, which returns a
    bidirectional set (people the viewer blocked ∪ people who blocked the
    viewer), so a block hides photos both ways without changing the feed
    query (DL-F06-03, DL-F10-04).
    """
    from app.services import block_service

    return block_service.get_blocked_user_ids(db, viewer_id)


def _encode_cursor(created_at: datetime, post_id: uuid.UUID) -> str:
    """Encode ``(created_at, post_id)`` into an opaque base64 cursor."""
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "post_id": str(post_id)}
    )
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode an opaque cursor back into ``(created_at, post_id)``.

    Raises:
        InvalidCursorError: If the cursor is malformed (DL-F06-08).
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        created_at = datetime.fromisoformat(data["created_at"])
        post_id = uuid.UUID(data["post_id"])
    except (
        binascii.Error,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        raise InvalidCursorError(f"Malformed cursor: {cursor!r}") from exc
    return created_at, post_id


def get_feed(
    db: Session,
    *,
    viewer_id: str,
    cursor: str | None = None,
    limit: int = FEED_PAGE_SIZE,
) -> tuple[list[dict], str | None]:
    """Return one page of the viewer's received feed, newest first.

    Args:
        db: Active SQLAlchemy session.
        viewer_id: UUID string of the viewer (recipient).
        cursor: Opaque cursor from a previous page; ``None`` = first page.
        limit: Page size; clamped to ``FEED_MAX_PAGE_SIZE`` (DL-F06-08).

    Returns:
        A tuple ``(items, next_cursor)`` where ``items`` is a list of
        feed-item dicts (Design §2.1) and ``next_cursor`` is an opaque
        string when more pages remain, else ``None``.

    Raises:
        InvalidCursorError: If ``cursor`` is malformed (DL-F06-08).
    """
    viewer_uuid = uuid.UUID(viewer_id)
    page_size = max(1, min(limit, FEED_MAX_PAGE_SIZE))
    now = datetime.now(UTC)

    query = (
        db.query(
            Post,
            PostRecipient.seen_at,
            User.display_name,
            User.avatar_url,
            PetProfile.name,
        )
        .join(PostRecipient, PostRecipient.post_id == Post.id)
        .join(User, User.id == Post.user_id)
        .outerjoin(PetProfile, PetProfile.user_id == Post.user_id)
        .filter(PostRecipient.recipient_id == viewer_uuid)
        .filter(Post.expires_at > now)
    )

    blocked = _blocked_sender_ids(db, viewer_uuid)
    if blocked:
        query = query.filter(Post.user_id.notin_(blocked))

    if cursor is not None:
        c_created, c_post_id = _decode_cursor(cursor)
        query = query.filter(
            or_(
                Post.created_at < c_created,
                and_(
                    Post.created_at == c_created,
                    Post.id < c_post_id,
                ),
            )
        )

    rows = (
        query.order_by(Post.created_at.desc(), Post.id.desc())
        .limit(page_size + 1)
        .all()
    )

    has_next = len(rows) > page_size
    page_rows = rows[:page_size]

    items: list[dict] = []
    for post, seen_at, display_name, avatar_url, pet_name in page_rows:
        items.append(
            {
                "post_id": str(post.id),
                "sender_id": str(post.user_id),
                "sender_display_name": display_name,
                "sender_avatar_url": avatar_url,
                "pet_name": pet_name,
                "cdn_url": post.cdn_url,
                "created_at": post.created_at.isoformat(),
                "seen": seen_at is not None,
            }
        )

    next_cursor: str | None = None
    if has_next and page_rows:
        last_post = page_rows[-1][0]
        next_cursor = _encode_cursor(last_post.created_at, last_post.id)

    return items, next_cursor
