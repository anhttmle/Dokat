"""Unit tests for pet_service helpers (no HTTP layer).

Written TDD-style; tests are expected to FAIL until the pet service
is implemented in later F02 tasks.

Refs: Design 4.2, 6.1
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.pet_profile import PetGender, PetProfile, PetSpecies
from app.models.user import Base, User
from app.services import pet_service


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


def _make_user(db_session: Session) -> User:
    """Insert and return a user row."""
    now = datetime.now(UTC)
    user = User(
        firebase_uid="svc-pet-uid",
        is_anonymous=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_assert_can_create_pet_allowed(db_session: Session) -> None:
    """A user with no pets passes the limit check."""
    user = _make_user(db_session)
    pet_service.assert_can_create_pet(db_session, user.id)


def test_assert_can_create_pet_blocked(db_session: Session) -> None:
    """A user at the limit raises PetLimitReachedError."""
    user = _make_user(db_session)
    db_session.add(
        PetProfile(
            user_id=user.id,
            name="Mochi",
            species=PetSpecies.dog,
            gender=PetGender.male,
        )
    )
    db_session.commit()

    with pytest.raises(pet_service.PetLimitReachedError):
        pet_service.assert_can_create_pet(db_session, user.id)
