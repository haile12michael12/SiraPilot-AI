import io
import os
import re
import secrets
import zipfile
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Literal
from uuid import UUID

import fitz
from docx import Document
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
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

CvCategory = Literal["experience", "education", "skill", "project", "certification"]
MAX_EXTRACTED_CHARACTERS = 200_000
_HEADINGS: dict[str, CvCategory] = {
    "experience": "experience",
    "work experience": "experience",
    "employment history": "experience",
    "professional experience": "experience",
    "education": "education",
    "academic background": "education",
    "skills": "skill",
    "technical skills": "skill",
    "core competencies": "skill",
    "projects": "project",
    "selected projects": "project",
    "certifications": "certification",
    "certificates": "certification",
}
_DATE_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})(?:\s*[-–]\s*(19\d{2}|20\d{2}|present|current))?\b", re.I)


def _safe_filename(filename: str) -> str:
    basename = PureWindowsPath(filename).name
    basename = Path(basename).name
    basename = re.sub(r"[^A-Za-z0-9._ -]", "_", basename).strip(" .")
    return basename[:180] or "resume"


def _validate_docx_archive(content: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if (
                len(entries) > 1000
                or sum(entry.file_size for entry in entries) > 30 * 1024 * 1024
                or "[Content_Types].xml" not in archive.namelist()
                or "word/document.xml" not in archive.namelist()
            ):
                raise ValueError("Invalid DOCX archive")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("Invalid DOCX archive") from exc


def extract_cv_text(content: bytes, filename: str, content_type: str) -> tuple[str, str]:
    safe_name = _safe_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix == ".pdf" and content_type == "application/pdf" and content.startswith(b"%PDF-"):
        try:
            document = fitz.open(stream=content, filetype="pdf")
            if document.is_encrypted or document.page_count > 200:
                document.close()
                raise ValueError("PDF cannot be processed")
            text = "\n".join(page.get_text("text") for page in document)
            document.close()
        except (fitz.FileDataError, RuntimeError) as exc:
            raise ValueError("Invalid PDF document") from exc
        mime_type = "application/pdf"
    elif (
        suffix == ".docx"
        and content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        and content.startswith(b"PK")
    ):
        _validate_docx_archive(content)
        try:
            document = Document(io.BytesIO(content))
            paragraphs = [paragraph.text for paragraph in document.paragraphs]
            paragraphs.extend(
                cell.text
                for table in document.tables
                for row in table.rows
                for cell in row.cells
            )
            text = "\n".join(paragraphs)
        except (KeyError, ValueError, zipfile.BadZipFile) as exc:
            raise ValueError("Invalid DOCX document") from exc
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise ValueError("Only valid PDF and DOCX files are accepted")

    cleaned = "\n".join(line.strip() for line in text.splitlines()).strip()
    if not cleaned:
        raise ValueError("No readable text was found in the document")
    if len(cleaned) > MAX_EXTRACTED_CHARACTERS:
        cleaned = cleaned[:MAX_EXTRACTED_CHARACTERS]
    return cleaned, mime_type


def _parse_year(value: str | None) -> date | None:
    if not value or value.lower() in {"present", "current"}:
        return None
    try:
        return date(int(value), 1, 1)
    except ValueError:
        return None


def extract_proposals(text: str) -> list[dict]:
    proposals: list[dict] = []
    category: CvCategory | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip().lstrip("•-* ").strip()
        if not line:
            continue
        heading = line.rstrip(":").strip().lower()
        if heading in _HEADINGS:
            category = _HEADINGS[heading]
            continue
        if category is None:
            continue
        values = re.split(r"[,;|]", line) if category == "skill" else [line]
        for value in values:
            value = value.strip()
            if not value:
                continue
            date_match = _DATE_PATTERN.search(value)
            start_date = _parse_year(date_match.group(1)) if date_match else None
            end_date = _parse_year(date_match.group(2)) if date_match else None
            without_dates = _DATE_PATTERN.sub("", value).strip(" -|,;")
            title, organization = without_dates, None
            if category != "skill":
                for delimiter in (" | ", " at ", " - "):
                    if delimiter in without_dates:
                        title, organization = (
                            part.strip() for part in without_dates.split(delimiter, 1)
                        )
                        break
            proposals.append(
                {
                    "category": category,
                    "title": title[:180] or value[:180],
                    "organization": organization[:180] if organization else None,
                    "start_date": start_date,
                    "end_date": end_date,
                    "description": None,
                    "confidence": 55 if category == "skill" else 40,
                }
            )
    return proposals


def persist_upload(
    session: Session,
    user: User,
    settings: Settings,
    filename: str,
    content_type: str | None,
    content: bytes,
) -> CvDocument:
    safe_name = _safe_filename(filename)
    try:
        extracted_text, mime_type = extract_cv_text(content, safe_name, content_type or "")
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    suffix = ".pdf" if mime_type == "application/pdf" else ".docx"
    storage_name = f"{secrets.token_hex(24)}{suffix}"
    directory = settings.private_storage_path.resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        directory.chmod(0o700)
    destination = directory / storage_name
    try:
        destination.write_bytes(content)
        if destination.stat().st_size != len(content):
            raise OSError("Incomplete upload write")
        profile_exists = session.scalar(
            select(CareerProfile.id).where(CareerProfile.user_id == user.id)
        )
        if profile_exists is None:
            session.add(CareerProfile(user_id=user.id))
            session.flush()
        document = CvDocument(
            user_id=user.id,
            original_filename=safe_name,
            storage_name=storage_name,
            mime_type=mime_type,
            size_bytes=len(content),
            status="review",
            extracted_text=extracted_text,
        )
        session.add(document)
        session.flush()
        session.add_all(
            CvProposalItem(document_id=document.id, **proposal)
            for proposal in extract_proposals(extracted_text)
        )
        session.commit()
        session.refresh(document)
        return document
    except Exception:
        session.rollback()
        destination.unlink(missing_ok=True)
        raise


async def read_upload_content(upload: UploadFile, max_bytes: int) -> bytes:
    content = await upload.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds the upload limit")
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "File is empty")
    return content


def remove_private_file(settings: Settings, storage_name: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{48}\.(?:pdf|docx)", storage_name):
        return
    directory = settings.private_storage_path.resolve()
    target = (directory / storage_name).resolve()
    if target.parent == directory:
        target.unlink(missing_ok=True)


def get_owned_document(session: Session, user: User, document_id: UUID) -> CvDocument:
    document = session.scalar(
        select(CvDocument).where(
            CvDocument.id == document_id,
            CvDocument.user_id == user.id,
        )
    )
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document