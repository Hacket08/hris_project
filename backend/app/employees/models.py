import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class EmploymentStatus(StrEnum):
    probationary = "probationary"
    regular = "regular"
    separated = "separated"


class EmploymentChangeType(StrEnum):
    hire = "hire"
    transfer = "transfer"
    promotion = "promotion"
    status_change = "status_change"


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(150), nullable=False)
    last_name: Mapped[str] = mapped_column(String(150), nullable=False)
    contact_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        Enum(EmploymentStatus, name="employment_status"), nullable=False
    )
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("position.id"), nullable=False
    )
    # BR-18 (confirmed 2026-09-16): HRIS is the sole system of record for these —
    # Payroll receives them only via the employee-master export (Phase 5). Same
    # application-level Fernet encryption as MFA secrets (app/core/crypto.py).
    # Nullable: not every employee necessarily has all four captured at hire time
    # (e.g. TIN pending BIR registration) — Phase 1 doesn't mandate collection.
    sss_number_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    philhealth_number_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pagibig_number_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tin_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EmploymentHistory(Base):
    """Append-only (05_data_model.md, AC-02) — never update/delete a row here,
    only insert new ones. No application-level enforcement beyond convention
    yet (unlike audit_log's DB-grant lockdown); revisit if this needs the same
    hard guarantee."""

    __tablename__ = "employment_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id"), nullable=False
    )
    change_type: Mapped[EmploymentChangeType] = mapped_column(
        Enum(EmploymentChangeType, name="employment_change_type"), nullable=False
    )
    old_value: Mapped[str | None] = mapped_column(String, nullable=True)
    new_value: Mapped[str | None] = mapped_column(String, nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
