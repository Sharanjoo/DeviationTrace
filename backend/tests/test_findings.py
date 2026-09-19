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


def _upload_and_process(token: str) -> str:
    upload = client.post(
        "/documents",
        headers=_headers(token),
        data={"type": "sop", "process_area": "capa"},
        files={"file": ("sop.docx", _sparse_sop_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload.json()["id"]
    process = client.post(f"/documents/{document_id}/process", headers=_headers(token))
    assert process.json()["status"] == "processed"
    return document_id


def test_get_single_finding_includes_document_summary():
    token, _ = _register()
    document_id = _upload_and_process(token)

    listed = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    finding_id = listed[0]["id"]

    response = client.get(f"/findings/{finding_id}", headers=_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == finding_id
    assert body["document"]["id"] == document_id
    assert body["document"]["title"] == "sop.docx"
    assert body["clause"]["clause_number"]
    assert body["section"]["heading"]


def test_get_single_finding_404_for_other_org():
    token_a, _ = _register()
    document_id = _upload_and_process(token_a)
    finding_id = client.get("/findings", headers=_headers(token_a), params={"document_id": document_id}).json()[0]["id"]

    token_b, _ = _register()
    response = client.get(f"/findings/{finding_id}", headers=_headers(token_b))
    assert response.status_code == 404


def test_get_single_finding_404_for_unknown_id():
    token, _ = _register()
    response = client.get(f"/findings/{uuid.uuid4()}", headers=_headers(token))
    assert response.status_code == 404
