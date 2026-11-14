import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentationIssue(Base):
    """A blank signature, stamp, date or required entry, or an unfilled
    template placeholder, found in a document by the documentation
    completeness check (app/core/documentation/completeness.py). Replaced
    whenever the document is re-checked."""

    __tablename__ = "documentation_issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    field: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="high")

    document: Mapped["Document"] = relationship(back_populates="documentation_issues")
