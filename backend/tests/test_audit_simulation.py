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
