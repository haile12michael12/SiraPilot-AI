"""Account-scoped PostgreSQL models for the initial job-tracking schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    desc,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Account(Base):
    """Opaque ownership namespace; authentication credentials are not part of this layer."""

    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    jobs: Mapped[list[Job]] = relationship(back_populates="account")
    blocked_companies: Mapped[list[BlockedCompany]] = relationship(back_populates="account")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("account_id", "id", name="uq_jobs_account_id"),
        Index("ix_jobs_account_updated", "account_id", desc("updated_at")),
        Index(
            "ix_jobs_account_status_updated",
            "account_id",
            "status",
            desc("updated_at"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    company_key: Mapped[str | None] = mapped_column(Text)
    title_key: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="new")
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    starred: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    application_stale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    account: Mapped[Account] = relationship(back_populates="jobs")
    listings: Mapped[list[Listing]] = relationship(back_populates="job")
    documents: Mapped[list[Document]] = relationship(back_populates="job")


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "job_id"],
            ["jobs.account_id", "jobs.id"],
            name="fk_listings_account_job",
        ),
        UniqueConstraint(
            "account_id", "platform", "platform_id", name="uq_listings_account_platform_identity"
        ),
        Index("ix_listings_account_job", "account_id", "job_id"),
    )

    account_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    platform_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    apply_type: Mapped[str | None] = mapped_column(String(32))
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    availability: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default="unknown"
    )
    availability_message: Mapped[str | None] = mapped_column(Text)
    availability_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_detail_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    job: Mapped[Job] = relationship(back_populates="listings")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "job_id"],
            ["jobs.account_id", "jobs.id"],
            name="fk_events_account_job",
        ),
        ForeignKeyConstraint(
            ["account_id", "listing_id"],
            ["listings.account_id", "listings.id"],
            name="fk_events_account_listing",
        ),
        Index("ix_events_account_job_event", "account_id", "job_id", "event"),
        Index("ix_events_account_job_ts", "account_id", "job_id", desc("ts")),
        Index("ix_events_account_listing", "account_id", "listing_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    job_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    listing_id: Mapped[str | None] = mapped_column(String(255))
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    meta_hash: Mapped[str | None] = mapped_column(String(64))

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "job_id"],
            ["jobs.account_id", "jobs.id"],
            name="fk_documents_account_job",
        ),
        Index("ix_documents_account_job_created", "account_id", "job_id", desc("created_at")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    job_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    requested: Mapped[str | None] = mapped_column(String(32))
    provided: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    content: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    job: Mapped[Job] = relationship(back_populates="documents")


class BlockedCompany(Base):
    __tablename__ = "blocked_companies"
    __table_args__ = (
        Index("ix_blocked_companies_account_platform", "account_id", "platform"),
    )

    account_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("accounts.id"),
        primary_key=True,
    )
    company_key: Mapped[str] = mapped_column(Text, primary_key=True)
    platform: Mapped[str] = mapped_column(String(64), primary_key=True, server_default="*")
    label: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    account: Mapped[Account] = relationship(back_populates="blocked_companies")
