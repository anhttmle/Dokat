"""Integration tests for F09 notification flow.

Tests that span the full stack: post creation → FCM push, and
preference toggle → reminder suppression.

Uses SQLite in-memory + mocked Firebase Admin SDK + FastAPI TestClient.

Refs: Design §6.9; AC-F09-1, AC-F09-5; FR-7; DL-F09-04
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.block import BlockedUser
from app.models.friendship import Friendship
from app.models.notification_pref import (  # noqa: F401
    NotificationPreference,
    ReminderType,
)
from app.models.pet_profile import PetProfile, PetSpecies
from app.models.user import Base, User
from app.reminder_scheduler import ReminderEntry, run_reminder_job
from app.routers.auth import get_db
from app.services import notification_pref_service

_HEADERS = {"Authorization": "Bearer fake-token"}
_UID = "test-uid-anonymous"


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


@pytest.fixture()
def client(
    db_session: Session, mock_verify_id_token: MagicMock
) -> TestClient:
    """TestClient with DB overridden and Firebase token mocked."""
    db_session.add(User(firebase_uid=_UID, is_anonymous=True))
    db_session.commit()
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _make_friend(
    db: Session, sender: User, fcm_token: str | None = "tok"
) -> User:
    friend = User(
        firebase_uid=str(uuid.uuid4()),
        is_anonymous=True,
        fcm_token=fcm_token,
    )
    db.add(friend)
    db.flush()
    db.add(
        Friendship(user_id_a=sender.id, user_id_b=friend.id)
    )
    db.commit()
    return friend


def _get_sender(db: Session) -> User:
    return db.query(User).filter(User.firebase_uid == _UID).first()


@patch("firebase_admin.messaging.send", return_value="msg-id")
def test_new_photo_push_sent_to_recipients(
    mock_send: MagicMock,
    client: TestClient,
    db_session: Session,
) -> None:
    """POST /posts with N friends → FCM mock receives N calls (AC-F09-1)."""
    sender = _get_sender(db_session)
    f1 = _make_friend(db_session, sender, fcm_token="t1")
    f2 = _make_friend(db_session, sender, fcm_token="t2")

    resp = client.post(
        "/posts",
        json={
            "s3_key": "key/img.jpg",
            "cdn_url": "https://cdn/img.jpg",
            "recipient_ids": [str(f1.id), str(f2.id)],
        },
        headers=_HEADERS,
    )

    assert resp.status_code in (200, 201), resp.text
    assert mock_send.call_count == 2


@patch("firebase_admin.messaging.send", return_value="msg-id")
def test_new_photo_no_push_zero_recipients(
    mock_send: MagicMock,
    client: TestClient,
    db_session: Session,
) -> None:
    """POST /posts with 0 recipients → FCM not called (FR-7)."""
    resp = client.post(
        "/posts",
        json={
            "s3_key": "key/img.jpg",
            "cdn_url": "https://cdn/img.jpg",
            "recipient_ids": [],
        },
        headers=_HEADERS,
    )

    assert resp.status_code in (200, 201), resp.text
    mock_send.assert_not_called()


@patch("firebase_admin.messaging.send", return_value="msg-id")
def test_new_photo_blocked_recipient_skipped(
    mock_send: MagicMock,
    client: TestClient,
    db_session: Session,
) -> None:
    """Sender blocks recipient → FCM not sent to that recipient."""
    sender = _get_sender(db_session)
    blocked_friend = _make_friend(db_session, sender, fcm_token="t1")

    db_session.add(
        BlockedUser(
            blocker_id=sender.id, blocked_id=blocked_friend.id
        )
    )
    db_session.commit()

    resp = client.post(
        "/posts",
        json={
            "s3_key": "key/img.jpg",
            "cdn_url": "https://cdn/img.jpg",
            "recipient_ids": [str(blocked_friend.id)],
        },
        headers=_HEADERS,
    )

    assert resp.status_code in (200, 201), resp.text
    mock_send.assert_not_called()


def test_preference_toggle_affects_reminder_job(
    db_session: Session,
) -> None:
    """Set bathing=False → reminder job skips bathing for that user."""
    user = User(
        firebase_uid=str(uuid.uuid4()),
        is_anonymous=True,
        fcm_token="t1",
        timezone="UTC",
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        PetProfile(
            user_id=user.id,
            name="Mochi",
            species=PetSpecies.dog,
        )
    )
    db_session.commit()

    notification_pref_service.set_preference(
        db_session, user.id, ReminderType.bathing, False
    )

    entries = [
        ReminderEntry(
            species="dog",
            reminder_type=ReminderType.bathing,
            hour=10,
            minute=0,
        )
    ]
    now_utc = datetime(2026, 6, 22, 10, 0, 0, tzinfo=UTC)

    with patch(
        "app.services.notification_service.NotificationService.send_reminder"
    ) as mock_send:
        run_reminder_job(
            lambda: db_session, entries, now_utc=now_utc
        )

    mock_send.assert_not_called()
