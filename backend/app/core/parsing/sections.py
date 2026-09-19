import re
from dataclasses import dataclass

# Canonical heading -> phrases that identify it. Deliberately rule-based and
# small so the split is deterministic and auditable, per the PRD's "keep the
# core deterministic" methodology note. batch_record has no vocabulary yet —
# extraction for it is explicitly deferred to a later milestone.
HEADING_VOCAB: dict[str, list[tuple[str, list[str]]]] = {
    "sop": [
        ("Scope", ["scope"]),
        ("Purpose", ["purpose"]),
        ("Procedure", ["procedure"]),
        ("Responsibilities", ["responsibilities"]),
        ("Records", ["records"]),
        ("References", ["references"]),
    ],
    "deviation": [
        ("Description", ["description"]),
        ("Investigation", ["investigation"]),
        ("Root Cause", ["root cause"]),
        ("Corrective Action (CAPA)", ["corrective action", "capa"]),
        ("Closure", ["closure"]),
    ],
}

_NUMBERING_PREFIX = re.compile(r"^(section\s+)?\d+(\.\d+)*[\.:)\-]?\s*", re.IGNORECASE)
_MAX_HEADING_LINE_LENGTH = 60


@dataclass
class SectionData:
    heading: str
    text: str
    order: int
    span_start: int
    span_end: int


def _normalize_heading_candidate(line: str) -> str:
    stripped = line.strip()
    stripped = _NUMBERING_PREFIX.sub("", stripped)
    return stripped.rstrip(":").strip().casefold()


def _match_heading(normalized: str, vocab: list[tuple[str, list[str]]]) -> str | None:
    if not normalized or len(normalized) > _MAX_HEADING_LINE_LENGTH:
        return None
    for canonical, aliases in vocab:
        for alias in aliases:
            if normalized == alias or normalized.startswith(f"{alias} "):
                return canonical
    return None


def split_into_sections(text: str, document_type: str) -> list[SectionData]:
    vocab = HEADING_VOCAB.get(document_type)
    if vocab is None:
        return [SectionData("Full Document", text, 0, 0, len(text))] if text.strip() else []

    matches: list[tuple[int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        heading = _match_heading(_normalize_heading_candidate(line), vocab)
        if heading:
            matches.append((offset, heading))
        offset += len(line)

    if not matches:
        return [SectionData("Unclassified", text, 0, 0, len(text))] if text.strip() else []

    sections: list[SectionData] = []
    order = 0

    preamble_end = matches[0][0]
    preamble = text[:preamble_end]
    if preamble.strip():
        sections.append(SectionData("Unclassified", preamble, order, 0, preamble_end))
        order += 1

    for i, (start, heading) in enumerate(matches):
        end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        sections.append(SectionData(heading, text[start:end], order, start, end))
        order += 1

    return sections
