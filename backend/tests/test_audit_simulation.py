"""Requires a running Postgres with migrations applied and both libraries
seeded (see README). Run: docker compose up -d && alembic upgrade head &&
python -m app.seed.load_clauses && python -m app.seed.load_checklist && pytest."""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed.department_demo_documents import DEFAULT_OUTPUT_DIR, DEPARTMENT_DEMO_DOCUMENTS, build_all

client = TestClient(app)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# (department, item_name) -> expected status. Derived from which demo
# documents were deliberately given a real body, a title-only stub, or no
# document at all — see department_demo_documents.py's module docstring.
EXPECTED_STATUS: dict[tuple[str, str], str] = {
    ("qc", "Equipment Calibration Records"): "satisfied",
    ("qc", "Incoming Inspection Report"): "missing",
    ("qc", "Out-of-Specification Investigation Log"): "satisfied",
    ("qa", "Internal Audit Schedule & Reports"): "satisfied",
    ("qa", "Management Review Minutes"): "incomplete",
    ("qa", "CAPA Log"): "missing",
    ("utilities", "Water System Validation Report"): "satisfied",
    ("utilities", "HVAC Qualification Report"): "missing",
    ("utilities", "Utility Monitoring Log"): "missing",
    ("manufacturing", "Device History Record"): "satisfied",
    ("manufacturing", "Process Validation Report"): "missing",
    ("manufacturing", "Equipment Maintenance Log"): "satisfied",
    ("engineering", "Design History File"): "satisfied",
    ("engineering", "Risk Management File"): "incomplete",
    ("engineering", "Engineering Change Order Log"): "missing",
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
    directory = tmp_path_factory.mktemp("department_demo_documents")
    build_all(directory)
    return directory


def test_every_department_demo_document_maps_to_a_known_checklist_item():
    departments = {demo.department for demo in DEPARTMENT_DEMO_DOCUMENTS}
    assert departments == {"qc", "qa", "utilities", "manufacturing", "engineering"}


def test_committed_department_demo_documents_match_the_generator():
    for demo in DEPARTMENT_DEMO_DOCUMENTS:
        committed = DEFAULT_OUTPUT_DIR / demo.filename
        assert committed.exists(), "run `python -m app.seed.department_demo_documents` and commit demo_documents/"


def test_audit_simulation_finds_the_intended_missing_incomplete_satisfied_mix(demo_dir):
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}

    for demo in DEPARTMENT_DEMO_DOCUMENTS:
        upload = client.post(
            "/documents",
            headers=headers,
            data={"type": "report", "process_area": "general", "department": demo.department},
            files={
                "file": (
                    demo.filename,
                    (demo_dir / demo.filename).read_bytes(),
                    DOCX_MIME,
                )
            },
        )
        assert upload.status_code == 201
        document_id = upload.json()["id"]

        process = client.post(f"/documents/{document_id}/process", headers=headers)
        assert process.status_code == 202
        assert process.json()["status"] == "processed"

    run = client.post("/audit-simulation/run", headers=headers)
    assert run.status_code == 200
    counts = run.json()
    assert counts == {"missing": 6, "incomplete": 2, "satisfied": 7}

    listed = client.get("/audit-simulation/findings", headers=headers)
    assert listed.status_code == 200
    actual = {
        (f["checklist_item"]["department"], f["checklist_item"]["item_name"]): f["status"] for f in listed.json()
    }
    assert actual == EXPECTED_STATUS


def test_rerunning_audit_simulation_upserts_instead_of_duplicating(demo_dir):
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}

    demo = DEPARTMENT_DEMO_DOCUMENTS[0]
    upload = client.post(
        "/documents",
        headers=headers,
        data={"type": "report", "process_area": "general", "department": demo.department},
        files={"file": (demo.filename, (demo_dir / demo.filename).read_bytes(), DOCX_MIME)},
    )
    document_id = upload.json()["id"]
    client.post(f"/documents/{document_id}/process", headers=headers)

    client.post("/audit-simulation/run", headers=headers)
    first_count = len(client.get("/audit-simulation/findings", headers=headers).json())

    client.post("/audit-simulation/run", headers=headers)
    second_count = len(client.get("/audit-simulation/findings", headers=headers).json())

    assert first_count == second_count


def test_effective_checklist_lists_global_items_as_not_custom_not_excluded():
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}

    checklist = client.get("/audit-simulation/checklist", headers=headers).json()
    assert len(checklist) == 15
    assert all(not item["is_custom"] and not item["is_excluded"] for item in checklist)


