import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accept_valid_local_configuration() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:pass@localhost:5432/sirapilot",
        redis_url="redis://localhost:6379/0",
        secret_key="sufficiently-long-test-secret-key-value",
    )

    assert settings.api_v1_prefix == "/api/v1"
    assert settings.cors_origins == ["http://localhost:5173"]


def test_settings_reject_non_postgresql_database_url() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+psycopg"):
        Settings(
            _env_file=None,
            database_url="sqlite:///local.db",
            redis_url="redis://localhost:6379/0",
            secret_key="sufficiently-long-test-secret-key-value",
        )


def test_settings_reject_short_secret() -> None:
    with pytest.raises(ValidationError, match="secret_key"):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://user:pass@localhost:5432/sirapilot",
            redis_url="redis://localhost:6379/0",
            secret_key="short",
        )


def test_settings_include_phase_one_security_defaults() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:pass@localhost:5432/sirapilot",
        redis_url="redis://localhost:6379/0",
        secret_key="sufficiently-long-test-secret-key-value",
    )

    assert settings.auth_access_token_minutes == 15
    assert settings.auth_refresh_token_days == 30
    assert settings.cookie_samesite == "lax"
    assert settings.max_cv_upload_bytes == 10 * 1024 * 1024


def test_production_requires_secure_cookies_and_email_delivery() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+psycopg://user:pass@localhost:5432/sirapilot",
            redis_url="redis://localhost:6379/0",
            secret_key="secure-production-test-secret-value",
        )
