"""Shared pytest fixtures for unit and integration tests.

Module-level env var defaults ensure Settings() works in all tests.
Individual tests can override via monkeypatch (see test_config.py).
"""

import os
from unittest.mock import patch

import fakeredis.aioredis
import httpx
import pytest
import respx

# ---------------------------------------------------------------------------
# Env var defaults — applied via pytest_configure so they are set before
# any app module is imported during collection or test runs.
# ---------------------------------------------------------------------------
_TEST_ENV: dict[str, str] = {
    "JWT_SECRET_KEY": "test-jwt-secret-32-chars-minimum!!",
    "REDIS_URL": "redis://localhost:6379/0",
    "FIREBASE_CREDENTIALS_PATH": "/tmp/fake-firebase-creds.json",
    "UPSTREAM_USER_SERVICE_URL": "http://user-svc:8000",
    "UPSTREAM_PET_SERVICE_URL": "http://pet-svc:8000",
    "UPSTREAM_POST_SERVICE_URL": "http://post-svc:8000",
    "UPSTREAM_SOCIAL_SERVICE_URL": "http://social-svc:8000",
    "UPSTREAM_CAPTURE_SERVICE_URL": "http://capture-svc:8000",
    "UPSTREAM_SEND_SERVICE_URL": "http://send-svc:8000",
    "UPSTREAM_VIEW_SERVICE_URL": "http://view-svc:8000",
    "UPSTREAM_RESPONSE_SERVICE_URL": "http://response-svc:8000",
    "UPSTREAM_HISTORY_SERVICE_URL": "http://history-svc:8000",
    "UPSTREAM_ONBOARDING_SERVICE_URL": "http://onboarding-svc:8000",
    "UPSTREAM_NOTIFICATION_SERVICE_URL": "http://notification-svc:8000",
    "UPSTREAM_SETTING_SERVICE_URL": "http://setting-svc:8000",
    "UPSTREAM_AI_API_URL": "http://ai-provider.example.com",
}

_UPSTREAM_BASE_URLS: tuple[str, ...] = tuple(
    sorted({v for k, v in _TEST_ENV.items() if k.startswith("UPSTREAM_")})
)


def pytest_configure(config) -> None:  # noqa: ANN001
    """Set required env vars before app modules are imported."""
    for k, v in _TEST_ENV.items():
        os.environ.setdefault(k, v)


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

#: Firebase claims returned by the happy-path mock.
VALID_FIREBASE_CLAIMS: dict = {
    "uid": "test-user-123",
    "email": "test@example.com",
    "firebase": {"sign_in_provider": "google.com"},
}

#: Anonymous Firebase claims (Quick Auth / Device ID login).
ANON_FIREBASE_CLAIMS: dict = {
    "uid": "anon-device-456",
    "email": None,
    "firebase": {"sign_in_provider": "anonymous"},
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_verify_id_token():
    """Patch Firebase verify_id_token to return valid test claims.

    Yields:
        The MagicMock so tests can configure side_effect or return_value.
    """
    with patch("app.auth.firebase.verify_id_token") as mock:
        mock.return_value = VALID_FIREBASE_CLAIMS.copy()
        yield mock


@pytest.fixture()
def fake_redis():
    """In-memory async Redis for rate limit tests (T-08)."""
    return fakeredis.aioredis.FakeRedis()


@pytest.fixture(autouse=True)
def _patch_redis(fake_redis, monkeypatch):  # noqa: ANN001
    """Use fakeredis for all tests so no real Redis is required."""
    monkeypatch.setattr("redis.asyncio.from_url", lambda *a, **k: fake_redis)


@pytest.fixture()
def mock_upstream_health_up():
    """Mock all upstream /health endpoints as 200 OK (T-10)."""
    with respx.mock:
        for base_url in _UPSTREAM_BASE_URLS:
            respx.get(f"{base_url}/health").mock(
                return_value=httpx.Response(200, json={"status": "ok"})
            )
        yield
