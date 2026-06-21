"""Migration schema tests for the pet_profiles table.

Covers task 2.1 (migration schema contract) and task 2.2 (ORM model).

Approach: SQLite in-memory via ``Base.metadata.create_all()``; FK
enforcement enabled via ``PRAGMA foreign_keys=ON``.
See decision_log DL-F02-07 for the native_enum=False rationale and
DL-006 (F01) for the SQLite-over-PostgreSQL rationale.

Refs: Design §2.2; FR-3, FR-4
"""

import uuid

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.pet_profile import PetGender, PetProfile, PetSpecies
from app.models.user import Base, User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_INSERT_USER = (
    "INSERT INTO users "
    "(id, firebase_uid, is_anonymous, created_at, updated_at) "
    "VALUES (:id, :fuid, 1, datetime('now'), datetime('now'))"
)


@pytest.fixture()
def db_engine():
    """SQLite in-memory engine with FK enforcement and all tables created."""
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


@pytest.fixture()
def db_session(db_engine) -> Session:
    """Isolated ORM session for the same in-memory engine."""
    factory = sessionmaker(bind=db_engine, autoflush=True)
    session = factory()
    yield session
    session.close()


@pytest.fixture()
def seed_user(db_session) -> User:
    """Insert and return one User row for FK-based tests."""
    user = User(
        firebase_uid="firebase-seed-user",
        is_anonymous=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Task 2.1 — Migration schema tests
# ---------------------------------------------------------------------------


def test_pet_profiles_table_exists(db_engine):
    """pet_profiles table must exist after metadata creation."""
    inspector = inspect(db_engine)
    assert "pet_profiles" in inspector.get_table_names()


def test_pet_profiles_columns(db_engine):
    """pet_profiles must contain all columns defined in design §2.2."""
    cols = {
        c["name"]
        for c in inspect(db_engine).get_columns("pet_profiles")
    }
    assert cols >= {
        "id",
        "user_id",
        "name",
        "species",
        "gender",
        "birthdate",
        "avatar_url",
        "created_at",
        "updated_at",
    }


def test_pet_profiles_fk_to_users(db_engine):
    """pet_profiles.user_id must reference the users table."""
    fks = inspect(db_engine).get_foreign_keys("pet_profiles")
    assert any(fk["referred_table"] == "users" for fk in fks)


# ---------------------------------------------------------------------------
# Task 2.2 — ORM model tests
# ---------------------------------------------------------------------------


def test_orm_create_pet_profile(db_session, seed_user):
    """PetProfile insert must succeed; gender defaults to 'unknown'."""
    pet = PetProfile(
        user_id=seed_user.id,
        name="Mochi",
        species=PetSpecies.dog,
    )
    db_session.add(pet)
    db_session.commit()

    assert pet.id is not None
    assert pet.gender == PetGender.unknown
    assert pet.avatar_url is None
