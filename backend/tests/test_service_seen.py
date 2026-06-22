"""Unit tests for seen_service (F07).

Uses SQLite in-memory DB seeded with users, posts and post_recipients
so no PostgreSQL instance is needed (mirrors test_service_post.py).

Refs: Design §6.1; FR-1, FR-2, FR-3, FR-4, FR-6;
AC-F07-1, AC-F07-2, AC-F07-3;
DL-F07-01, DL-F07-02, DL-F07-03, DL-F07-04, DL-F07-08
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import Base, User
from app.services.seen_service import (
    NotRecipientError,
    NotSenderError,
    PostNotFoundError,
    get_seen_by,
    mark_seen,
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
    db: Session,
    *,
    firebase_uid: str,
    display_name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    """Insert and return a minimal User row."""
    now = datetime.now(UTC)
    user = User(
        firebase_uid=firebase_uid,
        is_anonymous=False,
        display_name=display_name,
        avatar_url=avatar_url,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_post(db: Session, sender: User) -> Post:
    """Insert and return a post owned by *sender*."""
    now = datetime.now(UTC)
    post = Post(
        user_id=sender.id,
        s3_key="k",
        cdn_url="u",
        expires_at=now + timedelta(hours=24),
        created_at=now,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def _add_recipient(
    db: Session,
    post: Post,
    user: User,
    *,
    seen_at: datetime | None = None,
) -> PostRecipient:
    """Insert a recipient edge, optionally pre-marked as seen."""
    edge = PostRecipient(
        post_id=post.id,
        recipient_id=user.id,
        seen_at=seen_at,
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


# --- mark_seen (Task 2) -------------------------------------------------


def test_mark_seen_sets_seen_at(db_session: Session) -> None:
    """Recipient marks seen → seen_at is set (FR-1, FR-2, AC-F07-1)."""
    sender = _make_user(db_session, firebase_uid="sender")
    viewer = _make_user(db_session, firebase_uid="viewer")
    post = _make_post(db_session, sender)
    _add_recipient(db_session, post, viewer)

    seen_at = mark_seen(
        db_session, post_id=str(post.id), viewer_id=str(viewer.id)
    )

    assert seen_at is not None
    edge = (
        db_session.query(PostRecipient)
        .filter(
            PostRecipient.post_id == post.id,
            PostRecipient.recipient_id == viewer.id,
        )
        .one()
    )
    assert edge.seen_at is not None


def test_mark_seen_idempotent(db_session: Session) -> None:
    """Second mark keeps the first seen_at (first-seen wins, DL-F07-02)."""
    sender = _make_user(db_session, firebase_uid="sender")
    viewer = _make_user(db_session, firebase_uid="viewer")
    post = _make_post(db_session, sender)
    _add_recipient(db_session, post, viewer)

    first = mark_seen(
        db_session, post_id=str(post.id), viewer_id=str(viewer.id)
    )
    second = mark_seen(
        db_session, post_id=str(post.id), viewer_id=str(viewer.id)
    )

    assert first == second


def test_mark_seen_non_recipient_raises(db_session: Session) -> None:
    """A non-recipient viewer raises NotRecipientError (DL-F07-03)."""
    sender = _make_user(db_session, firebase_uid="sender")
    stranger = _make_user(db_session, firebase_uid="stranger")
    post = _make_post(db_session, sender)

    with pytest.raises(NotRecipientError):
        mark_seen(db_session, post_id=str(post.id), viewer_id=str(stranger.id))


def test_mark_seen_post_not_found_raises(db_session: Session) -> None:
    """An unknown post raises PostNotFoundError."""
    viewer = _make_user(db_session, firebase_uid="viewer")

    with pytest.raises(PostNotFoundError):
        mark_seen(
            db_session,
            post_id=str(uuid.uuid4()),
            viewer_id=str(viewer.id),
        )


# --- get_seen_by (Task 3) ----------------------------------------------


def test_seen_by_lists_viewers(db_session: Session) -> None:
    """Returns seen recipients with name/avatar/seen_at (FR-3)."""
    sender = _make_user(db_session, firebase_uid="sender")
    viewer = _make_user(
        db_session,
        firebase_uid="viewer",
        display_name="Châu",
        avatar_url="https://cdn/a.jpg",
    )
    post = _make_post(db_session, sender)
    _add_recipient(db_session, post, viewer, seen_at=datetime.now(UTC))

    viewers, count = get_seen_by(
        db_session, post_id=str(post.id), viewer_id=str(sender.id)
    )

    assert count == 1
    assert viewers[0]["user_id"] == str(viewer.id)
    assert viewers[0]["display_name"] == "Châu"
    assert viewers[0]["avatar_url"] == "https://cdn/a.jpg"
    assert viewers[0]["seen_at"] is not None


def test_seen_by_count_aggregates(db_session: Session) -> None:
    """Multiple viewers → seen_count counts them all (FR-4)."""
    sender = _make_user(db_session, firebase_uid="sender")
    post = _make_post(db_session, sender)
    for i in range(3):
        viewer = _make_user(db_session, firebase_uid=f"viewer-{i}")
        _add_recipient(db_session, post, viewer, seen_at=datetime.now(UTC))

    _, count = get_seen_by(
        db_session, post_id=str(post.id), viewer_id=str(sender.id)
    )

    assert count == 3


def test_seen_by_excludes_unseen(db_session: Session) -> None:
    """A recipient who has not seen is not listed nor counted."""
    sender = _make_user(db_session, firebase_uid="sender")
    seen_user = _make_user(db_session, firebase_uid="seen")
    unseen_user = _make_user(db_session, firebase_uid="unseen")
    post = _make_post(db_session, sender)
    _add_recipient(db_session, post, seen_user, seen_at=datetime.now(UTC))
    _add_recipient(db_session, post, unseen_user)

    viewers, count = get_seen_by(
        db_session, post_id=str(post.id), viewer_id=str(sender.id)
    )

    ids = {v["user_id"] for v in viewers}
    assert count == 1
    assert str(seen_user.id) in ids
    assert str(unseen_user.id) not in ids


def test_seen_by_orders_recent_first(db_session: Session) -> None:
    """Viewers are sorted by seen_at descending."""
    sender = _make_user(db_session, firebase_uid="sender")
    earlier = _make_user(db_session, firebase_uid="earlier")
    later = _make_user(db_session, firebase_uid="later")
    post = _make_post(db_session, sender)
    base = datetime.now(UTC)
    _add_recipient(
        db_session, post, earlier, seen_at=base - timedelta(minutes=5)
    )
    _add_recipient(db_session, post, later, seen_at=base)

    viewers, _ = get_seen_by(
        db_session, post_id=str(post.id), viewer_id=str(sender.id)
    )

    assert [v["user_id"] for v in viewers] == [
        str(later.id),
        str(earlier.id),
    ]


def test_seen_by_not_sender_raises(db_session: Session) -> None:
    """A non-sender viewer raises NotSenderError (DL-F07-04)."""
    sender = _make_user(db_session, firebase_uid="sender")
    other = _make_user(db_session, firebase_uid="other")
    post = _make_post(db_session, sender)

    with pytest.raises(NotSenderError):
        get_seen_by(db_session, post_id=str(post.id), viewer_id=str(other.id))


def test_seen_by_empty_when_nobody_seen(db_session: Session) -> None:
    """Nobody seen → seen_count=0, viewers=[]."""
    sender = _make_user(db_session, firebase_uid="sender")
    viewer = _make_user(db_session, firebase_uid="viewer")
    post = _make_post(db_session, sender)
    _add_recipient(db_session, post, viewer)

    viewers, count = get_seen_by(
        db_session, post_id=str(post.id), viewer_id=str(sender.id)
    )

    assert count == 0
    assert viewers == []
