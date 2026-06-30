"""Unit tests for app.core.jwt_auth."""

import time
from unittest.mock import patch

import pytest

from app.core.jwt_auth import JWTAuthError, create_token, verify_token

_SECRET = "test-secret-key"
_ALGO = "HS256"


@pytest.fixture(autouse=True)
def _patch_settings():
    """Patch JWT settings for all tests in this module."""
    with patch("app.core.jwt_auth.settings") as mock:
        mock.jwt_secret_key = _SECRET
        mock.jwt_algorithm = _ALGO
        mock.jwt_expire_days = 30
        yield mock


def test_create_and_verify_round_trip():
    """create_token → verify_token returns same sub."""
    token = create_token("device-abc")
    sub = verify_token(token)
    assert sub == "device-abc"


def test_verify_wrong_secret_raises():
    """Token signed with different secret should raise JWTAuthError."""
    import jwt

    import app.core.jwt_auth as jwt_mod

    # Temporarily sign with a different key.
    token = jwt.encode(
        {"sub": "x", "exp": int(time.time()) + 9999},
        "wrong-secret",
        algorithm=_ALGO,
    )
    with pytest.raises(JWTAuthError):
        jwt_mod.verify_token(token)


def test_verify_expired_token_raises():
    """Expired token should raise JWTAuthError with reason 'expired'."""
    import jwt

    import app.core.jwt_auth as jwt_mod

    token = jwt.encode(
        {"sub": "x", "exp": int(time.time()) - 1},
        _SECRET,
        algorithm=_ALGO,
    )
    with pytest.raises(JWTAuthError) as exc_info:
        jwt_mod.verify_token(token)
    assert exc_info.value.reason == "expired"


def test_verify_malformed_token_raises():
    """Garbage string should raise JWTAuthError."""
    with pytest.raises(JWTAuthError):
        verify_token("not.a.token")


def test_verify_missing_sub_raises():
    """Token without sub claim should raise JWTAuthError."""
    import jwt

    import app.core.jwt_auth as jwt_mod

    token = jwt.encode(
        {"exp": int(time.time()) + 9999},
        _SECRET,
        algorithm=_ALGO,
    )
    with pytest.raises(JWTAuthError):
        jwt_mod.verify_token(token)
