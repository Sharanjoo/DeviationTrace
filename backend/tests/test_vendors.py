"""Vendors and per-vendor audits: a vendor audit uploads the vendor's audit
report, reads it, and cross-checks it against the vendor category's
standards in one step. Requires the vendor standards library seeded."""

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DEMO = Path(__file__).resolve().parents[2] / "demo_documents"
ACME = DEMO / "VEN-RM-2026-008_Acme_Excipient_Supplier_Audit_Report.docx"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _headers() -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "org_name": "Vendor Org",
            "industry": "device",
            "email": f"vendors-{uuid.uuid4().hex}@acme.example.com",
            "password": "testpass123",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _vendor(headers, name="Acme Excipient Supplier", category="raw_material_supplier"):
    response = client.post("/vendors", headers=headers, json={"name": name, "vendor_category": category})
    assert response.status_code == 201, response.text
    return response.json()


def _audit(headers, vendor_id, **form):
    data = {"auditor_name": "Priya Raman", "auditor_employee_id": "EMP-1042", "audit_date": "2026-11-01", **form}
    return client.post(
        f"/vendors/{vendor_id}/audits",
        headers=headers,
        data=data,
        files={"file": (ACME.name, ACME.read_bytes(), DOCX_MIME)},
    )


def test_create_and_list_vendors():
    headers = _headers()
    vendor = _vendor(headers)
    assert vendor["audit_count"] == 0 and vendor["latest_audit"] is None and vendor["audits"] == []
    listed = client.get("/vendors", headers=headers).json()
    assert [v["name"] for v in listed] == ["Acme Excipient Supplier"]


def test_vendor_validation_and_duplicate_names():
    headers = _headers()
    assert client.post("/vendors", headers=headers, json={"name": " ", "vendor_category": "raw_material_supplier"}).status_code == 422
    assert client.post("/vendors", headers=headers, json={"name": "X", "vendor_category": "made_up"}).status_code == 422
    _vendor(headers)
    assert client.post(
        "/vendors", headers=headers, json={"name": "Acme Excipient Supplier", "vendor_category": "raw_material_supplier"}
    ).status_code == 409


def test_new_audit_uploads_reads_and_cross_checks_the_report():
    headers = _headers()
    vendor = _vendor(headers)
    response = _audit(headers, vendor["id"])
    assert response.status_code == 201, response.text
    audit = response.json()
    assert audit["audit_code"] == "VA-0001"
    assert audit["document_status"] == "processed"
    assert (audit["missing"], audit["partial"], audit["satisfied"]) == (1, 1, 1)
    assert audit["auditor_employee_id"] == "EMP-1042" and audit["audit_date"] == "2026-11-01"
    assert {f["status"] for f in audit["findings"]} == {"missing", "partial", "satisfied"}
    # Worst first.
    assert audit["findings"][0]["status"] == "missing"


def test_vendor_history_is_newest_first_with_latest_summary():
    headers = _headers()
    vendor = _vendor(headers)
    _audit(headers, vendor["id"])
    _audit(headers, vendor["id"], audit_date="2026-11-10")

    detail = client.get(f"/vendors/{vendor['id']}", headers=headers).json()
    assert [a["audit_code"] for a in detail["audits"]] == ["VA-0002", "VA-0001"]
    assert detail["audit_count"] == 2 and detail["latest_audit"]["audit_code"] == "VA-0002"


def test_new_audit_requires_auditor_and_a_supported_file():
    headers = _headers()
    vendor = _vendor(headers)
    assert _audit(headers, vendor["id"], auditor_employee_id=" ").status_code == 422
    bad = client.post(
        f"/vendors/{vendor['id']}/audits",
        headers=headers,
        data={"auditor_name": "A", "auditor_employee_id": "1"},
        files={"file": ("report.exe", b"x", "application/octet-stream")},
    )
    assert bad.status_code == 422


