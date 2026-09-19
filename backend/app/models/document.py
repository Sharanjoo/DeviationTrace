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
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # "sop" | "deviation" | "batch_record"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    process_area: Mapped[str] = mapped_column(String(64), nullable=False)
    file_ref: Mapped[str] = mapped_column(String(512), nullable=False)  # local path today, S3 key later
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_process_area: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="documents")
    sections: Mapped[list["DocumentSection"]] = relationship(back_populates="document", cascade="all, delete-orphan")
