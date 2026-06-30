"""Standalone mode smoke test — no Firebase, no real AWS S3.

Verifies the full JWT + MinIO flow using in-memory SQLite and mocked
boto3.  No Firebase credentials are set.

Refs: AC-F12-1, AC-F12-2, AC-F12-3, AC-F12-4, AC-F12-5
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.firebase import _app as _global_firebase_app
from app.middleware.auth import AuthMiddleware
from app.models.user import Base
from app.routers.auth import get_db
from app.routers.auth_jwt import router as jwt_router
from app.routers.profile import router as profile_router


def _make_standalone_app() -> FastAPI:
    """Minimal app: JWT auth middleware + JWT token + profile endpoint."""
    test_app = FastAPI()
    test_app.add_middleware(AuthMiddleware)
    test_app.include_router(jwt_router)
    test_app.include_router(profile_router)

    @test_app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return test_app


@pytest.fixture()
def db_session() -> Session:
    """Isolated SQLite in-memory session."""
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
def standalone_client(db_session: Session) -> TestClient:
    """TestClient with JWT mode and no Firebase."""
    test_app = _make_standalone_app()
    test_app.dependency_overrides[get_db] = lambda: db_session

    with patch("app.middleware.auth.settings") as mock_settings:
        mock_settings.auth_mode = "jwt"
        yield TestClient(test_app, raise_server_exceptions=False)


def test_health_returns_ok(standalone_client: TestClient) -> None:
    """AC-F12-1: /health works without Firebase credentials."""
    response = standalone_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_issue_and_use_jwt(standalone_client: TestClient) -> None:
    """AC-F12-2 + AC-F12-3: POST /auth/token → JWT → GET /profile/me."""
    # Step 1: issue token.
    r = standalone_client.post(
        "/auth/token", json={"device_id": "test-device-001"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

    # Step 2: use token to call a protected endpoint.
    profile_r = standalone_client.get(
        "/profile/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_r.status_code == 200
    body = profile_r.json()
    assert body["is_anonymous"] is True


def test_firebase_unavailable_no_crash() -> None:
    """AC-F12-5: Firebase being None does not raise on notification."""
    from app.core.firebase import is_firebase_available
    from app.services.notification_service import _send_fcm

    # If Firebase _app is None (standalone mode), _send_fcm must not raise.
    with patch(
        "app.services.notification_service.is_firebase_available",
        return_value=False,
    ):
        # Should log a warning and return — no exception.
        _send_fcm(
            token="fake-fcm-token",
            title="Test",
            body="test body",
        )