def test_unassigned_reports_can_be_attached_to_a_vendor():
    headers = _headers()
    upload = client.post(
        "/documents",
        headers=headers,
        data={"type": "vendor_audit_report", "process_area": "general", "vendor_category": "contract_manufacturer"},
        files={"file": (ACME.name, ACME.read_bytes(), DOCX_MIME)},
    ).json()
    client.post(f"/documents/{upload['id']}/process", headers=headers)

    unassigned = client.get("/vendors/unassigned-reports", headers=headers).json()
    assert [d["id"] for d in unassigned] == [upload["id"]]

    vendor = _vendor(headers)  # raw material supplier, unlike the upload's category
    audit = client.post(
        f"/vendors/{vendor['id']}/assign-report", headers=headers, json={"document_id": upload["id"]}
    ).json()
    assert audit["audit_code"] == "VA-0001"
    # Re-checked under the vendor's own category.
    assert audit["vendor_category"] == "raw_material_supplier"
    assert (audit["missing"], audit["partial"], audit["satisfied"]) == (1, 1, 1)
    assert client.get("/vendors/unassigned-reports", headers=headers).json() == []
    # Can't be attached twice.
    again = client.post(f"/vendors/{vendor['id']}/assign-report", headers=headers, json={"document_id": upload["id"]})
    assert again.status_code == 404


def test_rerun_keeps_results():
    headers = _headers()
    vendor = _vendor(headers)
    audit = _audit(headers, vendor["id"]).json()
    rerun = client.post(f"/vendor-audits/{audit['id']}/rerun", headers=headers).json()
    assert (rerun["missing"], rerun["partial"], rerun["satisfied"]) == (1, 1, 1)


def test_another_orgs_vendors_and_audits_are_not_found():
    owner, other = _headers(), _headers()
    vendor = _vendor(owner)
    audit = _audit(owner, vendor["id"]).json()
    assert client.get(f"/vendors/{vendor['id']}", headers=other).status_code == 404
    assert _audit(other, vendor["id"]).status_code == 404
    assert client.get(f"/vendor-audits/{audit['id']}", headers=other).status_code == 404
    assert client.get("/vendors", headers=other).json() == []


def test_history_is_ordered_by_audit_date_not_entry_order():
    headers = _headers()
    vendor = _vendor(headers)
    _audit(headers, vendor["id"], audit_date="2026-11-10")  # VA-0001, newer
    _audit(headers, vendor["id"], audit_date="2026-03-02")  # VA-0002, entered later but older

    detail = client.get(f"/vendors/{vendor['id']}", headers=headers).json()
    assert [a["audit_code"] for a in detail["audits"]] == ["VA-0001", "VA-0002"]
    assert detail["latest_audit"]["audit_code"] == "VA-0001"


def test_audit_details_can_be_edited_and_reorder_history():
    headers = _headers()
    vendor = _vendor(headers)
    first = _audit(headers, vendor["id"], audit_date="2026-11-10").json()   # VA-0001
    second = _audit(headers, vendor["id"], audit_date="2026-11-12").json()  # VA-0002, latest

    response = client.patch(
        f"/vendor-audits/{second['id']}",
        headers=headers,
        json={"audit_date": "2026-03-02", "auditor_name": " Sam Lee ", "auditor_employee_id": "EMP-2002", "notes": " "},
    )
    assert response.status_code == 200
    edited = response.json()
    assert (edited["audit_date"], edited["auditor_name"], edited["auditor_employee_id"], edited["notes"]) == (
        "2026-03-02", "Sam Lee", "EMP-2002", None,
    )
    # Results unchanged; and VA-0001 is now the latest by date.
    assert (edited["missing"], edited["partial"], edited["satisfied"]) == (1, 1, 1)
    detail = client.get(f"/vendors/{vendor['id']}", headers=headers).json()
    assert detail["latest_audit"]["id"] == first["id"]


def test_audit_edit_allows_unknown_auditor_and_checks_ownership():
    owner, other = _headers(), _headers()
    vendor = _vendor(owner)
    audit = _audit(owner, vendor["id"]).json()
    cleared = client.patch(
        f"/vendor-audits/{audit['id']}", headers=owner, json={"audit_date": "2026-01-05", "auditor_name": " ", "auditor_employee_id": None}
    ).json()
    assert (cleared["audit_date"], cleared["auditor_name"], cleared["auditor_employee_id"]) == ("2026-01-05", None, None)
    # Fields left out are kept.
    kept = client.patch(f"/vendor-audits/{audit['id']}", headers=owner, json={"notes": "Follow-up due"}).json()
    assert (kept["audit_date"], kept["notes"]) == ("2026-01-05", "Follow-up due")
    assert client.patch(f"/vendor-audits/{audit['id']}", headers=other, json={}).status_code == 404
