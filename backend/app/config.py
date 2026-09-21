"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/adplatform"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/adplatform"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # App
    app_name: str = "AI Personalization Platform"
    debug: bool = True
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    # ML
    model_path: str = "ml_models/ctr_model.pkl"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
