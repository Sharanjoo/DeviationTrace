"""Requires a running Postgres with migrations applied (see README), same as
test_clauses.py. Run: docker compose up -d && alembic upgrade head && pytest."""

import io
import uuid

from docx import Document as DocxDocument
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register() -> str:
    email = f"qa-{uuid.uuid4().hex}@acme.example.com"
    response = client.post(
        "/auth/register",
        json={"org_name": "Acme", "industry": "device", "email": email, "password": "testpass123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _sop_docx_bytes() -> bytes:
    doc = DocxDocument()
    doc.add_paragraph("Scope")
    doc.add_paragraph("This SOP covers deviation handling.")
    doc.add_paragraph("Procedure")
    doc.add_paragraph("Investigate and document root cause before CAPA closure.")
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()


def test_upload_process_and_fetch_sections():
    token = _register()
    headers = _auth_headers(token)

    upload = client.post(
        "/documents",
        headers=headers,
        data={"type": "sop", "process_area": "deviation_handling"},
        files={"file": ("sop.docx", _sop_docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    process = client.post(f"/documents/{document_id}/process", headers=headers)
    assert process.status_code == 202
    assert process.json()["status"] == "processed"
    assert process.json()["processing_error"] is None

    status_response = client.get(f"/documents/{document_id}/status", headers=headers)
    assert status_response.json()["status"] == "processed"

    detail = client.get(f"/documents/{document_id}", headers=headers)
    sections = detail.json()["sections"]
    headings = [s["heading"] for s in sections]

    assert "Scope" in headings
    assert "Procedure" in headings
    assert len(sections) > 0


def test_upload_rejects_disallowed_extension():
    token = _register()
    headers = _auth_headers(token)

    response = client.post(
        "/documents",
        headers=headers,
        data={"type": "sop", "process_area": "deviation_handling"},
        files={"file": ("malware.exe", b"not a real document", "application/octet-stream")},
    )
    assert response.status_code == 422


def test_list_documents_filters_by_type_and_scopes_by_org():
    token_a = _register()
    headers_a = _auth_headers(token_a)
    token_b = _register()
    headers_b = _auth_headers(token_b)

    client.post(
        "/documents",
        headers=headers_a,
        data={"type": "sop", "process_area": "deviation_handling"},
        files={"file": ("sop.docx", _sop_docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    client.post(
        "/documents",
        headers=headers_a,
        data={"type": "deviation", "process_area": "capa"},
        files={"file": ("dev.docx", _sop_docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    client.post(
        "/documents",
        headers=headers_b,
        data={"type": "sop", "process_area": "deviation_handling"},
        files={"file": ("other-org-sop.docx", _sop_docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    all_docs = client.get("/documents", headers=headers_a)
    assert all_docs.status_code == 200
    assert {d["type"] for d in all_docs.json()} == {"sop", "deviation"}
    assert all(d["title"] != "other-org-sop.docx" for d in all_docs.json())

    sop_only = client.get("/documents", headers=headers_a, params={"type": "sop"})
    assert [d["type"] for d in sop_only.json()] == ["sop"]


def test_process_failure_sets_failed_status_not_500():
    token = _register()
    headers = _auth_headers(token)

    upload = client.post(
        "/documents",
        headers=headers,
        data={"type": "sop", "process_area": "deviation_handling"},
        files={"file": ("broken.pdf", b"this is not a valid pdf", "application/pdf")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    process = client.post(f"/documents/{document_id}/process", headers=headers)
    assert process.status_code == 202
    assert process.json()["status"] == "failed"
    assert process.json()["processing_error"]
