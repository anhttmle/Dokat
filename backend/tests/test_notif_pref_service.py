"""Tests for notification_pref_service — get/set preferences.

TDD: written before implementation per F09 task spec.

Refs: Design §6.2; AC-F09-4, AC-F09-5; DL-F09-06
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.notification_pref import (  # noqa: F401
    NotificationPreference,
    ReminderType,
)
from app.models.user import Base
from app.services import notification_pref_service


@pytest.fixture()
def db() -> Session:
    """SQLite in-memory session for service tests."""
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


def _user_id() -> uuid.UUID:
    return uuid.uuid4()


def test_get_prefs_no_rows_defaults_all_true(db: Session) -> None:
    """No rows in the table → all four types return True (AC-F09-4)."""
    uid = _user_id()
    prefs = notification_pref_service.get_preferences(db, uid)
    assert len(prefs) == 4
    assert all(prefs.values()), "All prefs should default to True"


def test_set_preference_creates_row(db: Session) -> None:
    """Upsert with no existing row creates a new row."""
    uid = _user_id()
    notification_pref_service.set_preference(
        db, uid, ReminderType.bathing, False
    )
    prefs = notification_pref_service.get_preferences(db, uid)
    assert prefs[ReminderType.bathing] is False
    assert prefs[ReminderType.feeding] is True


def test_set_preference_updates_existing(db: Session) -> None:
    """Upsert on existing row updates the enabled flag."""
    uid = _user_id()
    notification_pref_service.set_preference(
        db, uid, ReminderType.playing, False
    )
    notification_pref_service.set_preference(
        db, uid, ReminderType.playing, True
    )
    prefs = notification_pref_service.get_preferences(db, uid)
    assert prefs[ReminderType.playing] is True


def test_set_preference_idempotent(db: Session) -> None:
    """Setting the same value twice does not raise and result is stable."""
    uid = _user_id()
    notification_pref_service.set_preference(
        db, uid, ReminderType.sleeping, False
    )
    notification_pref_service.set_preference(
        db, uid, ReminderType.sleeping, False
    )
    prefs = notification_pref_service.get_preferences(db, uid)
    assert prefs[ReminderType.sleeping] is False


def test_get_prefs_mixed(db: Session) -> None:
    """One bathing=false row; remaining three types still return True."""
    uid = _user_id()
    notification_pref_service.set_preference(
        db, uid, ReminderType.bathing, False
    )
    prefs = notification_pref_service.get_preferences(db, uid)
    assert prefs[ReminderType.bathing] is False
    assert prefs[ReminderType.feeding] is True
    assert prefs[ReminderType.sleeping] is True
    assert prefs[ReminderType.playing] is True
