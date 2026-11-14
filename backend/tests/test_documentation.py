"""Documentation completeness: blank signatures, stamps, dates, entries and
unfilled placeholders, found in Word, PDF and text files, and surfaced in
internal audit runs and vendor audits."""

import base64
import io
import uuid
from pathlib import Path

from docx import Document as DocxDocument
from fastapi.testclient import TestClient
from fpdf import FPDF

from app.core.documentation.completeness import check_documentation
from app.main import app
from app.seed.documentation_demo_documents import (
    CAPA_REVIEW,
    DHR,
    DOCUMENTATION_DEMO_DOCUMENTS,
    SCANNED_ECO,
    build_all,
)

client = TestClient(app)

# 1x1 PNG, used as a pasted signature image and as a "scan".
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _kinds(issues):
    return sorted((i.kind, i.field) for i in issues)


# ------------------------------------------------------------- detector


def test_text_finds_blank_fields_signature_lines_and_placeholders(tmp_path):
    path = tmp_path / "record.txt"
    path.write_text(
        "Batch No: 26-118    Date: 12-Nov-2026\n"
        "Operator: J. Smith\n"
        "Line clearance verified by: ________\n"
        "QA Approval Signature: ________   Date: __/__/____\n"
        "Comments: [Insert comments]\n"
        "Purpose: This record documents the filling.\n"
        "\n"
        "____________________\n"
        "Production Supervisor\n"
    )
    issues = check_documentation(str(path))
    kinds = _kinds(issues)
    assert ("missing_signature", "Line clearance verified by") in kinds
    assert ("missing_signature", "QA Approval Signature") in kinds
    assert ("missing_date", "Date") in kinds
    assert ("missing_entry", "Comments") in kinds  # "[Insert comments]" counts as blank, reported once
    assert not any(k == "placeholder" for k, _ in kinds)
    assert ("missing_signature", "Production Supervisor") in kinds
    # Filled fields and ordinary "Heading:" text aren't flagged.
    assert all(i.field not in ("Batch No", "Operator", "Purpose") for i in issues)


def test_values_next_to_other_fields_are_not_mistaken_for_blanks(tmp_path):
    path = tmp_path / "cal.txt"
    path.write_text(
        "Equipment ID: BAL-04    Location: QC lab 2\n"
        "Performed by: A. Kumar      Date: 10-Nov-2026\n"
        "Signature: ________ Date: ________\n"
    )
    kinds = _kinds(check_documentation(str(path)))
    assert kinds == [("missing_date", "Date"), ("missing_signature", "Signature")]


def test_docx_sign_off_table_and_key_value_table(tmp_path):
    doc = DocxDocument()
    doc.add_paragraph("Device History Record DHR-1")
    doc.add_paragraph("Lot number: [Insert lot number]")
    approvals = doc.add_table(rows=4, cols=4)
    for c, text in enumerate(["Role", "Name", "Signature", "Date"]):
        approvals.cell(0, c).text = text
    for c, text in enumerate(["Prepared by", "J. Smith", "", "12-Nov-2026"]):
        approvals.cell(1, c).text = text
    for c, text in enumerate(["Approved by", "R. Patel", "", ""]):
        approvals.cell(2, c).text = text
    approvals.cell(2, 2).paragraphs[0].add_run().add_picture(io.BytesIO(PNG))  # signed with an image
    # Row 4 left completely empty: an unused spare row, not a finding.
    stamp = doc.add_table(rows=2, cols=2)
    stamp.cell(0, 0).text = "QA release stamp"
    stamp.cell(1, 0).text = "Batch disposition"
    stamp.cell(1, 1).text = "Released"
    path = tmp_path / "dhr.docx"
    doc.save(path)

    kinds = _kinds(check_documentation(str(path)))
    assert ("missing_signature", "Prepared by - Signature") in kinds
    assert ("missing_date", "Approved by - Date") in kinds
    assert ("missing_stamp", "QA release stamp") in kinds
    assert ("missing_entry", "Lot number") in kinds  # holds only "[Insert lot number]"
    # The image-signed cell and the filled date aren't flagged.
    assert ("missing_signature", "Approved by - Signature") not in kinds
    assert ("missing_date", "Prepared by - Date") not in kinds


