import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    heading: str
    text: str
    order: int
    span_start: int
    span_end: int


class DocumentSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    type: str


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    type: str
    title: str
    process_area: str
    department: str | None = None
    vendor_category: str | None = None
    status: str
    detected_process_area: str | None = None
    processing_error: str | None = None
    uploaded_at: datetime
    # Blank signatures/dates/entries found; None until the document is checked.
    documentation_issue_count: int | None = None


class DocumentDetailOut(DocumentOut):
    sections: list[DocumentSectionOut] = []


class DocumentStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    detected_process_area: str | None = None
    processing_error: str | None = None
