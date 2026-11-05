import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, MetaData, Uuid, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.engine import Engine

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)
UuidPrimaryKey = Annotated[
    uuid.UUID,
    mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
]
UtcTimestamp = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now()),
]


class Base(DeclarativeBase):
    metadata = metadata


class UuidPrimaryKeyMixin:
    id: Mapped[UuidPrimaryKey]


class UtcTimestampMixin:
    created_at: Mapped[UtcTimestamp]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def create_db_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)
