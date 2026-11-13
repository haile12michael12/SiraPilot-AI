"""Create the first account-scoped PostgreSQL schema.

Revision ID: 0001_postgres_foundation
Revises:
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_postgres_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    existing_tables.discard("alembic_version")
    if existing_tables:
        raise RuntimeError(
            "The initial PostgreSQL migration requires an empty schema; "
            "existing tables were left unchanged."
        )

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("company_key", sa.Text(), nullable=True),
        sa.Column("title_key", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="new", nullable=False),
        sa.Column("hidden", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("starred", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("application_stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_jobs_account_id_accounts"),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        sa.UniqueConstraint("account_id", "id", name="uq_jobs_account_id"),
    )
    op.create_index(
        "ix_jobs_account_updated", "jobs", ["account_id", sa.text("updated_at DESC")]
    )
    op.create_index(
        "ix_jobs_account_status_updated",
        "jobs",
        ["account_id", "status", sa.text("updated_at DESC")],
    )
    op.create_table(
        "listings",
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("platform_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("apply_type", sa.String(length=32), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("availability", sa.String(length=24), server_default="unknown", nullable=False),
        sa.Column("availability_message", sa.Text(), nullable=True),
        sa.Column("availability_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_detail_captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "job_id"],
            ["jobs.account_id", "jobs.id"],
            name="fk_listings_account_job",
        ),
        sa.PrimaryKeyConstraint("account_id", "id", name="pk_listings"),
        sa.UniqueConstraint(
            "account_id",
            "platform",
            "platform_id",
            name="uq_listings_account_platform_identity",
        ),
    )
    op.create_index("ix_listings_account_job", "listings", ["account_id", "job_id"])
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", sa.String(length=255), nullable=True),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("meta_hash", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id", "job_id"],
            ["jobs.account_id", "jobs.id"],
            name="fk_events_account_job",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "listing_id"],
            ["listings.account_id", "listings.id"],
            name="fk_events_account_listing",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
    )
    op.create_index(
        "ix_events_account_job_event", "events", ["account_id", "job_id", "event"]
    )
    op.create_index(
        "ix_events_account_job_ts",
        "events",
        ["account_id", "job_id", sa.text("ts DESC")],
    )
    op.create_index("ix_events_account_listing", "events", ["account_id", "listing_id"])
    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("requested", sa.String(length=32), nullable=True),
        sa.Column("provided", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "job_id"],
            ["jobs.account_id", "jobs.id"],
            name="fk_documents_account_job",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
    )
    op.create_index(
        "ix_documents_account_job_created",
        "documents",
        ["account_id", "job_id", sa.text("created_at DESC")],
    )
    op.create_table(
        "blocked_companies",
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_key", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(length=64), server_default="*", nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name="fk_blocked_companies_account_id_accounts"
        ),
        sa.PrimaryKeyConstraint(
            "account_id", "company_key", "platform", name="pk_blocked_companies"
        ),
    )
    op.create_index(
        "ix_blocked_companies_account_platform", "blocked_companies", ["account_id", "platform"]
    )


def downgrade() -> None:
    raise RuntimeError(
        "PostgreSQL migrations are forward-only; restore a verified backup instead."
    )
