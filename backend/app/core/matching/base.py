import uuid
from dataclasses import dataclass
from typing import Protocol

from app.models.document import Document
from app.models.document_section import DocumentSection
from app.models.regulatory_clause import RegulatoryClause


@dataclass
class FindingData:
    clause_id: uuid.UUID
    section_id: uuid.UUID
    status: str  # "missing" | "partial" | "contradicted"
    severity: str  # "critical" | "major" | "minor"
    explanation: str


class MatchingEngine(Protocol):
    """Swappable per the PRD: a rule-based v1 today, an LLM-assisted engine
    later, without changing the caller in documents.py."""

    def evaluate(
        self,
        document: Document,
        sections: list[DocumentSection],
        clauses: list[RegulatoryClause],
    ) -> list[FindingData]: ...
