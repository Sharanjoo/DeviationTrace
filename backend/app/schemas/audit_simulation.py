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
    # The history entry this run was saved as.
    run_id: uuid.UUID
    run_number: int
    run_code: str


class AuditSimulationRunSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_number: int
    run_code: str
    created_at: datetime
    missing: int
    incomplete: int
    satisfied: int
    total: int


class AuditSimulationRunItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department: str
    item_name: str
    citation: str
    status: str
    severity: str
    explanation: str
    matched_document_title: str | None


class AuditSimulationRunDetailOut(AuditSimulationRunSummaryOut):
    items: list[AuditSimulationRunItemOut]


class EffectiveChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department: str
    item_name: str
    citation: str
    requirement_text: str
    match_phrases: list[str]
    is_custom: bool
    is_excluded: bool


class ChecklistItemCreate(BaseModel):
    department: str
    item_name: str
    citation: str
    requirement_text: str
    match_phrases: list[str] = []
