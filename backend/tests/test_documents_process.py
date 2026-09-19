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
