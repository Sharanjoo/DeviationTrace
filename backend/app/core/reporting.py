import uuid
from collections import Counter
from datetime import datetime, timezone

from fpdf import FPDF
from sqlalchemy.orm import Session, joinedload

from app.models.audit_simulation_run import AuditSimulationRun
from app.models.document import Document
from app.models.finding import Finding
from app.models.organization import Organization

SEVERITY_ORDER = ["critical", "major", "minor"]


def generate_summary_pdf(db: Session, org_id: uuid.UUID) -> bytes:
    org = db.get(Organization, org_id)
    findings = (
        db.query(Finding)
        .join(Document, Finding.document_id == Document.id)
        .filter(Document.org_id == org_id)
        .options(joinedload(Finding.document), joinedload(Finding.clause))
        .all()
    )

    severity_counts = Counter(f.severity for f in findings)
    process_area_counts = Counter(f.document.process_area for f in findings)

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "DeviationTrace Audit-Readiness Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Organization: {org.name if org else org_id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0,
        8,
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"Total findings: {len(findings)}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for severity in SEVERITY_ORDER:
        pdf.cell(0, 7, f"  {severity.capitalize()}: {severity_counts.get(severity, 0)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "By process area:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for area, count in process_area_counts.items():
        pdf.cell(0, 7, f"  {area}: {count}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Findings", new_x="LMARGIN", new_y="NEXT")
    for finding in findings:
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(
            0,
            6,
            f"[{finding.severity.upper()}] {finding.document.title} - "
            f"{finding.clause.regulation.upper()} {finding.clause.clause_number} ({finding.status})",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, finding.explanation, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    return bytes(pdf.output())


# --------------------------------------------------- audit simulation run

_DEPARTMENT_NAMES = {
    "qc": "Quality Control",
    "qa": "Quality Assurance",
    "utilities": "Utilities",
    "manufacturing": "Manufacturing",
    "engineering": "Engineering",
}
_STATUS_COLORS = {"missing": (220, 38, 38), "incomplete": (217, 119, 6), "satisfied": (5, 150, 105)}

_UNICODE_FALLBACKS = {
    "—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "•": "-", " ": " ",
}


def _latin1(text: str) -> str:
    """fpdf2's built-in Helvetica only covers Latin-1; swap common typographic
    characters and replace anything else rather than failing the download."""
    for char, plain in _UNICODE_FALLBACKS.items():
        text = text.replace(char, plain)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_audit_run_pdf(org: Organization, run: AuditSimulationRun) -> bytes:
    """Report for one internal audit simulation run, from its frozen items."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def line(text: str, size: int = 11, style: str = "", height: float = 7) -> None:
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(0, height, _latin1(text), new_x="LMARGIN", new_y="NEXT")

    line("Internal Audit Simulation Report", size=18, style="B", height=10)
    line(f"{run.run_code}  |  {org.name}", size=12)
    line(f"Run on {run.created_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", size=10)
    line(f"Report generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", size=10)
    pdf.ln(4)

    readiness = round(run.satisfied / run.total * 100) if run.total else 0
    line(f"Audit readiness: {readiness}%  ({run.satisfied} of {run.total} required records satisfied)", size=13, style="B")
    line(f"Missing: {run.missing}    Incomplete: {run.incomplete}    Satisfied: {run.satisfied}")
    pdf.ln(4)

    current_department = None
    for item in run.items:
        if item.department != current_department:
            current_department = item.department
            pdf.ln(2)
            line(_DEPARTMENT_NAMES.get(item.department, item.department.upper()), size=13, style="B", height=8)
        pdf.set_text_color(*_STATUS_COLORS.get(item.status, (0, 0, 0)))
        line(f"[{item.status.upper()}] {item.item_name}", size=10, style="B", height=6)
        pdf.set_text_color(0, 0, 0)
        line(item.citation, size=9, height=5)
        line(item.explanation, size=10, height=5)
        if item.matched_document_title:
            line(f"Matched document: {item.matched_document_title}", size=9, height=5)
        pdf.ln(2)

    return bytes(pdf.output())
