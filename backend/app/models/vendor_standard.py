import uuid

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VendorStandard(Base):
    """The vendor-audit standards library: per vendor/material category, a
    requirement a vendor's own audit report content must address, and the
    match_phrases used to check for it. Versioned like RegulatoryClause and
    AuditChecklistItem so edits don't silently change the meaning of past
    findings that cite an earlier version."""

    __tablename__ = "vendor_standards"
    __table_args__ = (
        UniqueConstraint("vendor_category", "requirement_name", "version", name="uq_vendor_standard_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    requirement_name: Mapped[str] = mapped_column(String(255), nullable=False)
    citation: Mapped[str] = mapped_column(String(128), nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    match_phrases: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False, default=list)
    expected_heading: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    findings: Mapped[list["VendorAuditFinding"]] = relationship(back_populates="standard")
