from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CvProposalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: Literal["experience", "education", "skill", "project", "certification"]
    title: str
    organization: str | None
    start_date: date | None
    end_date: date | None
    description: str | None
    confidence: int


class CvDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    status: str
    created_at: datetime
    items: list[CvProposalRead] = Field(default_factory=list)


class CvProposalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    organization: str | None = Field(default=None, max_length=180)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = Field(default=None, max_length=10_000)


class CvApprovalRequest(BaseModel):
    item_ids: list[UUID] = Field(min_length=1, max_length=200)


class CvApprovalResponse(BaseModel):
    document_id: UUID
    status: Literal["approved"]
    items_saved: int
    items_skipped: int