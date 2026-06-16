"""Unit tests for app.auth.jwt_issuer — written before implementation (TDD).

Tests verify:
- Issued JWT contains all required claims.
- exp is within 15 minutes of iat.
- Anonymous user: auth_provider='anonymous', email=None.
- extract_auth_provider maps Firebase sign_in_provider correctly.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

_SECRET = "test-jwt-secret-32-chars-minimum!!"


# ---------------------------------------------------------------------------
# import guard — fails fast if module doesn't exist yet
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def jwt_issuer():
    """Import the module under test."""
    from app.auth import jwt_issuer  # noqa: PLC0415

    return jwt_issuer


# ---------------------------------------------------------------------------
# issue_internal_jwt — claim presence
# ---------------------------------------------------------------------------


class TestIssueInternalJwtClaims:
    def test_all_required_claims_present(self, jwt_issuer):
        token = jwt_issuer.issue_internal_jwt(
            uid="user-abc",
            email="user@example.com",
            auth_provider="google.com",
            secret_key=_SECRET,
        )
        payload = jwt.decode(token, _SECRET, algorithms=["HS256"])

        assert payload["uid"] == "user-abc"
        assert payload["email"] == "user@example.com"
        assert payload["auth_provider"] == "google.com"
        assert payload["iss"] == "dokat-api-gateway"
        assert payload["sub"] == "user-abc"
        assert "iat" in payload
        assert "exp" in payload

    def test_sub_equals_uid(self, jwt_issuer):
        token = jwt_issuer.issue_internal_jwt(
            uid="user-xyz",
            email=None,
            auth_provider="password",
            secret_key=_SECRET,
        )
        payload = jwt.decode(token, _SECRET, algorithms=["HS256"])
        assert payload["sub"] == payload["uid"]

    def test_algorithm_is_hs256(self, jwt_issuer):
        token = jwt_issuer.issue_internal_jwt(
            uid="u1",
            email="a@b.com",
            auth_provider="google.com",
            secret_key=_SECRET,
        )
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "HS256"


# ---------------------------------------------------------------------------
# issue_internal_jwt — expiry
# ---------------------------------------------------------------------------


class TestIssueInternalJwtExpiry:
    def test_exp_within_15_minutes(self, jwt_issuer):
        before = datetime.now(UTC)
        token = jwt_issuer.issue_internal_jwt(
            uid="u1",
            email="a@b.com",
            auth_provider="google.com",
            secret_key=_SECRET,
        )
        payload = jwt.decode(token, _SECRET, algorithms=["HS256"])

        iat = datetime.fromtimestamp(payload["iat"], tz=UTC)
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)

        assert exp > before
        assert (exp - iat) <= timedelta(minutes=15)

    def test_custom_expiry_respected(self, jwt_issuer):
        token = jwt_issuer.issue_internal_jwt(
            uid="u1",
            email=None,
            auth_provider="anonymous",
            secret_key=_SECRET,
            expiry_minutes=10,
        )
        payload = jwt.decode(token, _SECRET, algorithms=["HS256"])
        iat = datetime.fromtimestamp(payload["iat"], tz=UTC)
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        assert timedelta(minutes=9) < (exp - iat) <= timedelta(minutes=10)


# ---------------------------------------------------------------------------
# issue_internal_jwt — anonymous user (FR-02.6)
# ---------------------------------------------------------------------------


class TestAnonymousToken:
    def test_anonymous_auth_provider(self, jwt_issuer):
        token = jwt_issuer.issue_internal_jwt(
            uid="anon-device-456",
            email=None,
            auth_provider="anonymous",
            secret_key=_SECRET,
        )
        payload = jwt.decode(token, _SECRET, algorithms=["HS256"])
        assert payload["auth_provider"] == "anonymous"

    def test_anonymous_email_is_none(self, jwt_issuer):
        token = jwt_issuer.issue_internal_jwt(
            uid="anon-device-456",
            email=None,
            auth_provider="anonymous",
            secret_key=_SECRET,
        )
        payload = jwt.decode(token, _SECRET, algorithms=["HS256"])
        assert payload["email"] is None


# ---------------------------------------------------------------------------
# extract_auth_provider
# ---------------------------------------------------------------------------


class TestExtractAuthProvider:
    @pytest.mark.parametrize(
        "sign_in_provider,expected",
        [
            ("anonymous", "anonymous"),
            ("google.com", "google.com"),
            ("facebook.com", "facebook.com"),
            ("apple.com", "apple.com"),
            ("password", "password"),
        ],
    )
    def test_maps_sign_in_provider(
        self, jwt_issuer, sign_in_provider, expected
    ):
        claims = {"firebase": {"sign_in_provider": sign_in_provider}}
        assert jwt_issuer.extract_auth_provider(claims) == expected

    def test_missing_firebase_key_returns_unknown(self, jwt_issuer):
        assert jwt_issuer.extract_auth_provider({}) == "unknown"

    def test_missing_sign_in_provider_returns_unknown(self, jwt_issuer):
        assert jwt_issuer.extract_auth_provider({"firebase": {}}) == "unknown"