def test_digital_pdf_blank_approval(tmp_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Calibration record CAL-7", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "Approved by: ____________", new_x="LMARGIN", new_y="NEXT")
    path = tmp_path / "cal.pdf"
    pdf.output(str(path))
    assert ("missing_signature", "Approved by") in _kinds(check_documentation(str(path)))


def test_scanned_pdf_is_flagged_for_manual_check(tmp_path):
    image = tmp_path / "scan.png"
    image.write_bytes(PNG)
    pdf = FPDF()
    pdf.add_page()
    pdf.image(str(image), x=10, y=10, w=180)
    path = tmp_path / "scan.pdf"
    pdf.output(str(path))
    issues = check_documentation(str(path))
    assert [i.kind for i in issues] == ["scanned"]


def test_complete_record_has_no_issues(tmp_path):
    path = tmp_path / "ok.txt"
    path.write_text("Approved by: R. Patel\nSignature: R Patel\nDate: 12-Nov-2026\n")
    assert check_documentation(str(path)) == []


def test_demo_documents_raise_no_false_alarms():
    demo = Path(__file__).resolve().parents[2] / "demo_documents"
    planted = {name for name, _ in DOCUMENTATION_DEMO_DOCUMENTS}  # gaps on purpose
    for path in demo.glob("*.docx"):
        if path.name not in planted:
            assert check_documentation(str(path)) == [], path.name


def test_documentation_demo_documents_flag_exactly_the_planted_gaps(tmp_path):
    for path in build_all(tmp_path):
        found = _kinds(check_documentation(str(path)))
        expected = {
            DHR: [
                ("missing_date", "QA approval - Date"),
                ("missing_signature", "QA approval - Signature"),
                ("missing_signature", "Reviewed by (Production) - Signature"),
                ("missing_stamp", "QA release stamp"),
                ("placeholder", "[Insert disposition]"),
            ],
            CAPA_REVIEW: [("missing_date", "Date"), ("missing_signature", "Approved by")],
            SCANNED_ECO: [("scanned", "Scanned document")],
        }[path.name]
        assert found == expected, path.name


# ------------------------------------------------------------- in the app


def _headers():
    response = client.post(
        "/auth/register",
        json={
            "org_name": "GDP Org",
            "industry": "device",
            "email": f"gdp-{uuid.uuid4().hex}@acme.example.com",
            "password": "testpass123",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


UNSIGNED = (
    "Equipment Calibration Records - Autoclave AC3\n"
    + "Calibration of the autoclave temperature probes was performed against a traceable reference. " * 6
    + "\nPerformed by: ________\nDate: __/__/____\n"
)


def test_processing_records_issues_and_runs_freeze_them():
    headers = _headers()
    doc = client.post(
        "/documents",
        headers=headers,
        data={"type": "report", "process_area": "general", "department": "qc"},
        files={"file": ("CAL_unsigned.txt", UNSIGNED.encode(), "text/plain")},
    ).json()
    client.post(f"/documents/{doc['id']}/process", headers=headers)

    listed = next(d for d in client.get("/documents", headers=headers).json() if d["id"] == doc["id"])
    assert listed["documentation_issue_count"] == 2  # performed-by signature, date

    draft = client.post(
        "/audit-simulation/audits",
        headers=headers,
        json={"title": "GDP", "audit_type": "internal_audit", "lead_name": "A", "lead_employee_id": "1", "departments": ["qc"]},
    ).json()
    run = client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=headers).json()
    assert run["documentation_issue_count"] == 2
    assert {i["kind"] for i in run["documentation_issues"]} == {"missing_signature", "missing_date"}
    assert all(i["document_title"] == "CAL_unsigned.txt" for i in run["documentation_issues"])
    pdf = client.get(f"/audit-simulation/runs/{run['id']}/report", headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_scanned_upload_is_reported_as_scanned_not_as_blanks(tmp_path):
    headers = _headers()
    image = tmp_path / "scan.png"
    image.write_bytes(PNG)
    pdf = FPDF()
    pdf.add_page()
    pdf.image(str(image), x=10, y=10, w=180)
    path = tmp_path / "scan.pdf"
    pdf.output(str(path))
    doc = client.post(
        "/documents",
        headers=headers,
        data={"type": "report", "process_area": "general", "department": "qa"},
        files={"file": ("scan.pdf", path.read_bytes(), "application/pdf")},
    ).json()
    client.post(f"/documents/{doc['id']}/process", headers=headers)
    listed = next(d for d in client.get("/documents", headers=headers).json() if d["id"] == doc["id"])
    assert listed["documentation_scanned"] is True
    assert listed["documentation_issue_count"] == 0


def test_vendor_audit_shows_report_issues():
    headers = _headers()
    vendor = client.post("/vendors", headers=headers, json={"name": "V", "vendor_category": "raw_material_supplier"}).json()
    audit = client.post(
        f"/vendors/{vendor['id']}/audits",
        headers=headers,
        data={"auditor_name": "A", "auditor_employee_id": "1"},
        files={"file": ("vendor.txt", b"Supplier audit report\nAuditor signature: ______\n", "text/plain")},
    ).json()
    assert [(i["kind"], i["field"]) for i in audit["documentation_issues"]] == [("missing_signature", "Auditor signature")]
