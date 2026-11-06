"""Add Phase 1 authentication, career profile, and CV tables.

Revision ID: 0002_phase_1_core
Revises: 0001_phase_0_baseline
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_phase_1_core"
down_revision: str | None = "0001_phase_0_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "career_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=100)),
        sa.Column("last_name", sa.String(length=100)),
        sa.Column("headline", sa.String(length=200)),
        sa.Column("summary", sa.Text()),
        sa.Column("phone", sa.String(length=40)),
        sa.Column("city", sa.String(length=120)),
        sa.Column("region", sa.String(length=120)),
        sa.Column("country", sa.String(length=120)),
        sa.Column("current_status", sa.String(length=40)),
        sa.Column("onboarding_step", sa.Integer(), nullable=False),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_career_profiles_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_career_profiles"),
        sa.UniqueConstraint("user_id", name="uq_career_profiles_user_id"),
    )
    op.create_table(
        "career_preferences",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("profile_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("career_goal", sa.Text()),
        sa.Column("employment_type", sa.String(length=40)),
        sa.Column("remote_preference", sa.String(length=40)),
        sa.Column("minimum_salary", sa.Integer()),
        sa.Column("salary_currency", sa.String(length=3), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["profile_id"], ["career_profiles.id"], name="fk_career_preferences_profile_id_career_profiles", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_career_preferences"),
        sa.UniqueConstraint("profile_id", name="uq_career_preferences_profile_id"),
    )
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_email_verification_tokens_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_email_verification_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_email_verification_tokens_token_hash"),
    )
    op.create_index("ix_email_verification_tokens_user_id", "email_verification_tokens", ["user_id"])
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_password_reset_tokens_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("family_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("replaced_by_id", sa.Uuid(as_uuid=True)),
        *_timestamps(),
        sa.ForeignKeyConstraint(["replaced_by_id"], ["refresh_sessions.id"], name="fk_refresh_sessions_replaced_by_id_refresh_sessions", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_refresh_sessions_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_sessions_token_hash"),
    )
    op.create_index("ix_refresh_sessions_user_family", "refresh_sessions", ["user_id", "family_id"])

    profile_tables = (
        ("profile_skills", [sa.Column("name", sa.String(length=120), nullable=False), sa.Column("proficiency_level", sa.String(length=20), nullable=False)], [sa.UniqueConstraint("profile_id", "name", name="uq_profile_skills_profile_id") , sa.CheckConstraint("proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')", name="ck_profile_skills_valid_proficiency_level")]),
        ("work_experiences", [sa.Column("title", sa.String(length=160), nullable=False), sa.Column("company", sa.String(length=160), nullable=False), sa.Column("location", sa.String(length=180)), sa.Column("start_date", sa.Date()), sa.Column("end_date", sa.Date()), sa.Column("is_current", sa.Boolean(), nullable=False), sa.Column("description", sa.Text())], []),
        ("profile_education", [sa.Column("institution", sa.String(length=180), nullable=False), sa.Column("degree", sa.String(length=160)), sa.Column("field_of_study", sa.String(length=160)), sa.Column("start_date", sa.Date()), sa.Column("end_date", sa.Date()), sa.Column("description", sa.Text())], []),
        ("profile_certifications", [sa.Column("name", sa.String(length=180), nullable=False), sa.Column("issuer", sa.String(length=180)), sa.Column("issued_on", sa.Date()), sa.Column("expires_on", sa.Date()), sa.Column("credential_id", sa.String(length=120)), sa.Column("credential_url", sa.String(length=500))], []),
        ("profile_projects", [sa.Column("name", sa.String(length=180), nullable=False), sa.Column("role", sa.String(length=160)), sa.Column("description", sa.Text()), sa.Column("project_url", sa.String(length=500)), sa.Column("start_date", sa.Date()), sa.Column("end_date", sa.Date())], []),
        ("profile_links", [sa.Column("label", sa.String(length=80), nullable=False), sa.Column("url", sa.String(length=500), nullable=False)], []),
    )
    for table_name, columns, constraints in profile_tables:
        op.create_table(
            table_name,
            sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("profile_id", sa.Uuid(as_uuid=True), nullable=False),
            *columns,
            *_timestamps(),
            sa.ForeignKeyConstraint(["profile_id"], ["career_profiles.id"], name=f"fk_{table_name}_profile_id_career_profiles", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=f"pk_{table_name}"),
            *constraints,
        )
        if table_name != "profile_skills":
            op.create_index(f"ix_{table_name}_profile_id", table_name, ["profile_id"])
        else:
            op.create_index("ix_profile_skills_profile_id", table_name, ["profile_id"])

    op.create_table(
        "career_preference_options",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("profile_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("value", sa.String(length=180), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("kind IN ('job_title', 'industry', 'location')", name="ck_career_preference_options_valid_preference_kind"),
        sa.ForeignKeyConstraint(["profile_id"], ["career_profiles.id"], name="fk_career_preference_options_profile_id_career_profiles", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_career_preference_options"),
        sa.UniqueConstraint("profile_id", "kind", "value", name="uq_career_preference_options_profile_id"),
    )
    op.create_index("ix_career_preference_options_profile_id", "career_preference_options", ["profile_id"])
    op.create_table(
        "cv_documents",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_name", sa.String(length=80), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_cv_documents_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_cv_documents"),
        sa.UniqueConstraint("storage_name", name="uq_cv_documents_storage_name"),
    )
    op.create_index("ix_cv_documents_user_id", "cv_documents", ["user_id"])
    op.create_table(
        "cv_proposal_items",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("organization", sa.String(length=180)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("description", sa.Text()),
        sa.Column("confidence", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["document_id"], ["cv_documents.id"], name="fk_cv_proposal_items_document_id_cv_documents", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_cv_proposal_items"),
    )
    op.create_index("ix_cv_proposal_items_document_id", "cv_proposal_items", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_cv_proposal_items_document_id", table_name="cv_proposal_items")
    op.drop_table("cv_proposal_items")
    op.drop_index("ix_cv_documents_user_id", table_name="cv_documents")
    op.drop_table("cv_documents")
    op.drop_index("ix_career_preference_options_profile_id", table_name="career_preference_options")
    op.drop_table("career_preference_options")
    for table_name in (
        "profile_links",
        "profile_projects",
        "profile_certifications",
        "profile_education",
        "work_experiences",
        "profile_skills",
    ):
        op.drop_index(f"ix_{table_name}_profile_id", table_name=table_name)
        op.drop_table(table_name)
    op.drop_index("ix_refresh_sessions_user_family", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_email_verification_tokens_user_id", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_table("career_preferences")
    op.drop_table("career_profiles")
    op.drop_table("users")