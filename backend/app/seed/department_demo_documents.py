"""Generate the synthetic department documents used for the Phase 1
(Internal Audit Simulation) SME review session.

Run from backend/: python -m app.seed.department_demo_documents
Writes .docx files to <repo root>/demo_documents/.

Every document is fictional and says so in its title block. Deliberately
covers all three audit-simulation outcomes across the 5 departments: most
checklist items are satisfied by a real-looking report, two are matched by
a title only (a stub with no real body, "incomplete"), and the remaining
items have no corresponding document at all ("missing") — so an SME
reviewing the output sees a realistic mix of gaps, not a clean sweep.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from docx import Document as DocxDocument

from app.seed.demo_documents import DEFAULT_OUTPUT_DIR, SYNTHETIC_NOTICE

_FIXED_TIMESTAMP = datetime(2026, 1, 1)


@dataclass(frozen=True)
class DepartmentDemoDocument:
    filename: str
    department: str  # qc | qa | utilities | manufacturing | engineering
    title_block: tuple[str, ...]
    sections: tuple[tuple[str, tuple[str, ...]], ...]


DEPARTMENT_DEMO_DOCUMENTS: tuple[DepartmentDemoDocument, ...] = (
    # QC — satisfied, satisfied. "Incoming Inspection Report" left unmatched (missing).
    DepartmentDemoDocument(
        filename="QC-CAL-002_Autoclave_AC3_Calibration_Log.docx",
        department="qc",
        title_block=(
            "QC-CAL-002 Autoclave AC-3 Calibration Log",
            "Effective 2026-01-10 | Owner: Quality Control | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "Calibration Record",
                (
                    "Autoclave AC-3 was calibrated on 2026-01-10 by Metrology Services against a "
                    "NIST-traceable reference probe. Temperature and pressure readings at 121C/15psi "
                    "were within +/-0.5C and +/-0.3psi of the reference standard across all three "
                    "verification runs.",
                    "The calibration sticker was updated with the next due date of 2027-01-10. No "
                    "out-of-tolerance conditions were observed. Records of the calibration, including "
                    "the reference standard's own certificate, are retained in the QC calibration file.",
                ),
            ),
        ),
    ),
    DepartmentDemoDocument(
        filename="QC-OOS-2026-004_Tablet_Hardness_OOS_Investigation.docx",
        department="qc",
        title_block=(
            "QC-OOS-2026-004 Tablet hardness out-of-specification investigation",
            "Raised 2026-02-11 | Owner: Quality Control | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "Investigation",
                (
                    "Lot 26-029 tablet hardness testing returned one result of 6.1 kP against a "
                    "specification of 7-12 kP. The out-of-specification result was logged the same "
                    "shift and an investigation was opened per the site OOS procedure.",
                    "Retesting of retained samples confirmed the original result was an isolated punch "
                    "wear issue on tablet press station 4. The affected sub-lot was quarantined and the "
                    "press station was refurbished before the next run.",
                ),
            ),
        ),
    ),
    # QA — satisfied, incomplete (title only, no real body). "CAPA Log" left unmatched (missing).
    DepartmentDemoDocument(
        filename="QA-AUD-2026_Internal_Audit_Schedule_and_Reports.docx",
        department="qa",
        title_block=(
            "QA-AUD-2026 Internal Audit Schedule and Reports",
            "Effective 2026-01-05 | Owner: Quality Assurance | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "Audit Schedule",
                (
                    "The 2026 internal audit schedule covers all five site departments once per "
                    "calendar year, with QC and Manufacturing audited twice given their higher process "
                    "risk. Auditors are drawn from a cross-department pool trained on ISO 13485 Clause "
                    "8.2.4.",
                    "Completed audit reports for Q1 2026 are attached below: QC (2026-01-20, two minor "
                    "findings, both closed), Engineering (2026-02-18, no findings), and Utilities "
                    "(2026-03-05, one major finding related to HVAC requalification, CAPA-2026-0033 "
                    "opened).",
                ),
            ),
        ),
    ),
    DepartmentDemoDocument(
        filename="QA-MGMT-2026-Q1_Management_Review_Minutes.docx",
        department="qa",
        title_block=(
            "QA-MGMT-2026-Q1 Management Review Minutes",
            "Draft | Owner: Quality Assurance | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(),
    ),
    # Utilities — satisfied only. "HVAC Qualification Report" and "Utility Monitoring Log" left unmatched (missing).
    DepartmentDemoDocument(
        filename="UT-VAL-003_Purified_Water_System_Validation_Report.docx",
        department="utilities",
        title_block=(
            "UT-VAL-003 Purified water system validation report",
            "Effective 2025-11-20 | Owner: Utilities Engineering | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "Water System Validation",
                (
                    "The purified water loop (PW-1) completed a three-phase water system validation "
                    "(installation, operational, and performance qualification) between 2025-09-01 and "
                    "2025-11-15. Conductivity, TOC, and microbial results met USP Purified Water limits "
                    "at all sample points across the 20-day performance qualification phase.",
                    "The validation report was approved by Utilities Engineering and Quality Assurance "
                    "on 2025-11-20 and is retained with the ongoing utility monitoring plan.",
                ),
            ),
        ),
    ),
    # Manufacturing — satisfied, satisfied. "Process Validation Report" left unmatched (missing).
    DepartmentDemoDocument(
        filename="DHR-2026-0512_Lot_26-118_Device_History_Record.docx",
        department="manufacturing",
        title_block=(
            "DHR-2026-0512 Lot 26-118 device history record",
            "Released 2026-03-02 | Owner: Manufacturing | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "Device History Record",
                (
                    "This device history record for lot 26-118 documents manufacture in accordance with "
                    "the approved device master record, including component lot traceability, in-process "
                    "inspection results, and final release testing.",
                    "All in-process checks were within specification and the lot was released by the "
                    "quality control unit on 2026-03-02 after final review of the complete record "
                    "against the device master record.",
                ),
            ),
        ),
    ),
    DepartmentDemoDocument(
        filename="MFG-PM-2026-011_Filling_Line_3_Equipment_Maintenance_Log.docx",
        department="manufacturing",
        title_block=(
            "MFG-PM-2026-011 Filling line 3 equipment maintenance log",
            "Owner: Manufacturing | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "Maintenance Log",
                (
                    "Filling line 3 preventive maintenance was performed on schedule in January, "
                    "February, and March 2026 per the site preventive maintenance program. Each entry "
                    "records the technician, parts replaced, and post-maintenance verification run.",
                    "No unplanned maintenance events were logged for filling line 3 during this period.",
                ),
            ),
        ),
    ),
    # Engineering — satisfied, incomplete (title only, no real body). "Engineering Change Order Log" left unmatched (missing).
    DepartmentDemoDocument(
        filename="DHF-X200_Design_History_File.docx",
        department="engineering",
        title_block=(
            "DHF-X200 Design history file, Model X200",
            "Owner: Engineering | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "Design History File",
                (
                    "This design history file for the Model X200 device contains the approved design "
                    "plan, design inputs and outputs, verification and validation protocols and reports, "
                    "and design review records, demonstrating the design was developed in accordance "
                    "with the approved design plan.",
                    "Design transfer to Manufacturing was completed and approved on 2025-12-10 following "
                    "successful process validation.",
                ),
            ),
        ),
    ),
    DepartmentDemoDocument(
        filename="RMF-X200_Risk_Management_File.docx",
        department="engineering",
        title_block=(
            "RMF-X200 Risk management file, Model X200",
            "Draft | Owner: Engineering | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(),
    ),
)


def build_document(demo: DepartmentDemoDocument, output_dir: Path) -> Path:
    doc = DocxDocument()
    core = doc.core_properties
    core.author = core.last_modified_by = "DeviationTrace demo generator"
    core.created = core.modified = _FIXED_TIMESTAMP
    core.title = demo.filename.removesuffix(".docx")

    doc.add_heading(demo.title_block[0], level=0)
    for line in demo.title_block[1:]:
        doc.add_paragraph(line)
    for heading, paragraphs in demo.sections:
        doc.add_heading(heading, level=1)
        for paragraph in paragraphs:
            doc.add_paragraph(paragraph)

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / demo.filename
    doc.save(path)
    return path


def build_all(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    return [build_document(demo, output_dir) for demo in DEPARTMENT_DEMO_DOCUMENTS]


if __name__ == "__main__":
    for written in build_all():
        print(f"Wrote {written}")
