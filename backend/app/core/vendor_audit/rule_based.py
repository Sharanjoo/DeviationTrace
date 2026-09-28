from app.core.vendor_audit.base import VendorAuditFindingData
from app.models.document import Document
from app.models.document_section import DocumentSection
from app.models.vendor_standard import VendorStandard


def _pick_section(sections: list[DocumentSection], expected_heading: str | None) -> DocumentSection:
    by_heading = {s.heading: s for s in sections}
    if expected_heading and expected_heading in by_heading:
        return by_heading[expected_heading]
    if "Unclassified" in by_heading:
        return by_heading["Unclassified"]
    return sections[-1]


class RuleBasedVendorAuditEngine:
    """v1: deterministic keyword/phrase matching of a single vendor audit
    report document's content against each applicable VendorStandard's
    match_phrases — same technique as RuleBasedMatchingEngine
    (app/core/matching/rule_based.py), but unlike it, full phrase coverage
    still produces a row (status="satisfied"), not silence, since the SME
    needs to see what the vendor's report did claim, not only where it fell
    short (same full-coverage philosophy as RuleBasedAuditSimulationEngine,
    app/core/audit_simulation/rule_based.py)."""

    def evaluate(
        self,
        document: Document,
        sections: list[DocumentSection],
        standards: list[VendorStandard],
    ) -> list[VendorAuditFindingData]:
        if not sections:
            return []

        corpus = "\n".join(section.text for section in sections).casefold()
        findings: list[VendorAuditFindingData] = []

        for standard in standards:
            phrases = standard.match_phrases or []
            if not phrases:
                continue

            found = [phrase for phrase in phrases if phrase.casefold() in corpus]
            section = _pick_section(sections, standard.expected_heading)

            if len(found) == len(phrases):
                findings.append(
                    VendorAuditFindingData(
                        standard_id=standard.id,
                        section_id=section.id,
                        status="satisfied",
                        severity="resolved",
                        explanation=(
                            f"Vendor audit report addresses '{standard.requirement_name}' "
                            f"({standard.citation}): all expected language "
                            f"({', '.join(phrases)}) was found."
                        ),
                    )
                )
            elif not found:
                findings.append(
                    VendorAuditFindingData(
                        standard_id=standard.id,
                        section_id=section.id,
                        status="missing",
                        severity="critical",
                        explanation=(
                            f"Vendor audit report does not address '{standard.requirement_name}' "
                            f"({standard.citation}): none of the expected language "
                            f"({', '.join(phrases)}) was found."
                        ),
                    )
                )
            else:
                missing_phrases = [p for p in phrases if p not in found]
                findings.append(
                    VendorAuditFindingData(
                        standard_id=standard.id,
                        section_id=section.id,
                        status="partial",
                        severity="major",
                        explanation=(
                            f"Vendor audit report partially addresses '{standard.requirement_name}' "
                            f"({standard.citation}): found {', '.join(found)}, but still missing "
                            f"{', '.join(missing_phrases)}."
                        ),
                    )
                )

        return findings
