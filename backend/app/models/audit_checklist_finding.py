import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditChecklistFinding(Base):
    """One row per (org, checklist item), re-evaluated and upserted in place
    on every /audit-simulation/run — unlike Finding, this stores full
    coverage (missing/incomplete/satisfied), not just gaps, since the
    internal-audit checklist's value is showing what WAS found too."""

    __tablename__ = "audit_checklist_findings"
    __table_args__ = (UniqueConstraint("org_id", "checklist_item_id", name="uq_audit_finding_identity"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    checklist_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("audit_checklist_items.id"), nullable=False)
    matched_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # "missing" | "incomplete" | "satisfied"
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # critical|major|resolved
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    checklist_item: Mapped["AuditChecklistItem"] = relationship(back_populates="findings")
    matched_document: Mapped["Document | None"] = relationship()
