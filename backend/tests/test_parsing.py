from docx import Document as DocxDocument
from fpdf import FPDF

from app.core.parsing.classify import detect_process_area
from app.core.parsing.extract import extract_text
from app.core.parsing.sections import split_into_sections


def _write_docx(tmp_path, filename: str, paragraphs: list[str]) -> str:
    doc = DocxDocument()
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph)
    path = tmp_path / filename
    doc.save(path)
    return str(path)


def _write_pdf(tmp_path, filename: str, lines: list[str]) -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in lines:
        pdf.cell(0, 10, text=line, new_x="LMARGIN", new_y="NEXT")
    path = tmp_path / filename
    pdf.output(str(path))
    return str(path)


def test_extract_and_split_sop_docx(tmp_path):
    path = _write_docx(
        tmp_path,
        "sop.docx",
        [
            "Scope",
            "This SOP covers deviation handling for widget assembly.",
            "Procedure",
            "Step 1: identify the nonconformance. Step 2: notify QA.",
            "Records",
            "Retain deviation records for seven years.",
        ],
    )

    text = extract_text(path)
    sections = split_into_sections(text, "sop")
    headings = [s.heading for s in sections]

    assert headings == ["Scope", "Procedure", "Records"]
    assert "identify the nonconformance" in sections[1].text
    for section in sections:
        assert text[section.span_start : section.span_end] == section.text


def test_extract_and_split_deviation_pdf(tmp_path):
    path = _write_pdf(
        tmp_path,
        "deviation.pdf",
        [
            "Description",
            "Widget batch 42 failed torque spec.",
            "Root Cause",
            "Fixture calibration drift caused under-torqueing.",
            "Corrective Action (CAPA)",
            "Recalibrate fixture and retrain operators.",
        ],
    )

    text = extract_text(path)
    sections = split_into_sections(text, "deviation")
    headings = [s.heading for s in sections]

    assert headings == ["Description", "Root Cause", "Corrective Action (CAPA)"]
    assert "torque spec" in sections[0].text


def test_batch_record_falls_back_to_single_section(tmp_path):
    path = tmp_path / "batch.txt"
    path.write_text("Lot 100 produced 500 units. All in spec.", encoding="utf-8")

    text = extract_text(str(path))
    sections = split_into_sections(text, "batch_record")

    assert len(sections) == 1
    assert sections[0].heading == "Full Document"
    assert sections[0].text == text


def test_unclassified_preamble_is_preserved():
    text = "Cover page notes.\nScope\nThis is the scope body."
    sections = split_into_sections(text, "sop")

    assert sections[0].heading == "Unclassified"
    assert "Cover page notes" in sections[0].text
    assert sections[1].heading == "Scope"


def test_classify_capa_vs_deviation():
    capa_area, capa_confidence = detect_process_area(
        "We implemented a corrective action and a preventive action per our CAPA procedure."
    )
    deviation_area, deviation_confidence = detect_process_area(
        "This deviation investigation found a nonconformance requiring root cause analysis."
    )

    assert capa_area == "capa"
    assert capa_confidence > 0.5
    assert deviation_area == "deviation_handling"
    assert deviation_confidence > 0.5


def test_classify_no_keywords_returns_none():
    area, confidence = detect_process_area("The sky is blue today.")
    assert area is None
    assert confidence == 0.0
