"""Block service — block / unblock users and read block relationships.

Blocking requires an existing friendship (FR-4); it deletes that
friendship (DL-F10-03) and records a one-directional ``blocked_users``
row. The operation is **silent** — no notification is ever sent (FR-5).
Unblocking removes the row but never restores the friendship
(DL-F10-05). The block-id lookup is bidirectional so the feed hides
photos in both directions (DL-F10-04).

Refs: Design §1.2, §1.3, §4.1; FR-4, FR-5, FR-8;
DL-F10-03, DL-F10-04, DL-F10-05, DL-F10-09, DL-F10-11
"""

import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.block import BlockedUser
from app.models.friendship import Friendship
from app.models.user import User
from app.services import friend_service


class SelfBlockError(Exception):
    """Raised when a user attempts to block themselves (DL-F10-11)."""


class NotFriendsError(Exception):
    """Raised when blocking a user who is not a current friend (FR-4)."""


def _as_uuid(value: str | uuid.UUID) -> uuid.UUID:
    """Coerce a UUID string or object into a ``uuid.UUID``."""
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _are_friends(db: Session, a: uuid.UUID, b: uuid.UUID) -> bool:
    """Return True if a canonical friendship row exists for the pair."""
    uid_a, uid_b = sorted([str(a), str(b)])
    return (
        db.query(Friendship)
        .filter(
            Friendship.user_id_a == uuid.UUID(uid_a),
            Friendship.user_id_b == uuid.UUID(uid_b),
        )
        .first()
        is not None
    )


def block_user(db: Session, *, blocker_id: str, blocked_id: str) -> None:
    """Block ``blocked_id`` on behalf of ``blocker_id`` (silent).

    Validates the request, deletes the friendship (DL-F10-03), and
    upserts the ``blocked_users`` row. No notification is sent (FR-5).

    Args:
        db: Active SQLAlchemy session.
        blocker_id: UUID string of the user performing the block.
        blocked_id: UUID string of the user being blocked.

    Raises:
        SelfBlockError: If ``blocker_id == blocked_id`` (DL-F10-11).
        NotFriendsError: If the two users are not friends (FR-4).
    """
    if blocker_id == blocked_id:
        raise SelfBlockError("Cannot block yourself")

    blocker_uuid = _as_uuid(blocker_id)
    blocked_uuid = _as_uuid(blocked_id)

    existing = (
        db.query(BlockedUser)
        .filter(
            BlockedUser.blocker_id == blocker_uuid,
            BlockedUser.blocked_id == blocked_uuid,
        )
        .first()
    )
    if existing is not None:
        # Idempotent: already blocked, nothing more to do (DL-F10-03).
        return

    if not _are_friends(db, blocker_uuid, blocked_uuid):
        raise NotFriendsError("Can only block a current friend")

    friend_service.delete_friendship(db, blocker_id, blocked_id)

    db.add(BlockedUser(blocker_id=blocker_uuid, blocked_id=blocked_uuid))
    db.commit()


def unblock_user(db: Session, *, blocker_id: str, blocked_id: str) -> None:
    """Remove the block row if present (idempotent — DL-F10-05).

    Does not restore the friendship; the two users must re-add each
    other via QR (F03).

    Args:
        db: Active SQLAlchemy session.
        blocker_id: UUID string of the user who blocked.
        blocked_id: UUID string of the user to unblock.
    """
    row = (
        db.query(BlockedUser)
        .filter(
            BlockedUser.blocker_id == _as_uuid(blocker_id),
            BlockedUser.blocked_id == _as_uuid(blocked_id),
        )
        .first()
    )
    if row is not None:
        db.delete(row)
        db.commit()


def list_blocked(db: Session, blocker_id: str) -> list[dict]:
    """Return the users blocked by ``blocker_id`` with profile metadata.

    Args:
        db: Active SQLAlchemy session.
        blocker_id: UUID string of the requesting user.

    Returns:
        List of dicts with keys ``user_id``, ``display_name``,
        ``avatar_url`` and ``blocked_at`` (DL-F10-09), newest first.
    """
    rows = (
        db.query(BlockedUser, User)
        .join(User, User.id == BlockedUser.blocked_id)
        .filter(BlockedUser.blocker_id == _as_uuid(blocker_id))
        .order_by(BlockedUser.created_at.desc())
        .all()
    )
    return [
        {
            "user_id": str(user.id),
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "blocked_at": block.created_at,
        }
        for block, user in rows
    ]


def get_blocked_user_ids(
    db: Session, user_id: str | uuid.UUID
) -> set[uuid.UUID]:
    """Return the bidirectional set of blocked user IDs for ``user_id``.

    Includes both the people ``user_id`` blocked and the people who
    blocked ``user_id`` (DL-F10-04), used by the feed hook to hide
    photos in both directions.

    Args:
        db: Active SQLAlchemy session.
        user_id: UUID string or object of the viewer.

    Returns:
        Set of ``uuid.UUID`` identifiers to exclude.
    """
    uid = _as_uuid(user_id)
    rows = (
        db.query(BlockedUser)
        .filter(
            or_(
                BlockedUser.blocker_id == uid,
                BlockedUser.blocked_id == uid,
            )
        )
        .all()
    )
    result: set[uuid.UUID] = set()
    for row in rows:
        other = row.blocked_id if row.blocker_id == uid else row.blocker_id
        result.add(other)
    return result
