"""Run history for the internal audit simulation: every run is saved as a
numbered, frozen snapshot with its own PDF report."""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers(industry: str = "device") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "org_name": "Run History Org",
            "industry": industry,
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


# ---------------------------------------------------------------- audit flow

AUDIT = {
    "title": "Q4 2026 internal audit",
    "audit_type": "internal_audit",
    "planned_date": "2026-12-01",
    "lead_name": "Priya Raman",
    "lead_employee_id": "EMP-1042",
    "lead_title": "QA Manager",
    "lead_email": "priya@acme.example.com",
    "objective": "Pre-certification readiness check",
    "departments": ["qa", "qc"],
    "department_contacts": [
        {"department": "qc", "name": "Dan Ortiz", "employee_id": "EMP-2201"},
        {"department": "qa", "name": "", "employee_id": ""},
    ],
}


def test_starting_an_audit_creates_a_numbered_draft_with_details():
    headers = _headers()
    response = client.post("/audit-simulation/audits", headers=headers, json=AUDIT)
    assert response.status_code == 201
    run = response.json()
    assert run["run_code"] == "SIM-0001"
    assert run["status"] == "draft"
    assert run["missing"] is None and run["items"] == []
    assert run["lead_employee_id"] == "EMP-1042"
    # Departments come back in standard order; blank contacts are dropped.
    assert run["departments"] == ["qc", "qa"]
    assert run["department_contacts"] == [{"department": "qc", "name": "Dan Ortiz", "employee_id": "EMP-2201"}]


def test_audit_details_are_validated():
    headers = _headers()
    for bad in (
        {**AUDIT, "lead_employee_id": "  "},
        {**AUDIT, "title": ""},
        {**AUDIT, "audit_type": "made_up"},
        {**AUDIT, "departments": []},
        {**AUDIT, "departments": ["qc", "marketing"]},
        {**AUDIT, "department_contacts": [{"department": "utilities", "name": "X", "employee_id": "1"}]},
    ):
        assert client.post("/audit-simulation/audits", headers=headers, json=bad).status_code == 422


def test_executing_a_draft_evaluates_only_its_departments():
    headers = _headers()
    draft = client.post("/audit-simulation/audits", headers=headers, json=AUDIT).json()

    run = client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=headers).json()
    assert run["status"] == "completed"
    assert run["completed_at"] is not None
    assert {i["department"] for i in run["items"]} == {"qc", "qa"}
    assert run["total"] == 6  # 3 global checklist items per department
    assert run["title"] == AUDIT["title"]


def test_draft_can_be_edited_but_completed_run_cannot():
    headers = _headers()
    draft = client.post("/audit-simulation/audits", headers=headers, json=AUDIT).json()

    edited = client.patch(
        f"/audit-simulation/runs/{draft['id']}", headers=headers, json={**AUDIT, "lead_name": "Sam Lee"}
    )
    assert edited.status_code == 200 and edited.json()["lead_name"] == "Sam Lee"

    client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=headers)
    assert client.patch(f"/audit-simulation/runs/{draft['id']}", headers=headers, json=AUDIT).status_code == 409
    assert client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=headers).status_code == 409


def test_draft_can_be_discarded_but_completed_run_cannot():
    headers = _headers()
    draft = client.post("/audit-simulation/audits", headers=headers, json=AUDIT).json()
    assert client.delete(f"/audit-simulation/runs/{draft['id']}", headers=headers).status_code == 204
    assert client.get(f"/audit-simulation/runs/{draft['id']}", headers=headers).status_code == 404

    done = client.post("/audit-simulation/audits", headers=headers, json=AUDIT).json()
    client.post(f"/audit-simulation/runs/{done['id']}/execute", headers=headers)
    assert client.delete(f"/audit-simulation/runs/{done['id']}", headers=headers).status_code == 409


def test_draft_has_no_report_until_run_and_report_includes_details():
    headers = _headers()
    draft = client.post("/audit-simulation/audits", headers=headers, json=AUDIT).json()
    assert client.get(f"/audit-simulation/runs/{draft['id']}/report", headers=headers).status_code == 409

    client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=headers)
    pdf = client.get(f"/audit-simulation/runs/{draft['id']}/report", headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_drafts_show_in_run_list_and_share_numbering_with_quick_runs():
    headers = _headers()
    client.post("/audit-simulation/run", headers=headers)
    client.post("/audit-simulation/audits", headers=headers, json=AUDIT)

    runs = client.get("/audit-simulation/runs", headers=headers).json()
    assert [(r["run_code"], r["status"]) for r in runs] == [("SIM-0002", "draft"), ("SIM-0001", "completed")]


def test_another_orgs_draft_cannot_be_touched():
    owner, other = _headers(), _headers()
    draft = client.post("/audit-simulation/audits", headers=owner, json=AUDIT).json()
    assert client.patch(f"/audit-simulation/runs/{draft['id']}", headers=other, json=AUDIT).status_code == 404
    assert client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=other).status_code == 404
    assert client.delete(f"/audit-simulation/runs/{draft['id']}", headers=other).status_code == 404


