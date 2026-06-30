"""Unit tests for AuthMiddleware (JWT mode and Firebase mode).

Refs: FR-3, FR-4; Design §4; AC-F12-1, AC-F12-3
"""

from unittest.mock import patch

import firebase_admin.auth
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.middleware.auth import AuthMiddleware


def _make_test_app() -> FastAPI:
    """Return a minimal FastAPI app with AuthMiddleware applied."""
    test_app = FastAPI()
    test_app.add_middleware(AuthMiddleware)

    @test_app.get("/probe")
    async def probe(request: Request) -> JSONResponse:
        return JSONResponse({"firebase_uid": request.state.firebase_uid})

    return test_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """TestClient wrapping the minimal app; server exceptions suppressed."""
    return TestClient(_make_test_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Firebase mode tests
# ---------------------------------------------------------------------------


def test_valid_firebase_token_injects_uid(client: TestClient) -> None:
    """Valid Firebase token → request.state.firebase_uid populated."""
    with (
        patch("app.middleware.auth.settings") as mock_settings,
        patch("firebase_admin.auth.verify_id_token") as mock_verify,
    ):
        mock_settings.auth_mode = "firebase"
        mock_verify.return_value = {"uid": "test-uid-123"}
        response = client.get(
            "/probe",
            headers={"Authorization": "Bearer valid-token"},
        )

    assert response.status_code == 200
    assert response.json()["firebase_uid"] == "test-uid-123"


def test_missing_token_returns_401(client: TestClient) -> None:
    """No Authorization header → HTTP 401, error AUTH_TOKEN_MISSING."""
    response = client.get("/probe")

    assert response.status_code == 401
    assert response.json()["error"] == "AUTH_TOKEN_MISSING"


def test_expired_firebase_token_returns_401(client: TestClient) -> None:
    """ExpiredIdTokenError → HTTP 401, error AUTH_TOKEN_EXPIRED."""
    with (
        patch("app.middleware.auth.settings") as mock_settings,
        patch("firebase_admin.auth.verify_id_token") as mock_verify,
    ):
        mock_settings.auth_mode = "firebase"
        mock_verify.side_effect = firebase_admin.auth.ExpiredIdTokenError(
            "Token expired", cause=None
        )
        response = client.get(
            "/probe",
            headers={"Authorization": "Bearer expired-token"},
        )

    assert response.status_code == 401
    assert response.json()["error"] == "AUTH_TOKEN_EXPIRED"


def test_revoked_firebase_token_returns_401(client: TestClient) -> None:
    """RevokedIdTokenError → HTTP 401, error AUTH_TOKEN_REVOKED."""
    with (
        patch("app.middleware.auth.settings") as mock_settings,
        patch("firebase_admin.auth.verify_id_token") as mock_verify,
    ):
        mock_settings.auth_mode = "firebase"
        mock_verify.side_effect = firebase_admin.auth.RevokedIdTokenError(
            "Token revoked"
        )
        response = client.get(
            "/probe",
            headers={"Authorization": "Bearer revoked-token"},
        )

    assert response.status_code == 401
    assert response.json()["error"] == "AUTH_TOKEN_REVOKED"


def test_firebase_sdk_error_returns_503(client: TestClient) -> None:
    """Generic Firebase SDK exception → HTTP 503."""
    with (
        patch("app.middleware.auth.settings") as mock_settings,
        patch("firebase_admin.auth.verify_id_token") as mock_verify,
    ):
        mock_settings.auth_mode = "firebase"
        mock_verify.side_effect = Exception("Firebase SDK internal error")
        response = client.get(
            "/probe",
            headers={"Authorization": "Bearer some-token"},
        )

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# JWT mode tests
# ---------------------------------------------------------------------------


def test_valid_jwt_injects_firebase_uid(client: TestClient) -> None:
    """Valid JWT → request.state.firebase_uid = device_id (sub claim)."""
    with (
        patch("app.middleware.auth.settings") as mock_settings,
        patch("app.middleware.auth.verify_token") as mock_verify,
    ):
        mock_settings.auth_mode = "jwt"
        mock_verify.return_value = "device-abc-123"
        response = client.get(
            "/probe",
            headers={"Authorization": "Bearer some-jwt"},
        )

    assert response.status_code == 200
    assert response.json()["firebase_uid"] == "device-abc-123"


def test_expired_jwt_returns_401(client: TestClient) -> None:
    """Expired JWT → HTTP 401, error AUTH_TOKEN_EXPIRED."""
    from app.core.jwt_auth import JWTAuthError

    with (
        patch("app.middleware.auth.settings") as mock_settings,
        patch("app.middleware.auth.verify_token") as mock_verify,
    ):
        mock_settings.auth_mode = "jwt"
        mock_verify.side_effect = JWTAuthError("expired")
        response = client.get(
            "/probe",
            headers={"Authorization": "Bearer expired-jwt"},
        )

    assert response.status_code == 401
    assert response.json()["error"] == "AUTH_TOKEN_EXPIRED"


def test_invalid_jwt_returns_401(client: TestClient) -> None:
    """Invalid JWT → HTTP 401, error AUTH_TOKEN_INVALID."""
    from app.core.jwt_auth import JWTAuthError

    with (
        patch("app.middleware.auth.settings") as mock_settings,
        patch("app.middleware.auth.verify_token") as mock_verify,
    ):
        mock_settings.auth_mode = "jwt"
        mock_verify.side_effect = JWTAuthError("invalid signature")
        response = client.get(
            "/probe",
            headers={"Authorization": "Bearer bad-jwt"},
        )

    assert response.status_code == 401
    assert response.json()["error"] == "AUTH_TOKEN_INVALID"


def test_public_path_bypasses_auth(client: TestClient) -> None:
    """Requests to /auth/token bypass middleware — no token required."""
    # /auth/token is in _PUBLIC_PATHS; no 401 even without a token.
    # We need a route registered for this path to avoid 404.
    test_app = FastAPI()
    test_app.add_middleware(AuthMiddleware)

    @test_app.post("/auth/token")
    async def token_endpoint() -> dict:
        return {"ok": True}

    public_client = TestClient(test_app, raise_server_exceptions=False)
    response = public_client.post("/auth/token", json={"device_id": "x"})
    assert response.status_code == 200
