import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_sections.id"), nullable=False)
    clause_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regulatory_clauses.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # "missing" | "partial" | "contradicted"
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # critical|major|minor|resolved
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped["Document"] = relationship()
    section: Mapped["DocumentSection"] = relationship(back_populates="findings")
    clause: Mapped["RegulatoryClause"] = relationship(back_populates="findings")
    triage_decision: Mapped["TriageDecision | None"] = relationship(back_populates="finding", uselist=False)
