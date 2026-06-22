"""Migration schema tests for the blocked_users and reports tables (F10).

Covers task 2:
- blocked_users table exists with the UNIQUE (blocker_id, blocked_id)
  pair and FKs to users (§2.1).
- reports table exists with the reason column and FKs to users (§2.2).
- both tables can be dropped (downgrade equivalent).

Approach: SQLite in-memory via ``Base.metadata.create_all()`` with FK
enforcement, mirroring ``test_posts_migration.py``. The real Alembic
migration is PostgreSQL-specific (``gen_random_uuid()``,
``postgresql.ENUM``) and cannot run on SQLite, so the ORM metadata is
the source of truth verified here (DL-F10-12).

Refs: Design §2.1, §2.2, §2.3, §6.6; FR-4, FR-6, FR-7;
DL-F10-03, DL-F10-06, DL-F10-11
"""

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.pool import StaticPool

from app.models.block import BlockedUser  # noqa: F401 — registers model
from app.models.report import Report  # noqa: F401 — registers model
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


def test_blocked_users_table_exists(db_engine):
    """blocked_users exists with required columns, FKs and UNIQUE pair."""
    inspector = inspect(db_engine)
    assert "blocked_users" in inspector.get_table_names()

    cols = {c["name"] for c in inspector.get_columns("blocked_users")}
    assert cols >= {"id", "blocker_id", "blocked_id", "created_at"}

    referred = {
        fk["referred_table"]
        for fk in inspector.get_foreign_keys("blocked_users")
    }
    assert referred == {"users"}

    uq_names = {
        uq["name"] for uq in inspector.get_unique_constraints("blocked_users")
    }
    assert "blocked_users_unique_pair" in uq_names


def test_reports_table_exists(db_engine):
    """reports exists with the reason column and FKs to users."""
    inspector = inspect(db_engine)
    assert "reports" in inspector.get_table_names()

    cols = {c["name"] for c in inspector.get_columns("reports")}
    assert cols >= {
        "id",
        "reporter_id",
        "reported_user_id",
        "reason",
        "created_at",
    }

    referred = {
        fk["referred_table"] for fk in inspector.get_foreign_keys("reports")
    }
    assert referred == {"users"}


def test_downgrade_drops_tables(db_engine):
    """Dropping both F10 tables removes them from the schema."""
    Base.metadata.drop_all(
        db_engine,
        tables=[BlockedUser.__table__, Report.__table__],
    )
    names = inspect(db_engine).get_table_names()
    assert "blocked_users" not in names
    assert "reports" not in names
