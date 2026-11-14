import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Vendor(Base):
    """A supplier the org audits (e.g. "Acme Excipient Supplier"), in one
    vendor category, which decides the standards its audit reports are
    cross-checked against."""

    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_vendor_name_per_org"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_category: Mapped[str] = mapped_column(String(32), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Newest audit first by the date it took place (not the order it was
    # entered): an older report attached later must not become "latest".
    audits: Mapped[list["VendorAudit"]] = relationship(
        back_populates="vendor",
        order_by=lambda: (VendorAudit.audit_date.desc().nulls_last(), VendorAudit.audit_number.desc()),
    )


class VendorAudit(Base):
    """One audit of a vendor: the vendor's audit report (a Document of type
    vendor_audit_report) plus who audited and when. Its cross-check results
    are the VendorAuditFinding rows for that document. audit_number counts
    up per org and is shown as VA-0001."""

    __tablename__ = "vendor_audits"
    __table_args__ = (
        UniqueConstraint("org_id", "audit_number", name="uq_vendor_audit_number"),
        UniqueConstraint("document_id", name="uq_vendor_audit_document"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    audit_number: Mapped[int] = mapped_column(Integer, nullable=False)
    audit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    auditor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auditor_employee_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    vendor: Mapped[Vendor] = relationship(back_populates="audits")
    document: Mapped["Document"] = relationship()

    @property
    def audit_code(self) -> str:
        return f"VA-{self.audit_number:04d}"
