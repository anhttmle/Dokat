"""Tests for POST /auth/session endpoint.

Written TDD-style; all 6 tests expected to FAIL until task 4.2 is
complete.

Refs: FR-1, FR-2, FR-6, FR-9; AC-F01-1, AC-F01-4, AC-F01-6
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.user import Base, OAuthProvider, User, UserProvider
from app.routers.auth import get_db

_HEADERS = {"Authorization": "Bearer fake-token"}


@pytest.fixture()
def db_session() -> Session:
    """Isolated SQLite in-memory session per test.

    ``StaticPool`` forces SQLAlchemy to reuse a single connection so the
    in-memory database (and its tables) is visible across all threads.
    ``check_same_thread=False`` lets FastAPI's worker thread reuse that
    connection (DL-014).
    """
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


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """TestClient with the DB dependency overridden per test."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_new_guest_creates_user_record(
    client: TestClient, db_session: Session
) -> None:
    """New firebase_uid → 1 user in DB, is_anonymous=True, 200 OK."""
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "new-guest-uid"}
        response = client.post("/auth/session", headers=_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["firebase_uid"] == "new-guest-uid"
    assert body["is_anonymous"] is True
    assert body["force_link_required"] is False
    assert "user_id" in body
    assert db_session.query(User).count() == 1


def test_existing_user_no_duplicate(
    client: TestClient, db_session: Session
) -> None:
    """Two calls with same firebase_uid → still exactly 1 user record."""
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "existing-uid"}
        client.post("/auth/session", headers=_HEADERS)
        client.post("/auth/session", headers=_HEADERS)

    assert db_session.query(User).count() == 1


def test_force_link_false_before_7_days(
    client: TestClient, db_session: Session
) -> None:
    """force_link_at = tomorrow → force_link_required=False."""
    now = datetime.now(UTC)
    user = User(
        firebase_uid="user-force-false",
        is_anonymous=True,
        created_at=now,
        updated_at=now,
        force_link_at=now + timedelta(days=1),
    )
    db_session.add(user)
    db_session.commit()

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "user-force-false"}
        response = client.post("/auth/session", headers=_HEADERS)

    assert response.status_code == 200
    assert response.json()["force_link_required"] is False


def test_force_link_true_at_7_days(
    client: TestClient, db_session: Session
) -> None:
    """force_link_at in the past → force_link_required=True."""
    now = datetime.now(UTC)
    user = User(
        firebase_uid="user-force-true",
        is_anonymous=True,
        created_at=now - timedelta(days=7),
        updated_at=now - timedelta(days=7),
        force_link_at=now - timedelta(seconds=1),
    )
    db_session.add(user)
    db_session.commit()

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "user-force-true"}
        response = client.post("/auth/session", headers=_HEADERS)

    assert response.status_code == 200
    assert response.json()["force_link_required"] is True


def test_providers_list_empty_for_guest(
    client: TestClient,
) -> None:
    """Fresh guest user → providers=[]."""
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "guest-no-providers"}
        response = client.post("/auth/session", headers=_HEADERS)

    assert response.status_code == 200
    assert response.json()["providers"] == []


def test_providers_list_populated_for_linked_user(
    client: TestClient, db_session: Session
) -> None:
    """User with one google user_providers row → providers=["google"]."""
    now = datetime.now(UTC)
    user = User(
        firebase_uid="linked-user-uid",
        is_anonymous=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.flush()

    provider = UserProvider(
        user_id=user.id,
        provider=OAuthProvider.google,
        provider_uid="google-sub-abc",
    )
    db_session.add(provider)
    db_session.commit()

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "linked-user-uid"}
        response = client.post("/auth/session", headers=_HEADERS)

    assert response.status_code == 200
    assert response.json()["providers"] == ["google"]
