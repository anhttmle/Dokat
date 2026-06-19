"""Unit tests for the users table migration schema.

These tests verify the schema contract defined in design §2.1:
- The `users` table exists and is queryable after table creation.
- The `firebase_uid` column has a UNIQUE constraint.

Approach: use SQLite in-memory via Base.metadata.create_all() to test
the schema without requiring a running PostgreSQL instance.
See decision_log DL-006 for rationale.
"""

import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.models.user import Base


@pytest.fixture
def db_engine():
    """SQLite in-memory engine with all ORM tables created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_users_table_exists(db_engine):
    """SELECT 1 FROM users LIMIT 1 must not raise after table creation."""
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM users LIMIT 1"))
        assert result is not None


def test_firebase_uid_unique_constraint(db_engine):
    """Insert two rows with the same firebase_uid must raise IntegrityError."""
    firebase_uid = "firebase_uid_duplicate_test"

    with db_engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO users "
                "(id, firebase_uid, is_anonymous, created_at, updated_at) "
                "VALUES (:id, :fuid, 1, datetime('now'), datetime('now'))"
            ),
            {"id": str(uuid.uuid4()), "fuid": firebase_uid},
        )
        conn.commit()

    with pytest.raises(IntegrityError):
        with db_engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users "
                    "(id, firebase_uid, is_anonymous, created_at, updated_at)"
                    " VALUES (:id, :fuid, 1, datetime('now'), datetime('now'))"
                ),
                {"id": str(uuid.uuid4()), "fuid": firebase_uid},
            )
            conn.commit()
