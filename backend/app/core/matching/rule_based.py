from app.core.matching.base import FindingData
from app.models.document import Document
from app.models.document_section import DocumentSection
from app.models.regulatory_clause import RegulatoryClause


def _pick_section(sections: list[DocumentSection], expected_heading: str | None) -> DocumentSection:
    by_heading = {s.heading: s for s in sections}
    if expected_heading and expected_heading in by_heading:
        return by_heading[expected_heading]
    if "Unclassified" in by_heading:
        return by_heading["Unclassified"]
    return sections[-1]


class RuleBasedMatchingEngine:
    """v1: deterministic keyword/phrase matching against each clause's
    curated match_phrases. Never produces "contradicted" findings — that
    needs real cross-document comparison, which is future work behind this
    same swappable interface (see base.MatchingEngine)."""

    def evaluate(
        self,
        document: Document,
        sections: list[DocumentSection],
        clauses: list[RegulatoryClause],
    ) -> list[FindingData]:
        if not sections:
            return []

        corpus = "\n".join(section.text for section in sections).casefold()
        findings: list[FindingData] = []

        for clause in clauses:
            phrases = clause.match_phrases or []
            if not phrases:
                continue

            found = [phrase for phrase in phrases if phrase.casefold() in corpus]
            if len(found) == len(phrases):
                continue  # fully addressed, no finding

            section = _pick_section(sections, clause.expected_heading)

            if not found:
                status = "missing"
                severity = "critical"
                explanation = (
                    f"{document.type.upper()} does not address {clause.regulation.upper()} "
                    f"{clause.clause_number}: none of the expected language "
                    f"({', '.join(phrases)}) was found."
                )
            else:
                status = "partial"
                severity = "major"
                missing_phrases = [p for p in phrases if p not in found]
                explanation = (
                    f"{document.type.upper()} partially addresses {clause.regulation.upper()} "
                    f"{clause.clause_number}: found {', '.join(found)}, but still missing "
                    f"{', '.join(missing_phrases)}."
                )

            findings.append(
                FindingData(
                    clause_id=clause.id,
                    section_id=section.id,
                    status=status,
                    severity=severity,
                    explanation=explanation,
                )
            )

        return findings
