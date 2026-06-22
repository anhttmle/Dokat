"""Unit tests for history_service.get_sent (F08).

Uses a SQLite in-memory DB seeded with users, posts and recipients
(mirrors test_service_feed.py). F08 is read-only, so tests seed F05/F07
data directly and assert the read result.

Refs: Design §6.1; FR-2, FR-3, FR-4, FR-5;
AC-F08-1, AC-F08-4; DL-F08-01, DL-F08-03, DL-F08-05
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import Base, User
from app.services.history_service import get_sent


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
    """Insert and return a User row."""
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


def _make_post(
    db: Session,
    *,
    sender: User,
    created_at: datetime,
    expires_at: datetime | None = None,
) -> Post:
    """Insert and return a post for *sender* at *created_at*."""
    post = Post(
        user_id=sender.id,
        s3_key=f"posts/{sender.id}/{created_at.isoformat()}.jpg",
        cdn_url=f"https://cdn/{sender.id}.jpg",
        expires_at=expires_at or (created_at + timedelta(hours=24)),
        created_at=created_at,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def _add_recipient(
    db: Session,
    *,
    post: Post,
    recipient: User,
    seen_at: datetime | None = None,
) -> None:
    """Insert a recipient edge linking *post* to *recipient*."""
    db.add(
        PostRecipient(
            post_id=post.id,
            recipient_id=recipient.id,
            seen_at=seen_at,
        )
    )
    db.commit()


def test_sent_returns_authored_posts(db_session: Session) -> None:
    """Viewer sees own authored posts; others' posts do not (FR-2)."""
    author = _make_user(db_session, firebase_uid="a")
    other = _make_user(db_session, firebase_uid="o")

    now = datetime.now(UTC)
    mine = _make_post(db_session, sender=author, created_at=now)
    _make_post(db_session, sender=other, created_at=now)

    items, _ = get_sent(db_session, viewer_id=str(author.id))
    assert [i["post_id"] for i in items] == [str(mine.id)]


def test_sent_orders_newest_first(db_session: Session) -> None:
    """Items are ordered created_at DESC (FR-2, AC-F08-1)."""
    author = _make_user(db_session, firebase_uid="a")

    now = datetime.now(UTC)
    older = _make_post(
        db_session, sender=author, created_at=now - timedelta(minutes=5)
    )
    newer = _make_post(db_session, sender=author, created_at=now)

    items, _ = get_sent(db_session, viewer_id=str(author.id))
    assert [i["post_id"] for i in items] == [str(newer.id), str(older.id)]


def test_sent_excludes_expired(db_session: Session) -> None:
    """Posts with expires_at <= now() are hidden (FR-4, AC-F08-1)."""
    author = _make_user(db_session, firebase_uid="a")

    now = datetime.now(UTC)
    expired = _make_post(
        db_session,
        sender=author,
        created_at=now - timedelta(hours=25),
        expires_at=now - timedelta(hours=1),
    )
    live = _make_post(db_session, sender=author, created_at=now)

    items, _ = get_sent(db_session, viewer_id=str(author.id))
    ids = [i["post_id"] for i in items]
    assert str(live.id) in ids
    assert str(expired.id) not in ids


def test_sent_counts_recipients_and_seen(db_session: Session) -> None:
    """recipient_count/seen_count are correct (FR-3, FR-5, DL-F08-05)."""
    author = _make_user(db_session, firebase_uid="a")
    r1 = _make_user(db_session, firebase_uid="r1")
    r2 = _make_user(db_session, firebase_uid="r2")
    r3 = _make_user(db_session, firebase_uid="r3")

    now = datetime.now(UTC)
    post = _make_post(db_session, sender=author, created_at=now)
    _add_recipient(db_session, post=post, recipient=r1, seen_at=now)
    _add_recipient(db_session, post=post, recipient=r2, seen_at=now)
    _add_recipient(db_session, post=post, recipient=r3)

    items, _ = get_sent(db_session, viewer_id=str(author.id))
    assert items[0]["recipient_count"] == 3
    assert items[0]["seen_count"] == 2


def test_sent_zero_recipients(db_session: Session) -> None:
    """A post with no recipients returns counts of 0 but is shown."""
    author = _make_user(db_session, firebase_uid="a")

    now = datetime.now(UTC)
    post = _make_post(db_session, sender=author, created_at=now)

    items, _ = get_sent(db_session, viewer_id=str(author.id))
    assert [i["post_id"] for i in items] == [str(post.id)]
    assert items[0]["recipient_count"] == 0
    assert items[0]["seen_count"] == 0


def test_sent_empty_when_none(db_session: Session) -> None:
    """Viewer with no authored posts → empty list (AC-F08-4)."""
    author = _make_user(db_session, firebase_uid="a")
    items, next_cursor = get_sent(db_session, viewer_id=str(author.id))
    assert items == []
    assert next_cursor is None
