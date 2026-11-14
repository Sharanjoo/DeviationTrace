import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import ROLES


def _role(value: str) -> str:
    if value not in ROLES:
        raise ValueError(f"must be one of {list(ROLES)}")
    return value


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str | None
    email: str
    role: str
    created_at: datetime


class OrgProfileOut(BaseModel):
    id: uuid.UUID
    name: str
    industry: str
    created_at: datetime
    onboarded_at: datetime | None
    scope_label: str | None
    member_count: int
    you: MemberOut


class OrgProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("is required")
        return value


class MemberCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    role: str = "member"

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("is required")
        return value

    @field_validator("role")
    @classmethod
    def _valid_role(cls, value: str) -> str:
        return _role(value)


class MemberCreated(BaseModel):
    member: MemberOut
    # Shown once to the admin who added the member, to pass on; it isn't
    # stored anywhere in readable form.
    temporary_password: str


class MemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    role: str | None = None

    @field_validator("role")
    @classmethod
    def _valid_role(cls, value: str | None) -> str | None:
        return None if value is None else _role(value)
