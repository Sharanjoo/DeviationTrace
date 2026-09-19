# Lightweight keyword-scored process-area detector. The user's own
# upload-time selection (Document.process_area) stays authoritative; this is
# only stored alongside it as a signal to compare against, per the PRD's open
# question about validating automated classification before trusting it.

CAPA_KEYWORDS = [
    "corrective action",
    "preventive action",
    "capa",
    "effectiveness verification",
    "effectiveness of the corrective action",
]

DEVIATION_KEYWORDS = [
    "deviation",
    "nonconformance",
    "non-conformance",
    "root cause",
    "investigation",
    "discrepancy",
]


def detect_process_area(text: str) -> tuple[str | None, float]:
    """Returns (detected_process_area, confidence). Confidence is the
    winning category's share of total keyword hits; (None, 0.0) if no
    keywords matched at all."""
    normalized = text.casefold()
    capa_score = sum(normalized.count(keyword) for keyword in CAPA_KEYWORDS)
    deviation_score = sum(normalized.count(keyword) for keyword in DEVIATION_KEYWORDS)
    total = capa_score + deviation_score

    if total == 0:
        return None, 0.0
    if capa_score >= deviation_score:
        return "capa", capa_score / total
    return "deviation_handling", deviation_score / total
