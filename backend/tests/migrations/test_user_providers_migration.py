"""Unit tests for the user_providers table migration schema.

These tests verify the schema contract defined in design §2.2:
- FK to users(id) is enforced (ForeignKeyViolation on bad user_id).
- UNIQUE(provider, provider_uid) prevents duplicate OAuth accounts.
- One user may link multiple distinct providers.

Approach: SQLite in-memory with PRAGMA foreign_keys=ON.
See decision_log DL-006 for the SQLite-over-PostgreSQL rationale.
"""

import uuid

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError

from app.models.user import Base

_INSERT_USER = (
    "INSERT INTO users "
    "(id, firebase_uid, is_anonymous, created_at, updated_at) "
    "VALUES (:id, :fuid, 1, datetime('now'), datetime('now'))"
)

_INSERT_PROVIDER = (
    "INSERT INTO user_providers "
    "(id, user_id, provider, provider_uid, linked_at) "
    "VALUES (:id, :uid, :provider, :puid, datetime('now'))"
)


@pytest.fixture
def db_engine():
    """SQLite in-memory engine with FK enforcement enabled."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_fk(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sample_user_id(db_engine):
    """Insert one user row and return its UUID string."""
    user_id = str(uuid.uuid4())
    with db_engine.connect() as conn:
        conn.execute(
            text(_INSERT_USER),
            {"id": user_id, "fuid": f"firebase-{user_id}"},
        )
        conn.commit()
    return user_id


def test_user_providers_fk(db_engine):
    """Insert user_providers with non-existent user_id must fail."""
    with pytest.raises(IntegrityError):
        with db_engine.connect() as conn:
            conn.execute(
                text(_INSERT_PROVIDER),
                {
                    "id": str(uuid.uuid4()),
                    "uid": str(uuid.uuid4()),  # no matching users row
                    "provider": "apple",
                    "puid": "apple-sub-nonexistent",
                },
            )
            conn.commit()


def test_provider_uid_unique_per_provider(db_engine, sample_user_id):
    """Two rows with same (provider, provider_uid) must raise IntegrityError."""
    with db_engine.connect() as conn:
        conn.execute(
            text(_INSERT_PROVIDER),
            {
                "id": str(uuid.uuid4()),
                "uid": sample_user_id,
                "provider": "google",
                "puid": "google-sub-123",
            },
        )
        conn.commit()

    with pytest.raises(IntegrityError):
        with db_engine.connect() as conn:
            conn.execute(
                text(_INSERT_PROVIDER),
                {
                    "id": str(uuid.uuid4()),
                    "uid": sample_user_id,
                    "provider": "google",
                    "puid": "google-sub-123",  # same (provider, puid)
                },
            )
            conn.commit()


def test_multi_provider_same_user(db_engine, sample_user_id):
    """A user may link both apple and google without error."""
    with db_engine.connect() as conn:
        conn.execute(
            text(_INSERT_PROVIDER),
            {
                "id": str(uuid.uuid4()),
                "uid": sample_user_id,
                "provider": "apple",
                "puid": "apple-sub-abc",
            },
        )
        conn.execute(
            text(_INSERT_PROVIDER),
            {
                "id": str(uuid.uuid4()),
                "uid": sample_user_id,
                "provider": "google",
                "puid": "google-sub-xyz",
            },
        )
        conn.commit()

    with db_engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM user_providers WHERE user_id = :uid"
            ),
            {"uid": sample_user_id},
        )
        assert result.scalar() == 2
