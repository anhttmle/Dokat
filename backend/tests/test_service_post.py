"""Unit tests for post_service.create_post (F05).

Uses SQLite in-memory DB seeded with users and friendships so no
PostgreSQL instance is needed (mirrors test_service_friend.py).

Refs: Design §6.2; FR-5, FR-6, FR-7, FR-11;
AC-F05-2, AC-F05-3, AC-F05-4; DL-F05-03, DL-F05-07; F11 AC-F11-1/2
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.friendship import Friendship
from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import Base, User
from app.services.post_service import (
    POST_EXPIRY_HOURS,
    InvalidRecipientError,
    create_post,
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


def _make_user(db: Session, *, firebase_uid: str) -> User:
    """Insert and return a minimal User row."""
    now = datetime.now(UTC)
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


def _make_friendship(db: Session, a: User, b: User) -> None:
    """Insert a canonical friendship edge between two users."""
    uid_a, uid_b = sorted([str(a.id), str(b.id)])
    db.add(
        Friendship(
            user_id_a=uuid.UUID(uid_a),
            user_id_b=uuid.UUID(uid_b),
        )
    )
    db.commit()


def _seed(db: Session, friend_count: int) -> tuple[User, list[User]]:
    """Create a sender plus *friend_count* befriended users."""
    sender = _make_user(db, firebase_uid="sender")
    friends = []
    for i in range(friend_count):
        friend = _make_user(db, firebase_uid=f"friend-{i}")
        _make_friendship(db, sender, friend)
        friends.append(friend)
    return sender, friends


def test_create_post_sets_expiry_24h(db_session: Session) -> None:
    """expires_at must be roughly created_at + 24h (DL-F05-03)."""
    sender, _ = _seed(db_session, 0)
    post, _ = create_post(
        db_session,
        user_id=str(sender.id),
        s3_key="posts/x/1.jpg",
        cdn_url="https://cdn/x/1.jpg",
        recipient_ids=[],
    )
    delta = post.expires_at - post.created_at
    assert abs(delta.total_seconds() - POST_EXPIRY_HOURS * 3600) < 5


def test_create_post_inserts_recipients(db_session: Session) -> None:
    """N friends → N post_recipients rows (FR-6, AC-F05-2)."""
    sender, friends = _seed(db_session, 3)
    post, count = create_post(
        db_session,
        user_id=str(sender.id),
        s3_key="k",
        cdn_url="u",
        recipient_ids=[str(f.id) for f in friends],
    )
    assert count == 3
    rows = (
        db_session.query(PostRecipient)
        .filter(PostRecipient.post_id == post.id)
        .all()
    )
    assert len(rows) == 3


def test_create_post_subset(db_session: Session) -> None:
    """Only the chosen subset gets recipient rows (AC-F05-3)."""
    sender, friends = _seed(db_session, 4)
    subset = [str(friends[0].id), str(friends[1].id)]
    post, count = create_post(
        db_session,
        user_id=str(sender.id),
        s3_key="k",
        cdn_url="u",
        recipient_ids=subset,
    )
    assert count == 2
    stored = {
        str(r.recipient_id)
        for r in db_session.query(PostRecipient)
        .filter(PostRecipient.post_id == post.id)
        .all()
    }
    assert stored == set(subset)


def test_create_post_zero_recipients(db_session: Session) -> None:
    """0 recipients → post created, 0 recipient rows (FR-7, AC-F05-4)."""
    sender, _ = _seed(db_session, 2)
    post, count = create_post(
        db_session,
        user_id=str(sender.id),
        s3_key="k",
        cdn_url="u",
        recipient_ids=[],
    )
    assert count == 0
    assert db_session.query(Post).filter(Post.id == post.id).one()
    assert (
        db_session.query(PostRecipient)
        .filter(PostRecipient.post_id == post.id)
        .count()
        == 0
    )


def test_create_post_dedup_recipients(db_session: Session) -> None:
    """Duplicate recipient ids collapse to a single row."""
    sender, friends = _seed(db_session, 1)
    fid = str(friends[0].id)
    post, count = create_post(
        db_session,
        user_id=str(sender.id),
        s3_key="k",
        cdn_url="u",
        recipient_ids=[fid, fid, fid],
    )
    assert count == 1
    assert (
        db_session.query(PostRecipient)
        .filter(PostRecipient.post_id == post.id)
        .count()
        == 1
    )


def test_create_post_rejects_non_friend(db_session: Session) -> None:
    """A stranger recipient raises InvalidRecipientError (DL-F05-07)."""
    sender, _ = _seed(db_session, 0)
    stranger = _make_user(db_session, firebase_uid="stranger")
    with pytest.raises(InvalidRecipientError):
        create_post(
            db_session,
            user_id=str(sender.id),
            s3_key="k",
            cdn_url="u",
            recipient_ids=[str(stranger.id)],
        )
    # No post should have been persisted on the failure path.
    assert db_session.query(Post).count() == 0


def test_create_post_stores_latlng(db_session: Session) -> None:
    """lat/lng stored at 8-digit precision (F11 AC-F11-1)."""
    sender, _ = _seed(db_session, 0)
    post, _ = create_post(
        db_session,
        user_id=str(sender.id),
        s3_key="k",
        cdn_url="u",
        recipient_ids=[],
        latitude=10.77621500,
        longitude=106.69505800,
    )
    assert float(post.latitude) == pytest.approx(10.77621500)
    assert float(post.longitude) == pytest.approx(106.69505800)


def test_create_post_null_latlng(db_session: Session) -> None:
    """Missing lat/lng leaves the columns NULL (F11 AC-F11-2)."""
    sender, _ = _seed(db_session, 0)
    post, _ = create_post(
        db_session,
        user_id=str(sender.id),
        s3_key="k",
        cdn_url="u",
        recipient_ids=[],
    )
    assert post.latitude is None
    assert post.longitude is None
