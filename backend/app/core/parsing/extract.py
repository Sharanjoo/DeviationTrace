from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument


def extract_text(file_path: str) -> str:
    """Dispatches on file extension. Raises ValueError for unsupported types
    so the caller can record a clear processing_error instead of a 500."""
    suffix = Path(file_path).suffix.lower()

    if suffix == ".txt":
        return Path(file_path).read_text(encoding="utf-8", errors="replace")

    if suffix == ".docx":
        docx_doc = DocxDocument(file_path)
        return "\n".join(paragraph.text for paragraph in docx_doc.paragraphs)

    if suffix == ".pdf":
        with pdfplumber.open(file_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    raise ValueError(f"Unsupported file type: {suffix}")
