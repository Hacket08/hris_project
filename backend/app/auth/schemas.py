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
    must_change_password: bool


class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class SetupStatusResponse(BaseModel):
    setup_required: bool


class SetupInitRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class SetupInitResponse(BaseModel):
    setup_token: str
    mfa_secret: str
    provisioning_uri: str


class SetupConfirmRequest(BaseModel):
    setup_token: str
    code: str


class MfaResetInitRequest(BaseModel):
    mfa_pending_token: str


class MfaResetInitResponse(BaseModel):
    reset_token: str
    mfa_secret: str
    provisioning_uri: str


class MfaResetConfirmRequest(BaseModel):
    reset_token: str
    code: str
