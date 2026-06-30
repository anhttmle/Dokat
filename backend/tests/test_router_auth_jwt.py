"""Tests for POST /auth/token endpoint (JWT standalone mode).

Uses a dedicated minimal FastAPI app so the test is independent of
``AUTH_MODE`` at ``app.main`` import time.

Refs: FR-2, FR-3; AC-F12-2; Design §3
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.user import Base, User
from app.routers.auth import get_db
from app.routers.auth_jwt import router as jwt_router


def _make_jwt_test_app() -> FastAPI:
    """Return a minimal FastAPI app with only the JWT auth router."""
    test_app = FastAPI()
    test_app.include_router(jwt_router)
    return test_app


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


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """TestClient with DB overridden and JWT_SECRET_KEY patched."""
    test_app = _make_jwt_test_app()
    test_app.dependency_overrides[get_db] = lambda: db_session

    with patch("app.routers.auth_jwt.create_token") as mock_create:
        mock_create.side_effect = lambda sub: f"jwt-{sub}"
        yield TestClient(test_app, raise_server_exceptions=False)


def test_issue_token_happy_path(client: TestClient) -> None:
    """POST /auth/token with valid device_id returns access_token + user_id."""
    response = client.post(
        "/auth/token", json={"device_id": "my-device-001"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "jwt-my-device-001"
    assert data["is_anonymous"] is True
    assert uuid.UUID(data["user_id"])  # valid UUID


def test_issue_token_empty_device_id_returns_422(
    client: TestClient,
) -> None:
    """Empty device_id string → 422."""
    response = client.post("/auth/token", json={"device_id": "   "})
    assert response.status_code == 422


def test_issue_token_idempotent(
    client: TestClient, db_session: Session
) -> None:
    """Same device_id twice → same user_id."""
    r1 = client.post("/auth/token", json={"device_id": "idempotent-dev"})
    r2 = client.post("/auth/token", json={"device_id": "idempotent-dev"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["user_id"] == r2.json()["user_id"]

    count = db_session.query(User).filter(
        User.firebase_uid == "idempotent-dev"
    ).count()
    assert count == 1


def test_different_device_ids_create_different_users(
    client: TestClient,
) -> None:
    """Two distinct device_ids → two distinct user_ids."""
    r1 = client.post("/auth/token", json={"device_id": "dev-A"})
    r2 = client.post("/auth/token", json={"device_id": "dev-B"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["user_id"] != r2.json()["user_id"]
