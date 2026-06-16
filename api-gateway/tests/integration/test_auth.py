"""Integration tests for Firebase auth & Internal JWT — T-05 (TDD).

Tests verify (AC-02, FR-02.1, FR-02.5, FR-02.7):
- Expired/invalid Firebase token → 401 UNAUTHORIZED, request not forwarded.
- Missing Authorization header → 401.
- GET /health (public route) → 200 without any token.
"""

from fastapi.testclient import TestClient

from app.errors.codes import ErrorCode
from app.errors.handlers import GatewayError
from app.main import create_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_client(mock_verify_id_token):
    """Return a TestClient with mocked verify_id_token."""
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


def _make_unauthed_client():
    """Return a TestClient with NO mock — real auth guard paths."""
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# AC-02 / FR-02.5 — expired / invalid token
# ---------------------------------------------------------------------------


class TestExpiredToken:
    def test_expired_token_returns_401(self, mock_verify_id_token):
        """Expired Firebase token must yield 401 UNAUTHORIZED (AC-02)."""
        mock_verify_id_token.side_effect = GatewayError(
            code=ErrorCode.UNAUTHORIZED,
            message="Firebase ID token has expired.",
            status_code=401,
        )
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get(
                "/pets/123",
                headers={"Authorization": "Bearer expired.token.here"},
            )

        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == ErrorCode.UNAUTHORIZED

    def test_expired_token_body_has_trace_id(self, mock_verify_id_token):
        mock_verify_id_token.side_effect = GatewayError(
            code=ErrorCode.UNAUTHORIZED,
            message="Firebase ID token has expired.",
            status_code=401,
        )
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get(
                "/pets/123",
                headers={"Authorization": "Bearer expired.token.here"},
            )

        body = resp.json()
        assert "trace_id" in body["error"]
        assert body["error"]["trace_id"] != ""

    def test_revoked_token_returns_401(self, mock_verify_id_token):
        mock_verify_id_token.side_effect = GatewayError(
            code=ErrorCode.UNAUTHORIZED,
            message="Firebase ID token has been revoked.",
            status_code=401,
        )
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get(
                "/users/me",
                headers={"Authorization": "Bearer revoked.token"},
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# FR-02.1 — missing Authorization header
# ---------------------------------------------------------------------------


class TestMissingAuthorization:
    def test_no_header_returns_401(self):
        with _make_unauthed_client() as c:
            resp = c.get("/pets/123")
        assert resp.status_code == 401

    def test_no_header_error_code_unauthorized(self):
        with _make_unauthed_client() as c:
            body = c.get("/pets/123").json()
        assert body["error"]["code"] == ErrorCode.UNAUTHORIZED

    def test_non_bearer_scheme_returns_401(self):
        with _make_unauthed_client() as c:
            resp = c.get(
                "/pets/123",
                headers={"Authorization": "Basic dXNlcjpwYXNz"},
            )
        assert resp.status_code == 401

    def test_empty_bearer_returns_401(self):
        with _make_unauthed_client() as c:
            resp = c.get(
                "/pets/123",
                headers={"Authorization": "Bearer "},
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# FR-02.7 — public route /health needs no token
# ---------------------------------------------------------------------------


class TestPublicHealthRoute:
    def test_health_no_token_returns_200(self):
        """GET /health must succeed without any Authorization header."""
        with _make_unauthed_client() as c:
            resp = c.get("/health")
        assert resp.status_code == 200

    def test_health_with_token_still_returns_200(self, mock_verify_id_token):
        """Auth token is ignored for the public /health route."""
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get(
                "/health",
                headers={"Authorization": "Bearer some.token"},
            )
        assert resp.status_code == 200
