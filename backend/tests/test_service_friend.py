"""Unit tests for FriendService — friendship create / list / delete.

Written TDD-style; tests are expected to FAIL until FriendService is
implemented in a later F03 task.

Uses SQLite in-memory DB so no PostgreSQL instance is needed.

Refs: Design §6.1, AC-F03-2, AC-F03-5, AC-F03-7, AC-F03-8, AC-F03-9
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.friendship  # noqa: F401  register table on Base
from app.models.friendship import Friendship
from app.models.user import Base, User
from app.services.friend_service import (
    AlreadyFriendsError,
    FriendLimitError,
    SelfFriendError,
    create_friendship,
    delete_friendship,
    list_friends,
)

FRIEND_LIMIT = 20


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


def _make_user(db: Session, *, firebase_uid: str) -> User:
    """Insert and return a minimal User row."""
    now = datetime.now(timezone.utc)
    user = User(
        firebase_uid=firebase_uid,
        is_anonymous=False,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_friendship(db: Session, user_a: User, user_b: User) -> Friendship:
    """Insert a canonical friendship row directly."""
    import uuid as _uuid

    uid_a_str, uid_b_str = sorted([str(user_a.id), str(user_b.id)])
    row = Friendship(
        user_id_a=_uuid.UUID(uid_a_str),
        user_id_b=_uuid.UUID(uid_b_str),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# create_friendship tests
# ---------------------------------------------------------------------------


def test_create_friendship_success(db_session: Session) -> None:
    """Insert row in canonical order (user_id_a < user_id_b)."""
    initiator = _make_user(db_session, firebase_uid="uid-A")
    scanner = _make_user(db_session, firebase_uid="uid-B")

    friendship = create_friendship(
        db_session,
        initiator_id=str(initiator.id),
        scanner_id=str(scanner.id),
    )

    assert friendship.id is not None
    assert str(friendship.user_id_a) < str(friendship.user_id_b)


def test_create_self_friend(db_session: Session) -> None:
    """Initiator == Scanner raises SelfFriendError."""
    user = _make_user(db_session, firebase_uid="uid-self")

    with pytest.raises(SelfFriendError):
        create_friendship(
            db_session,
            initiator_id=str(user.id),
            scanner_id=str(user.id),
        )


def test_create_already_friends(db_session: Session) -> None:
    """Duplicate pair raises AlreadyFriendsError."""
    a = _make_user(db_session, firebase_uid="uid-dup-A")
    b = _make_user(db_session, firebase_uid="uid-dup-B")
    _make_friendship(db_session, a, b)

    with pytest.raises(AlreadyFriendsError):
        create_friendship(
            db_session,
            initiator_id=str(a.id),
            scanner_id=str(b.id),
        )


def test_create_initiator_at_limit(db_session: Session) -> None:
    """Initiator already has 20 friends → FriendLimitError."""
    initiator = _make_user(db_session, firebase_uid="uid-init-limit")

    for i in range(FRIEND_LIMIT):
        other = _make_user(db_session, firebase_uid=f"uid-other-{i}")
        _make_friendship(db_session, initiator, other)

    scanner = _make_user(db_session, firebase_uid="uid-scanner-new")

    with pytest.raises(FriendLimitError):
        create_friendship(
            db_session,
            initiator_id=str(initiator.id),
            scanner_id=str(scanner.id),
        )


def test_create_scanner_at_limit(db_session: Session) -> None:
    """Scanner already has 20 friends → FriendLimitError."""
    scanner = _make_user(db_session, firebase_uid="uid-scanner-limit")

    for i in range(FRIEND_LIMIT):
        other = _make_user(db_session, firebase_uid=f"uid-sc-other-{i}")
        _make_friendship(db_session, scanner, other)

    initiator = _make_user(db_session, firebase_uid="uid-init-new")

    with pytest.raises(FriendLimitError):
        create_friendship(
            db_session,
            initiator_id=str(initiator.id),
            scanner_id=str(scanner.id),
        )


# ---------------------------------------------------------------------------
# list_friends tests
# ---------------------------------------------------------------------------


def test_list_friends_empty(db_session: Session) -> None:
    """User with no friends returns empty list."""
    user = _make_user(db_session, firebase_uid="uid-lonely")
    result = list_friends(db_session, str(user.id))
    assert result == []


def test_list_friends_bidirectional(db_session: Session) -> None:
    """Both users see each other; result contains user_id, display_name,
    avatar_url, friendship_created_at."""
    a = _make_user(db_session, firebase_uid="uid-bi-A")
    b = _make_user(db_session, firebase_uid="uid-bi-B")
    _make_friendship(db_session, a, b)

    a_friends = list_friends(db_session, str(a.id))
    b_friends = list_friends(db_session, str(b.id))

    assert len(a_friends) == 1
    assert str(a_friends[0]["user_id"]) == str(b.id)
    assert "display_name" in a_friends[0]
    assert "avatar_url" in a_friends[0]
    assert "friendship_created_at" in a_friends[0]

    assert len(b_friends) == 1
    assert str(b_friends[0]["user_id"]) == str(a.id)


# ---------------------------------------------------------------------------
# delete_friendship tests
# ---------------------------------------------------------------------------


def test_delete_friendship(db_session: Session) -> None:
    """Deleting a friendship removes the row; second call is idempotent."""
    a = _make_user(db_session, firebase_uid="uid-del-A")
    b = _make_user(db_session, firebase_uid="uid-del-B")
    _make_friendship(db_session, a, b)

    delete_friendship(db_session, str(a.id), str(b.id))

    assert list_friends(db_session, str(a.id)) == []

    # Idempotent: no exception on second call
    delete_friendship(db_session, str(a.id), str(b.id))
