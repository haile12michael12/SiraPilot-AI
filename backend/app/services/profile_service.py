from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    CareerPreference,
    CareerProfile,
    Certification,
    Education,
    PreferenceOption,
    ProfileLink,
    Project,
    Skill,
    User,
    WorkExperience,
)
from app.schemas.career_profile import (
    CareerPreferenceRead,
    CareerProfileData,
    CertificationRead,
    EducationRead,
    ExperienceRead,
    PreferenceOptionRead,
    ProfileLinkRead,
    ProfileRead,
    ProjectRead,
    SkillRead,
)

OwnedModel = TypeVar(
    "OwnedModel",
    Skill,
    WorkExperience,
    Education,
    Certification,
    Project,
    ProfileLink,
)


def get_or_create_profile(session: Session, user: User) -> CareerProfile:
    profile = session.scalar(
        select(CareerProfile).where(CareerProfile.user_id == user.id)
    )
    if profile is None:
        profile = CareerProfile(user_id=user.id)
        session.add(profile)
        session.flush()
    return profile


def get_owned_record(
    session: Session,
    user: User,
    model: type[OwnedModel],
    record_id: UUID,
) -> OwnedModel:
    profile = get_or_create_profile(session, user)
    record = session.scalar(
        select(model).where(model.id == record_id, model.profile_id == profile.id)
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found")
    return record


def create_owned_record(
    session: Session,
    user: User,
    model: type[OwnedModel],
    values: dict,
) -> OwnedModel:
    profile = get_or_create_profile(session, user)
    record = model(profile_id=profile.id, **values)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def update_owned_record(
    session: Session,
    user: User,
    model: type[OwnedModel],
    record_id: UUID,
    values: dict,
) -> OwnedModel:
    record = get_owned_record(session, user, model, record_id)
    for field, value in values.items():
        setattr(record, field, value)
    session.commit()
    session.refresh(record)
    return record


def delete_owned_record(
    session: Session,
    user: User,
    model: type[OwnedModel],
    record_id: UUID,
) -> None:
    record = get_owned_record(session, user, model, record_id)
    session.delete(record)
    session.commit()


def list_owned_records(
    session: Session,
    user: User,
    model: type[OwnedModel],
) -> list[OwnedModel]:
    profile = get_or_create_profile(session, user)
    records = list(
        session.scalars(
            select(model)
            .where(model.profile_id == profile.id)
            .order_by(model.created_at.desc())
        )
    )
    session.commit()
    return records


def get_profile_data(session: Session, user: User) -> CareerProfileData:
    profile = get_or_create_profile(session, user)
    preference = session.scalar(
        select(CareerPreference).where(CareerPreference.profile_id == profile.id)
    )

    def values(model: type[OwnedModel], schema: type) -> list:
        records = session.scalars(
            select(model)
            .where(model.profile_id == profile.id)
            .order_by(model.created_at.desc())
        )
        return [schema.model_validate(record) for record in records]

    options = session.scalars(
        select(PreferenceOption)
        .where(PreferenceOption.profile_id == profile.id)
        .order_by(PreferenceOption.kind, PreferenceOption.value)
    )
    return CareerProfileData(
        profile=ProfileRead.model_validate(profile),
        skills=values(Skill, SkillRead),
        experiences=values(WorkExperience, ExperienceRead),
        education=values(Education, EducationRead),
        certifications=values(Certification, CertificationRead),
        projects=values(Project, ProjectRead),
        links=values(ProfileLink, ProfileLinkRead),
        preferences=CareerPreferenceRead.model_validate(preference) if preference else None,
        preference_options=[PreferenceOptionRead.model_validate(option) for option in options],
    )


def update_preferences(
    session: Session,
    user: User,
    values: dict,
) -> CareerPreference:
    profile = get_or_create_profile(session, user)
    preference = session.scalar(
        select(CareerPreference).where(CareerPreference.profile_id == profile.id)
    )
    if preference is None:
        preference = CareerPreference(profile_id=profile.id, **values)
        session.add(preference)
    else:
        for field, value in values.items():
            setattr(preference, field, value)
    session.commit()
    session.refresh(preference)
    return preference


def replace_preference_options(
    session: Session,
    user: User,
    items: list[dict],
) -> list[PreferenceOption]:
    profile = get_or_create_profile(session, user)
    session.execute(
        delete(PreferenceOption).where(PreferenceOption.profile_id == profile.id)
    )
    records = [PreferenceOption(profile_id=profile.id, **item) for item in items]
    session.add_all(records)
    session.commit()
    return records


def complete_onboarding(session: Session, user: User) -> CareerProfile:
    profile = get_or_create_profile(session, user)
    profile.onboarding_step = 9
    profile.onboarding_completed_at = datetime.now(UTC)
    session.commit()
    session.refresh(profile)
    return profile