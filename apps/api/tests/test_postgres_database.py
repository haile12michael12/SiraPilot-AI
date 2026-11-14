from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import NullPool

from alembic import command
from app.config import Settings
from app.core.paths import settings_paths
from app.infra.postgres.config import AuthSettings, PostgresSettings, load_postgres_settings
from app.infra.postgres.models import Account
from app.infra.postgres.repositories import JobRepository
from app.infra.postgres.sessions import PostgresDatabase
from app.main import create_app
from app.modules.auth.dependencies import get_auth_settings, get_postgres_database
from app.modules.auth.models import AuthToken
from app.modules.auth.repository import AuthRepository
from app.modules.auth.router import _auth_page
from app.modules.auth.service import (
    login,
    register,
    request_password_reset,
    request_verification,
    reset_password,
    token_digest,
    verify_email,
)
from app.platform.runtime import RuntimeResources
from app.shared.timeutil import utc_now

API_ROOT = Path(__file__).resolve().parents[1]


def _alembic_config(connection: object | None = None) -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def _upgrade(engine: Engine) -> None:
    with engine.connect() as connection:
        command.upgrade(_alembic_config(connection), "head")


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    raw_url = os.environ.get("POSTGRES_TEST_URL")
    if not raw_url:
        pytest.skip("set POSTGRES_TEST_URL to a disposable local *_test database")

    url = make_url(raw_url)
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or not (url.database or "").endswith("_test")
    ):
        pytest.fail(
            "POSTGRES_TEST_URL must use postgresql+psycopg, a loopback host, "
            "and a database name ending in _test"
        )

    admin_engine = create_engine(url, poolclass=NullPool)
    schema = f"test_sirapilot_{uuid4().hex}"
    schema_created = False
    test_engine: Engine | None = None
    try:
        with admin_engine.begin() as connection:
            database_name = connection.scalar(text("SELECT current_database()"))
            if database_name != url.database:
                pytest.fail("POSTGRES_TEST_URL did not connect to its named test database")
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            schema_created = True

        test_url = url.update_query_dict({"options": f"-csearch_path={schema}"})
        test_engine = create_engine(test_url, poolclass=NullPool)
        _upgrade(test_engine)
        yield test_engine
    finally:
        if test_engine is not None:
            test_engine.dispose()
        if schema_created:
            with admin_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


@pytest.fixture
def postgres_database(postgres_engine: Engine) -> Iterator[PostgresDatabase]:
    database = PostgresDatabase(
        PostgresSettings(database_url=str(postgres_engine.url), pool_size=1, max_overflow=0)
    )
    try:
        yield database
    finally:
        database.close()


