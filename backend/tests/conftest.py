"""Shared pytest fixtures for the backend test suite."""

import os
from unittest.mock import patch

import pytest

# Ensure JWT_SECRET_KEY is set so jwt_auth tests work without .env.
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-secret-key-minimum-32-chars!!"
)


@pytest.fixture(autouse=False)
def mock_verify_id_token():
    """Mock firebase_admin.auth.verify_id_token to avoid real Firebase calls.

    Yields a MagicMock. Tests can configure return_value or
    side_effect to simulate valid / invalid / expired tokens.

    Usage::

        def test_something(mock_verify_id_token):
            mock_verify_id_token.return_value = {
                "uid": "test-uid-123",
                "firebase": {"sign_in_provider": "anonymous"},
            }
    """
    with patch(
        "firebase_admin.auth.verify_id_token",
        autospec=True,
    ) as mock:
        mock.return_value = {
            "uid": "test-uid-anonymous",
            "firebase": {"sign_in_provider": "anonymous"},
        }
        yield mock


@pytest.fixture
def anonymous_token_payload() -> dict:
    """Return a sample decoded token payload for an anonymous user."""
    return {
        "uid": "test-uid-anonymous",
        "firebase": {"sign_in_provider": "anonymous"},
    }


@pytest.fixture
def linked_token_payload() -> dict:
    """Return a sample decoded token payload for a Google-linked user."""
    return {
        "uid": "test-uid-linked",
        "firebase": {
            "sign_in_provider": "google.com",
            "identities": {"google.com": ["google-sub-123"]},
        },
    }
