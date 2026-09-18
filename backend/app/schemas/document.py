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


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    type: str
    title: str
    process_area: str
    status: str
    uploaded_at: datetime


class DocumentDetailOut(DocumentOut):
    sections: list[DocumentSectionOut] = []


class DocumentStatusOut(BaseModel):
    id: uuid.UUID
    status: str
