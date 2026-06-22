"""Migration schema tests for the posts and post_recipients tables.

Covers task 2:
- posts table exists with required columns (incl. latitude, longitude,
  expires_at) and a FK to users.
- post_recipients table exists with required columns (incl. seen_at),
  FKs to posts and users, and the unique (post_id, recipient_id) pair.

Approach: SQLite in-memory via ``Base.metadata.create_all()``; FK
enforcement enabled via PRAGMA foreign_keys=ON (mirrors
``test_friendships_migration.py``).

Refs: Design §2.1, §2.2; FR-5, FR-6; AC-F05-4;
DL-F05-01, DL-F05-03, DL-F05-04; F11 Design §2.3
"""

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.pool import StaticPool

from app.models.post import Post  # noqa: F401 — registers model
from app.models.post_recipient import (  # noqa: F401 — registers model
    PostRecipient,
)
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


def test_posts_table_exists(db_engine):
    """posts table must exist after metadata creation."""
    assert "posts" in inspect(db_engine).get_table_names()


def test_posts_columns(db_engine):
    """posts must contain all columns defined in design §2.1."""
    cols = {c["name"] for c in inspect(db_engine).get_columns("posts")}
    assert cols >= {
        "id",
        "user_id",
        "s3_key",
        "cdn_url",
        "expires_at",
        "latitude",
        "longitude",
        "created_at",
    }


def test_posts_fk_to_users(db_engine):
    """posts.user_id must reference the users table."""
    fks = inspect(db_engine).get_foreign_keys("posts")
    referred = {fk["referred_table"] for fk in fks}
    assert referred == {"users"}


def test_post_recipients_table_exists(db_engine):
    """post_recipients table must exist after metadata creation."""
    assert "post_recipients" in inspect(db_engine).get_table_names()


def test_post_recipients_columns(db_engine):
    """post_recipients must contain all columns defined in design §2.2."""
    cols = {
        c["name"] for c in inspect(db_engine).get_columns("post_recipients")
    }
    assert cols >= {
        "id",
        "post_id",
        "recipient_id",
        "seen_at",
        "created_at",
    }


def test_post_recipients_fks(db_engine):
    """post_id → posts and recipient_id → users."""
    fks = inspect(db_engine).get_foreign_keys("post_recipients")
    referred = {fk["referred_table"] for fk in fks}
    assert referred == {"posts", "users"}


def test_post_recipients_unique_pair(db_engine):
    """UNIQUE constraint post_recipients_unique_pair must be present."""
    uqs = inspect(db_engine).get_unique_constraints("post_recipients")
    names = {uq["name"] for uq in uqs}
    assert "post_recipients_unique_pair" in names
