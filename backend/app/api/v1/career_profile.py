from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from pydantic import BaseModel, ValidationError
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
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
    CareerPreferenceUpdate,
    CareerProfileData,
    CertificationCreate,
    CertificationRead,
    CertificationUpdate,
    EducationCreate,
    EducationRead,
    EducationUpdate,
    ExperienceCreate,
    ExperienceRead,
    ExperienceUpdate,
    PreferenceOptionRead,
    PreferenceOptionsUpdate,
    ProfileRead,
    ProfileUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    ProfileLinkCreate,
    ProfileLinkRead,
    ProfileLinkUpdate,
    SkillCreate,
    SkillRead,
    SkillUpdate,
)
from app.services.profile_service import (
    complete_onboarding,
    create_owned_record,
    delete_owned_record,
    get_or_create_profile,
    get_owned_record,
    get_profile_data,
    list_owned_records,
    replace_preference_options,
    update_owned_record,
    update_preferences,
)

router = APIRouter(tags=["career profile"])
Collection = Literal["skills", "experience", "education", "certifications", "projects", "links"]
COLLECTIONS: dict[str, tuple[type, type[BaseModel], type[BaseModel], type[BaseModel]]] = {
    "skills": (Skill, SkillCreate, SkillUpdate, SkillRead),
    "experience": (WorkExperience, ExperienceCreate, ExperienceUpdate, ExperienceRead),
    "education": (Education, EducationCreate, EducationUpdate, EducationRead),
    "certifications": (Certification, CertificationCreate, CertificationUpdate, CertificationRead),
    "projects": (Project, ProjectCreate, ProjectUpdate, ProjectRead),
    "links": (ProfileLink, ProfileLinkCreate, ProfileLinkUpdate, ProfileLinkRead),
}


def _validate_payload(schema: type[BaseModel], payload: dict[str, Any], *, partial: bool) -> dict:
    try:
        value = schema.model_validate(payload)
    except ValidationError as error:
        raise RequestValidationError(
            [{**item, "loc": ("body", *item["loc"])} for item in error.errors()]
        ) from error
    return value.model_dump(mode="json", exclude_unset=partial)


def _get_collection(collection: str) -> tuple[type, type[BaseModel], type[BaseModel], type[BaseModel]]:
    try:
        return COLLECTIONS[collection]
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found") from None


@router.get("/career-profile", response_model=CareerProfileData)
def read_career_profile(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CareerProfileData:
    return get_profile_data(session, user)


@router.patch("/career-profile", response_model=ProfileRead)
def update_career_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ProfileRead:
    profile = get_or_create_profile(session, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    session.commit()
    session.refresh(profile)
    return ProfileRead.model_validate(profile)


@router.get("/career-profile/entries/{collection}", response_model=list[dict])
def list_collection(
    collection: Collection,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[dict]:
    model, _, _, read_schema = _get_collection(collection)
    records = list_owned_records(session, user, model)
    return [read_schema.model_validate(record).model_dump(mode="json") for record in records]


@router.post(
    "/career-profile/entries/{collection}",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
def create_collection_entry(
    collection: Collection,
    payload: dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict:
    model, create_schema, _, read_schema = _get_collection(collection)
    values = _validate_payload(create_schema, payload, partial=False)
    record = create_owned_record(session, user, model, values)
    return read_schema.model_validate(record).model_dump(mode="json")


@router.patch("/career-profile/entries/{collection}/{record_id}", response_model=dict)
def update_collection_entry(
    collection: Collection,
    record_id: UUID,
    payload: dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict:
    model, _, update_schema, read_schema = _get_collection(collection)
    values = _validate_payload(update_schema, payload, partial=True)
    record = update_owned_record(session, user, model, record_id, values)
    return read_schema.model_validate(record).model_dump(mode="json")


@router.delete(
    "/career-profile/entries/{collection}/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_collection_entry(
    collection: Collection,
    record_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    model, _, _, _ = _get_collection(collection)
    delete_owned_record(session, user, model, record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/career-profile/preferences", response_model=CareerPreferenceRead | None)
def read_preferences(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CareerPreferenceRead | None:
    profile = get_or_create_profile(session, user)
    preference = session.scalar(
        select(CareerPreference).where(CareerPreference.profile_id == profile.id)
    )
    return CareerPreferenceRead.model_validate(preference) if preference else None


@router.patch("/career-profile/preferences", response_model=CareerPreferenceRead)
def save_preferences(
    payload: CareerPreferenceUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CareerPreferenceRead:
    values = payload.model_dump(mode="json", exclude_unset=True)
    preference = update_preferences(session, user, values)
    return CareerPreferenceRead.model_validate(preference)


@router.put("/career-profile/preference-options", response_model=list[PreferenceOptionRead])
def save_preference_options(
    payload: PreferenceOptionsUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[PreferenceOptionRead]:
    items = [item.model_dump(mode="json") for item in payload.items]
    if len({(item["kind"], item["value"].strip().casefold()) for item in items}) != len(items):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Duplicate preference values")
    records = replace_preference_options(
        session,
        user,
        [{**item, "value": item["value"].strip()} for item in items],
    )
    return [PreferenceOptionRead.model_validate(record) for record in records]


@router.post("/career-profile/onboarding/complete", response_model=ProfileRead)
def finish_onboarding(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ProfileRead:
    profile = complete_onboarding(session, user)
    return ProfileRead.model_validate(profile)