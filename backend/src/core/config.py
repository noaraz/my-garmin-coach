from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

_DEV_SECRETS = {
    "dev-jwt-secret-change-in-prod",
    "dev-secret-change-in-prod",
    "dev-bootstrap-secret-change-in-prod",
}


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:////data/garmincoach.db"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # JWT / Auth
    jwt_secret: str = "dev-jwt-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Garmin token encryption
    garmincoach_secret_key: str = "dev-secret-change-in-prod"

    # Admin bootstrap
    bootstrap_secret: str = "dev-bootstrap-secret-change-in-prod"

    # Google OAuth
    google_client_id: str = ""

    model_config = {"env_file": ".env"}

    @model_validator(mode="after")
    def enforce_prod_secrets(self) -> Settings:
        if self.environment == "production":
            if self.jwt_secret in _DEV_SECRETS:
                raise ValueError("JWT_SECRET must be set to a strong secret in production")
            if self.garmincoach_secret_key in _DEV_SECRETS:
                raise ValueError("GARMINCOACH_SECRET_KEY must be set in production")
            if self.bootstrap_secret in _DEV_SECRETS:
                raise ValueError("BOOTSTRAP_SECRET must be set in production")
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