def test_org_can_add_and_delete_a_custom_checklist_item():
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/audit-simulation/checklist",
        headers=headers,
        json={
            "department": "qc",
            "item_name": "Microbial Limit Test Records",
            "citation": "Company SOP-QC-099",
            "requirement_text": "Microbial limit testing shall be performed per the site's own SOP.",
            "match_phrases": ["microbial limit test"],
        },
    )
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert created.json()["is_custom"] is True

    checklist = client.get("/audit-simulation/checklist", headers=headers).json()
    assert any(item["id"] == item_id for item in checklist)
    assert len(checklist) == 16

    deleted = client.delete(f"/audit-simulation/checklist/{item_id}", headers=headers)
    assert deleted.status_code == 204

    checklist_after = client.get("/audit-simulation/checklist", headers=headers).json()
    assert len(checklist_after) == 15


def test_org_cannot_add_custom_item_for_invalid_department():
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/audit-simulation/checklist",
        headers=headers,
        json={
            "department": "not-a-real-department",
            "item_name": "Something",
            "citation": "N/A",
            "requirement_text": "N/A",
        },
    )
    assert response.status_code == 422


def test_excluding_a_global_item_removes_it_from_findings():
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}

    checklist = client.get("/audit-simulation/checklist", headers=headers).json()
    target = next(item for item in checklist if (item["department"], item["item_name"]) == ("qc", "Incoming Inspection Report"))

    excluded = client.post(f"/audit-simulation/checklist/{target['id']}/exclude", headers=headers)
    assert excluded.status_code == 204

    checklist_after = client.get("/audit-simulation/checklist", headers=headers).json()
    excluded_item = next(item for item in checklist_after if item["id"] == target["id"])
    assert excluded_item["is_excluded"] is True

    client.post("/audit-simulation/run", headers=headers)
    findings = client.get("/audit-simulation/findings", headers=headers).json()
    assert all(f["checklist_item"]["item_name"] != "Incoming Inspection Report" for f in findings)

    included = client.delete(f"/audit-simulation/checklist/{target['id']}/exclude", headers=headers)
    assert included.status_code == 204
    checklist_restored = client.get("/audit-simulation/checklist", headers=headers).json()
    restored_item = next(item for item in checklist_restored if item["id"] == target["id"])
    assert restored_item["is_excluded"] is False


def test_checklist_customization_is_scoped_per_org():
    token_a = _register()
    token_b = _register()

    client.post(
        "/audit-simulation/checklist",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "department": "qc",
            "item_name": "Org A Only Item",
            "citation": "N/A",
            "requirement_text": "N/A",
        },
    )

    checklist_a = client.get("/audit-simulation/checklist", headers={"Authorization": f"Bearer {token_a}"}).json()
    checklist_b = client.get("/audit-simulation/checklist", headers={"Authorization": f"Bearer {token_b}"}).json()

    assert any(item["item_name"] == "Org A Only Item" for item in checklist_a)
    assert all(item["item_name"] != "Org A Only Item" for item in checklist_b)
    assert len(checklist_b) == 15


def test_excluding_an_item_after_a_run_removes_its_existing_finding():
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/audit-simulation/run", headers=headers)
    findings = client.get("/audit-simulation/findings", headers=headers).json()
    assert any(f["checklist_item"]["item_name"] == "Incoming Inspection Report" for f in findings)

    checklist = client.get("/audit-simulation/checklist", headers=headers).json()
    target = next(item for item in checklist if (item["department"], item["item_name"]) == ("qc", "Incoming Inspection Report"))
    client.post(f"/audit-simulation/checklist/{target['id']}/exclude", headers=headers)

    # Gone immediately, and stays gone after a re-run.
    findings = client.get("/audit-simulation/findings", headers=headers).json()
    assert all(f["checklist_item"]["item_name"] != "Incoming Inspection Report" for f in findings)
    client.post("/audit-simulation/run", headers=headers)
    findings = client.get("/audit-simulation/findings", headers=headers).json()
    assert all(f["checklist_item"]["item_name"] != "Incoming Inspection Report" for f in findings)
    assert len(findings) == 14


def test_deleting_a_custom_item_after_a_run_succeeds():
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/audit-simulation/checklist",
        headers=headers,
        json={"department": "qc", "item_name": "Run Then Delete", "citation": "N/A", "requirement_text": "N/A"},
    ).json()
    client.post("/audit-simulation/run", headers=headers)
    findings = client.get("/audit-simulation/findings", headers=headers).json()
    assert any(f["checklist_item"]["item_name"] == "Run Then Delete" for f in findings)

    deleted = client.delete(f"/audit-simulation/checklist/{created['id']}", headers=headers)
    assert deleted.status_code == 204

    findings = client.get("/audit-simulation/findings", headers=headers).json()
    assert all(f["checklist_item"]["item_name"] != "Run Then Delete" for f in findings)
