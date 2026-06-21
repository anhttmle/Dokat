"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration for the FastAPI backend."""

    firebase_credentials_json: str = ""
    database_url: str = "postgresql+asyncpg://localhost/me_dev"
    debug: bool = False

    s3_bucket: str = "pawsnap"
    cdn_base_url: str = "https://cdn.pawsnap.app"
    aws_region: str = "us-east-1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
