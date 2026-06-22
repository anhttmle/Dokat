"""API-level tests for the notifications router (/notifications).

Uses SQLite in-memory DB + mocked Firebase token (same pattern as
other router tests).

Refs: Design §6.4; AC-F09-4, AC-F09-5
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.notification_pref import (  # noqa: F401
    NotificationPreference,
)
from app.models.user import Base, User
from app.routers.auth import get_db

_HEADERS = {"Authorization": "Bearer fake-token"}
_UID = "test-uid-anonymous"


def _ensure_user(db: Session, firebase_uid: str = _UID) -> User:
    user = User(firebase_uid=firebase_uid, is_anonymous=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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


@pytest.fixture()
def client(
    db_session: Session, mock_verify_id_token: MagicMock
) -> TestClient:
    """TestClient with DB overridden and Firebase token mocked."""
    _ensure_user(db_session, firebase_uid=_UID)
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_get_preferences_default_all_true(client: TestClient) -> None:
    """GET /notifications/preferences with no rows → all True (AC-F09-4)."""
    resp = client.get("/notifications/preferences", headers=_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "feeding": True,
        "sleeping": True,
        "bathing": True,
        "playing": True,
    }


def test_put_preference_204(client: TestClient) -> None:
    """PUT bathing=false → 204."""
    resp = client.put(
        "/notifications/preferences/bathing",
        json={"enabled": False},
        headers=_HEADERS,
    )
    assert resp.status_code == 204


def test_put_preference_idempotent(client: TestClient) -> None:
    """PUT same value twice → 204 both times (idempotent)."""
    for _ in range(2):
        resp = client.put(
            "/notifications/preferences/bathing",
            json={"enabled": False},
            headers=_HEADERS,
        )
        assert resp.status_code == 204


def test_put_preference_invalid_type_422(client: TestClient) -> None:
    """PUT with unknown reminder_type → 422."""
    resp = client.put(
        "/notifications/preferences/unknown_type",
        json={"enabled": False},
        headers=_HEADERS,
    )
    assert resp.status_code == 422


def test_get_prefs_reflects_update(client: TestClient) -> None:
    """PUT then GET → updated value is returned."""
    client.put(
        "/notifications/preferences/bathing",
        json={"enabled": False},
        headers=_HEADERS,
    )
    resp = client.get("/notifications/preferences", headers=_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["bathing"] is False
    assert body["feeding"] is True
