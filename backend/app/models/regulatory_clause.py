import uuid

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RegulatoryClause(Base):
    """The curated reference library. Versioned so clause updates don't
    silently change the meaning of past findings that cite an earlier version."""

    __tablename__ = "regulatory_clauses"
    __table_args__ = (UniqueConstraint("regulation", "clause_number", "version", name="uq_clause_identity"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regulation: Mapped[str] = mapped_column(String(32), nullable=False)  # "qmsr" | "iso13485" | "cfr211"
    clause_number: Mapped[str] = mapped_column(String(64), nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    process_area: Mapped[str] = mapped_column(String(64), nullable=False)
    document_type_applicability: Mapped[list[str]] = mapped_column(ARRAY(String(32)), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    findings: Mapped[list["Finding"]] = relationship(back_populates="clause")
