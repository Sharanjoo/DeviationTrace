import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _blank_to_none(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class AiSettingsOut(BaseModel):
    enabled: bool
    provider: str
    model: str
    region: str | None
    project_id: str | None
    resource: str | None
    # The key itself is never returned.
    api_key_set: bool
    redact_identifiers: bool
    updated_at: datetime | None
    updated_by: str | None
    # What's still needed before AI can be used (None when ready).
    missing_configuration: str | None
    providers: dict[str, str]


class AiSettingsIn(BaseModel):
    enabled: bool
    provider: str
    model: str = Field(min_length=1, max_length=128)
    region: str | None = None
    project_id: str | None = None
    resource: str | None = None
    # None keeps the stored key; "" removes it; anything else replaces it.
    api_key: str | None = None
    redact_identifiers: bool = True

    @field_validator("region", "project_id", "resource", mode="before")
    @classmethod
    def _optional(cls, value):
        return _blank_to_none(value)

    @field_validator("model")
    @classmethod
    def _model(cls, value: str) -> str:
        return value.strip()


class AiReviewRequest(BaseModel):
    # None means every section.
    section_ids: list[uuid.UUID] | None = None
    # None means the organization's default.
    redact: bool | None = None


class SectionOut(BaseModel):
    id: uuid.UUID
    heading: str
    characters: int
    preview: str


class RequirementOut(BaseModel):
    citation: str
    title: str


class AiPreviewOut(BaseModel):
    document_title: str
    provider: str
    provider_label: str
    model: str
    sections: list[SectionOut]
    selected_section_ids: list[uuid.UUID]
    redact: bool
    redaction_count: int
    requirements: list[RequirementOut]
    # Exactly what will be sent.
    system_prompt: str
    user_prompt: str


class AiAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interaction_id: uuid.UUID
    document_id: uuid.UUID | None
    document_title: str
    citation: str
    requirement_title: str
    verdict: str
    evidence: str | None
    evidence_verified: bool
    reasoning: str
    created_at: datetime


class AiInteractionSummaryOut(BaseModel):
    # "model_requested"/"model_used" are field names, not pydantic internals.
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    created_at: datetime
    user_name: str
    purpose: str
    run_id: uuid.UUID | None
    document_title: str | None
    provider: str
    model_requested: str
    model_used: str | None
    fallback_used: bool
    status: str
    error: str | None
    redacted: bool
    redaction_count: int
    sections_sent: list[dict]
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: int | None


class AiInteractionDetailOut(AiInteractionSummaryOut):
    system_prompt: str
    user_prompt: str
    response_text: str | None
    request_id: str | None


class AiReviewOut(BaseModel):
    interaction: AiInteractionSummaryOut
    assessments: list[AiAssessmentOut]