def test_postgres_settings_do_not_change_legacy_sqlite_records(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("POSTGRES_DATABASE_URL", raising=False)
    conn.execute(
        "INSERT INTO jobs (id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
        ("legacy-job", "new", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    )

    settings = load_postgres_settings()
    with pytest.raises(RuntimeError, match="POSTGRES_DATABASE_URL"):
        settings.require_database_url()

    row = conn.execute("SELECT id, status FROM jobs WHERE id = ?", ("legacy-job",)).fetchone()
    assert row == ("legacy-job", "new")


def test_postgres_settings_redact_credentials() -> None:
    settings = PostgresSettings(
        database_url="postgresql+psycopg://tracker:example-password@localhost/sirapilot_test"
    )
    assert "example-password" not in repr(settings)


def test_auth_pages_allow_same_origin_requests_under_csp() -> None:
    response = _auth_page("<!doctype html>")

    assert "connect-src 'self';" in response.headers["Content-Security-Policy"]


@pytest.mark.postgres
def test_alembic_upgrade_is_repeatable_and_creates_justified_indexes(
    postgres_engine: Engine,
) -> None:
    _upgrade(postgres_engine)
    with postgres_engine.connect() as connection:
        command.check(_alembic_config(connection))

    inspector = inspect(postgres_engine)
    assert {
        "accounts",
        "users",
        "auth_tokens",
        "auth_sessions",
        "auth_rate_limits",
        "jobs",
        "listings",
        "events",
        "documents",
        "blocked_companies",
        "alembic_version",
    }.issubset(inspector.get_table_names())
    assert {index["name"] for index in inspector.get_indexes("jobs")} >= {
        "ix_jobs_account_updated",
        "ix_jobs_account_status_updated",
    }
    assert "fk_listings_account_job" in {
        constraint["name"] for constraint in inspector.get_foreign_keys("listings")
    }


@pytest.mark.postgres
def test_alembic_downgrade_refuses_to_drop_postgres_data(postgres_engine: Engine) -> None:
    with pytest.raises(RuntimeError, match="forward-only"), postgres_engine.connect() as connection:
        command.downgrade(_alembic_config(connection), "base")

    assert "jobs" in inspect(postgres_engine).get_table_names()


@pytest.mark.postgres
def test_initial_migration_refuses_a_nonempty_schema_without_changing_records(
    postgres_engine: Engine,
) -> None:
    schema = f"test_existing_{uuid4().hex}"
    with postgres_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    schema_url = postgres_engine.url.set(query={"options": f"-csearch_path={schema}"})
    existing_engine = create_engine(schema_url, poolclass=NullPool)
    try:
        with existing_engine.begin() as connection:
            connection.execute(text("CREATE TABLE existing_records (value TEXT NOT NULL)"))
            connection.execute(text("INSERT INTO existing_records VALUES ('preserved')"))

        with pytest.raises(RuntimeError, match="requires an empty schema"):
            _upgrade(existing_engine)

        with existing_engine.connect() as connection:
            assert connection.scalar(text("SELECT value FROM existing_records")) == "preserved"
            assert "accounts" not in inspect(connection).get_table_names()
    finally:
        existing_engine.dispose()
        with postgres_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


@pytest.mark.postgres
def test_job_repository_scopes_reads_and_transactions_rollback(
    postgres_database: PostgresDatabase,
) -> None:
    first_account, other_account = uuid4(), uuid4()
    with postgres_database.transaction() as session:
        session.add_all([Account(id=first_account), Account(id=other_account)])
        job = JobRepository(session, first_account).create(
            title="Example role", company="Example employer"
        )
        job_id = job.id

    with postgres_database.session() as session:
        assert JobRepository(session, first_account).get(job_id) is not None
        assert JobRepository(session, other_account).get(job_id) is None

    with (
        pytest.raises(RuntimeError, match="rollback probe"),
        postgres_database.transaction() as session,
    ):
        JobRepository(session, first_account).create(
            title="Uncommitted role", company="Example employer"
        )
        raise RuntimeError("rollback probe")

    with postgres_database.session() as session:
        assert [job.title for job in JobRepository(session, first_account).list_recent()] == [
            "Example role"
        ]


@pytest.mark.postgres
def test_postgres_migration_leaves_existing_sqlite_records_accessible(
    conn: sqlite3.Connection, postgres_engine: Engine
) -> None:
    legacy_id = "legacy-record"
    conn.execute(
        "INSERT INTO jobs (id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (legacy_id, "applied", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"),
    )

    _upgrade(postgres_engine)

    row = conn.execute(
        "SELECT id, status, created_at, updated_at FROM jobs WHERE id = ?", (legacy_id,)
    ).fetchone()
    assert row == (legacy_id, "applied", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z")


@pytest.mark.postgres
def test_auth_lifecycle_verifies_account_and_revokes_sessions_on_password_reset(
    postgres_database: PostgresDatabase,
) -> None:
    settings = AuthSettings(
        public_base_url="https://auth.example.test",
        email_from="no-reply@example.test",
        smtp_host="smtp.example.test",
        rate_limit_secret="rate-limit-secret-value-32-characters",
    )
    email, limited = register(
        postgres_database,
        settings,
        email="person@example.test",
        password="a sufficiently long password",
        client_ip="127.0.0.1",
    )
    assert not limited
    assert email is not None
    with postgres_database.session() as session:
        user = AuthRepository(session).user_by_email("person@example.test")
        assert user is not None
        assert user.password_hash != "a sufficiently long password"
        token = session.scalar(
            select(AuthToken).where(
                AuthToken.user_id == user.id, AuthToken.purpose == "verification"
            )
        )
        assert token is not None
        assert token.token_hash == token_digest(email.token)
        assert email.token not in token.token_hash

    assert verify_email(postgres_database, email.token)
    assert not verify_email(postgres_database, email.token)
    created, limited = login(
        postgres_database,
        settings,
        email="person@example.test",
        password="a sufficiently long password",
        client_ip="127.0.0.1",
    )
    assert not limited
    assert created is not None
    with postgres_database.session() as session:
        assert (
            AuthRepository(session).get_active_session(token_digest(created.token), utc_now())
            is not None
        )

    reset_email, limited = request_password_reset(
        postgres_database, settings, email="person@example.test", client_ip="127.0.0.1"
    )
    assert not limited
    assert reset_email is not None
    updated, limited = reset_password(
        postgres_database,
        settings,
        token=reset_email.token,
        password="a different long password",
        client_ip="127.0.0.1",
    )
    assert updated and not limited
    with postgres_database.session() as session:
        assert (
            AuthRepository(session).get_active_session(token_digest(created.token), utc_now())
            is None
        )
    assert not verify_email(postgres_database, reset_email.token)

    new_login, limited = login(
        postgres_database,
        settings,
        email="person@example.test",
        password="a different long password",
        client_ip="127.0.0.1",
    )
    assert new_login is not None and not limited


@pytest.mark.postgres
def test_auth_registration_throttles_and_keeps_unknown_recovery_generic(
    postgres_database: PostgresDatabase,
) -> None:
    settings = AuthSettings(
        public_base_url="https://auth.example.test",
        email_from="no-reply@example.test",
        smtp_host="smtp.example.test",
        rate_limit_secret="rate-limit-secret-value-32-characters",
    )
    for _ in range(3):
        message, limited = request_verification(
            postgres_database, settings, email="unknown@example.test", client_ip="127.0.0.1"
        )
        assert message is None and not limited
    message, limited = request_verification(
        postgres_database, settings, email="unknown@example.test", client_ip="127.0.0.1"
    )
    assert message is None and limited

    message, limited = request_password_reset(
        postgres_database, settings, email="unknown@example.test", client_ip="127.0.0.1"
    )
    assert message is None and not limited


@pytest.mark.postgres
def test_auth_http_routes_are_public_but_legacy_data_routes_remain_protected(
    postgres_database: PostgresDatabase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth_settings = AuthSettings(
        public_base_url="https://testserver",
        email_from="no-reply@example.test",
        smtp_host="smtp.example.test",
        rate_limit_secret="rate-limit-secret-value-32-characters",
    )
    settings = Settings(
        _env_file=None,
        app_env="local",
        db_path=str(tmp_path / "jobs.db"),
        web_dist_path=tmp_path / "missing-dashboard",
        api_key="protected-key",
        turso_auth_token=None,
        turso_database_url=None,
    )
    paths = settings_paths(
        settings,
        environ={
            "JOB_TRACKER_PROFILE": "direct",
            "JOB_TRACKER_DATA_DIR": str(tmp_path),
            "JOB_TRACKER_CONFIG_DIR": str(tmp_path / "config"),
            "JOB_TRACKER_STATE_DIR": str(tmp_path / "state"),
            "JOB_TRACKER_BACKUP_DIR": str(tmp_path / "backups"),
        },
    )
    application = create_app(settings, resources=RuntimeResources(paths))
    application.dependency_overrides[get_postgres_database] = lambda: postgres_database
    application.dependency_overrides[get_auth_settings] = lambda: auth_settings
    sent: list[str] = []
    monkeypatch.setattr(
        "app.modules.auth.router.send_auth_email",
        lambda settings, *, recipient, purpose, token: sent.append(token),
    )

    client = TestClient(application, base_url="https://testserver")
    try:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "browser@example.test", "password": "a sufficiently long password"},
        )
        assert registration.status_code == 202
        assert client.get("/api/jobs").status_code == 401
        assert len(sent) == 1

        verified = client.post("/api/v1/auth/verify-email", json={"token": sent.pop()})
        assert verified.status_code == 200
        logged_in = client.post(
            "/api/v1/auth/sessions",
            json={"email": "browser@example.test", "password": "a sufficiently long password"},
        )
        assert logged_in.status_code == 200
        assert "access_token" not in logged_in.json()
        assert logged_in.cookies.get("__Host-sirapilot_session")
        set_cookie = logged_in.headers["set-cookie"]
        assert "Secure" in set_cookie and "HttpOnly" in set_cookie and "SameSite=lax" in set_cookie
        assert client.get("/api/v1/auth/me").json()["email"] == "browser@example.test"
        assert client.post("/api/v1/auth/logout").status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401

        extension_origin = f"chrome-extension://{settings.extension_id}"
        extension_login = client.post(
            "/api/v1/auth/sessions",
            headers={"Origin": extension_origin},
            json={"email": "browser@example.test", "password": "a sufficiently long password"},
        )
        assert extension_login.status_code == 200
        assert extension_login.json()["token_type"] == "Bearer"
        assert extension_login.json()["access_token"]
        assert (
            client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {extension_login.json()['access_token']}"},
            ).status_code
            == 200
        )
    finally:
        client.close()
        application.dependency_overrides.clear()
