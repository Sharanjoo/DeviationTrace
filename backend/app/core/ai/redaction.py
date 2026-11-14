"""Optional removal of personal identifiers before text is sent to an AI
model. Replaces emails, phone numbers, employee IDs and people's names in
sign-off fields with placeholders. Deliberately conservative: it targets
identifiers, not product, lot or document numbers the assessment needs."""

import re

_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[EMAIL]"),
    (re.compile(r"\+\d[\d\s().-]{7,}\d|\(\d{3}\)\s?\d{3}[-.\s]\d{4}"), "[PHONE]"),
    (re.compile(r"\b(?:EMP|EID|EMPLOYEE)[-\s]?(?:ID[-\s]?)?\d{3,}\b", re.I), "[EMPLOYEE-ID]"),
    # Names after a sign-off role, e.g. "Approved by: Rita Patel".
    (
        re.compile(
            r"(\b(?:prepared|reviewed|approved|verified|checked|performed|authori[sz]ed|released|witnessed|signed|"
            r"operator|analyst|reviewer|approver|auditor|owner)(?:\s+by)?\s*[:\-]\s*)"
            r"([A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,3})",
            re.I,
        ),
        r"\1[NAME]",
    ),
    # Initial-plus-surname, e.g. "J. Lee".
    (re.compile(r"\b[A-Z]\.\s?[A-Z][a-z]+(?:-[A-Z][a-z]+)?\b"), "[NAME]"),
]


def redact(text: str) -> tuple[str, int]:
    """(redacted text, number of replacements)."""
    total = 0
    for pattern, replacement in _RULES:
        text, count = pattern.subn(replacement, text)
        total += count
    return text, total
