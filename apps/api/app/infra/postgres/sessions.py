"""Explicit PostgreSQL engine, session, and transaction lifecycle."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infra.postgres.config import PostgresSettings


class PostgresDatabase:
    def __init__(self, settings: PostgresSettings) -> None:
        self.engine: Engine = create_engine(
            settings.require_database_url(),
            pool_pre_ping=True,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            pool_timeout=settings.pool_timeout_seconds,
        )
        self._session_factory = sessionmaker(
            bind=self.engine, autoflush=False, expire_on_commit=False
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Yield a short-lived session; uncommitted writes are rolled back on close."""
        with self._session_factory() as session:
            yield session

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        """Commit the complete unit on success and roll it back on any failure."""
        with self._session_factory.begin() as session:
            yield session

    def close(self) -> None:
        self.engine.dispose()


def session_dependency(database: PostgresDatabase) -> Iterator[Session]:
    """Provide a request-scoped read session without committing implicitly."""
    with database.session() as session:
        yield session