# ------------------------------------------------------------ content check

from pathlib import Path  # noqa: E402

DEMO = Path(__file__).resolve().parents[2] / "demo_documents"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _upload(headers, name, doc_type, department, process_area):
    doc = client.post(
        "/documents",
        headers=headers,
        data={"type": doc_type, "process_area": process_area, "department": department},
        files={"file": (name, (DEMO / name).read_bytes(), DOCX_MIME)},
    ).json()
    assert client.post(f"/documents/{doc['id']}/process", headers=headers).json()["status"] == "processed"
    return doc


def test_run_checks_content_of_in_scope_sops_and_deviation_reports():
    headers = _headers()  # a device maker: QMSR + ISO 13485 apply
    # Against the device regulations, SOP-QA-014 has one unaddressed
    # deviation-handling requirement (its other documented gap, 211.192, is a
    # drug cGMP rule; see the drug test below).
    _upload(headers, "SOP-QA-014_Control_of_Nonconforming_Product.docx", "sop", "qa", "deviation_handling")
    # Engineering isn't in AUDIT's scope (QC + QA), so this one isn't checked.
    _upload(headers, "DEV-2026-0417_Stability_Chamber_Temperature_Excursion.docx", "deviation", "engineering", "deviation_handling")

    draft = client.post("/audit-simulation/audits", headers=headers, json=AUDIT).json()  # qa + qc
    run = client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=headers).json()

    assert run["content_documents_checked"] == 1
    gaps = run["content_findings"]
    assert {g["document_title"] for g in gaps} == {"SOP-QA-014_Control_of_Nonconforming_Product.docx"}
    assert [g["status"] for g in gaps] == ["missing"]
    assert (run["content_critical"], run["content_major"], run["content_unreviewed"]) == (1, 0, 1)
    assert all(g["department"] == "qa" and g["requirement_title"] for g in gaps)
    assert not any(g["citation"].startswith("21 CFR") for g in gaps)


def test_drug_maker_sops_are_checked_against_21_cfr_211_only():
    headers = _headers(industry="drug")
    _upload(headers, "SOP-QA-014_Control_of_Nonconforming_Product.docx", "sop", "qa", "deviation_handling")
    draft = client.post("/audit-simulation/audits", headers=headers, json=AUDIT).json()
    run = client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=headers).json()

    gaps = run["content_findings"]
    assert gaps and all(g["citation"].startswith("21 CFR") for g in gaps)
    # The documented 211.192 partial gap ("followup" vs "follow-up").
    assert any(g["citation"] == "21 CFR 211.192" and g["status"] == "partial" for g in gaps)


def test_content_findings_can_be_reviewed_and_false_positives_stop_counting():
    headers = _headers()
    _upload(headers, "SOP-QA-014_Control_of_Nonconforming_Product.docx", "sop", "qa", "deviation_handling")
    draft = client.post("/audit-simulation/audits", headers=headers, json=AUDIT).json()
    run = client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=headers).json()
    critical = next(g for g in run["content_findings"] if g["severity"] == "critical")

    url = f"/audit-simulation/runs/{run['id']}/content-findings/{critical['id']}/review"
    reviewed = client.post(url, headers=headers, json={"decision": "false_positive", "note": "Covered in section 4"}).json()
    assert reviewed["decision"] == "false_positive" and reviewed["decided_by"] and reviewed["decision_note"] == "Covered in section 4"

    after = client.get(f"/audit-simulation/runs/{run['id']}", headers=headers).json()
    assert (after["content_critical"], after["content_major"], after["content_unreviewed"]) == (0, 0, 0)

    cleared = client.post(url, headers=headers, json={"decision": None}).json()
    assert cleared["decision"] is None and cleared["decided_by"] is None
    assert client.post(url, headers=headers, json={"decision": "maybe"}).status_code == 422


def test_reviewing_another_orgs_finding_is_not_found():
    owner, other = _headers(), _headers()
    _upload(owner, "SOP-QA-014_Control_of_Nonconforming_Product.docx", "sop", "qa", "deviation_handling")
    draft = client.post("/audit-simulation/audits", headers=owner, json=AUDIT).json()
    run = client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=owner).json()
    url = f"/audit-simulation/runs/{run['id']}/content-findings/{run['content_findings'][0]['id']}/review"
    assert client.post(url, headers=other, json={"decision": "confirmed"}).status_code == 404
