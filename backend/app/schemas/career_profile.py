from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

Proficiency = Literal["beginner", "intermediate", "advanced", "expert"]
PreferenceKind = Literal["job_title", "industry", "location"]


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    headline: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=10_000)
    phone: str | None = Field(default=None, max_length=40)
    city: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    current_status: str | None = Field(default=None, max_length=40)
    onboarding_step: int | None = Field(default=None, ge=0, le=9)


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str | None
    last_name: str | None
    headline: str | None
    summary: str | None
    phone: str | None
    city: str | None
    region: str | None
    country: str | None
    current_status: str | None
    onboarding_step: int
    onboarding_completed_at: datetime | None


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    proficiency_level: Proficiency = "intermediate"


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    proficiency_level: Proficiency | None = None


class SkillRead(SkillCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class ExperienceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    company: str = Field(min_length=1, max_length=160)
    location: str | None = Field(default=None, max_length=180)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = Field(default=None, max_length=10_000)


class ExperienceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    company: str | None = Field(default=None, min_length=1, max_length=160)
    location: str | None = Field(default=None, max_length=180)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    description: str | None = Field(default=None, max_length=10_000)


class ExperienceRead(ExperienceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class EducationCreate(BaseModel):
    institution: str = Field(min_length=1, max_length=180)
    degree: str | None = Field(default=None, max_length=160)
    field_of_study: str | None = Field(default=None, max_length=160)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = Field(default=None, max_length=10_000)


class EducationUpdate(BaseModel):
    institution: str | None = Field(default=None, min_length=1, max_length=180)
    degree: str | None = Field(default=None, max_length=160)
    field_of_study: str | None = Field(default=None, max_length=160)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = Field(default=None, max_length=10_000)


class EducationRead(EducationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class CertificationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    issuer: str | None = Field(default=None, max_length=180)
    issued_on: date | None = None
    expires_on: date | None = None
    credential_id: str | None = Field(default=None, max_length=120)
    credential_url: AnyHttpUrl | None = None


class CertificationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    issuer: str | None = Field(default=None, max_length=180)
    issued_on: date | None = None
    expires_on: date | None = None
    credential_id: str | None = Field(default=None, max_length=120)
    credential_url: AnyHttpUrl | None = None


class CertificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    issuer: str | None
    issued_on: date | None
    expires_on: date | None
    credential_id: str | None
    credential_url: AnyHttpUrl | None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    role: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=10_000)
    project_url: AnyHttpUrl | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    role: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=10_000)
    project_url: AnyHttpUrl | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    role: str | None
    description: str | None
    project_url: AnyHttpUrl | None
    start_date: date | None
    end_date: date | None


class ProfileLinkCreate(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    url: AnyHttpUrl


class ProfileLinkUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    url: AnyHttpUrl | None = None


class ProfileLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    label: str
    url: AnyHttpUrl


class CareerPreferenceUpdate(BaseModel):
    career_goal: str | None = Field(default=None, max_length=10_000)
    employment_type: str | None = Field(default=None, max_length=40)
    remote_preference: str | None = Field(default=None, max_length=40)
    minimum_salary: int | None = Field(default=None, ge=0, le=100_000_000)
    salary_currency: str = Field(default="USD", min_length=3, max_length=3)


class CareerPreferenceRead(CareerPreferenceUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class PreferenceOptionCreate(BaseModel):
    kind: PreferenceKind
    value: str = Field(min_length=1, max_length=180)


class PreferenceOptionsUpdate(BaseModel):
    items: list[PreferenceOptionCreate] = Field(max_length=100)


class PreferenceOptionRead(PreferenceOptionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class CareerProfileData(BaseModel):
    profile: ProfileRead
    skills: list[SkillRead] = Field(default_factory=list)
    experiences: list[ExperienceRead] = Field(default_factory=list)
    education: list[EducationRead] = Field(default_factory=list)
    certifications: list[CertificationRead] = Field(default_factory=list)
    projects: list[ProjectRead] = Field(default_factory=list)
    links: list[ProfileLinkRead] = Field(default_factory=list)
    preferences: CareerPreferenceRead | None = None
    preference_options: list[PreferenceOptionRead] = Field(default_factory=list)