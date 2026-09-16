import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, func
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
    # Personal-info fields (05_data_model.md, expanded 2026-09-16, grounded in
    # standard Philippine 201-file/HR recordkeeping conventions — see that
    # doc's provenance note). All nullable: Phase 1 doesn't mandate collecting
    # every field at hire time.
    middle_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    suffix: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    maiden_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    civil_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    spouse_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # RA 8972 (BRULE-05) and a real PH statutory tax-exemption status (TRAIN
    # law) respectively — not general recordkeeping trivia.
    is_solo_parent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_minimum_wage_earner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    religion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    corporate_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    personal_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permanent_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    current_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        Enum(EmploymentStatus, name="employment_status"), nullable=False
    )
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    regularization_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Job title (e.g. "HR Associate") — distinct from Position, which is where
    # they sit in the org/department hierarchy, not what they're called.
    position_title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Placeholder for Phase 2 Time & Attendance — no `schedule` table exists
    # yet, so this is a plain nullable column, not a real FK constraint. Add
    # the constraint once that table exists rather than migrating twice.
    default_schedule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
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
