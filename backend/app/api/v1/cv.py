from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.rate_limit import rate_limit
from app.models import (
    CareerProfile,
    Certification,
    CvDocument,
    CvProposalItem,
    Education,
    Project,
    Skill,
    User,
    WorkExperience,
)
from app.schemas.cv import (
    CvApprovalRequest,
    CvApprovalResponse,
    CvDocumentRead,
    CvProposalRead,
    CvProposalUpdate,
)
from app.services.cv_service import (
    get_owned_document,
    persist_upload,
    read_upload_content,
    remove_private_file,
)
from app.services.profile_service import get_or_create_profile

router = APIRouter(tags=["CV upload and review"])


def _serialize_document(session: Session, document: CvDocument) -> CvDocumentRead:
    proposals = session.scalars(
        select(CvProposalItem)
        .where(CvProposalItem.document_id == document.id)
        .order_by(CvProposalItem.category, CvProposalItem.created_at)
    )
    return CvDocumentRead(
        id=document.id,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        status=document.status,
        created_at=document.created_at,
        items=[CvProposalRead.model_validate(item) for item in proposals],
    )


def _get_owned_proposal(
    session: Session,
    document: CvDocument,
    item_id: UUID,
) -> CvProposalItem:
    item = session.scalar(
        select(CvProposalItem).where(
            CvProposalItem.id == item_id,
            CvProposalItem.document_id == document.id,
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposal not found")
    return item


@router.post(
    "/career-profile/cv",
    response_model=CvDocumentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("cv-upload", 5))],
)
async def upload_cv(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CvDocumentRead:
    if not file.filename:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A filename is required")
    content = await read_upload_content(
        file,
        request.app.state.settings.max_cv_upload_bytes,
    )
    document = persist_upload(
        session,
        user,
        request.app.state.settings,
        file.filename,
        file.content_type,
        content,
    )
    return _serialize_document(session, document)


@router.get("/career-profile/cv", response_model=list[CvDocumentRead])
def list_cv_uploads(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CvDocumentRead]:
    documents = session.scalars(
        select(CvDocument)
        .where(CvDocument.user_id == user.id)
        .order_by(CvDocument.created_at.desc())
    )
    return [_serialize_document(session, document) for document in documents]


@router.get("/career-profile/cv/{document_id}", response_model=CvDocumentRead)
def read_cv_upload(
    document_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CvDocumentRead:
    return _serialize_document(session, get_owned_document(session, user, document_id))


@router.patch(
    "/career-profile/cv/{document_id}/items/{item_id}",
    response_model=CvProposalRead,
)
def update_cv_proposal(
    document_id: UUID,
    item_id: UUID,
    payload: CvProposalUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CvProposalRead:
    document = get_owned_document(session, user, document_id)
    if document.status != "review":
        raise HTTPException(status.HTTP_409_CONFLICT, "This document is no longer reviewable")
    item = _get_owned_proposal(session, document, item_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    session.commit()
    session.refresh(item)
    return CvProposalRead.model_validate(item)


@router.post(
    "/career-profile/cv/{document_id}/approve",
    response_model=CvApprovalResponse,
)
def approve_cv_proposals(
    document_id: UUID,
    payload: CvApprovalRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CvApprovalResponse:
    document = get_owned_document(session, user, document_id)
    if document.status != "review":
        raise HTTPException(status.HTTP_409_CONFLICT, "This document is no longer reviewable")
    if len(set(payload.item_ids)) != len(payload.item_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Duplicate proposal IDs")
    items = list(
        session.scalars(
            select(CvProposalItem).where(
                CvProposalItem.document_id == document.id,
                CvProposalItem.id.in_(payload.item_ids),
            )
        )
    )
    if len(items) != len(payload.item_ids):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposal not found")

    profile = get_or_create_profile(session, user)
    records: list[object] = []
    skipped = 0
    for item in items:
        if item.category == "skill":
            exists = session.scalar(
                select(Skill.id).where(
                    Skill.profile_id == profile.id,
                    Skill.name.ilike(item.title),
                )
            )
            if exists:
                skipped += 1
                continue
            records.append(Skill(profile_id=profile.id, name=item.title, proficiency_level="intermediate"))
        elif item.category == "experience":
            if not item.organization:
                skipped += 1
                continue
            records.append(
                WorkExperience(
                    profile_id=profile.id,
                    title=item.title,
                    company=item.organization,
                    start_date=item.start_date,
                    end_date=item.end_date,
                    description=item.description,
                )
            )
        elif item.category == "education":
            if not item.organization:
                skipped += 1
                continue
            records.append(
                Education(
                    profile_id=profile.id,
                    institution=item.organization,
                    degree=item.title,
                    start_date=item.start_date,
                    end_date=item.end_date,
                    description=item.description,
                )
            )
        elif item.category == "certification":
            records.append(
                Certification(profile_id=profile.id, name=item.title, issuer=item.organization)
            )
        elif item.category == "project":
            records.append(
                Project(
                    profile_id=profile.id,
                    name=item.title,
                    role=item.organization,
                    description=item.description,
                    start_date=item.start_date,
                    end_date=item.end_date,
                )
            )

    session.add_all(records)
    document.status = "approved"
    document.reviewed_at = datetime.now(UTC)
    session.commit()
    return CvApprovalResponse(
        document_id=document.id,
        status="approved",
        items_saved=len(records),
        items_skipped=skipped,
    )


@router.post("/career-profile/cv/{document_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_cv_upload(
    document_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    document = get_owned_document(session, user, document_id)
    if document.status != "review":
        raise HTTPException(status.HTTP_409_CONFLICT, "This document is no longer reviewable")
    storage_name = document.storage_name
    document.status = "rejected"
    document.extracted_text = ""
    session.execute(
        delete(CvProposalItem).where(CvProposalItem.document_id == document.id)
    )
    session.commit()
    remove_private_file(request.app.state.settings, storage_name)


@router.delete("/career-profile/cv/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cv_upload(
    document_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    document = get_owned_document(session, user, document_id)
    storage_name = document.storage_name
    session.delete(document)
    session.commit()
    remove_private_file(request.app.state.settings, storage_name)