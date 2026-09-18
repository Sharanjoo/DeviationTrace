import uuid

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    org_name: str
    industry: str  # "device" | "drug"
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    org_id: uuid.UUID
