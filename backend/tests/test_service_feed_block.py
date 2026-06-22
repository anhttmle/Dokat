"""Tests for the feed_service block hook filled in by F10.

After F10, ``feed_service._blocked_sender_ids`` delegates to
``block_service.get_blocked_user_ids`` which returns a bidirectional
set, so a block hides photos in both directions (DL-F10-04) without
changing the feed query structure (DL-F06-03).

Refs: Design §0, §4.1, §6.4; FR-8; DL-F10-04; DL-F06-03
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.block import BlockedUser  # noqa: F401 — registers model
from app.models.friendship import Friendship
from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import Base, User
from app.services.block_service import block_user
from app.services.feed_service import get_feed


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
    """Insert a canonical friendship row directly."""
    import uuid

    uid_a, uid_b = sorted([str(a.id), str(b.id)])
    db.add(Friendship(user_id_a=uuid.UUID(uid_a), user_id_b=uuid.UUID(uid_b)))
    db.commit()


def _make_post_to(db: Session, *, sender: User, recipient: User) -> Post:
    """Create a live post from *sender* delivered to *recipient*."""
    now = datetime.now(UTC)
    post = Post(
        user_id=sender.id,
        s3_key=f"posts/{sender.id}.jpg",
        cdn_url=f"https://cdn/{sender.id}.jpg",
        expires_at=now + timedelta(hours=24),
        created_at=now,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    db.add(PostRecipient(post_id=post.id, recipient_id=recipient.id))
    db.commit()
    return post


def test_feed_excludes_blocked_sender(db_session: Session) -> None:
    """A blocks B → B's photo disappears from A's feed (FR-8)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")
    _make_friendship(db_session, a, b)
    post = _make_post_to(db_session, sender=b, recipient=a)

    # Sanity: before block, A sees B's post.
    items, _ = get_feed(db_session, viewer_id=str(a.id))
    assert [i["post_id"] for i in items] == [str(post.id)]

    block_user(db_session, blocker_id=str(a.id), blocked_id=str(b.id))

    items, _ = get_feed(db_session, viewer_id=str(a.id))
    assert items == []


def test_feed_excludes_when_blocked_by(db_session: Session) -> None:
    """B blocks A → B's photo still hidden from A's feed (DL-F10-04)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")
    _make_friendship(db_session, a, b)
    post = _make_post_to(db_session, sender=b, recipient=a)

    block_user(db_session, blocker_id=str(b.id), blocked_id=str(a.id))

    items, _ = get_feed(db_session, viewer_id=str(a.id))
    assert str(post.id) not in [i["post_id"] for i in items]
