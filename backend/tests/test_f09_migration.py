"""Migration schema tests for F09: users.timezone and notification_preferences.

Approach: SQLite in-memory via ``Base.metadata.create_all()``.
Mirrors the pattern from ``tests/migrations/test_friendships_migration.py``.

Refs: Design §6.1; DL-F09-02, DL-F09-06
"""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from app.models.notification_pref import (  # noqa: F401 — registers model
    NotificationPreference,
)
from app.models.user import Base


@pytest.fixture()
def db_engine():
    """SQLite in-memory engine with all ORM tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_users_timezone_column(db_engine):
    """users.timezone must exist and be nullable."""
    cols = {
        c["name"]: c
        for c in inspect(db_engine).get_columns("users")
    }
    assert "timezone" in cols, "users.timezone column is missing"
    assert cols["timezone"]["nullable"], (
        "users.timezone must be nullable"
    )


def test_notif_pref_table_exists(db_engine):
    """notification_preferences table must exist after metadata create."""
    tables = inspect(db_engine).get_table_names()
    assert "notification_preferences" in tables


def test_notif_pref_columns(db_engine):
    """notification_preferences must have the required columns."""
    cols = {
        c["name"]
        for c in inspect(db_engine).get_columns(
            "notification_preferences"
        )
    }
    required = {"id", "user_id", "reminder_type", "enabled", "updated_at"}
    assert required <= cols, (
        f"Missing columns: {required - cols}"
    )


def test_notif_pref_unique_pair(db_engine):
    """UNIQUE constraint notif_pref_unique_pair must be present."""
    uqs = inspect(db_engine).get_unique_constraints(
        "notification_preferences"
    )
    names = {uq["name"] for uq in uqs}
    assert "notif_pref_unique_pair" in names, (
        "Unique constraint notif_pref_unique_pair is missing"
    )
