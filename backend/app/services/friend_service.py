"""Friend service — create, list, and delete friendship edges.

Business rules (Design §1.2, §5.1):
- Canonical ordering: user_id_a < user_id_b (UUID string comparison).
- Hard limit: 20 friends per user.
- Self-friend and duplicate edges are rejected.

Refs: Design §2.2, §3.2, §3.3, §3.4
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.friendship import Friendship
from app.models.user import User

FRIEND_LIMIT = 20


class SelfFriendError(Exception):
    """Raised when a user attempts to befriend themselves."""


class AlreadyFriendsError(Exception):
    """Raised when the two users are already friends."""


class FriendLimitError(Exception):
    """Raised when either user has reached the 20-friend limit.

    Args:
        side: ``"initiator"`` or ``"scanner"`` — who hit the limit.
    """

    def __init__(self, side: str) -> None:
        super().__init__(f"Friend limit reached for {side}")
        self.side = side


class UserNotFoundError(Exception):
    """Raised when a referenced user does not exist."""


def _canonical_pair(
    uid1: str,
    uid2: str,
) -> tuple[str, str]:
    """Return ``(min, max)`` UUID strings for canonical ordering."""
    return (min(uid1, uid2), max(uid1, uid2))


def _count_friends(db: Session, user_id: str) -> int:
    """Return the number of friendships for *user_id*."""
    uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    return (
        db.query(Friendship)
        .filter(
            or_(Friendship.user_id_a == uid, Friendship.user_id_b == uid)
        )
        .count()
    )


def create_friendship(
    db: Session,
    *,
    initiator_id: str,
    scanner_id: str,
) -> Friendship:
    """Validate rules and insert a new friendship row.

    Args:
        db: Active SQLAlchemy session.
        initiator_id: UUID string of the QR owner (Initiator).
        scanner_id: UUID string of the scanner (Scanner).

    Returns:
        The newly created ``Friendship`` ORM object.

    Raises:
        SelfFriendError: If initiator_id == scanner_id.
        AlreadyFriendsError: If the pair already exists.
        FriendLimitError: If either user is at the 20-friend limit.
    """
    if initiator_id == scanner_id:
        raise SelfFriendError("Cannot befriend yourself")

    if _count_friends(db, initiator_id) >= FRIEND_LIMIT:
        raise FriendLimitError(side="initiator")

    if _count_friends(db, scanner_id) >= FRIEND_LIMIT:
        raise FriendLimitError(side="scanner")

    uid_a, uid_b = _canonical_pair(initiator_id, scanner_id)
    uid_a_obj = uuid.UUID(uid_a)
    uid_b_obj = uuid.UUID(uid_b)

    existing = (
        db.query(Friendship)
        .filter(
            Friendship.user_id_a == uid_a_obj,
            Friendship.user_id_b == uid_b_obj,
        )
        .first()
    )
    if existing is not None:
        raise AlreadyFriendsError("These users are already friends")

    row = Friendship(user_id_a=uid_a_obj, user_id_b=uid_b_obj)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_friends(db: Session, user_id: str) -> list[dict]:
    """Return all friends of *user_id* with profile and metadata.

    JOINs with the users table to include ``display_name`` and
    ``avatar_url`` for each friend.

    Args:
        db: Active SQLAlchemy session.
        user_id: UUID string of the requesting user.

    Returns:
        List of dicts with keys ``user_id``, ``display_name``,
        ``avatar_url``, and ``friendship_created_at``, ordered
        by most recent first.
    """
    uid = uuid.UUID(user_id)
    rows = (
        db.query(Friendship)
        .filter(
            or_(Friendship.user_id_a == uid, Friendship.user_id_b == uid)
        )
        .order_by(Friendship.created_at.desc())
        .all()
    )

    result = []
    for row in rows:
        friend_uuid = (
            row.user_id_b if row.user_id_a == uid else row.user_id_a
        )
        friend_user = db.query(User).filter(User.id == friend_uuid).first()
        result.append(
            {
                "user_id": str(friend_uuid),
                "display_name": (
                    friend_user.display_name if friend_user else None
                ),
                "avatar_url": (
                    friend_user.avatar_url if friend_user else None
                ),
                "friendship_created_at": row.created_at,
            }
        )
    return result


def delete_friendship(
    db: Session,
    user_id: str,
    friend_id: str,
) -> None:
    """Delete the friendship edge between two users (idempotent).

    Args:
        db: Active SQLAlchemy session.
        user_id: UUID string of the requesting user.
        friend_id: UUID string of the friend to remove.
    """
    uid_a, uid_b = _canonical_pair(user_id, friend_id)
    uid_a_obj = uuid.UUID(uid_a)
    uid_b_obj = uuid.UUID(uid_b)

    row = (
        db.query(Friendship)
        .filter(
            Friendship.user_id_a == uid_a_obj,
            Friendship.user_id_b == uid_b_obj,
        )
        .first()
    )
    if row is not None:
        db.delete(row)
        db.commit()


def get_friend_profile(db: Session, user_id: str) -> dict:
    """Return minimal profile info for *user_id*.

    Args:
        db: Active SQLAlchemy session.
        user_id: UUID string of the user.

    Returns:
        Dict with keys ``user_id``, ``display_name``, ``avatar_url``.

    Raises:
        UserNotFoundError: If the user does not exist.
    """
    uid = uuid.UUID(user_id)
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        raise UserNotFoundError(f"User {user_id!r} not found")
    return {
        "user_id": str(user.id),
        "display_name": getattr(user, "display_name", None),
        "avatar_url": getattr(user, "avatar_url", None),
    }


def save_fcm_token(db: Session, user_id: str, fcm_token: str) -> None:
    """Persist the FCM device token for *user_id*.

    Args:
        db: Active SQLAlchemy session.
        user_id: UUID string of the requesting user.
        fcm_token: Firebase Cloud Messaging device token.
    """
    uid = uuid.UUID(user_id)
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        raise UserNotFoundError(f"User {user_id!r} not found")
    user.fcm_token = fcm_token  # type: ignore[attr-defined]
    db.commit()
