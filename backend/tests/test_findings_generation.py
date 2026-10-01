"""Requires a running Postgres with migrations applied and clauses seeded
(see README). Run: docker compose up -d && alembic upgrade head &&
python -m app.seed.load_clauses && pytest."""

import io
import uuid
from concurrent.futures import ThreadPoolExecutor

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


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _docx_bytes(paragraphs: list[str]) -> bytes:
    doc = DocxDocument()
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()


SPARSE_SOP_TEXT = [
    "Procedure",
    "We assemble widgets according to the engineering drawing and inspect "
    "dimensions before packaging.",
]

# Covers every match_phrase for every capa clause applicable to `sop` docs
# (see backend/app/seed/data/*.yaml), so the matcher should find zero gaps.
THOROUGH_SOP_TEXT = [
    "Procedure",
    "Our corrective and preventive action procedure and corrective and "
    "preventive action process require a root cause investigation whenever "
    "nonconformities occur; we investigated the cause of each event. We "
    "verify the corrective action and validate the corrective action to "
    "confirm the effectiveness of the corrective action taken, including "
    "review of the effectiveness and determination of causes, and every "
    "corrective action to eliminate recurrence is tracked. Preventive "
    "action is taken to address potential nonconformities before they "
    "occur. Findings are disseminated to those directly responsible and "
    "submitted for management review. Our production and process controls "
    "ensure every deviation shall be recorded, and all deviations are "
    "recorded and justified.",
]


def _upload_and_process(token: str, paragraphs: list[str], filename: str = "sop.docx") -> str:
    upload = client.post(
        "/documents",
        headers=_headers(token),
        data={"type": "sop", "process_area": "capa"},
        files={"file": (filename, _docx_bytes(paragraphs), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    process = client.post(f"/documents/{document_id}/process", headers=_headers(token))
    assert process.status_code == 202
    assert process.json()["status"] == "processed"
    return document_id


def test_sparse_sop_produces_missing_finding_with_citations():
    token = _register()
    document_id = _upload_and_process(token, SPARSE_SOP_TEXT)

    findings = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    assert len(findings) > 0

    target = next(f for f in findings if f["clause"]["clause_number"] == "8.5.2(e)")
    assert target["status"] == "missing"
    assert target["severity"] == "critical"
    assert target["clause"]["regulation"] == "qmsr"
    assert target["section"]["id"]
    assert target["explanation"]


def test_thorough_sop_produces_no_findings():
    token = _register()
    document_id = _upload_and_process(token, THOROUGH_SOP_TEXT)

    findings = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    assert findings == []


def test_reprocessing_preserves_finding_ids_not_duplicates():
    token = _register()

    upload = client.post(
        "/documents",
        headers=_headers(token),
        data={"type": "sop", "process_area": "capa"},
        files={"file": ("sop.docx", _docx_bytes(SPARSE_SOP_TEXT), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload.json()["id"]

    first_process = client.post(f"/documents/{document_id}/process", headers=_headers(token))
    assert first_process.json()["status"] == "processed"
    first_findings = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    first_ids = sorted(f["id"] for f in first_findings)

    second_process = client.post(f"/documents/{document_id}/process", headers=_headers(token))
    assert second_process.json()["status"] == "processed"
    second_findings = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    second_ids = sorted(f["id"] for f in second_findings)

    assert len(first_findings) > 0
    assert first_ids == second_ids


def test_triage_survives_reprocessing():
    token = _register()

    upload = client.post(
        "/documents",
        headers=_headers(token),
        data={"type": "sop", "process_area": "capa"},
        files={"file": ("sop.docx", _docx_bytes(SPARSE_SOP_TEXT), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload.json()["id"]
    first_process = client.post(f"/documents/{document_id}/process", headers=_headers(token))
    assert first_process.json()["status"] == "processed"

    findings = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    finding_id = findings[0]["id"]

    triage = client.post(
        f"/findings/{finding_id}/triage",
        headers=_headers(token),
        json={"decision": "confirmed", "note": "Confirmed real gap"},
    )
    assert triage.status_code == 201

    second_process = client.post(f"/documents/{document_id}/process", headers=_headers(token))
    assert second_process.json()["status"] == "processed"

    findings_after = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    assert any(f["id"] == finding_id for f in findings_after)


def test_concurrent_process_calls_do_not_duplicate_findings():
    """Regression test: two /process requests for the same brand-new document
    racing each other (e.g. a double-click, a retry, or React StrictMode's dev
    double-invoke) must not both insert findings for the same clause. Without
    the row lock in documents.py's process_document, both requests read "no
    existing findings" and both insert, doubling the count."""
    token = _register()

    upload = client.post(
        "/documents",
        headers=_headers(token),
        data={"type": "sop", "process_area": "capa"},
        files={"file": ("sop.docx", _docx_bytes(SPARSE_SOP_TEXT), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload.json()["id"]

    def process() -> int:
        response = client.post(f"/documents/{document_id}/process", headers=_headers(token))
        assert response.json()["status"] == "processed"
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: process(), range(2)))
    assert results == [202, 202]

    findings = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    clause_ids = [f["clause"]["id"] for f in findings]
    assert len(clause_ids) == len(set(clause_ids)), "duplicate findings for the same clause"
