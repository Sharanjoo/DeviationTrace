"""Generate the synthetic documents for the documentation completeness
(Good Documentation Practice) demo: reports with sign-off fields
deliberately left blank, so the check has something real to flag.

Run from backend/: python -m app.seed.documentation_demo_documents
Writes to <repo root>/demo_documents/. Every document is fictional and says
so in its title block.

What each one should produce (see tests/test_documentation.py):
- DHR-2026-0601 (Word, Manufacturing): a sign-off table with the production
  reviewer unsigned, QA approval unsigned and undated, an empty QA release
  stamp, and an unfilled "[Insert disposition]". The "Prepared by" row is
  complete, and "QA release" is signed with a pasted image, so neither is
  flagged.
- QA-CAPA-2026-019 (digital PDF, QA): "Approved by" and its date blank.
- ENG-ECO-2026-044 (scanned PDF, Engineering): no text layer, so it's
  flagged for a manual check.
"""

import base64
import io
from datetime import datetime
from pathlib import Path

from docx import Document as DocxDocument
from fpdf import FPDF
from PIL import Image

from app.seed.demo_documents import DEFAULT_OUTPUT_DIR, SYNTHETIC_NOTICE

_FIXED_TIMESTAMP = datetime(2026, 1, 1)
# 1x1 PNG standing in for a pasted signature image.
_SIGNATURE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

DHR = "DHR-2026-0601_Lot_26-131_Device_History_Record.docx"
CAPA_REVIEW = "QA-CAPA-2026-019_CAPA_Effectiveness_Review.pdf"
SCANNED_ECO = "ENG-ECO-2026-044_Engineering_Change_Order_scanned.pdf"

# (filename, department) for the seed scenario that uploads them.
DOCUMENTATION_DEMO_DOCUMENTS: tuple[tuple[str, str], ...] = (
    (DHR, "manufacturing"),
    (CAPA_REVIEW, "qa"),
    (SCANNED_ECO, "engineering"),
)


def _build_dhr(path: Path) -> None:
    doc = DocxDocument()
    doc.add_heading("DHR-2026-0601 Lot 26-131 Device History Record", level=1)
    doc.add_paragraph(SYNTHETIC_NOTICE)
    doc.add_paragraph("Device: X200 infusion set    Lot number: 26-131    Quantity manufactured: 4,800 units")
    doc.add_paragraph(
        "Manufacturing was performed on line 2 per work instruction WI-MFG-022 revision C. In-process inspection "
        "results were within specification for all sampled units, and final acceptance testing was completed per "
        "the device master record before release to inventory. Environmental monitoring of the assembly room "
        "remained within limits throughout the run."
    )
    doc.add_paragraph("Labelling reconciliation: issued 4,900 labels, used 4,800, destroyed 100.")
    doc.add_paragraph("Final release decision: [Insert disposition]")

    approvals = doc.add_table(rows=5, cols=4)
    approvals.style = "Table Grid"
    rows = [
        ["Role", "Name", "Signature", "Date"],
        ["Prepared by", "A. Kumar", "A. Kumar", "03-Nov-2026"],
        ["Reviewed by (Production)", "J. Lee", "", "04-Nov-2026"],
        ["QA approval", "R. Patel", "", ""],
        ["QA release", "M. Gomez", "", "05-Nov-2026"],
    ]
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            approvals.cell(r, c).text = text
    approvals.cell(4, 2).paragraphs[0].add_run().add_picture(io.BytesIO(_SIGNATURE_PNG))

    stamp = doc.add_table(rows=1, cols=2)
    stamp.style = "Table Grid"
    stamp.cell(0, 0).text = "QA release stamp"

    core = doc.core_properties
    core.title = path.stem
    core.created = core.modified = _FIXED_TIMESTAMP
    doc.save(path)


def _build_capa_review(path: Path) -> None:
    pdf = FPDF()
    pdf.set_creation_date(_FIXED_TIMESTAMP)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in [
        "QA-CAPA-2026-019 CAPA Effectiveness Review",
        SYNTHETIC_NOTICE[:80],
        "",
        "CAPA-2026-019 addressed recurring label reconciliation discrepancies on line 2.",
        "Effectiveness was verified by reviewing 12 consecutive batches; no further",
        "discrepancies were recorded and the corrective action is considered effective.",
        "",
        "Reviewed by: M. Gomez        Date: 06-Nov-2026",
        "Approved by: ______________   Date: ______________",
    ]:
        pdf.cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))


def _build_scanned_eco(path: Path) -> None:
    # A blank "scanned page": an image with no text layer.
    page = io.BytesIO()
    Image.new("RGB", (850, 1100), "white").save(page, format="PNG")
    page.seek(0)
    pdf = FPDF()
    pdf.set_creation_date(_FIXED_TIMESTAMP)
    pdf.add_page()
    pdf.image(page, x=5, y=5, w=200)
    pdf.output(str(path))


def build_all(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    builders = {DHR: _build_dhr, CAPA_REVIEW: _build_capa_review, SCANNED_ECO: _build_scanned_eco}
    written = []
    for filename, build in builders.items():
        path = output_dir / filename
        build(path)
        written.append(path)
    return written


if __name__ == "__main__":
    for written in build_all():
        print(f"Wrote {written}")
