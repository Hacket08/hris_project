import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.employees.models import EmploymentChangeType, EmploymentStatus


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    contact_info: str | None = None
    employment_status: EmploymentStatus
    hire_date: date
    position_id: uuid.UUID
    sss_number: str | None = None
    philhealth_number: str | None = None
    pagibig_number: str | None = None
    tin: str | None = None


class EmployeeUpdate(BaseModel):
    """All fields optional — PATCH semantics. Changing position_id or
    employment_status creates an EmploymentHistory entry (AC-02)."""

    first_name: str | None = None
    last_name: str | None = None
    contact_info: str | None = None
    employment_status: EmploymentStatus | None = None
    position_id: uuid.UUID | None = None
    sss_number: str | None = None
    philhealth_number: str | None = None
    pagibig_number: str | None = None
    tin: str | None = None


class EmployeeListItem(BaseModel):
    """List view deliberately omits government-ID fields — restricted PII
    (dev plan §5.1) doesn't belong in a bulk listing response."""

    id: uuid.UUID
    first_name: str
    last_name: str
    employment_status: EmploymentStatus
    hire_date: date
    position_id: uuid.UUID

    model_config = {"from_attributes": True}


class EmploymentHistoryRead(BaseModel):
    id: uuid.UUID
    change_type: EmploymentChangeType
    old_value: str | None
    new_value: str | None
    effective_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class EmployeeDetail(BaseModel):
    """Detail view — the only place government-ID fields are ever decrypted
    and returned, and only to hr_admin (route-level RBAC)."""

    id: uuid.UUID
    first_name: str
    last_name: str
    contact_info: str | None
    employment_status: EmploymentStatus
    hire_date: date
    position_id: uuid.UUID
    sss_number: str | None
    philhealth_number: str | None
    pagibig_number: str | None
    tin: str | None
    history: list[EmploymentHistoryRead]
