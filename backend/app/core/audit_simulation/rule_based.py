from collections import defaultdict

from app.core.audit_simulation.base import AuditChecklistFindingData
from app.models.audit_checklist_item import AuditChecklistItem
from app.models.document import Document

# A matched document with less real content than this (e.g. a title page with
# no body) is treated as incomplete rather than satisfied — "has some text" is
# not enough to call a required report complete.
MIN_SUBSTANTIVE_LENGTH = 400


def _corpus(document: Document) -> str:
    """Document.title is the raw uploaded filename (underscores, no spaces),
    not prose — so, like the existing content-matching engine, phrases are
    matched against extracted section text (which includes the real title
    block heading as written inside the file), not the filename."""
    return "\n".join(section.text for section in document.sections).casefold()


def _match_score(item: AuditChecklistItem, document: Document) -> int:
    corpus = _corpus(document)
    return sum(1 for phrase in item.match_phrases if phrase.casefold() in corpus)


def _best_candidate(item: AuditChecklistItem, documents: list[Document]) -> Document | None:
    candidates = [doc for doc in documents if _match_score(item, doc) > 0]
    if not candidates:
        return None
    return max(candidates, key=lambda doc: (_match_score(item, doc), doc.uploaded_at))


class RuleBasedAuditSimulationEngine:
    """v1: deterministic keyword matching of each checklist item's
    match_phrases against candidate documents' extracted content within the
    same department, then a shallow completeness check (successfully
    processed, enough real content) — an existence/completeness check, not
    the content clause-match that's the existing MatchingEngine's job
    (app/core/matching/rule_based.py)."""

    def evaluate(
        self,
        documents: list[Document],
        checklist_items: list[AuditChecklistItem],
    ) -> list[AuditChecklistFindingData]:
        by_department: dict[str, list[Document]] = defaultdict(list)
        for document in documents:
            if document.department:
                by_department[document.department].append(document)

        findings: list[AuditChecklistFindingData] = []
        for item in checklist_items:
            candidates = by_department.get(item.department, [])
            match = _best_candidate(item, candidates)

            if match is None:
                findings.append(
                    AuditChecklistFindingData(
                        checklist_item_id=item.id,
                        status="missing",
                        severity="critical",
                        matched_document_id=None,
                        explanation=(
                            f"No document found in {item.department.upper()} matching '{item.item_name}' "
                            f"({item.citation})."
                        ),
                    )
                )
                continue

            is_complete = match.status == "processed" and any(
                len(s.text.strip()) >= MIN_SUBSTANTIVE_LENGTH for s in match.sections
            )
            if not is_complete:
                findings.append(
                    AuditChecklistFindingData(
                        checklist_item_id=item.id,
                        status="incomplete",
                        severity="major",
                        matched_document_id=match.id,
                        explanation=(
                            f"'{match.title}' was matched to '{item.item_name}' ({item.citation}) but is not a "
                            f"complete record (status={match.status})."
                        ),
                    )
                )
            else:
                findings.append(
                    AuditChecklistFindingData(
                        checklist_item_id=item.id,
                        status="satisfied",
                        severity="resolved",
                        matched_document_id=match.id,
                        explanation=f"'{match.title}' satisfies '{item.item_name}' ({item.citation}).",
                    )
                )

        return findings
