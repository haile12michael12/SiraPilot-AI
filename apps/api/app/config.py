"""Profile-selected settings with process-environment overrides. See apps/api/README.md for database modes and configuration."""

from __future__ import annotations

import os
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import resolve_paths


def local_timezone() -> str:
    path = str(Path("/etc/localtime").resolve())
    value = os.environ.get("TZ") or (
        path.split("/zoneinfo/", 1)[1] if "/zoneinfo/" in path else "UTC"
    )
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError, ValueError:
        return "UTC"
    return value


class AIModelRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["openai", "anthropic", "local"]
    model: str = Field(min_length=1, max_length=128)
    input_cost_per_million: Decimal | None = Field(default=None, ge=0)
    output_cost_per_million: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    pricing_version: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def _validate_pricing(self) -> AIModelRoute:
        has_input_price = self.input_cost_per_million is not None
        has_output_price = self.output_cost_per_million is not None
        if has_input_price != has_output_price:
            raise ValueError("Both input and output prices must be configured together")
        if has_input_price != (self.pricing_version is not None):
            raise ValueError("A pricing version is required exactly when prices are configured")
        return self


class Settings(BaseSettings):
    # The selected profile, not pydantic's import location or the current home,
    # chooses the config file in get_settings(). Direct Settings construction is
    # intentionally environment-only, which keeps unit tests isolated by default.
    model_config = SettingsConfigDict(extra="ignore")

    # Test mode requires a throwaway Turso URL and isolates replica files under .test-db/.
    app_env: str = "local"

    db_path: str = "jobtracker.db"
    port: int = 3456
    # Relative path settings are anchored by core.paths after config loading.
    web_dist_path: Path | None = None

    turso_database_url: str | None = None
    turso_auth_token: SecretStr | None = None

    # Separate test credentials avoid editing the production database address.
    turso_test_database_url: str | None = None
    turso_test_auth_token: SecretStr | None = None

    # Local-first (pyturso) mode: reads and writes stay local and instant, pushed in
    # the background. False = libSQL embedded replica, where writes write-through.
    turso_local_first: bool = False
    # Seconds of write-quiet before a debounced background push fires.
    turso_push_debounce_seconds: float = 4.0
    # Maximum seconds pyturso may wait without network progress while connecting,
    # pulling, or pushing. Its synchronous HTTP adapter otherwise inherits Python's
    # unlimited socket timeout and can hold the process-wide database lock forever.
    turso_http_timeout_seconds: float = Field(default=10.0, gt=0)
    # Pull cadence for libSQL sync_interval or the local-first background scheduler.
    turso_pull_interval_seconds: int = 60

    # Maintenance reports live under <scripts_output_dir>/log/.
    scripts_output_dir: Path = Path("script-output")

    # Whole inactive days since a status event or note; zero disables attention.
    attention_applied_days: int = Field(default=21, ge=0)
    attention_in_process_days: int = Field(default=14, ge=0)
    # Enable on exactly one instance when multiple local APIs share a Turso database.
    notification_scheduler_enabled: bool = True
    stale_notification_timezone: str = Field(default_factory=local_timezone)
    web_push_enabled: bool = True
    web_push_subject: str = "https://github.com/haile12michael12/SiraPilot-AI"

    # AI providers are opt-in. Feature code selects a logical model alias from these routes.
    ai_model_routes: dict[str, AIModelRoute] = Field(default_factory=dict)
    ai_openai_api_key: SecretStr | None = None
    ai_anthropic_api_key: SecretStr | None = None
    ai_local_api_key: SecretStr | None = None
    ai_local_base_url: AnyHttpUrl | None = None
    ai_request_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    ai_max_output_tokens: int = Field(default=2048, gt=0, le=32768)
    ai_max_input_characters: int = Field(default=100_000, ge=1000, le=1_000_000)
    ai_max_agent_steps: int = Field(default=8, ge=1, le=32)
    ai_max_agent_tool_calls: int = Field(default=6, ge=0, le=32)

    # --- security ----------------------------------------------------------

    # The dashboard is same-origin in production. Allow Vite and the extension's
    # stable manifest-key origin for cross-origin browser requests.
    web_dev_origin: str = "http://localhost:5173"
    extension_id: str = "kepjjdggnlkcnedgabpknmpnknblokil"

    # Host allowlist guards against DNS rebinding; testserver admits FastAPI tests.
    trusted_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]

    # Optional shared-secret gate (`X-API-Key`) on every /api request. Unset means no
    # auth, matching a purely-localhost personal tool. Neither the dashboard nor the
    # extension sends this header, so enabling it requires a trusted intermediary that
    # injects it, or API scripts that supply it.
    api_key: SecretStr | None = None

    @model_validator(mode="after")
    def _apply_test_env(self) -> Settings:
        """Redirect both remote and replica paths for test mode; changing only the remote would mix test data with the production replica."""
        for alias in self.ai_model_routes:
            if not re.fullmatch(r"[a-zA-Z0-9_.-]+", alias):
                raise ValueError(
                    "AI model aliases may contain only letters, digits, dot, dash, and underscore"
                )
        if self.app_env != "test":
            return self
        if not self.turso_test_database_url:
            raise ValueError(
                "APP_ENV=test requires TURSO_TEST_DATABASE_URL — point it at a "
                "throwaway Turso database, never the real primary."
            )
        self.turso_database_url = self.turso_test_database_url
        self.turso_auth_token = self.turso_test_auth_token
        # Relocate the whole replica family (db, .sync, .sync-wal, …) into a sibling
        # .test-db/ so it never sits next to, or clobbers, prod's files.
        p = Path(self.db_path)
        self.db_path = str(p.parent / ".test-db" / p.name)
        return self

    @field_validator("ai_local_base_url")
    @classmethod
    def _reject_credentials_in_local_url(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is not None and (
            value.username or value.password or value.query or value.fragment
        ):
            raise ValueError(
                "AI_LOCAL_BASE_URL cannot contain credentials, query, or fragment data"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """Load the selected profile's config, then let process env override it."""
    paths = resolve_paths()
    return Settings(  # type: ignore[call-arg]
        _env_file=paths.config_file, _env_file_encoding="utf-8"
    )
