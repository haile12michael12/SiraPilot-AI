from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import ArgumentError, make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    app_name: str = "SiraPilot AI"
    app_env: Literal["development", "test", "staging", "production"] = (
        "development"
    )
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(min_length=1)
    redis_url: str = Field(min_length=1)
    secret_key: SecretStr = Field(min_length=32)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        try:
            parsed = make_url(value)
        except (ArgumentError, ValueError) as exc:
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL") from exc
        if parsed.drivername != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use the postgresql+psycopg driver")
        if not parsed.host or not parsed.database:
            raise ValueError("DATABASE_URL must include a host and database name")
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
            raise ValueError("REDIS_URL must be a valid Redis URL")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("CORS_ORIGINS must contain at least one origin")
        for origin in value:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or origin == "*"
            ):
                raise ValueError(f"Invalid CORS origin: {origin}")
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if (
            self.app_env == "production"
            and self.secret_key.get_secret_value().startswith("local-development-")
        ):
            raise ValueError("A production SECRET_KEY must not use a local value")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
