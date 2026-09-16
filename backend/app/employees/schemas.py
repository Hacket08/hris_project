import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.employees.models import EmploymentChangeType, EmploymentStatus


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: str | None = None
    suffix: str | None = None
    nickname: str | None = None
    maiden_name: str | None = None
    gender: str | None = None
    birthdate: date | None = None
    birth_place: str | None = None
    civil_status: str | None = None
    spouse_name: str | None = None
    is_solo_parent: bool = False
    is_minimum_wage_earner: bool = False
    religion: str | None = None
    nationality: str | None = None
    corporate_email: str | None = None
    personal_email: str | None = None
    permanent_address: str | None = None
    current_address: str | None = None
    contact_info: str | None = None
    employment_status: EmploymentStatus
    hire_date: date
    regularization_date: date | None = None
    position_title: str | None = None
    default_schedule_id: uuid.UUID | None = None
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
    middle_name: str | None = None
    suffix: str | None = None
    nickname: str | None = None
    maiden_name: str | None = None
    gender: str | None = None
    birthdate: date | None = None
    birth_place: str | None = None
    civil_status: str | None = None
    spouse_name: str | None = None
    is_solo_parent: bool | None = None
    is_minimum_wage_earner: bool | None = None
    religion: str | None = None
    nationality: str | None = None
    corporate_email: str | None = None
    personal_email: str | None = None
    permanent_address: str | None = None
    current_address: str | None = None
    contact_info: str | None = None
    employment_status: EmploymentStatus | None = None
    regularization_date: date | None = None
    position_title: str | None = None
    default_schedule_id: uuid.UUID | None = None
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
    middle_name: str | None
    suffix: str | None
    nickname: str | None
    maiden_name: str | None
    gender: str | None
    birthdate: date | None
    birth_place: str | None
    civil_status: str | None
    spouse_name: str | None
    is_solo_parent: bool
    is_minimum_wage_earner: bool
    religion: str | None
    nationality: str | None
    corporate_email: str | None
    personal_email: str | None
    permanent_address: str | None
    current_address: str | None
    contact_info: str | None
    employment_status: EmploymentStatus
    hire_date: date
    regularization_date: date | None
    position_title: str | None
    default_schedule_id: uuid.UUID | None
    position_id: uuid.UUID
    sss_number: str | None
    philhealth_number: str | None
    pagibig_number: str | None
    tin: str | None
    history: list[EmploymentHistoryRead]
