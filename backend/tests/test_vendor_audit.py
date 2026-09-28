"""Requires a running Postgres with migrations applied and the vendor
standards library seeded (see README). Run: docker compose up -d &&
alembic upgrade head && python -m app.seed.load_vendor_standards && pytest."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed.vendor_audit_demo_documents import DEFAULT_OUTPUT_DIR, VENDOR_AUDIT_DEMO_DOCUMENTS, build_all

client = TestClient(app)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# (vendor_category, requirement_name) -> expected status. Derived from which
# passage in each demo document gives full phrase coverage, partial coverage
# in plain English, or no coverage at all — see
# vendor_audit_demo_documents.py's module docstring.
EXPECTED_STATUS: dict[tuple[str, str], str] = {
    ("raw_material_supplier", "Certificate of Analysis per lot"): "satisfied",
    ("raw_material_supplier", "Supplier Qualification Assessment"): "partial",
    ("raw_material_supplier", "Change Notification Agreement"): "missing",
    ("contract_manufacturer", "Quality Agreement in Place"): "satisfied",
    ("contract_manufacturer", "Batch Release Procedure"): "partial",
    ("contract_manufacturer", "Deviation Reporting to Client"): "missing",
    ("sterilization_service", "Validated Sterilization Cycle"): "satisfied",
    ("sterilization_service", "Biological Indicator Results"): "partial",
    ("sterilization_service", "Dose Audit / Bioburden Report"): "missing",
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


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload_and_process(token: str, demo, demo_dir: Path) -> str:
    upload = client.post(
        "/documents",
        headers=_headers(token),
        data={"type": "vendor_audit_report", "process_area": "general", "vendor_category": demo.vendor_category},
        files={"file": (demo.filename, (demo_dir / demo.filename).read_bytes(), DOCX_MIME)},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    process = client.post(f"/documents/{document_id}/process", headers=_headers(token))
    assert process.status_code == 202
    assert process.json()["status"] == "processed"
    return document_id


@pytest.fixture(scope="module")
def demo_dir(tmp_path_factory) -> Path:
    directory = tmp_path_factory.mktemp("vendor_audit_demo_documents")
    build_all(directory)
    return directory


def test_every_vendor_audit_demo_document_maps_to_a_known_vendor_category():
    categories = {demo.vendor_category for demo in VENDOR_AUDIT_DEMO_DOCUMENTS}
    assert categories == {"raw_material_supplier", "contract_manufacturer", "sterilization_service"}


def test_committed_vendor_audit_demo_documents_match_the_generator():
    for demo in VENDOR_AUDIT_DEMO_DOCUMENTS:
        committed = DEFAULT_OUTPUT_DIR / demo.filename
        assert committed.exists(), "run `python -m app.seed.vendor_audit_demo_documents` and commit demo_documents/"


def test_vendor_audit_finds_the_intended_missing_partial_satisfied_mix(demo_dir):
    token = _register()

    for demo in VENDOR_AUDIT_DEMO_DOCUMENTS:
        document_id = _upload_and_process(token, demo, demo_dir)
        run = client.post(f"/vendor-audit/{document_id}/run", headers=_headers(token))
        assert run.status_code == 200
        assert run.json() == {"missing": 1, "partial": 1, "satisfied": 1}

    listed = client.get("/vendor-audit/findings", headers=_headers(token))
    assert listed.status_code == 200
    actual = {
        (f["standard"]["vendor_category"], f["standard"]["requirement_name"]): f["status"] for f in listed.json()
    }
    assert actual == EXPECTED_STATUS


def test_vendor_audit_run_requires_processed_document(demo_dir):
    token = _register()
    demo = VENDOR_AUDIT_DEMO_DOCUMENTS[0]

    upload = client.post(
        "/documents",
        headers=_headers(token),
        data={"type": "vendor_audit_report", "process_area": "general", "vendor_category": demo.vendor_category},
        files={"file": (demo.filename, (demo_dir / demo.filename).read_bytes(), DOCX_MIME)},
    )
    document_id = upload.json()["id"]

    run = client.post(f"/vendor-audit/{document_id}/run", headers=_headers(token))
    assert run.status_code == 409


def test_rerunning_vendor_audit_upserts_instead_of_duplicating(demo_dir):
    token = _register()
    demo = VENDOR_AUDIT_DEMO_DOCUMENTS[0]
    document_id = _upload_and_process(token, demo, demo_dir)

    client.post(f"/vendor-audit/{document_id}/run", headers=_headers(token))
    first_ids = sorted(
        f["id"]
        for f in client.get("/vendor-audit/findings", headers=_headers(token), params={"document_id": document_id}).json()
    )

    client.post(f"/vendor-audit/{document_id}/run", headers=_headers(token))
    second_ids = sorted(
        f["id"]
        for f in client.get("/vendor-audit/findings", headers=_headers(token), params={"document_id": document_id}).json()
    )

    assert len(first_ids) > 0
    assert first_ids == second_ids


def test_concurrent_vendor_audit_run_calls_do_not_duplicate_findings(demo_dir):
    """Regression test mirroring test_concurrent_process_calls_do_not_duplicate_findings
    in test_findings_generation.py: two /run requests for the same document
    racing each other must not both insert findings for the same standard."""
    token = _register()
    demo = VENDOR_AUDIT_DEMO_DOCUMENTS[0]
    document_id = _upload_and_process(token, demo, demo_dir)

    def run() -> int:
        response = client.post(f"/vendor-audit/{document_id}/run", headers=_headers(token))
        assert response.status_code == 200
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: run(), range(2)))
    assert results == [200, 200]

    findings = client.get(
        "/vendor-audit/findings", headers=_headers(token), params={"document_id": document_id}
    ).json()
    standard_ids = [f["standard"]["id"] for f in findings]
    assert len(standard_ids) == len(set(standard_ids)), "duplicate findings for the same standard"
