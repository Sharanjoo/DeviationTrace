import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.clause import RegulatoryClauseOut
from app.schemas.document import DocumentSectionOut, DocumentSummaryOut

TriageDecisionValue = Literal["confirmed", "false_positive", "needs_sme"]


class TriageRequest(BaseModel):
    decision: TriageDecisionValue
    note: str | None = None


class TriageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    decision: str
    note: str | None
    decided_at: datetime


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    document: DocumentSummaryOut
    section: DocumentSectionOut
    clause: RegulatoryClauseOut
    status: str
    severity: str
    explanation: str
    triage_decision: TriageOut | None = None
