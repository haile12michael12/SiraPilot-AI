import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import (
    Base,
    UtcTimestampMixin,
    UuidPrimaryKeyMixin,
    create_db_engine,
)


class FoundationRecord(UuidPrimaryKeyMixin, UtcTimestampMixin, Base):
    __tablename__ = "foundation_test_records"

    name: Mapped[str] = mapped_column()


def test_database_engine_connectivity() -> None:
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()


def test_base_declares_uuid_and_utc_timestamp_foundation() -> None:
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"
    assert FoundationRecord.__table__.c.id.type.native_uuid
    assert FoundationRecord.__table__.c.created_at.type.timezone
    assert FoundationRecord.__table__.c.updated_at.type.timezone


def test_uuid_and_timestamp_mixins_persist() -> None:
    engine = create_db_engine("sqlite+pysqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            record = FoundationRecord(name="test")
            session.add(record)
            session.commit()
            session.refresh(record)

            assert isinstance(record.id, uuid.UUID)
            assert record.created_at is not None
            assert record.updated_at is not None
    finally:
        engine.dispose()


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Set TEST_DATABASE_URL to run the PostgreSQL connectivity check.",
)
def test_configured_postgresql_connectivity() -> None:
    engine = create_db_engine(os.environ["TEST_DATABASE_URL"])
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()
