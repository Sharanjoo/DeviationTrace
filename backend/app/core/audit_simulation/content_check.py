"""Content check for the internal audit simulation: does each SOP or
deviation report actually address the regulatory requirements that apply
to it? This is the "is it adequate?" half of an internal audit, alongside
the checklist's "does the record exist?" half (rule_based.py).

It reuses the clause library and the swappable MatchingEngine (the original
SOP & deviation check), so the matching logic stays one module that the
simulation calls rather than a copy."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.matching.rule_based import RuleBasedMatchingEngine
from app.models.document import Document
from app.models.regulatory_clause import RegulatoryClause

CONTENT_DOCUMENT_TYPES = ("sop", "deviation")
PROCESS_AREAS = ("deviation_handling", "capa")

_REGULATION_NAMES = {"qmsr": "QMSR", "iso13485": "ISO 13485", "cfr211": "21 CFR"}

# Which regulations apply depends on what the company makes: device makers
# are held to QMSR (21 CFR 820) and ISO 13485; drug makers to the cGMP rules
# in 21 CFR 211. Checking a device SOP against 211 (or the reverse) would
# report gaps against requirements that don't apply.
REGULATIONS_BY_INDUSTRY = {"device": ("qmsr", "iso13485"), "drug": ("cfr211",)}


@dataclass
class ContentGap:
    clause: RegulatoryClause
    section_heading: str | None
    status: str  # missing | partial
    severity: str  # critical | major
    explanation: str


def process_areas_for(document: Document) -> tuple[str, ...]:
    """The process area the user chose; otherwise the one detected from the
    text; otherwise both (we can't tell, so check against all)."""
    if document.process_area in PROCESS_AREAS:
        return (document.process_area,)
    if document.detected_process_area in PROCESS_AREAS:
        return (document.detected_process_area,)
    return PROCESS_AREAS


def requirement_title(clause: RegulatoryClause) -> str:
    return clause.title or f"{_REGULATION_NAMES.get(clause.regulation, clause.regulation)} {clause.clause_number}"


def check_document_content(db: Session, document: Document, industry: str) -> list[ContentGap]:
    """Content gaps for one processed SOP or deviation report, against the
    regulations that apply to the company's industry."""
    if document.type not in CONTENT_DOCUMENT_TYPES or document.status != "processed" or not document.sections:
        return []

    clauses = (
        db.query(RegulatoryClause)
        .filter(
            RegulatoryClause.process_area.in_(process_areas_for(document)),
            RegulatoryClause.regulation.in_(REGULATIONS_BY_INDUSTRY.get(industry, ("qmsr", "iso13485", "cfr211"))),
            RegulatoryClause.document_type_applicability.any(document.type),
        )
        .all()
    )
    by_id = {c.id: c for c in clauses}
    sections = sorted(document.sections, key=lambda s: s.order)
    headings = {s.id: s.heading for s in sections}
    kind = "SOP" if document.type == "sop" else "deviation report"

    gaps = []
    for result in RuleBasedMatchingEngine().evaluate(document, sections, clauses):
        clause = by_id[result.clause_id]
        if result.status == "missing":
            explanation = f"This {kind} doesn't address this requirement."
        else:
            explanation = f"This {kind} only partly addresses this requirement; some of what's required isn't covered."
        gaps.append(
            ContentGap(
                clause=clause,
                section_heading=headings.get(result.section_id),
                status=result.status,
                severity=result.severity,
                explanation=explanation,
            )
        )
    return gaps
