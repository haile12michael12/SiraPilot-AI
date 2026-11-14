"""Configuration for the separate PostgreSQL target database."""

from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
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


class AuthSettings(BaseSettings):
    """Settings required only when PostgreSQL-backed authentication is enabled."""

    model_config = SettingsConfigDict(env_prefix="AUTH_", extra="ignore")

    public_base_url: str | None = None
    email_from: EmailStr | None = None
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    smtp_use_ssl: bool = False
    rate_limit_secret: SecretStr | None = None
    session_ttl_seconds: int = Field(default=1_209_600, ge=300, le=2_592_000)
    verification_ttl_seconds: int = Field(default=86_400, ge=300, le=604_800)
    password_reset_ttl_seconds: int = Field(default=3_600, ge=300, le=86_400)
    smtp_timeout_seconds: float = Field(default=10, gt=0, le=60)

    @field_validator("smtp_host", "smtp_username", mode="before")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> AuthSettings:
        if self.smtp_starttls and self.smtp_use_ssl:
            raise ValueError("AUTH_SMTP_STARTTLS and AUTH_SMTP_USE_SSL cannot both be enabled")
        if (self.smtp_username is None) != (self.smtp_password is None):
            raise ValueError("AUTH_SMTP_USERNAME and AUTH_SMTP_PASSWORD must be configured together")
        if self.rate_limit_secret is not None and len(
            self.rate_limit_secret.get_secret_value()
        ) < 32:
            raise ValueError("AUTH_RATE_LIMIT_SECRET must contain at least 32 characters")
        return self

    def require_ready(self) -> AuthSettings:
        missing = [
            name
            for name, value in (
                ("AUTH_PUBLIC_BASE_URL", self.public_base_url),
                ("AUTH_EMAIL_FROM", self.email_from),
                ("AUTH_SMTP_HOST", self.smtp_host),
                ("AUTH_RATE_LIMIT_SECRET", self.rate_limit_secret),
            )
            if value is None
        ]
        if missing:
            raise RuntimeError(f"PostgreSQL authentication requires: {', '.join(missing)}")
        assert self.public_base_url is not None
        parsed = urlsplit(self.public_base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("AUTH_PUBLIC_BASE_URL must be an HTTPS origin or base path")
        if parsed.query or parsed.fragment:
            raise ValueError("AUTH_PUBLIC_BASE_URL cannot contain a query or fragment")
        if not (self.smtp_starttls or self.smtp_use_ssl):
            raise ValueError("PostgreSQL authentication requires TLS-protected SMTP")
        return self
