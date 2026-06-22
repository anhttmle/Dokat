"""Unit tests for FirebaseAuthMiddleware.

Written TDD-style: all 5 tests are expected to FAIL until
``FirebaseAuthMiddleware`` is implemented in ``app/middleware/auth.py``.

Refs: FR-10; Design §3.3; Design §5.1
"""

from unittest.mock import patch

import firebase_admin.auth
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.middleware.auth import FirebaseAuthMiddleware


def _make_test_app() -> FastAPI:
    """Return a minimal FastAPI app with FirebaseAuthMiddleware applied."""
    test_app = FastAPI()
    test_app.add_middleware(FirebaseAuthMiddleware)

    @test_app.get("/probe")
    async def probe(request: Request) -> JSONResponse:
        return JSONResponse({"firebase_uid": request.state.firebase_uid})

    return test_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """TestClient wrapping the minimal app; server exceptions suppressed."""
    return TestClient(_make_test_app(), raise_server_exceptions=False)


def test_valid_token_injects_firebase_uid(client: TestClient) -> None:
    """Valid token → request.state.firebase_uid is populated correctly."""
    with patch("firebase_admin.auth.verify_id_token") as mock_verify:
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


def test_expired_token_returns_401(client: TestClient) -> None:
    """ExpiredIdTokenError → HTTP 401, error AUTH_TOKEN_EXPIRED."""
    with patch("firebase_admin.auth.verify_id_token") as mock_verify:
        mock_verify.side_effect = firebase_admin.auth.ExpiredIdTokenError(
            "Token expired", cause=None
        )
        response = client.get(
            "/probe",
            headers={"Authorization": "Bearer expired-token"},
        )

    assert response.status_code == 401
    assert response.json()["error"] == "AUTH_TOKEN_EXPIRED"


def test_revoked_token_returns_401(client: TestClient) -> None:
    """RevokedIdTokenError → HTTP 401, error AUTH_TOKEN_REVOKED."""
    with patch("firebase_admin.auth.verify_id_token") as mock_verify:
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
    with patch("firebase_admin.auth.verify_id_token") as mock_verify:
        mock_verify.side_effect = Exception("Firebase SDK internal error")
        response = client.get(
            "/probe",
            headers={"Authorization": "Bearer some-token"},
        )

    assert response.status_code == 503
