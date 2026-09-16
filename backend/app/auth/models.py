import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class UserRole(StrEnum):
    hr_admin = "hr_admin"
    hr_staff = "hr_staff"
    manager = "manager"
    employee = "employee"
    auditor_read = "auditor_read"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # MFA is mandatory in this MVP (mirrors Payroll's confirmed choice, pending
    # open question #8 on SSO) — every user has a secret from creation; there is
    # no "MFA not yet enrolled" state (no self-service registration in Phase 0).
    mfa_secret_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # BR-17/FR-22/BRULE-09: true for the auto-bootstrapped admin and any account
    # created via scripts.create_user, since someone other than the account's
    # owner chose the initial password. Enforced server-side in app/auth/deps.py,
    # not just a frontend redirect.
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
