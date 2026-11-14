import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # "sop" | "deviation" | "batch_record" | "report"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    process_area: Mapped[str] = mapped_column(String(64), nullable=False)
    department: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    vendor_category: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    file_ref: Mapped[str] = mapped_column(String(512), nullable=False)  # local path today, S3 key later
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_process_area: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # When the documentation-completeness check last ran (NULL: not yet;
    # documents from before the check existed are checked on first use).
    documentation_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="documents")
    sections: Mapped[list["DocumentSection"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    documentation_issues: Mapped[list["DocumentationIssue"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentationIssue.position"
    )

    @property
    def documentation_scanned(self) -> bool:
        """A scan: no text layer, so it needs a manual check instead."""
        return any(i.kind == "scanned" for i in self.documentation_issues)

    @property
    def documentation_issue_count(self) -> int | None:
        """Blanks found (a scan's "check by hand" note isn't counted)."""
        if self.documentation_checked_at is None:
            return None
        return sum(1 for i in self.documentation_issues if i.kind != "scanned")
