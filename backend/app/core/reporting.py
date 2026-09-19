import uuid
from collections import Counter
from datetime import datetime, timezone

from fpdf import FPDF
from sqlalchemy.orm import Session, joinedload

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
