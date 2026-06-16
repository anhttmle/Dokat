"""Integration tests for Quick Auth (Anonymous login) — T-05 (TDD).

Tests verify (AC-06, FR-02.6):
- Firebase Anonymous ID Token on /onboarding/* → Internal JWT issued with
  auth_provider='anonymous' and email=None.
"""

from unittest.mock import patch

import jwt
from fastapi.testclient import TestClient

from app.auth.dependency import authenticate_request
from app.config import Settings
from app.main import create_app

_ANON_CLAIMS = {
    "uid": "anon-device-456",
    "email": None,
    "firebase": {"sign_in_provider": "anonymous"},
}


def _anon_client():
    """Return a TestClient with Firebase returning anonymous claims."""
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# AC-06 — Quick Auth
# ---------------------------------------------------------------------------


class TestQuickAuthAnonymous:
    def test_anonymous_token_does_not_return_401(self):
        """Anonymous token on /onboarding/* must not be rejected (AC-06)."""
        with patch(
            "app.auth.firebase.verify_id_token",
            return_value=_ANON_CLAIMS,
        ):
            with _anon_client() as c:
                resp = c.get(
                    "/onboarding/welcome",
                    headers={"Authorization": "Bearer anon.firebase.token"},
                )
        # Proxy stub returns non-401 (may be 501 until T-06); auth passed.
        assert resp.status_code != 401

    def test_anonymous_internal_jwt_auth_provider(self):
        """Anonymous token accepted: status not 401 (detailed by dependency
        test below).
        """
        with patch(
            "app.auth.firebase.verify_id_token",
            return_value=_ANON_CLAIMS,
        ):
            with _anon_client() as c:
                resp = c.get(
                    "/onboarding/step2",
                    headers={"Authorization": "Bearer anon.firebase.token"},
                )
        assert resp.status_code != 401

    def test_anonymous_jwt_claims_via_dependency(self):
        """Directly verify anonymous claims produce correct Internal JWT."""
        settings = Settings()
        with patch(
            "app.auth.firebase.verify_id_token",
            return_value=_ANON_CLAIMS,
        ):
            auth_ctx = authenticate_request(
                authorization_header="Bearer anon.firebase.token",
                settings=settings,
            )

        assert auth_ctx.auth_provider == "anonymous"
        assert auth_ctx.email is None

        payload = jwt.decode(
            auth_ctx.internal_jwt,
            settings.jwt_secret_key,
            algorithms=["HS256"],
        )
        assert payload["auth_provider"] == "anonymous"
        assert payload["email"] is None

    def test_anonymous_uid_in_jwt(self):
        """Anonymous JWT sub and uid must match the Firebase anonymous UID."""
        settings = Settings()
        with patch(
            "app.auth.firebase.verify_id_token",
            return_value=_ANON_CLAIMS,
        ):
            auth_ctx = authenticate_request(
                authorization_header="Bearer anon.firebase.token",
                settings=settings,
            )

        payload = jwt.decode(
            auth_ctx.internal_jwt,
            settings.jwt_secret_key,
            algorithms=["HS256"],
        )
        assert payload["uid"] == "anon-device-456"
        assert payload["sub"] == "anon-device-456"
