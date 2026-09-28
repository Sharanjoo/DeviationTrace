import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.document import DocumentSectionOut, DocumentSummaryOut


class VendorStandardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendor_category: str
    requirement_name: str
    citation: str
    requirement_text: str


class VendorAuditFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document: DocumentSummaryOut
    section: DocumentSectionOut
    standard: VendorStandardOut
    status: str
    severity: str
    explanation: str
    evaluated_at: datetime


class VendorAuditRunResult(BaseModel):
    missing: int
    partial: int
    satisfied: int
