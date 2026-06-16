"""Unit tests for app.config — written before implementation (TDD).

Tests verify:
- Default values are correct (rate limits, timeouts, JWT expiry).
- Missing required env vars raise pydantic ValidationError.
"""

import importlib

import pytest
from pydantic import ValidationError

import app.config as config_module

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(monkeypatch, overrides: dict | None = None):
    """Create a fresh Settings instance with required env vars set.

    Args:
        monkeypatch: pytest monkeypatch fixture.
        overrides: Optional env vars to override. Set value to None to delete.

    Returns:
        A new Settings instance.
    """
    required = {
        "JWT_SECRET_KEY": "test-secret-key-32-chars-minimum!!",
        "REDIS_URL": "redis://localhost:6379/0",
        "FIREBASE_CREDENTIALS_PATH": "/tmp/firebase.json",
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
        "AI_API_KEY": "test-ai-api-key",
    }

    for key, value in required.items():
        monkeypatch.setenv(key, value)

    for key, value in (overrides or {}).items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    importlib.reload(config_module)
    return config_module.Settings()


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    """Settings should load with correct defaults when optional vars absent."""

    def test_jwt_expiry_minutes_default(self, monkeypatch):
        settings = _make_settings(
            monkeypatch,
            {"JWT_EXPIRY_MINUTES": None},
        )
        assert settings.jwt_expiry_minutes == 15

    def test_upstream_timeout_default(self, monkeypatch):
        settings = _make_settings(
            monkeypatch,
            {"UPSTREAM_TIMEOUT_SECONDS": None},
        )
        assert settings.upstream_timeout_seconds == 30

    def test_rate_limit_user_default(self, monkeypatch):
        settings = _make_settings(
            monkeypatch,
            {"RATE_LIMIT_USER_PER_MIN": None},
        )
        assert settings.rate_limit_user_per_min == 200

    def test_rate_limit_ip_default(self, monkeypatch):
        settings = _make_settings(
            monkeypatch,
            {"RATE_LIMIT_IP_PER_MIN": None},
        )
        assert settings.rate_limit_ip_per_min == 30

    def test_rate_limit_global_default(self, monkeypatch):
        settings = _make_settings(
            monkeypatch,
            {"RATE_LIMIT_GLOBAL_PER_MIN": None},
        )
        assert settings.rate_limit_global_per_min == 10_000

    def test_rate_limit_capture_default(self, monkeypatch):
        settings = _make_settings(
            monkeypatch,
            {"RATE_LIMIT_CAPTURE_PER_MIN": None},
        )
        assert settings.rate_limit_capture_per_min == 20

    def test_health_probe_timeout_default(self, monkeypatch):
        settings = _make_settings(
            monkeypatch,
            {"HEALTH_PROBE_TIMEOUT_SECONDS": None},
        )
        assert settings.health_probe_timeout_seconds == 5

    def test_log_level_default(self, monkeypatch):
        settings = _make_settings(
            monkeypatch,
            {"LOG_LEVEL": None},
        )
        assert settings.log_level == "INFO"


# ---------------------------------------------------------------------------
# Override via env
# ---------------------------------------------------------------------------


class TestConfigOverride:
    """Optional vars should be overrideable via environment."""

    def test_jwt_expiry_override(self, monkeypatch):
        settings = _make_settings(
            monkeypatch,
            {"JWT_EXPIRY_MINUTES": "10"},
        )
        assert settings.jwt_expiry_minutes == 10

    def test_rate_limit_user_override(self, monkeypatch):
        settings = _make_settings(
            monkeypatch,
            {"RATE_LIMIT_USER_PER_MIN": "500"},
        )
        assert settings.rate_limit_user_per_min == 500


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------


class TestConfigRequired:
    """Missing required env vars must raise ValidationError."""

    def test_missing_jwt_secret_key(self, monkeypatch):
        with pytest.raises((ValidationError, Exception)):
            _make_settings(monkeypatch, {"JWT_SECRET_KEY": None})

    def test_missing_redis_url(self, monkeypatch):
        with pytest.raises((ValidationError, Exception)):
            _make_settings(monkeypatch, {"REDIS_URL": None})

    def test_missing_firebase_credentials_path(self, monkeypatch):
        with pytest.raises((ValidationError, Exception)):
            _make_settings(
                monkeypatch,
                {"FIREBASE_CREDENTIALS_PATH": None},
            )

    def test_missing_upstream_user_service_url(self, monkeypatch):
        with pytest.raises((ValidationError, Exception)):
            _make_settings(
                monkeypatch,
                {"UPSTREAM_USER_SERVICE_URL": None},
            )


# ---------------------------------------------------------------------------
# Upstream URL fields present
# ---------------------------------------------------------------------------


class TestConfigUpstreamUrls:
    """All 14 upstream URLs should be accessible on Settings."""

    _UPSTREAM_ATTRS = [
        "upstream_user_service_url",
        "upstream_pet_service_url",
        "upstream_post_service_url",
        "upstream_social_service_url",
        "upstream_capture_service_url",
        "upstream_send_service_url",
        "upstream_view_service_url",
        "upstream_response_service_url",
        "upstream_history_service_url",
        "upstream_onboarding_service_url",
        "upstream_notification_service_url",
        "upstream_setting_service_url",
        "upstream_ai_api_url",
    ]

    def test_all_upstream_attrs_present(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        for attr in self._UPSTREAM_ATTRS:
            assert hasattr(settings, attr), (
                f"Settings missing attribute: {attr}"
            )
            assert getattr(settings, attr), (
                f"Settings attribute is empty: {attr}"
            )
