import uuid

from pydantic import BaseModel, EmailStr

from app.auth.models import UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    """Never a full access token — login only proves the password. MFA is a
    separate, mandatory step."""

    mfa_pending_token: str


class MFAVerifyRequest(BaseModel):
    mfa_pending_token: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}
