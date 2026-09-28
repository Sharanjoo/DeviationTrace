import uuid

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditChecklistItem(Base):
    """The internal-audit checklist library: per department, a required
    document/report and the citation backing it (ISO 13485 Clause 8.2.4 +
    company SOPs). Versioned like RegulatoryClause so edits don't silently
    change the meaning of past findings that cite an earlier version."""

    __tablename__ = "audit_checklist_items"
    __table_args__ = (UniqueConstraint("department", "item_name", "version", name="uq_checklist_item_identity"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    citation: Mapped[str] = mapped_column(String(128), nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    match_phrases: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    findings: Mapped[list["AuditChecklistFinding"]] = relationship(back_populates="checklist_item")
