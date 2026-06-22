"""Unit tests for history_service cursor pagination (F08).

SQLite in-memory; seeds a viewer with several sent/received posts at
distinct timestamps and walks pages via the opaque cursor reused from
feed_service (DL-F08-04).

Refs: Design §6.3; Technical Constraint (cursor pagination); DL-F08-04
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import Base, User
from app.services.history_service import (
    FEED_MAX_PAGE_SIZE,
    InvalidCursorError,
    get_received,
    get_sent,
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


def _seed_sent(db: Session, *, author: User, count: int) -> list[str]:
    """Create *count* authored posts; return ids newest→oldest."""
    base = datetime.now(UTC)
    ids: list[str] = []
    for i in range(count):
        post = Post(
            user_id=author.id,
            s3_key=f"posts/{i}.jpg",
            cdn_url=f"https://cdn/{i}.jpg",
            expires_at=base + timedelta(hours=24),
            created_at=base + timedelta(minutes=i),
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        ids.append(str(post.id))
    ids.reverse()  # newest first
    return ids


def _seed_received(
    db: Session, *, sender: User, viewer: User, count: int
) -> list[str]:
    """Create *count* received posts; return ids newest→oldest."""
    base = datetime.now(UTC)
    ids: list[str] = []
    for i in range(count):
        post = Post(
            user_id=sender.id,
            s3_key=f"posts/{i}.jpg",
            cdn_url=f"https://cdn/{i}.jpg",
            expires_at=base + timedelta(hours=24),
            created_at=base + timedelta(minutes=i),
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        db.add(PostRecipient(post_id=post.id, recipient_id=viewer.id))
        db.commit()
        ids.append(str(post.id))
    ids.reverse()  # newest first
    return ids


def test_sent_first_page_limit(db_session: Session) -> None:
    """limit=N → ≤ N items + a next_cursor while data remains."""
    author = _make_user(db_session, firebase_uid="a")
    _seed_sent(db_session, author=author, count=5)

    items, next_cursor = get_sent(
        db_session, viewer_id=str(author.id), limit=2
    )
    assert len(items) == 2
    assert next_cursor is not None


def test_sent_second_page_continues(db_session: Session) -> None:
    """Second page holds only older posts, no overlap (DL-F08-04)."""
    author = _make_user(db_session, firebase_uid="a")
    ordered = _seed_sent(db_session, author=author, count=5)

    page1, cursor1 = get_sent(db_session, viewer_id=str(author.id), limit=2)
    page2, _ = get_sent(
        db_session, viewer_id=str(author.id), limit=2, cursor=cursor1
    )

    ids1 = [i["post_id"] for i in page1]
    ids2 = [i["post_id"] for i in page2]
    assert ids1 == ordered[:2]
    assert ids2 == ordered[2:4]
    assert set(ids1).isdisjoint(ids2)


def test_received_invalid_cursor_raises(db_session: Session) -> None:
    """A malformed cursor raises InvalidCursorError (DL-F08-04)."""
    viewer = _make_user(db_session, firebase_uid="v")
    with pytest.raises(InvalidCursorError):
        get_received(
            db_session,
            viewer_id=str(viewer.id),
            cursor="not-a-valid-cursor!!!",
        )


def test_limit_clamped_to_max(db_session: Session) -> None:
    """limit > FEED_MAX_PAGE_SIZE is clamped, not rejected."""
    sender = _make_user(db_session, firebase_uid="s")
    viewer = _make_user(db_session, firebase_uid="v")
    _seed_received(db_session, sender=sender, viewer=viewer, count=3)

    items, _ = get_received(
        db_session,
        viewer_id=str(viewer.id),
        limit=FEED_MAX_PAGE_SIZE + 100,
    )
    # No crash; all 3 returned since the clamped page size exceeds count.
    assert len(items) == 3
