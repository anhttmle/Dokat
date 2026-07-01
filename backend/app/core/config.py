"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration for the FastAPI backend."""

    firebase_credentials_json: str = ""
    database_url: str = "postgresql+asyncpg://localhost/me_dev"
    debug: bool = False

    # Auth mode — "jwt" runs standalone; "firebase" uses Firebase Auth.
    # Default is "firebase" for backward compat; set AUTH_MODE=jwt in .env
    # to run without Firebase.
    auth_mode: Literal["firebase", "jwt"] = "firebase"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30

    # Storage backend — "minio" runs standalone; "s3" uses AWS S3.
    # Default is "s3" for backward compat; set STORAGE_BACKEND=minio in .env
    # to run without AWS.
    storage_backend: Literal["s3", "minio"] = "s3"
    s3_bucket: str = "pawsnap"
    cdn_base_url: str = "https://cdn.pawsnap.app"
    aws_region: str = "us-east-1"
    minio_endpoint_url: str = "http://localhost:9000"
    # Browser-reachable MinIO URL for presigned upload_url / cdn_url.
    # When backend runs in Docker, set internal endpoint above and public
    # endpoint to http://localhost:9000 for Flutter web / mobile on host.
    minio_public_endpoint_url: str = ""
    # MinIO root credentials (must match MINIO_ROOT_USER / MINIO_ROOT_PASSWORD).
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"

    redis_url: str = "redis://localhost:6379/0"
    deep_link_base: str = "https://petapp.example.com"
    # CORS regex for browser clients hitting :8000 directly (not /api proxy).
    cors_allow_origin_regex: str = (
        r"https?://(localhost|127\.0\.0\.1"
        r"|(?:\d{1,3}\.){3}\d{1,3}"
        r"|[\w.-]+)(:\d+)?"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
