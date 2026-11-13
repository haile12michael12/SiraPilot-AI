"""Configuration for the separate PostgreSQL target database."""

from __future__ import annotations

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    database_url: SecretStr | None = None
    pool_size: int = Field(default=5, ge=1)
    max_overflow: int = Field(default=5, ge=0)
    pool_timeout_seconds: float = Field(default=30, gt=0)

    @model_validator(mode="after")
    def _validate_database_url(self) -> PostgresSettings:
        if self.database_url is None:
            return self
        try:
            drivername = make_url(self.database_url.get_secret_value()).drivername
        except ArgumentError:
            raise ValueError("POSTGRES_DATABASE_URL must be a valid PostgreSQL URL") from None
        if drivername != "postgresql+psycopg":
            raise ValueError("POSTGRES_DATABASE_URL must use the postgresql+psycopg driver")
        return self

    def require_database_url(self) -> str:
        if self.database_url is None:
            raise RuntimeError("POSTGRES_DATABASE_URL must be configured for PostgreSQL operations")
        return self.database_url.get_secret_value()


def load_postgres_settings() -> PostgresSettings:
    """Load PostgreSQL-only settings without changing current SQLite/Turso settings."""
    return PostgresSettings()
