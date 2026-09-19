"""Requires a running Postgres with migrations applied and clauses seeded
(see README). Run: docker compose up -d && alembic upgrade head &&
python -m app.seed.load_clauses && pytest."""

import io
import uuid

from docx import Document as DocxDocument
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register() -> tuple[str, str]:
    email = f"qa-{uuid.uuid4().hex}@acme.example.com"
    response = client.post(
        "/auth/register",
        json={"org_name": "Acme", "industry": "device", "email": email, "password": "testpass123"},
    )
    assert response.status_code == 201
    body = response.json()
    return body["access_token"], body["org_id"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _sparse_sop_bytes() -> bytes:
    doc = DocxDocument()
    doc.add_paragraph("Procedure")
    doc.add_paragraph("We assemble widgets according to the engineering drawing.")
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()


def test_export_report_returns_pdf_with_findings():
    token, org_id = _register()

    upload = client.post(
        "/documents",
        headers=_headers(token),
        data={"type": "sop", "process_area": "capa"},
        files={"file": ("sop.docx", _sparse_sop_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload.json()["id"]
    client.post(f"/documents/{document_id}/process", headers=_headers(token))

    response = client.get(f"/reports/{org_id}/export", headers=_headers(token))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 500
    assert response.content.startswith(b"%PDF")


def test_export_report_forbidden_for_other_org():
    token_a, _ = _register()
    _, org_id_b = _register()

    response = client.get(f"/reports/{org_id_b}/export", headers=_headers(token_a))
    assert response.status_code == 403
