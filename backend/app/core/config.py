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

    redis_url: str = "redis://localhost:6379/0"
    deep_link_base: str = "https://petapp.example.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
