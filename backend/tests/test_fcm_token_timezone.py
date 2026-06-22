"""Tests for PUT /friends/fcm-token with optional timezone field.

Refs: Design §6.6; AC-F09-6; DL-F09-02
"""

from unittest.mock import MagicMock, patch

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


def test_put_fcm_token_with_timezone(
    client: TestClient, db_session: Session
) -> None:
    """PUT with fcm_token + valid timezone → 204, timezone persisted."""
    with patch(
        "app.routers.friends.save_fcm_token", return_value=None
    ):
        resp = client.put(
            "/friends/fcm-token",
            json={
                "fcm_token": "token-abc",
                "timezone": "Asia/Ho_Chi_Minh",
            },
            headers=_HEADERS,
        )
    assert resp.status_code == 204
    user = (
        db_session.query(User)
        .filter(User.firebase_uid == _UID)
        .first()
    )
    assert user is not None
    assert user.timezone == "Asia/Ho_Chi_Minh"


def test_put_fcm_token_without_timezone(
    client: TestClient, db_session: Session
) -> None:
    """PUT with only fcm_token → 204, existing timezone unchanged."""
    user = (
        db_session.query(User)
        .filter(User.firebase_uid == _UID)
        .first()
    )
    user.timezone = "Europe/London"
    db_session.commit()

    with patch(
        "app.routers.friends.save_fcm_token", return_value=None
    ):
        resp = client.put(
            "/friends/fcm-token",
            json={"fcm_token": "token-abc"},
            headers=_HEADERS,
        )
    assert resp.status_code == 204

    db_session.refresh(user)
    assert user.timezone == "Europe/London"


def test_put_fcm_token_invalid_timezone(client: TestClient) -> None:
    """PUT with invalid timezone → 422 INVALID_TIMEZONE."""
    with patch(
        "app.routers.friends.save_fcm_token", return_value=None
    ):
        resp = client.put(
            "/friends/fcm-token",
            json={
                "fcm_token": "token-abc",
                "timezone": "invalid/tz",
            },
            headers=_HEADERS,
        )
    assert resp.status_code == 422
    body = resp.json()
    assert body.get("error") == "INVALID_TIMEZONE"
