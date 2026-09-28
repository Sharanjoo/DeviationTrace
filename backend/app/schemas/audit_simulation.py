import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.document import DocumentSummaryOut


class AuditChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department: str
    item_name: str
    citation: str
    requirement_text: str


class AuditChecklistFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    checklist_item: AuditChecklistItemOut
    matched_document: DocumentSummaryOut | None
    status: str
    severity: str
    explanation: str
    evaluated_at: datetime


class AuditSimulationRunResult(BaseModel):
    missing: int
    incomplete: int
    satisfied: int
