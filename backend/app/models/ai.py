import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OrgAiSettings(Base):
    """Per-organization AI configuration, set by an admin. AI is off until
    an admin enables it. Each organization chooses where its data goes:
    Claude on Anthropic's API, or through its own Amazon Bedrock, Google
    Vertex AI or Microsoft Foundry account."""

    __tablename__ = "org_ai_settings"

    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="anthropic")
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="claude-opus-5-5")
    # Provider-specific location settings.
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)  # bedrock, vertex
    project_id: Mapped[str | None] = mapped_column(String(128), nullable=True)  # vertex
    resource: Mapped[str | None] = mapped_column(String(128), nullable=True)  # foundry
    # Encrypted at rest (app/core/ai/crypto.py); never returned by the API.
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)  # anthropic, foundry
    # Default for "remove names, emails and employee IDs before sending".
    redact_identifiers: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AiInteraction(Base):
    """One call to an AI model, logged in full: who asked, what exactly was
    sent (after redaction), what came back, which model answered, and what
    it cost in tokens. Kept as the audit trail for AI-assisted findings."""

    __tablename__ = "ai_interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)  # content_review
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("audit_simulation_runs.id"), nullable=True, index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    document_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model_requested: Mapped[str] = mapped_column(String(128), nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Which document sections were sent, and whether identifiers were removed.
    sections_sent: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    redacted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    redaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Exactly what was sent and received.
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # success | refused | error
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AuditSimulationAiAssessment(Base):
    """The AI's verdict on one requirement for one document in a run, with
    the evidence it quoted. Shown next to the rule-based result; it doesn't
    replace it. evidence_verified: the quote really appears in what was sent."""

    __tablename__ = "audit_simulation_ai_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("audit_simulation_runs.id"), nullable=False, index=True)
    interaction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_interactions.id"), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    document_title: Mapped[str] = mapped_column(String(512), nullable=False)
    citation: Mapped[str] = mapped_column(String(128), nullable=False)
    requirement_title: Mapped[str] = mapped_column(String(255), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)  # addressed | partly_addressed | not_addressed
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
