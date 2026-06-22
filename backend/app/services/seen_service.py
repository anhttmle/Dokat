"""Seen service — mark a post seen and list its viewers (F07).

F07 writes/reads ``post_recipients.seen_at`` (created by F05); it adds
no tables or migrations (DL-F07-07). ``mark_seen`` is idempotent —
first-seen wins (DL-F07-02) — and only a recipient of the post may
write seen (DL-F07-03). ``get_seen_by`` is sender-only (DL-F07-04) and
returns every recipient with a non-null ``seen_at`` plus the aggregate
count (DL-F07-08).

Refs: Design §1.1–§1.3, §2, §4.1; FR-1, FR-2, FR-3, FR-4, FR-6;
AC-F07-1, AC-F07-2, AC-F07-3;
DL-F07-01, DL-F07-02, DL-F07-03, DL-F07-04, DL-F07-08
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import User


class PostNotFoundError(Exception):
    """Raised when the target post does not exist."""


class NotRecipientError(Exception):
    """Raised when the viewer is not a recipient of the post (DL-F07-03)."""


class NotSenderError(Exception):
    """Raised when the viewer is not the sender of the post (DL-F07-04)."""


def mark_seen(
    db: Session,
    *,
    post_id: str,
    viewer_id: str,
) -> datetime:
    """Mark a post seen by a recipient (idempotent, first-seen wins).

    Args:
        db: Active SQLAlchemy session.
        post_id: UUID string of the post being viewed.
        viewer_id: UUID string of the recipient marking it seen.

    Returns:
        The ``seen_at`` timestamp (the first-seen value; unchanged on
        repeat calls — DL-F07-02).

    Raises:
        PostNotFoundError: If the post does not exist.
        NotRecipientError: If the viewer is not a recipient of the post
            (DL-F07-03).
    """
    post_uuid = uuid.UUID(post_id)
    viewer_uuid = uuid.UUID(viewer_id)

    post = db.query(Post).filter(Post.id == post_uuid).first()
    if post is None:
        raise PostNotFoundError(f"Post not found: {post_id}")

    edge = (
        db.query(PostRecipient)
        .filter(
            PostRecipient.post_id == post_uuid,
            PostRecipient.recipient_id == viewer_uuid,
        )
        .first()
    )
    if edge is None:
        raise NotRecipientError(
            f"User {viewer_id} is not a recipient of post {post_id}"
        )

    if edge.seen_at is None:
        edge.seen_at = datetime.now(UTC)
        db.commit()
        db.refresh(edge)

    return edge.seen_at


def get_seen_by(
    db: Session,
    *,
    post_id: str,
    viewer_id: str,
) -> tuple[list[dict], int]:
    """Return the recipients who have seen the post plus their count.

    Args:
        db: Active SQLAlchemy session.
        post_id: UUID string of the post.
        viewer_id: UUID string of the requester (must be the sender).

    Returns:
        A tuple ``(viewers, seen_count)`` where ``viewers`` is a list of
        dicts (``user_id``, ``display_name``, ``avatar_url``,
        ``seen_at``) sorted by ``seen_at`` descending, and
        ``seen_count == len(viewers)`` (DL-F07-08).

    Raises:
        PostNotFoundError: If the post does not exist.
        NotSenderError: If the viewer is not the post's sender
            (DL-F07-04).
    """
    post_uuid = uuid.UUID(post_id)
    viewer_uuid = uuid.UUID(viewer_id)

    post = db.query(Post).filter(Post.id == post_uuid).first()
    if post is None:
        raise PostNotFoundError(f"Post not found: {post_id}")

    if post.user_id != viewer_uuid:
        raise NotSenderError(
            f"User {viewer_id} is not the sender of post {post_id}"
        )

    rows = (
        db.query(
            PostRecipient.recipient_id,
            PostRecipient.seen_at,
            User.display_name,
            User.avatar_url,
        )
        .join(User, User.id == PostRecipient.recipient_id)
        .filter(
            PostRecipient.post_id == post_uuid,
            PostRecipient.seen_at.isnot(None),
        )
        .order_by(PostRecipient.seen_at.desc())
        .all()
    )

    viewers = [
        {
            "user_id": str(recipient_id),
            "display_name": display_name,
            "avatar_url": avatar_url,
            "seen_at": seen_at.isoformat(),
        }
        for recipient_id, seen_at, display_name, avatar_url in rows
    ]
    return viewers, len(viewers)
