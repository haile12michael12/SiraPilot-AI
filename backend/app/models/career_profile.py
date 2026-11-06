import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UtcTimestampMixin, UuidPrimaryKeyMixin


class CareerProfile(UuidPrimaryKeyMixin, UtcTimestampMixin, Base):
    __tablename__ = "career_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    headline: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(40))
    city: Mapped[str | None] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(120))
    current_status: Mapped[str | None] = mapped_column(String(40))
    onboarding_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class Skill(UuidPrimaryKeyMixin, UtcTimestampMixin, Base):
    __tablename__ = "profile_skills"
    __table_args__ = (
        UniqueConstraint("profile_id", "name"),
        CheckConstraint(
            "proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')",
            name="valid_proficiency_level",
        ),
        Index("ix_profile_skills_profile_id", "profile_id"),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    proficiency_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="intermediate"
    )


class WorkExperience(UuidPrimaryKeyMixin, UtcTimestampMixin, Base):
    __tablename__ = "work_experiences"
    __table_args__ = (Index("ix_work_experiences_profile_id", "profile_id"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    company: Mapped[str] = mapped_column(String(160), nullable=False)
    location: Mapped[str | None] = mapped_column(String(180))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text)


class Education(UuidPrimaryKeyMixin, UtcTimestampMixin, Base):
    __tablename__ = "profile_education"
    __table_args__ = (Index("ix_profile_education_profile_id", "profile_id"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    institution: Mapped[str] = mapped_column(String(180), nullable=False)
    degree: Mapped[str | None] = mapped_column(String(160))
    field_of_study: Mapped[str | None] = mapped_column(String(160))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)


class Certification(UuidPrimaryKeyMixin, UtcTimestampMixin, Base):
    __tablename__ = "profile_certifications"
    __table_args__ = (Index("ix_profile_certifications_profile_id", "profile_id"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(180))
    issued_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    credential_id: Mapped[str | None] = mapped_column(String(120))
    credential_url: Mapped[str | None] = mapped_column(String(500))


class Project(UuidPrimaryKeyMixin, UtcTimestampMixin, Base):
    __tablename__ = "profile_projects"
    __table_args__ = (Index("ix_profile_projects_profile_id", "profile_id"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    role: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    project_url: Mapped[str | None] = mapped_column(String(500))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)


class ProfileLink(UuidPrimaryKeyMixin, UtcTimestampMixin, Base):
    __tablename__ = "profile_links"
    __table_args__ = (Index("ix_profile_links_profile_id", "profile_id"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)


class CareerPreference(UuidPrimaryKeyMixin, UtcTimestampMixin, Base):
    __tablename__ = "career_preferences"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_profiles.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    career_goal: Mapped[str | None] = mapped_column(Text)
    employment_type: Mapped[str | None] = mapped_column(String(40))
    remote_preference: Mapped[str | None] = mapped_column(String(40))
    minimum_salary: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")


class PreferenceOption(UuidPrimaryKeyMixin, UtcTimestampMixin, Base):
    __tablename__ = "career_preference_options"
    __table_args__ = (
        UniqueConstraint("profile_id", "kind", "value"),
        Index("ix_career_preference_options_profile_id", "profile_id"),
        CheckConstraint(
            "kind IN ('job_title', 'industry', 'location')", name="valid_preference_kind"
        ),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[str] = mapped_column(String(180), nullable=False)