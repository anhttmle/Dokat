"""Migration schema tests for the friendships table and fcm_token column.

Covers task 2.1:
- friendships table exists with required columns.
- FK references from friendships to users.
- UNIQUE constraint ``friendships_unique_pair`` is present.
- users table gains the ``fcm_token`` column.

Approach: SQLite in-memory via ``Base.metadata.create_all()``; FK
enforcement enabled via PRAGMA foreign_keys=ON.
See DL-F03-01 for the CHECK-constraint/SQLite rationale.

Refs: Design §2.1, §2.2; FR-8
"""

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.pool import StaticPool

from app.models.friendship import Friendship  # noqa: F401 — registers model
from app.models.user import Base


@pytest.fixture()
def db_engine():
    """SQLite in-memory engine with FK enforcement and all ORM tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_fk(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_friendships_table_exists(db_engine):
    """friendships table must exist after metadata creation."""
    inspector = inspect(db_engine)
    assert "friendships" in inspector.get_table_names()


def test_friendships_columns(db_engine):
    """friendships must contain all columns defined in design §2.2."""
    cols = {
        c["name"]
        for c in inspect(db_engine).get_columns("friendships")
    }
    assert cols >= {"id", "user_id_a", "user_id_b", "created_at"}


def test_friendships_fk_to_users(db_engine):
    """Both user_id_a and user_id_b must reference the users table."""
    fks = inspect(db_engine).get_foreign_keys("friendships")
    referred = {fk["referred_table"] for fk in fks}
    assert referred == {"users"}


def test_friendships_unique_constraint_exists(db_engine):
    """UNIQUE constraint named friendships_unique_pair must be present."""
    uqs = inspect(db_engine).get_unique_constraints("friendships")
    names = {uq["name"] for uq in uqs}
    assert "friendships_unique_pair" in names


def test_users_table_has_fcm_token(db_engine):
    """users table must have the fcm_token column (added in this migration)."""
    cols = {
        c["name"]
        for c in inspect(db_engine).get_columns("users")
    }
    assert "fcm_token" in cols
