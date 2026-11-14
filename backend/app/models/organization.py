import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(String(32), nullable=False)  # "device" | "drug"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Set once, the first time the org finishes new-company onboarding
    # (adopting a scope template, or choosing the standard checklist).
    # NULL means onboarding hasn't been done, so the app routes there first.
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The scope template the org adopted; NULL if it kept the standard
    # checklist only (or hasn't onboarded yet).
    scope_category: Mapped[str | None] = mapped_column(String(64), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    documents: Mapped[list["Document"]] = relationship(back_populates="organization")
