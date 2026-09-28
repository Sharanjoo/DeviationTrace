import uuid
from dataclasses import dataclass
from typing import Protocol

from app.models.audit_checklist_item import AuditChecklistItem
from app.models.document import Document


@dataclass
class AuditChecklistFindingData:
    checklist_item_id: uuid.UUID
    status: str  # "missing" | "incomplete" | "satisfied"
    severity: str  # "critical" | "major" | "resolved"
    matched_document_id: uuid.UUID | None
    explanation: str


class AuditSimulationEngine(Protocol):
    """Swappable per the same pattern as MatchingEngine (app/core/matching/base.py):
    a rule-based v1 today, an LLM-assisted engine later, without changing the caller."""

    def evaluate(
        self,
        documents: list[Document],
        checklist_items: list[AuditChecklistItem],
    ) -> list[AuditChecklistFindingData]: ...
