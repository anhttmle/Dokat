"""History service — read sent/received posts for a viewer (F08).

F08 is a **read-only** feature over the data F05 created (DL-F08-01):
it never INSERTs/UPDATEs and adds no migration (DL-F08-02). Two reads:

- ``get_sent`` returns the posts a viewer **authored** within the last
  24h (``expires_at > now()`` — DL-F08-03), newest first, each carrying
  ``recipient_count`` and ``seen_count`` (DL-F08-05).
- ``get_received`` returns the posts a viewer has **received** within
  24h — the same query shape as ``feed_service.get_feed`` — with a
  derived ``seen`` flag (``seen_at IS NOT NULL`` — DL-F06-09) and
  sender/pet metadata.

Cursor pagination, the page-size constants and the block hook are
**reused** from ``feed_service`` rather than redefined (DRY —
DL-F08-04, DL-F08-06).

Refs: Design §1.1, §1.2, §1.5, §2, §3.1, §3.2, §4.1;
FR-2, FR-3, FR-4, FR-5; AC-F08-1, AC-F08-4;
DL-F08-01, DL-F08-03, DL-F08-04, DL-F08-05, DL-F08-06
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.pet_profile import PetProfile
from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import User
from app.services.feed_service import (
    FEED_MAX_PAGE_SIZE,
    FEED_PAGE_SIZE,
    InvalidCursorError,
    _blocked_sender_ids,
    _decode_cursor,
    _encode_cursor,
)

__all__ = [
    "FEED_MAX_PAGE_SIZE",
    "FEED_PAGE_SIZE",
    "InvalidCursorError",
    "get_received",
    "get_sent",
]


def _cursor_filter(cursor: str):
    """Build the ``(created_at, id)`` "older than cursor" filter.

    Args:
        cursor: Opaque cursor from a previous page (DL-F08-04).

    Returns:
        A SQLAlchemy boolean expression keeping only rows strictly older
        than the cursor under ``created_at DESC, id DESC`` ordering.

    Raises:
        InvalidCursorError: If ``cursor`` is malformed (DL-F08-04).
    """
    c_created, c_post_id = _decode_cursor(cursor)
    return or_(
        Post.created_at < c_created,
        and_(Post.created_at == c_created, Post.id < c_post_id),
    )


def get_sent(
    db: Session,
    *,
    viewer_id: str,
    cursor: str | None = None,
    limit: int = FEED_PAGE_SIZE,
) -> tuple[list[dict], str | None]:
    """Return one page of the viewer's sent history, newest first.

    Args:
        db: Active SQLAlchemy session.
        viewer_id: UUID string of the viewer (post author).
        cursor: Opaque cursor from a previous page; ``None`` = first page.
        limit: Page size; clamped to ``FEED_MAX_PAGE_SIZE`` (DL-F08-04).

    Returns:
        A tuple ``(items, next_cursor)`` where ``items`` is a list of
        sent-item dicts (Design §2.1, each with ``recipient_count`` and
        ``seen_count``) and ``next_cursor`` is an opaque string when
        more pages remain, else ``None``.

    Raises:
        InvalidCursorError: If ``cursor`` is malformed (DL-F08-04).
    """
    viewer_uuid = uuid.UUID(viewer_id)
    page_size = max(1, min(limit, FEED_MAX_PAGE_SIZE))
    now = datetime.now(UTC)

    query = (
        db.query(
            Post,
            func.count(PostRecipient.id).label("recipient_count"),
            func.count(PostRecipient.seen_at).label("seen_count"),
        )
        .outerjoin(PostRecipient, PostRecipient.post_id == Post.id)
        .filter(Post.user_id == viewer_uuid)
        .filter(Post.expires_at > now)
        .group_by(Post.id)
    )

    if cursor is not None:
        query = query.filter(_cursor_filter(cursor))

    rows = (
        query.order_by(Post.created_at.desc(), Post.id.desc())
        .limit(page_size + 1)
        .all()
    )

    has_next = len(rows) > page_size
    page_rows = rows[:page_size]

    items: list[dict] = [
        {
            "post_id": str(post.id),
            "cdn_url": post.cdn_url,
            "created_at": post.created_at.isoformat(),
            "recipient_count": recipient_count,
            "seen_count": seen_count,
        }
        for post, recipient_count, seen_count in page_rows
    ]

    next_cursor: str | None = None
    if has_next and page_rows:
        last_post = page_rows[-1][0]
        next_cursor = _encode_cursor(last_post.created_at, last_post.id)

    return items, next_cursor


def get_received(
    db: Session,
    *,
    viewer_id: str,
    cursor: str | None = None,
    limit: int = FEED_PAGE_SIZE,
) -> tuple[list[dict], str | None]:
    """Return one page of the viewer's received history, newest first.

    Same query shape as ``feed_service.get_feed`` (DL-F08-06): the
    viewer is a recipient, posts within 24h, block-aware, with a derived
    ``seen`` flag and sender/pet metadata.

    Args:
        db: Active SQLAlchemy session.
        viewer_id: UUID string of the viewer (recipient).
        cursor: Opaque cursor from a previous page; ``None`` = first page.
        limit: Page size; clamped to ``FEED_MAX_PAGE_SIZE`` (DL-F08-04).

    Returns:
        A tuple ``(items, next_cursor)`` where ``items`` is a list of
        received-item dicts (Design §2.1) and ``next_cursor`` is an
        opaque string when more pages remain, else ``None``.

    Raises:
        InvalidCursorError: If ``cursor`` is malformed (DL-F08-04).
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
        query = query.filter(_cursor_filter(cursor))

    rows = (
        query.order_by(Post.created_at.desc(), Post.id.desc())
        .limit(page_size + 1)
        .all()
    )

    has_next = len(rows) > page_size
    page_rows = rows[:page_size]

    items: list[dict] = [
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
        for post, seen_at, display_name, avatar_url, pet_name in page_rows
    ]

    next_cursor: str | None = None
    if has_next and page_rows:
        last_post = page_rows[-1][0]
        next_cursor = _encode_cursor(last_post.created_at, last_post.id)

    return items, next_cursor
