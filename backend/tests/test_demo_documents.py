"""Locks in the finding mix each synthetic SME-review document is designed to
produce, so changes to the clause library or matching engine that would
silently change the demo fail here instead. Requires the same Postgres setup
as the other API tests (see README)."""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.parsing.extract import extract_text
from app.core.parsing.sections import split_into_sections
from app.main import app
from app.seed.demo_documents import DEFAULT_OUTPUT_DIR, DEMO_DOCUMENTS, build_all

client = TestClient(app)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

SOP_HEADINGS = ["Purpose", "Scope", "Responsibilities", "Procedure", "Records", "References"]
DEVIATION_HEADINGS = ["Description", "Investigation", "Root Cause", "Corrective Action (CAPA)", "Closure"]

# (regulation, clause_number) -> status. Anything absent is fully addressed.
EXPECTED_FINDINGS: dict[str, dict[tuple[str, str], str]] = {
    "SOP-QA-014_Control_of_Nonconforming_Product.docx": {
        ("cfr211", "211.192"): "partial",
        ("iso13485", "8.3.4"): "missing",
    },
    "DEV-2026-0417_Stability_Chamber_Temperature_Excursion.docx": {
        ("iso13485", "8.2.3"): "partial",
        ("iso13485", "8.3.4"): "partial",
    },
    "DEV-2026-0433_Label_Reconciliation_Discrepancy.docx": {
        ("qmsr", "8.3.1"): "partial",
        ("qmsr", "8.2.2"): "partial",
        ("qmsr", "8.3.2"): "missing",
        ("iso13485", "8.3.1"): "missing",
        ("iso13485", "8.3.2"): "missing",
        ("iso13485", "8.3.4"): "missing",
        ("iso13485", "8.2.3"): "missing",
        ("cfr211", "211.192"): "missing",
        ("cfr211", "211.198(a)"): "missing",
    },
    "SOP-QA-021_Corrective_and_Preventive_Action.docx": {
        ("qmsr", "8.5.2(e)"): "partial",
    },
    "DEV-2026-0451_Filling_Line_Stopper_Feed_Jams.docx": {
        ("qmsr", "8.5.2"): "partial",
        ("qmsr", "8.5.2(e)"): "missing",
        ("qmsr", "5.6.2"): "partial",
        ("iso13485", "8.5.2"): "partial",
        ("iso13485", "8.5.3"): "partial",
        ("cfr211", "211.100(b)"): "missing",
    },
}


def _register() -> str:
    response = client.post(
        "/auth/register",
        json={
            "org_name": "Demo Org",
            "industry": "device",
            "email": f"demo-{uuid.uuid4().hex}@acme.example.com",
            "password": "testpass123",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def demo_dir(tmp_path_factory) -> Path:
    directory = tmp_path_factory.mktemp("demo_documents")
    build_all(directory)
    return directory


def test_every_demo_document_has_an_expected_mix():
    assert {d.filename for d in DEMO_DOCUMENTS} == set(EXPECTED_FINDINGS)


@pytest.mark.parametrize("demo", DEMO_DOCUMENTS, ids=lambda d: d.filename)
def test_demo_document_splits_into_the_intended_sections(demo, demo_dir):
    sections = split_into_sections(extract_text(str(demo_dir / demo.filename)), demo.document_type)
    expected = SOP_HEADINGS if demo.document_type == "sop" else DEVIATION_HEADINGS
    assert [s.heading for s in sections] == ["Unclassified", *expected]


@pytest.mark.parametrize("demo", DEMO_DOCUMENTS, ids=lambda d: d.filename)
def test_demo_document_produces_the_intended_findings(demo, demo_dir):
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}

    upload = client.post(
        "/documents",
        headers=headers,
        data={"type": demo.document_type, "process_area": demo.process_area},
        files={"file": (demo.filename, (demo_dir / demo.filename).read_bytes(), DOCX_MIME)},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    process = client.post(f"/documents/{document_id}/process", headers=headers)
    assert process.status_code == 202
    assert process.json()["status"] == "processed"

    listed = client.get("/findings", headers=headers, params={"document_id": document_id})
    assert listed.status_code == 200
    actual = {(f["clause"]["regulation"], f["clause"]["clause_number"]): f["status"] for f in listed.json()}
    assert actual == EXPECTED_FINDINGS[demo.filename]


@pytest.mark.parametrize("demo", DEMO_DOCUMENTS, ids=lambda d: d.filename)
def test_committed_demo_documents_match_the_generator(demo, demo_dir):
    committed = DEFAULT_OUTPUT_DIR / demo.filename
    assert committed.exists(), "run `python -m app.seed.demo_documents` and commit demo_documents/"
    assert extract_text(str(committed)) == extract_text(str(demo_dir / demo.filename))
