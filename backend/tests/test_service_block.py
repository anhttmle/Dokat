"""Unit tests for block_service — block / unblock / list / blocked-ids.

Uses a SQLite in-memory DB seeded with users and friendships, mirroring
``test_service_friend.py``. Block deletes the friendship (DL-F10-03) and
is silent (FR-5); the blocked-id lookup is bidirectional (DL-F10-04).

Refs: Design §1.2, §1.3, §6.1; FR-4, FR-5, FR-8;
AC-F10-3, AC-F10-4; DL-F10-03, DL-F10-04, DL-F10-05, DL-F10-09,
DL-F10-11
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.block import BlockedUser
from app.models.friendship import Friendship
from app.models.user import Base, User
from app.services import block_service
from app.services.block_service import (
    NotFriendsError,
    SelfBlockError,
    block_user,
    get_blocked_user_ids,
    list_blocked,
    unblock_user,
)


@pytest.fixture()
def db_session() -> Session:
    """Isolated SQLite in-memory session per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=True)
    session = factory()
    yield session
    session.close()
    engine.dispose()


def _make_user(
    db: Session, *, firebase_uid: str, name: str | None = None
) -> User:
    """Insert and return a minimal User row."""
    now = datetime.now(UTC)
    user = User(
        firebase_uid=firebase_uid,
        is_anonymous=False,
        display_name=name,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_friendship(db: Session, user_a: User, user_b: User) -> None:
    """Insert a canonical friendship row directly."""
    uid_a, uid_b = sorted([str(user_a.id), str(user_b.id)])
    db.add(Friendship(user_id_a=uuid.UUID(uid_a), user_id_b=uuid.UUID(uid_b)))
    db.commit()


def _are_friends(db: Session, a: User, b: User) -> bool:
    """Return True if a canonical friendship row exists for the pair."""
    uid_a, uid_b = sorted([str(a.id), str(b.id)])
    return (
        db.query(Friendship)
        .filter(
            Friendship.user_id_a == uuid.UUID(uid_a),
            Friendship.user_id_b == uuid.UUID(uid_b),
        )
        .first()
        is not None
    )


# ---------------------------------------------------------------------------
# block_user
# ---------------------------------------------------------------------------


def test_block_deletes_friendship(db_session: Session) -> None:
    """Blocking a friend deletes the friendship (FR-4, AC-F10-3)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")
    _make_friendship(db_session, a, b)

    block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    assert _are_friends(db_session, a, b) is False


def test_block_inserts_row(db_session: Session) -> None:
    """Blocking inserts a blocked_users(A, B) row."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")
    _make_friendship(db_session, a, b)

    block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    row = (
        db_session.query(BlockedUser)
        .filter(
            BlockedUser.blocker_id == a.id,
            BlockedUser.blocked_id == b.id,
        )
        .first()
    )
    assert row is not None


def test_block_requires_friendship(db_session: Session) -> None:
    """Blocking a non-friend raises NotFriendsError (FR-4, AC-F10-4)."""
    a = _make_user(db_session, firebase_uid="a")
    x = _make_user(db_session, firebase_uid="x")

    with pytest.raises(NotFriendsError):
        block_user(db_session, blocker_id=str(a.id), blocked_id=str(x.id))


def test_block_self_raises(db_session: Session) -> None:
    """Blocking oneself raises SelfBlockError (DL-F10-11)."""
    a = _make_user(db_session, firebase_uid="a")

    with pytest.raises(SelfBlockError):
        block_user(db_session, blocker_id=str(a.id), blocked_id=str(a.id))


def test_block_idempotent(db_session: Session) -> None:
    """Blocking twice yields a single row, no error (DL-F10-03)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")
    _make_friendship(db_session, a, b)

    block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))
    # Second block: no friendship remains, but must still be idempotent.
    block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    count = (
        db_session.query(BlockedUser)
        .filter(
            BlockedUser.blocker_id == a.id,
            BlockedUser.blocked_id == b.id,
        )
        .count()
    )
    assert count == 1


def test_block_is_silent(db_session: Session) -> None:
    """Blocking never invokes the NotificationService (FR-5)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")
    _make_friendship(db_session, a, b)

    with patch(
        "app.services.notification_service.NotificationService"
    ) as mock_notif:
        block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    mock_notif.assert_not_called()


# ---------------------------------------------------------------------------
# unblock_user
# ---------------------------------------------------------------------------


def test_unblock_removes_row(db_session: Session) -> None:
    """Unblocking removes the blocked_users row (AC-F10-3)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")
    _make_friendship(db_session, a, b)
    block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    unblock_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    row = (
        db_session.query(BlockedUser)
        .filter(
            BlockedUser.blocker_id == a.id,
            BlockedUser.blocked_id == b.id,
        )
        .first()
    )
    assert row is None


def test_unblock_idempotent(db_session: Session) -> None:
    """Unblocking a user who is not blocked is a no-op (DL-F10-05)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")

    unblock_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))


def test_unblock_does_not_restore_friendship(db_session: Session) -> None:
    """After unblock the pair is still not friends (DL-F10-05)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")
    _make_friendship(db_session, a, b)
    block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    unblock_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    assert _are_friends(db_session, a, b) is False


# ---------------------------------------------------------------------------
# list_blocked
# ---------------------------------------------------------------------------


def test_list_blocked_returns_profiles(db_session: Session) -> None:
    """list_blocked returns user_id and display_name per row (DL-F10-09)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b", name="Beta")
    _make_friendship(db_session, a, b)
    block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    blocked = list_blocked(db_session, str(a.id))

    assert len(blocked) == 1
    assert blocked[0]["user_id"] == str(b.id)
    assert blocked[0]["display_name"] == "Beta"
    assert "avatar_url" in blocked[0]
    assert "blocked_at" in blocked[0]


# ---------------------------------------------------------------------------
# get_blocked_user_ids
# ---------------------------------------------------------------------------


def test_blocked_ids_bidirectional(db_session: Session) -> None:
    """A block B → ids(A) contains B AND ids(B) contains A (DL-F10-04)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")
    _make_friendship(db_session, a, b)
    block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    assert b.id in get_blocked_user_ids(db_session, a.id)
    assert a.id in get_blocked_user_ids(db_session, b.id)


def test_blocked_ids_accepts_str(db_session: Session) -> None:
    """get_blocked_user_ids accepts a UUID string as well (router use)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")
    _make_friendship(db_session, a, b)
    block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    assert b.id in get_blocked_user_ids(db_session, str(a.id))


def test_block_service_module_importable() -> None:
    """Sanity: module exposes the documented public surface."""
    assert hasattr(block_service, "block_user")
    assert hasattr(block_service, "get_blocked_user_ids")
