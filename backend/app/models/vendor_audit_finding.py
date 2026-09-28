import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VendorAuditFinding(Base):
    """One row per (document, standard), re-evaluated and upserted in place
    on every /vendor-audit/{document_id}/run — like base Finding this is
    scoped to a single uploaded document (not org-wide like
    AuditChecklistFinding), but like AuditChecklistFinding it stores full
    coverage (missing/partial/satisfied), not just gaps, since the SME
    needs to see what the vendor's report did claim, not only where it
    fell short."""

    __tablename__ = "vendor_audit_findings"
    __table_args__ = (UniqueConstraint("document_id", "standard_id", name="uq_vendor_audit_finding_identity"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_sections.id"), nullable=False)
    standard_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vendor_standards.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # "missing" | "partial" | "satisfied"
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # critical|major|resolved
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped["Document"] = relationship()
    section: Mapped["DocumentSection"] = relationship()
    standard: Mapped["VendorStandard"] = relationship(back_populates="findings")
