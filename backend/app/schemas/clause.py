import uuid

from pydantic import BaseModel, ConfigDict


class RegulatoryClauseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    regulation: str
    clause_number: str
    requirement_text: str
    process_area: str
    document_type_applicability: list[str]
    version: int
