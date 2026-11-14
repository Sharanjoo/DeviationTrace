"""Run history for the internal audit simulation: every run is saved as a
numbered, frozen snapshot with its own PDF report."""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers() -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "org_name": "Run History Org",
            "industry": "device",
            "email": f"runs-{uuid.uuid4().hex}@acme.example.com",
            "password": "testpass123",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_each_run_gets_the_next_number_and_code():
    headers = _headers()
    first = client.post("/audit-simulation/run", headers=headers).json()
    second = client.post("/audit-simulation/run", headers=headers).json()

    assert (first["run_number"], first["run_code"]) == (1, "SIM-0001")
    assert (second["run_number"], second["run_code"]) == (2, "SIM-0002")
    assert first["run_id"] != second["run_id"]


def test_runs_are_listed_newest_first_with_counts():
    headers = _headers()
    client.post("/audit-simulation/run", headers=headers)
    client.post("/audit-simulation/run", headers=headers)

    runs = client.get("/audit-simulation/runs", headers=headers).json()
    assert [r["run_code"] for r in runs] == ["SIM-0002", "SIM-0001"]
    # A fresh org has no documents, so every global checklist item is missing.
    assert runs[0]["missing"] == runs[0]["total"] == 15
    assert runs[0]["satisfied"] == 0


def test_run_numbers_are_per_org():
    a, b = _headers(), _headers()
    client.post("/audit-simulation/run", headers=a)
    client.post("/audit-simulation/run", headers=a)
    assert client.post("/audit-simulation/run", headers=b).json()["run_code"] == "SIM-0001"


def test_run_detail_has_frozen_items_that_survive_checklist_changes():
    headers = _headers()
    run = client.post("/audit-simulation/run", headers=headers).json()

    # Exclude an item after the run; the past run must still include it.
    checklist = client.get("/audit-simulation/checklist", headers=headers).json()
    target = next(i for i in checklist if i["item_name"] == "Incoming Inspection Report")
    client.post(f"/audit-simulation/checklist/{target['id']}/exclude", headers=headers)
    client.post("/audit-simulation/run", headers=headers)

    detail = client.get(f"/audit-simulation/runs/{run['run_id']}", headers=headers).json()
    assert detail["run_code"] == "SIM-0001"
    assert len(detail["items"]) == 15
    assert any(i["item_name"] == "Incoming Inspection Report" for i in detail["items"])
    # Ordered by department (QC first), worst status first within it.
    assert detail["items"][0]["department"] == "qc"

    latest = client.get("/audit-simulation/runs", headers=headers).json()[0]
    assert latest["total"] == 14


def test_run_report_is_a_pdf_named_after_the_run():
    headers = _headers()
    run = client.post("/audit-simulation/run", headers=headers).json()

    response = client.get(f"/audit-simulation/runs/{run['run_id']}/report", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "SIM-0001" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_another_orgs_run_is_not_found():
    owner, other = _headers(), _headers()
    run = client.post("/audit-simulation/run", headers=owner).json()

    assert client.get(f"/audit-simulation/runs/{run['run_id']}", headers=other).status_code == 404
    assert client.get(f"/audit-simulation/runs/{run['run_id']}/report", headers=other).status_code == 404
