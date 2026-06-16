"""Application configuration loaded from environment variables.

All settings are read from the environment (or a .env file in development).
No secrets are hardcoded here — see .env.example for required variables.
"""

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Gateway configuration.

    Required fields have no default; pydantic-settings raises ValidationError
    when they are absent from the environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    firebase_credentials_path: str
    jwt_secret_key: str
    jwt_expiry_minutes: int = 15

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    redis_url: str

    # ------------------------------------------------------------------
    # Proxy
    # ------------------------------------------------------------------
    upstream_timeout_seconds: int = 30

    # ------------------------------------------------------------------
    # Rate limits  (FR-03)
    # ------------------------------------------------------------------
    rate_limit_user_per_min: int = 200
    rate_limit_ip_per_min: int = 30
    rate_limit_global_per_min: int = 10_000
    rate_limit_capture_per_min: int = 20

    # ------------------------------------------------------------------
    # Upstream service URLs  (FR-01.2, D-02)
    # ------------------------------------------------------------------
    upstream_user_service_url: AnyHttpUrl
    upstream_pet_service_url: AnyHttpUrl
    upstream_post_service_url: AnyHttpUrl
    upstream_social_service_url: AnyHttpUrl
    upstream_capture_service_url: AnyHttpUrl
    upstream_send_service_url: AnyHttpUrl
    upstream_view_service_url: AnyHttpUrl
    upstream_response_service_url: AnyHttpUrl
    upstream_history_service_url: AnyHttpUrl
    upstream_onboarding_service_url: AnyHttpUrl
    upstream_notification_service_url: AnyHttpUrl
    upstream_setting_service_url: AnyHttpUrl
    upstream_ai_api_url: AnyHttpUrl

    # ------------------------------------------------------------------
    # Third-party AI  (D-07)
    # ------------------------------------------------------------------
    ai_api_key: str = ""

    # ------------------------------------------------------------------
    # Health check  (D-09)
    # ------------------------------------------------------------------
    health_probe_timeout_seconds: int = 5

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Normalise log level to uppercase and check it is valid."""
        value = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if value not in allowed:
            raise ValueError(
                f"log_level must be one of {allowed}, got '{value}'"
            )
        return value
