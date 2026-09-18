import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.clause import RegulatoryClauseOut
from app.schemas.document import DocumentSectionOut


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    section: DocumentSectionOut
    clause: RegulatoryClauseOut
    status: str
    severity: str
    explanation: str


class TriageRequest(BaseModel):
    decision: str  # "confirmed" | "false_positive" | "needs_sme"
    note: str | None = None


class TriageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    decision: str
    note: str | None
