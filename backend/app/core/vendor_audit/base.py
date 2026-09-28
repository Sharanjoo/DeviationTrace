import uuid
from dataclasses import dataclass
from typing import Protocol

from app.models.document import Document
from app.models.document_section import DocumentSection
from app.models.vendor_standard import VendorStandard


@dataclass
class VendorAuditFindingData:
    standard_id: uuid.UUID
    section_id: uuid.UUID
    status: str  # "missing" | "partial" | "satisfied"
    severity: str  # "critical" | "major" | "resolved"
    explanation: str


class VendorAuditEngine(Protocol):
    """Swappable per the same pattern as MatchingEngine (app/core/matching/base.py)
    and AuditSimulationEngine (app/core/audit_simulation/base.py): a rule-based
    v1 today, an LLM-assisted engine later, without changing the caller."""

    def evaluate(
        self,
        document: Document,
        sections: list[DocumentSection],
        standards: list[VendorStandard],
    ) -> list[VendorAuditFindingData]: ...
