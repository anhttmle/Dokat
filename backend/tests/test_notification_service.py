"""Tests for NotificationService — send_new_photo and send_reminder.

Uses mocked Firebase Admin SDK + SQLite in-memory.

Refs: Design §6.3; AC-F09-1, AC-F09-2, AC-F09-3; DL-F09-01,
DL-F09-04
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.block import BlockedUser
from app.models.notification_pref import (  # noqa: F401
    NotificationPreference,
)
from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import Base, User
from app.services.notification_service import NotificationService


@pytest.fixture()
def db() -> Session:
    """SQLite in-memory session."""
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
    fcm_token: str | None = "token-abc",
) -> User:
    user = User(firebase_uid=str(uuid.uuid4()), is_anonymous=True)
    user.fcm_token = fcm_token
    db.add(user)
    db.flush()
    return user


def _make_post(
    db: Session, sender: User, cdn_url: str = "https://cdn/img.jpg"
) -> Post:
    now = datetime.now(UTC)
    post = Post(
        user_id=sender.id,
        s3_key="key/img.jpg",
        cdn_url=cdn_url,
        expires_at=now + timedelta(hours=24),
        created_at=now,
    )
    db.add(post)
    db.flush()
    return post


def _add_recipient(db: Session, post: Post, recipient: User) -> None:
    db.add(PostRecipient(post_id=post.id, recipient_id=recipient.id))
    db.flush()


def _add_block(
    db: Session, blocker: User, blocked: User
) -> None:
    db.add(BlockedUser(blocker_id=blocker.id, blocked_id=blocked.id))
    db.flush()


@patch("firebase_admin.messaging.send", return_value="msg-id")
def test_send_new_photo_calls_fcm_per_recipient(
    mock_send: MagicMock, db: Session
) -> None:
    """N recipients with valid tokens → N FCM sends (AC-F09-1)."""
    sender = _make_user(db)
    r1 = _make_user(db, fcm_token="t1")
    r2 = _make_user(db, fcm_token="t2")
    post = _make_post(db, sender)
    _add_recipient(db, post, r1)
    _add_recipient(db, post, r2)
    db.commit()

    NotificationService(db).send_new_photo(post, db)

    assert mock_send.call_count == 2


@patch("firebase_admin.messaging.send", return_value="msg-id")
def test_send_new_photo_skips_null_token(
    mock_send: MagicMock, db: Session
) -> None:
    """Recipient with fcm_token=NULL → FCM not called."""
    sender = _make_user(db)
    r1 = _make_user(db, fcm_token=None)
    post = _make_post(db, sender)
    _add_recipient(db, post, r1)
    db.commit()

    NotificationService(db).send_new_photo(post, db)

    mock_send.assert_not_called()


@patch("firebase_admin.messaging.send", return_value="msg-id")
def test_send_new_photo_skips_blocked(
    mock_send: MagicMock, db: Session
) -> None:
    """Recipient blocked by sender → FCM not called (DL-F09-04)."""
    sender = _make_user(db)
    r1 = _make_user(db, fcm_token="t1")
    _add_block(db, sender, r1)
    post = _make_post(db, sender)
    _add_recipient(db, post, r1)
    db.commit()

    NotificationService(db).send_new_photo(post, db)

    mock_send.assert_not_called()


@patch(
    "firebase_admin.messaging.send",
    side_effect=Exception("FCM down"),
)
def test_send_new_photo_fcm_error_no_raise(
    mock_send: MagicMock, db: Session
) -> None:
    """FCM error → warning logged, no exception raised (best-effort)."""
    sender = _make_user(db)
    r1 = _make_user(db, fcm_token="t1")
    post = _make_post(db, sender)
    _add_recipient(db, post, r1)
    db.commit()

    NotificationService(db).send_new_photo(post, db)


@patch("firebase_admin.messaging.send", return_value="msg-id")
def test_send_reminder_calls_fcm(
    mock_send: MagicMock, db: Session
) -> None:
    """send_reminder calls FCM with correct title/body (AC-F09-3)."""
    from app.models.notification_pref import ReminderType

    user = _make_user(db, fcm_token="t1")
    db.commit()

    NotificationService(db).send_reminder(
        user, "Mochi", ReminderType.bathing
    )

    assert mock_send.call_count == 1
    msg = mock_send.call_args[0][0]
    assert msg.notification.title == "Nhắc nhở thú cưng"
    assert "Mochi" in msg.notification.body
    assert "tắm" in msg.notification.body


@patch(
    "firebase_admin.messaging.send",
    side_effect=Exception("FCM down"),
)
def test_send_reminder_fcm_error_no_raise(
    mock_send: MagicMock, db: Session
) -> None:
    """FCM error in send_reminder → warning logged, no raise."""
    from app.models.notification_pref import ReminderType

    user = _make_user(db, fcm_token="t1")
    db.commit()

    NotificationService(db).send_reminder(
        user, "Mochi", ReminderType.bathing
    )
