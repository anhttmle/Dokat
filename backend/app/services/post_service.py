"""Post service — create a post and its recipient edges (F05).

Business rules (Design §1.1–§1.3, §2.4):
- Every post gets ``expires_at = created_at + POST_EXPIRY_HOURS`` (24h —
  DL-F05-03); the row is kept, only hidden from feed/history later.
- ``recipient_ids`` are de-duplicated and must all be friends of the
  sender; a stranger raises ``InvalidRecipientError`` (DL-F05-07).
- 0 recipients is valid: the post is created with no recipient rows
  (FR-7, AC-F05-4).
- This service does NOT send push notifications; the F09 hook plugs in
  after recipients are committed (DL-F05-05).

Refs: Design §1.1–§1.3, §2.4; FR-5, FR-6, FR-7, FR-11;
AC-F05-2, AC-F05-3, AC-F05-4; DL-F05-03, DL-F05-05, DL-F05-07
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.friendship import Friendship
from app.models.post import Post
from app.models.post_recipient import PostRecipient

POST_EXPIRY_HOURS = 24


class InvalidRecipientError(Exception):
    """Raised when a recipient is not a friend of the sender."""


def _friend_ids(db: Session, user_id: uuid.UUID) -> set[uuid.UUID]:
    """Return the set of user IDs that are friends of *user_id*."""
    rows = (
        db.query(Friendship)
        .filter(
            or_(
                Friendship.user_id_a == user_id,
                Friendship.user_id_b == user_id,
            )
        )
        .all()
    )
    return {
        row.user_id_b if row.user_id_a == user_id else row.user_id_a
        for row in rows
    }


def create_post(
    db: Session,
    *,
    user_id: str,
    s3_key: str,
    cdn_url: str,
    recipient_ids: list[str],
    latitude: float | None = None,
    longitude: float | None = None,
) -> tuple[Post, int]:
    """Create a post and insert one recipient row per chosen friend.

    Args:
        db: Active SQLAlchemy session.
        user_id: UUID string of the sender.
        s3_key: Authoritative S3 object key (server-issued).
        cdn_url: Public CDN URL for the uploaded image.
        recipient_ids: UUID strings of recipients (may be empty, may
            contain duplicates — de-duplicated here).
        latitude: Optional capture latitude (F11); stored as-is.
        longitude: Optional capture longitude (F11); stored as-is.

    Returns:
        A tuple ``(post, recipient_count)``.

    Raises:
        InvalidRecipientError: If any recipient is not a friend of the
            sender (DL-F05-07).
    """
    sender_uuid = uuid.UUID(user_id)

    unique_ids: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for rid in recipient_ids:
        rid_uuid = rid if isinstance(rid, uuid.UUID) else uuid.UUID(str(rid))
        if rid_uuid not in seen:
            seen.add(rid_uuid)
            unique_ids.append(rid_uuid)

    if unique_ids:
        friends = _friend_ids(db, sender_uuid)
        invalid = [rid for rid in unique_ids if rid not in friends]
        if invalid:
            raise InvalidRecipientError(
                f"Recipients are not friends: {invalid}"
            )

    now = datetime.now(UTC)
    post = Post(
        user_id=sender_uuid,
        s3_key=s3_key,
        cdn_url=cdn_url,
        expires_at=now + timedelta(hours=POST_EXPIRY_HOURS),
        latitude=latitude,
        longitude=longitude,
        created_at=now,
    )
    db.add(post)
    db.flush()

    for rid in unique_ids:
        db.add(PostRecipient(post_id=post.id, recipient_id=rid))

    db.commit()
    db.refresh(post)

    # F09 hook: send "new photo" push to each recipient here, after the
    # recipients are committed. F05 intentionally does not call FCM
    # (DL-F05-05).

    return post, len(unique_ids)
