"""Tests for reminder_scheduler — load_reminders + run_reminder_job.

Uses SQLite in-memory + mocked notification_service.send_reminder.

Refs: Design §6.5; AC-F09-3, AC-F09-5, AC-F09-6; DL-F09-05
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.notification_pref import (  # noqa: F401
    NotificationPreference,
    ReminderType,
)
from app.models.pet_profile import PetProfile, PetSpecies
from app.models.user import Base, User
from app.reminder_scheduler import ReminderEntry, load_reminders, run_reminder_job
from app.services import notification_pref_service

_VALID_YAML = """\
reminders:
  dog:
    - type: feeding
      hour: 7
      minute: 0
    - type: sleeping
      hour: 22
      minute: 0
  cat:
    - type: playing
      hour: 16
      minute: 0
"""

_INVALID_YAML = """\
reminders:
  dog:
    - type: unknown_type
      hour: 7
      minute: 0
"""


@pytest.fixture()
def db_session() -> Session:
    """SQLite in-memory session per test."""
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


def _write_yaml(tmp_path: Path, content: str) -> str:
    p = tmp_path / "reminders.yaml"
    p.write_text(content, encoding="utf-8")
    return str(p)


def _make_user_with_dog(
    db: Session,
    *,
    timezone: str | None = "Asia/Ho_Chi_Minh",
    fcm_token: str | None = "token-abc",
    pet_name: str = "Rex",
) -> tuple[User, PetProfile]:
    user = User(
        firebase_uid=str(uuid.uuid4()),
        is_anonymous=True,
        fcm_token=fcm_token,
        timezone=timezone,
    )
    db.add(user)
    db.flush()
    pet = PetProfile(
        user_id=user.id,
        name=pet_name,
        species=PetSpecies.dog,
    )
    db.add(pet)
    db.commit()
    return user, pet


def test_load_reminders_yaml_valid(tmp_path: Path) -> None:
    """Valid YAML → list of ReminderEntry with correct fields."""
    path = _write_yaml(tmp_path, _VALID_YAML)
    entries = load_reminders(path)
    assert len(entries) == 3
    types = {e.reminder_type for e in entries}
    assert ReminderType.feeding in types
    assert ReminderType.sleeping in types
    species = {e.species for e in entries}
    assert "dog" in species
    assert "cat" in species


def test_load_reminders_yaml_invalid_type(tmp_path: Path) -> None:
    """Unknown type in YAML → ValueError raised."""
    path = _write_yaml(tmp_path, _INVALID_YAML)
    with pytest.raises(ValueError, match="Invalid reminder type"):
        load_reminders(path)


def test_job_sends_to_matching_timezone_user(
    tmp_path: Path, db_session: Session
) -> None:
    """User whose local time matches the entry → send_reminder called."""
    user, pet = _make_user_with_dog(
        db_session, timezone="UTC", fcm_token="t1"
    )
    entries = [
        ReminderEntry(
            species="dog",
            reminder_type=ReminderType.feeding,
            hour=7,
            minute=0,
        )
    ]
    now_utc = datetime(2026, 6, 22, 7, 0, 0, tzinfo=UTC)

    with patch(
        "app.services.notification_service.NotificationService.send_reminder"
    ) as mock_send:
        run_reminder_job(lambda: db_session, entries, now_utc=now_utc)

    mock_send.assert_called_once()


def test_job_skips_non_matching_timezone(
    tmp_path: Path, db_session: Session
) -> None:
    """User's local time does not match the entry → not called."""
    user, pet = _make_user_with_dog(
        db_session, timezone="UTC", fcm_token="t1"
    )
    entries = [
        ReminderEntry(
            species="dog",
            reminder_type=ReminderType.feeding,
            hour=7,
            minute=0,
        )
    ]
    now_utc = datetime(2026, 6, 22, 8, 0, 0, tzinfo=UTC)

    with patch(
        "app.services.notification_service.NotificationService.send_reminder"
    ) as mock_send:
        run_reminder_job(lambda: db_session, entries, now_utc=now_utc)

    mock_send.assert_not_called()


def test_job_skips_disabled_preference(
    db_session: Session,
) -> None:
    """User has feeding=False → send_reminder not called (AC-F09-5)."""
    user, pet = _make_user_with_dog(
        db_session, timezone="UTC", fcm_token="t1"
    )
    notification_pref_service.set_preference(
        db_session, user.id, ReminderType.feeding, False
    )
    entries = [
        ReminderEntry(
            species="dog",
            reminder_type=ReminderType.feeding,
            hour=7,
            minute=0,
        )
    ]
    now_utc = datetime(2026, 6, 22, 7, 0, 0, tzinfo=UTC)

    with patch(
        "app.services.notification_service.NotificationService.send_reminder"
    ) as mock_send:
        run_reminder_job(lambda: db_session, entries, now_utc=now_utc)

    mock_send.assert_not_called()


def test_job_skips_null_timezone_user(db_session: Session) -> None:
    """User with timezone=NULL → skipped entirely."""
    user, pet = _make_user_with_dog(
        db_session, timezone=None, fcm_token="t1"
    )
    entries = [
        ReminderEntry(
            species="dog",
            reminder_type=ReminderType.feeding,
            hour=7,
            minute=0,
        )
    ]
    now_utc = datetime(2026, 6, 22, 7, 0, 0, tzinfo=UTC)

    with patch(
        "app.services.notification_service.NotificationService.send_reminder"
    ) as mock_send:
        run_reminder_job(lambda: db_session, entries, now_utc=now_utc)

    mock_send.assert_not_called()


def test_job_skips_null_fcm_token(db_session: Session) -> None:
    """User with fcm_token=NULL → query filters them out."""
    user, pet = _make_user_with_dog(
        db_session, timezone="UTC", fcm_token=None
    )
    entries = [
        ReminderEntry(
            species="dog",
            reminder_type=ReminderType.feeding,
            hour=7,
            minute=0,
        )
    ]
    now_utc = datetime(2026, 6, 22, 7, 0, 0, tzinfo=UTC)

    with patch(
        "app.services.notification_service.NotificationService.send_reminder"
    ) as mock_send:
        run_reminder_job(lambda: db_session, entries, now_utc=now_utc)

    mock_send.assert_not_called()
