"""Documentation completeness (Good Documentation Practice) check.

Finds sign-off fields left blank in a document: missing signatures, stamps,
dates and required entries, plus template placeholders that were never
filled in ("[Insert name]", "TBD", "dd/mm/yyyy"). Works on the file itself
rather than the extracted text, because sign-off blocks usually live in
tables, which the text extraction skips.

Digital documents (Word, digital PDF, text) only. Scanned PDFs have no text
layer, so they're reported as one "scanned" issue asking for a manual check:
verifying ink signatures and stamps on scans needs OCR plus image analysis,
which is a later phase.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument


@dataclass(frozen=True)
class DocIssue:
    kind: str  # missing_signature | missing_stamp | missing_date | missing_entry | placeholder | scanned
    field: str  # what's blank, e.g. "Approved by - Signature"
    context: str  # the line or row it was found in
    location: str | None  # "Table 1, row 3", "Page 2", "Line 14"
    confidence: str = "high"  # high | check (e.g. a PDF page that has images, which may be a signature)


# --------------------------------------------------------------- vocabulary

_SIGNATURE = re.compile(r"\b(signature|signed|sign[- ]?off|initials?|e-?sign)\b", re.I)
_STAMP = re.compile(r"\b(stamp|seal)\b", re.I)
_DATE = re.compile(r"\bdate\b", re.I)
# "Approved by:" left blank means the approval itself is missing.
_SIGN_OFF_ROLE = re.compile(
    r"\b(prepared|reviewed|approved|verified|checked|performed|authori[sz]ed|released|witnessed|completed|executed)\s+by\b",
    re.I,
)
# Other entries a record shouldn't leave blank.
_ENTRY = re.compile(
    r"\b(name|batch\s*(no\.?|number|#)|lot\s*(no\.?|number|#)|serial\s*(no\.?|number)|equipment\s*id|"
    r"quantity|qty|result|reading|time|temperature|disposition|comments?)\b",
    re.I,
)

_BLANK_VALUE = re.compile(r"^[\s_\-–—.·:|]*$")
_PLACEHOLDERS = [
    re.compile(r"\[(?:insert|enter|add|type|name|date|signature|sign|tbd|tbc|xx+)[^\]]{0,40}\]", re.I),
    re.compile(r"\{\{[^}]{1,40}\}\}"),
    re.compile(r"<<[^>]{1,40}>>"),
    re.compile(r"\b(?:TBD|TBC)\b"),
    re.compile(r"\b(?:dd|DD)[/\-.](?:mm|MM|mmm|MMM)[/\-.](?:yy|yyyy|YY|YYYY)\b"),
    re.compile(r"\b(?:mm|MM)[/\-.](?:dd|DD)[/\-.](?:yy|yyyy|YY|YYYY)\b"),
    re.compile(r"_{1,3}/_{1,3}/_{2,4}"),
    re.compile(r"\bXX/XX/XX(?:XX)?\b"),
]
# A field label starts a line or follows a clear separator (2+ spaces, a
# tab, "|", or a blank "____" field), and is at most six single-spaced
# words, so "Equipment ID: BAL-04    Location: Lab 2" is two fields and
# the value "BAL-04" isn't mistaken for part of the next label.
_LABEL = re.compile(
    r"(?:^|\s{2,}|\t|\||(?<=_)\s+)\s*([A-Za-z][\w/&()'.#-]*(?: [\w/&()'.#-]+){0,5})\s*:"
)
_SIGNATURE_LINE = re.compile(r"^\s*_{8,}\s*$")

_MAX_CONTEXT = 160


def _kind_for_label(label: str) -> str | None:
    if _STAMP.search(label):
        return "missing_stamp"
    if _SIGNATURE.search(label) or _SIGN_OFF_ROLE.search(label):
        return "missing_signature"
    if _DATE.search(label):
        return "missing_date"
    if _ENTRY.search(label):
        return "missing_entry"
    return None


def _is_blank(value: str) -> bool:
    return bool(_BLANK_VALUE.match(value)) or any(p.fullmatch(value.strip()) for p in _PLACEHOLDERS)


def _clip(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _MAX_CONTEXT else text[: _MAX_CONTEXT - 1] + "…"


# --------------------------------------------------------------- text lines


def _check_lines(lines: list[str], location_for) -> list[DocIssue]:
    """'Label: value' fields (several per line allowed), blank signature
    lines above a role, and placeholders anywhere."""
    issues: list[DocIssue] = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        labels = list(_LABEL.finditer(line))
        reported_spans = []  # field values already reported as blank
        for i, match in enumerate(labels):
            label = match.group(1).strip()
            kind = _kind_for_label(label)
            if kind is None:
                continue
            end = labels[i + 1].start() if i + 1 < len(labels) else len(line)  # next field's separator
            if _is_blank(line[match.end() : end]):
                issues.append(DocIssue(kind, label, _clip(line), location_for(index)))
                reported_spans.append((match.end(), end))

        # "________________" with the signer's role on the next line.
        if _SIGNATURE_LINE.match(line) and index + 1 < len(lines):
            below = lines[index + 1].strip()
            if below and (_SIGNATURE.search(below) or _SIGN_OFF_ROLE.search(below) or len(below) <= 40):
                issues.append(DocIssue("missing_signature", below, _clip(f"{line.strip()} / {below}"), location_for(index)))

        # Placeholders not already covered by a blank field on this line
        # ("Lot number: [Insert lot number]" is one blank entry, not two).
        for pattern in _PLACEHOLDERS:
            for found in pattern.finditer(line):
                if any(start <= found.start() < end for start, end in reported_spans):
                    continue
                issues.append(DocIssue("placeholder", found.group(0), _clip(line), location_for(index)))
    return issues


# --------------------------------------------------------------- tables


def _check_table(rows: list[list[tuple[str, bool]]], location_prefix: str) -> list[DocIssue]:
    """rows: cells as (text, has_image). Handles a header row of columns
    ("Role | Name | Signature | Date") and label/value pairs in a row
    ("Approved by | (blank)")."""
    issues: list[DocIssue] = []
    if not rows:
        return issues

    header = [text for text, _ in rows[0]]
    column_kinds = [_kind_for_label(h) if h else None for h in header]
    # A header row labels at least two columns ("Name | Signature | Date");
    # a single label next to a blank cell is a field, handled below.
    if any(column_kinds) and sum(1 for h in header if h.strip()) >= 2:
        for r, row in enumerate(rows[1:], start=2):
            texts = [t for t, _ in row]
            if not any(t.strip() for t in texts):
                continue  # an unused spare row
            row_label = next((t for t in texts if t.strip()), f"Row {r}")
            for c, (text, has_image) in enumerate(row):
                kind = column_kinds[c] if c < len(column_kinds) else None
                if kind and _is_blank(text) and not has_image:
                    issues.append(
                        DocIssue(
                            kind,
                            f"{row_label.strip()} - {header[c].strip()}",
                            _clip(" | ".join(texts)),
                            f"{location_prefix}, row {r}",
                        )
                    )
        return issues

    for r, row in enumerate(rows, start=1):
        for c in range(len(row) - 1):
            label, _ = row[c]
            value, has_image = row[c + 1]
            kind = _kind_for_label(label.rstrip(":")) if label.strip() else None
            if kind and _is_blank(value) and not has_image:
                issues.append(
                    DocIssue(kind, label.strip().rstrip(":"), _clip(" | ".join(t for t, _ in row)), f"{location_prefix}, row {r}")
                )
    return issues


# --------------------------------------------------------------- formats


def _check_docx(path: str) -> list[DocIssue]:
    doc = DocxDocument(path)
    paragraphs = [p.text for p in doc.paragraphs]
    issues = _check_lines(paragraphs, lambda i: f"Paragraph {i + 1}")
    for t, table in enumerate(doc.tables, start=1):
        rows = []
        for row in table.rows:
            cells, seen = [], set()
            for cell in row.cells:
                if id(cell._tc) in seen:  # merged cells repeat
                    continue
                seen.add(id(cell._tc))
                has_image = bool(cell._tc.xpath(".//w:drawing | .//w:pict"))
                cells.append((cell.text, has_image))
            rows.append(cells)
        issues += _check_table(rows, f"Table {t}")
        # Placeholders inside table cells.
        for r, row in enumerate(rows, start=1):
            for text, _ in row:
                for pattern in _PLACEHOLDERS:
                    for found in pattern.finditer(text):
                        issues.append(DocIssue("placeholder", found.group(0), _clip(text), f"Table {t}, row {r}"))
    return issues


def _check_pdf(path: str) -> list[DocIssue]:
    issues: list[DocIssue] = []
    with pdfplumber.open(path) as pdf:
        texts = [page.extract_text() or "" for page in pdf.pages]
        has_images = [bool(page.images) for page in pdf.pages]
        # No usable text layer but images: a scan.
        if pdf.pages and sum(len(t.strip()) for t in texts) < 20 * len(pdf.pages) and any(has_images):
            return [
                DocIssue(
                    "scanned",
                    "Scanned document",
                    "No readable text: signatures, stamps and handwritten entries can't be checked automatically yet.",
                    None,
                )
            ]
        for p, page in enumerate(pdf.pages, start=1):
            lines = texts[p - 1].splitlines()
            page_issues = _check_lines(lines, lambda i, p=p: f"Page {p}")
            for t, table in enumerate(page.extract_tables() or [], start=1):
                rows = [[((cell or ""), False) for cell in row] for row in table]
                page_issues += _check_table(rows, f"Page {p}, table {t}")
            # A pasted signature image can't be told apart from a blank yet.
            if has_images[p - 1]:
                page_issues = [
                    DocIssue(i.kind, i.field, i.context, i.location, "check")
                    if i.kind in ("missing_signature", "missing_stamp")
                    else i
                    for i in page_issues
                ]
            issues += page_issues
    return issues


def _check_txt(path: str) -> list[DocIssue]:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    return _check_lines(lines, lambda i: f"Line {i + 1}")


def check_documentation(path: str) -> list[DocIssue]:
    """All documentation-completeness issues in a file, de-duplicated, in
    document order."""
    suffix = Path(path).suffix.lower()
    if suffix == ".docx":
        found = _check_docx(path)
    elif suffix == ".pdf":
        found = _check_pdf(path)
    elif suffix == ".txt":
        found = _check_txt(path)
    else:
        return []
    unique, seen = [], set()
    for issue in found:
        key = (issue.kind, issue.field.lower(), issue.location)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique
