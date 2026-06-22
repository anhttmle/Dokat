"""Unit tests for feed_service.get_feed (F06).

Uses a SQLite in-memory DB seeded with users, posts, recipients and
pet_profiles (mirrors test_service_post.py). F06 is read-only, so tests
seed F05 data directly and assert the read result.

Refs: Design §6.1; FR-2, FR-3, FR-4, FR-6, FR-10;
AC-F06-1, AC-F06-2, AC-F06-4, AC-F06-6;
DL-F06-01, DL-F06-03, DL-F06-04, DL-F06-09
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.pet_profile import PetGender, PetProfile, PetSpecies
from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import Base, User
from app.services import feed_service
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


def _make_user(db: Session, *, firebase_uid: str, name: str | None) -> User:
    """Insert and return a User row with an optional display name."""
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


def _add_pet(db: Session, *, owner: User, name: str) -> None:
    """Insert a pet profile for *owner*."""
    db.add(
        PetProfile(
            user_id=owner.id,
            name=name,
            species=PetSpecies.cat,
            gender=PetGender.unknown,
        )
    )
    db.commit()


def test_feed_returns_received_posts(db_session: Session) -> None:
    """Viewer sees posts addressed to them; non-recipients do not (FR-2)."""
    sender = _make_user(db_session, firebase_uid="s", name="Sender")
    viewer = _make_user(db_session, firebase_uid="v", name="Viewer")
    other = _make_user(db_session, firebase_uid="o", name="Other")

    now = datetime.now(UTC)
    post = _make_post(db_session, sender=sender, created_at=now)
    _add_recipient(db_session, post=post, recipient=viewer)

    items, _ = get_feed(db_session, viewer_id=str(viewer.id))
    assert [i["post_id"] for i in items] == [str(post.id)]

    other_items, _ = get_feed(db_session, viewer_id=str(other.id))
    assert other_items == []


def test_feed_orders_newest_first(db_session: Session) -> None:
    """Items are ordered created_at DESC (AC-F06-1, AC-F06-6)."""
    sender = _make_user(db_session, firebase_uid="s", name="Sender")
    viewer = _make_user(db_session, firebase_uid="v", name="Viewer")

    now = datetime.now(UTC)
    older = _make_post(
        db_session, sender=sender, created_at=now - timedelta(minutes=5)
    )
    newer = _make_post(db_session, sender=sender, created_at=now)
    _add_recipient(db_session, post=older, recipient=viewer)
    _add_recipient(db_session, post=newer, recipient=viewer)

    items, _ = get_feed(db_session, viewer_id=str(viewer.id))
    assert [i["post_id"] for i in items] == [
        str(newer.id),
        str(older.id),
    ]


def test_feed_excludes_expired(db_session: Session) -> None:
    """Posts with expires_at <= now() are hidden (FR-3, AC-F06-2)."""
    sender = _make_user(db_session, firebase_uid="s", name="Sender")
    viewer = _make_user(db_session, firebase_uid="v", name="Viewer")

    now = datetime.now(UTC)
    expired = _make_post(
        db_session,
        sender=sender,
        created_at=now - timedelta(hours=25),
        expires_at=now - timedelta(hours=1),
    )
    live = _make_post(db_session, sender=sender, created_at=now)
    _add_recipient(db_session, post=expired, recipient=viewer)
    _add_recipient(db_session, post=live, recipient=viewer)

    items, _ = get_feed(db_session, viewer_id=str(viewer.id))
    assert [i["post_id"] for i in items] == [str(live.id)]


def test_feed_seen_flag(db_session: Session) -> None:
    """seen_at null → seen=False; set → seen=True (FR-6, DL-F06-09)."""
    sender = _make_user(db_session, firebase_uid="s", name="Sender")
    viewer = _make_user(db_session, firebase_uid="v", name="Viewer")

    now = datetime.now(UTC)
    unseen = _make_post(db_session, sender=sender, created_at=now)
    seen = _make_post(
        db_session, sender=sender, created_at=now - timedelta(minutes=1)
    )
    _add_recipient(db_session, post=unseen, recipient=viewer)
    _add_recipient(db_session, post=seen, recipient=viewer, seen_at=now)

    items, _ = get_feed(db_session, viewer_id=str(viewer.id))
    flags = {i["post_id"]: i["seen"] for i in items}
    assert flags[str(unseen.id)] is False
    assert flags[str(seen.id)] is True


def test_feed_includes_sender_and_pet(db_session: Session) -> None:
    """Item carries sender display name and pet name (FR-4)."""
    sender = _make_user(db_session, firebase_uid="s", name="Anh")
    viewer = _make_user(db_session, firebase_uid="v", name="Viewer")
    _add_pet(db_session, owner=sender, name="Mướp")

    now = datetime.now(UTC)
    post = _make_post(db_session, sender=sender, created_at=now)
    _add_recipient(db_session, post=post, recipient=viewer)

    items, _ = get_feed(db_session, viewer_id=str(viewer.id))
    assert items[0]["sender_display_name"] == "Anh"
    assert items[0]["pet_name"] == "Mướp"


def test_feed_pet_name_null_when_no_pet(db_session: Session) -> None:
    """Sender without a pet → pet_name is None (FR-4)."""
    sender = _make_user(db_session, firebase_uid="s", name="Anh")
    viewer = _make_user(db_session, firebase_uid="v", name="Viewer")

    now = datetime.now(UTC)
    post = _make_post(db_session, sender=sender, created_at=now)
    _add_recipient(db_session, post=post, recipient=viewer)

    items, _ = get_feed(db_session, viewer_id=str(viewer.id))
    assert items[0]["pet_name"] is None


def test_feed_empty_when_no_received(db_session: Session) -> None:
    """Viewer with no received posts → empty list (AC-F06-4)."""
    viewer = _make_user(db_session, firebase_uid="v", name="Viewer")
    items, next_cursor = get_feed(db_session, viewer_id=str(viewer.id))
    assert items == []
    assert next_cursor is None


def test_feed_excludes_blocked_sender(db_session: Session) -> None:
    """Senders from _blocked_sender_ids are excluded (FR-10)."""
    sender = _make_user(db_session, firebase_uid="s", name="Sender")
    viewer = _make_user(db_session, firebase_uid="v", name="Viewer")

    now = datetime.now(UTC)
    post = _make_post(db_session, sender=sender, created_at=now)
    _add_recipient(db_session, post=post, recipient=viewer)

    with patch.object(
        feed_service,
        "_blocked_sender_ids",
        return_value={sender.id},
    ):
        items, _ = get_feed(db_session, viewer_id=str(viewer.id))
    assert items == []
