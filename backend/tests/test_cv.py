import io

import fitz
from docx import Document
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.services.cv_service import extract_cv_text
from tests.helpers import register_verified_user


def _docx_bytes() -> bytes:
    document = Document()
    document.add_paragraph("Skills")
    document.add_paragraph("Python, TypeScript")
    document.add_paragraph("Experience")
    document.add_paragraph("Backend Engineer at Example Corp 2020-2023")
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def _pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Skills\nPython\nProjects\nCareer planner")
    content = document.tobytes()
    document.close()
    return content


def test_cv_extraction_accepts_valid_pdf_docx_and_rejects_spoofed_signatures() -> None:
    pdf_text, pdf_mime = extract_cv_text(_pdf_bytes(), "profile.pdf", "application/pdf")
    docx_text, docx_mime = extract_cv_text(
        _docx_bytes(),
        "profile.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert "Python" in pdf_text
    assert pdf_mime == "application/pdf"
    assert "Backend Engineer" in docx_text
    assert docx_mime.endswith("wordprocessingml.document")

    try:
        extract_cv_text(b"not a pdf", "profile.pdf", "application/pdf")
    except ValueError as error:
        assert "valid PDF and DOCX" in str(error)
    else:
        raise AssertionError("Expected invalid signature rejection")


def test_upload_requires_authentication_and_size_limit(client: TestClient) -> None:
    response = client.post(
        "/api/v1/career-profile/cv",
        files={"file": ("profile.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 401


def test_cv_upload_review_explicit_approval_and_owner_isolation(
    client: TestClient,
    monkeypatch: MonkeyPatch,
    tmp_path,
) -> None:
    token = register_verified_user(client, monkeypatch, "cv-owner@example.com")
    monkeypatch.setattr(client.app.state.settings, "private_storage_path", tmp_path)
    headers = {"Authorization": f"Bearer {token}"}
    uploaded = client.post(
        "/api/v1/career-profile/cv",
        files={
            "file": (
                "../private/profile.docx",
                _docx_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers=headers,
    )
    assert uploaded.status_code == 201
    document = uploaded.json()
    assert document["status"] == "review"
    assert len(document["items"]) == 3
    assert (tmp_path / "private").exists() is False
    assert len(list(tmp_path.iterdir())) == 1
    assert all(".docx" in path.name for path in tmp_path.iterdir())

    skills_before = client.get(
        "/api/v1/career-profile/entries/skills",
        headers=headers,
    ).json()
    assert skills_before == []

    other_token = register_verified_user(client, monkeypatch, "cv-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert client.get(
        f"/api/v1/career-profile/cv/{document['id']}",
        headers=other_headers,
    ).status_code == 404

    skill_items = [item for item in document["items"] if item["category"] == "skill"]
    approved = client.post(
        f"/api/v1/career-profile/cv/{document['id']}/approve",
        json={"item_ids": [item["id"] for item in skill_items]},
        headers=headers,
    )
    assert approved.status_code == 200
    assert approved.json()["items_saved"] == 2
    skills_after = client.get(
        "/api/v1/career-profile/entries/skills",
        headers=headers,
    ).json()
    assert {skill["name"] for skill in skills_after} == {"Python", "TypeScript"}