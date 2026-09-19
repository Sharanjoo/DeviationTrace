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


def _mixed_severity_sop_bytes() -> bytes:
    # One phrase of a multi-phrase clause yields a "partial"/major finding;
    # every clause with no phrase present yields "missing"/critical.
    doc = DocxDocument()
    doc.add_paragraph("Procedure")
    doc.add_paragraph("Personnel perform a root cause investigation when a deviation is raised.")
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()


def _upload_and_process_bytes(token: str, content: bytes) -> str:
    upload = client.post(
        "/documents",
        headers=_headers(token),
        data={"type": "sop", "process_area": "capa"},
        files={"file": ("sop.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]
    process = client.post(f"/documents/{document_id}/process", headers=_headers(token))
    assert process.status_code == 202
    assert process.json()["status"] == "processed"
    return document_id


def _triage(token: str, finding_id: str, decision: str, note: str | None = None):
    return client.post(
        f"/findings/{finding_id}/triage",
        headers=_headers(token),
        json={"decision": decision, "note": note},
    )


def test_triage_rejects_unknown_decision():
    token, _ = _register()
    document_id = _upload_and_process(token)
    finding_id = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()[0]["id"]

    response = _triage(token, finding_id, "maybe")
    assert response.status_code == 422


def test_findings_expose_triage_decision_once_recorded():
    token, _ = _register()
    document_id = _upload_and_process(token)
    finding_id = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()[0]["id"]

    before = client.get(f"/findings/{finding_id}", headers=_headers(token)).json()
    assert before["triage_decision"] is None

    recorded = _triage(token, finding_id, "needs_sme", "Ask QA lead")
    assert recorded.status_code == 201
    assert recorded.json()["decided_at"]

    detail = client.get(f"/findings/{finding_id}", headers=_headers(token)).json()
    assert detail["triage_decision"]["decision"] == "needs_sme"
    assert detail["triage_decision"]["note"] == "Ask QA lead"

    listed = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    by_id = {f["id"]: f for f in listed}
    assert by_id[finding_id]["triage_decision"]["decision"] == "needs_sme"
    assert all(f["triage_decision"] is None for fid, f in by_id.items() if fid != finding_id)


def test_retriage_replaces_decision_and_refreshes_timestamp():
    token, _ = _register()
    document_id = _upload_and_process(token)
    finding_id = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()[0]["id"]

    first = _triage(token, finding_id, "confirmed", "first pass")
    assert first.status_code == 201
    second = _triage(token, finding_id, "false_positive", "actually fine")
    assert second.status_code == 201

    assert second.json()["id"] == first.json()["id"]
    assert second.json()["decision"] == "false_positive"
    assert second.json()["note"] == "actually fine"
    assert second.json()["decided_at"] > first.json()["decided_at"]


def test_triage_filter_splits_pending_from_decided():
    token, _ = _register()
    document_id = _upload_and_process(token)
    listed = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    assert len(listed) >= 3
    confirmed_id, false_positive_id = listed[0]["id"], listed[1]["id"]

    assert _triage(token, confirmed_id, "confirmed").status_code == 201
    assert _triage(token, false_positive_id, "false_positive").status_code == 201

    def ids(triage: str) -> set[str]:
        response = client.get(
            "/findings", headers=_headers(token), params={"document_id": document_id, "triage": triage}
        )
        assert response.status_code == 200
        return {f["id"] for f in response.json()}

    assert ids("confirmed") == {confirmed_id}
    assert ids("false_positive") == {false_positive_id}
    assert ids("needs_sme") == set()
    assert ids("pending") == {f["id"] for f in listed} - {confirmed_id, false_positive_id}


def test_triage_filter_rejects_unknown_value():
    token, _ = _register()
    response = client.get("/findings", headers=_headers(token), params={"triage": "bogus"})
    assert response.status_code == 422


def test_findings_listed_critical_first():
    token, _ = _register()
    document_id = _upload_and_process_bytes(token, _mixed_severity_sop_bytes())

    listed = client.get("/findings", headers=_headers(token), params={"document_id": document_id}).json()
    severities = [f["severity"] for f in listed]
    assert "critical" in severities and "major" in severities, "fixture must produce a severity mix"
    rank = {"critical": 0, "major": 1, "minor": 2}
    assert severities == sorted(severities, key=rank.__getitem__)


def test_triage_filter_is_scoped_to_org():
    token_a, _ = _register()
    _upload_and_process(token_a)

    token_b, _ = _register()
    response = client.get("/findings", headers=_headers(token_b), params={"triage": "pending"})
    assert response.status_code == 200
    assert response.json() == []
