from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

from app.infra.postgres.config import PostgresSettings, load_postgres_settings
from app.infra.postgres.models import Account, Job
from app.infra.postgres.repositories import JobRepository
from app.infra.postgres.sessions import PostgresDatabase

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
        "jobs",
        "listings",
        "events",
        "documents",
        "blocked_companies",
        "alembic_version",
    }.issubset(inspector.get_table_names())
    assert {
        index["name"] for index in inspector.get_indexes("jobs")
    } >= {"ix_jobs_account_updated", "ix_jobs_account_status_updated"}
    assert "fk_listings_account_job" in {
        constraint["name"] for constraint in inspector.get_foreign_keys("listings")
    }


@pytest.mark.postgres
def test_alembic_downgrade_refuses_to_drop_postgres_data(postgres_engine: Engine) -> None:
    with pytest.raises(RuntimeError, match="forward-only"):
        with postgres_engine.connect() as connection:
            command.downgrade(_alembic_config(connection), "base")

    assert "jobs" in inspect(postgres_engine).get_table_names()


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

    with pytest.raises(RuntimeError, match="rollback probe"):
        with postgres_database.transaction() as session:
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
    assert row == (
        legacy_id,
        "applied",
        "2026-01-01T00:00:00Z",
        "2026-01-02T00:00:00Z",
    )
