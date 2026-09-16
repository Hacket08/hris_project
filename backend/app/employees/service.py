import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.core.crypto import decrypt_field, encrypt_field
from app.employees.models import Employee, EmploymentChangeType, EmploymentHistory
from app.employees.schemas import (
    EmployeeCreate,
    EmployeeDetail,
    EmployeeUpdate,
    EmploymentHistoryRead,
)


def _encrypt_or_none(value: str | None) -> str | None:
    return encrypt_field(value) if value else None


def _decrypt_or_none(value: str | None) -> str | None:
    return decrypt_field(value) if value else None


async def create_employee(
    db: AsyncSession, data: EmployeeCreate, changed_by: uuid.UUID
) -> Employee:
    employee = Employee(
        first_name=data.first_name,
        last_name=data.last_name,
        contact_info=data.contact_info,
        employment_status=data.employment_status,
        hire_date=data.hire_date,
        position_id=data.position_id,
        sss_number_encrypted=_encrypt_or_none(data.sss_number),
        philhealth_number_encrypted=_encrypt_or_none(data.philhealth_number),
        pagibig_number_encrypted=_encrypt_or_none(data.pagibig_number),
        tin_encrypted=_encrypt_or_none(data.tin),
    )
    db.add(employee)
    await db.flush()

    db.add(
        EmploymentHistory(
            employee_id=employee.id,
            change_type=EmploymentChangeType.hire,
            old_value=None,
            new_value=data.employment_status.value,
            effective_date=data.hire_date,
        )
    )
    await record_audit(
        db,
        entity_name="employee",
        entity_id=str(employee.id),
        changed_by=changed_by,
        reason="Employee hired",
    )
    await db.commit()
    await db.refresh(employee)
    return employee


async def get_employee(db: AsyncSession, employee_id: uuid.UUID) -> Employee | None:
    return await db.get(Employee, employee_id)


async def list_employees(db: AsyncSession) -> list[Employee]:
    result = await db.execute(select(Employee).order_by(Employee.last_name, Employee.first_name))
    return list(result.scalars().all())


async def get_employment_history(
    db: AsyncSession, employee_id: uuid.UUID
) -> list[EmploymentHistory]:
    result = await db.execute(
        select(EmploymentHistory)
        .where(EmploymentHistory.employee_id == employee_id)
        .order_by(EmploymentHistory.effective_date, EmploymentHistory.created_at)
    )
    return list(result.scalars().all())


async def build_employee_detail(db: AsyncSession, employee: Employee) -> EmployeeDetail:
    history = await get_employment_history(db, employee.id)
    return EmployeeDetail(
        id=employee.id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        contact_info=employee.contact_info,
        employment_status=employee.employment_status,
        hire_date=employee.hire_date,
        position_id=employee.position_id,
        sss_number=_decrypt_or_none(employee.sss_number_encrypted),
        philhealth_number=_decrypt_or_none(employee.philhealth_number_encrypted),
        pagibig_number=_decrypt_or_none(employee.pagibig_number_encrypted),
        tin=_decrypt_or_none(employee.tin_encrypted),
        history=[EmploymentHistoryRead.model_validate(h) for h in history],
    )


async def update_employee(
    db: AsyncSession, employee: Employee, data: EmployeeUpdate, changed_by: uuid.UUID
) -> Employee:
    """AC-02: a position change appends an EmploymentHistory row rather than
    silently overwriting — same for a status change. Effective date is
    "today" (the date the change is recorded), since the API doesn't take a
    separate effective-date input in this Phase 1 cut."""
    today = date.today()

    if data.position_id is not None and data.position_id != employee.position_id:
        db.add(
            EmploymentHistory(
                employee_id=employee.id,
                change_type=EmploymentChangeType.transfer,
                old_value=str(employee.position_id),
                new_value=str(data.position_id),
                effective_date=today,
            )
        )
        employee.position_id = data.position_id

    if data.employment_status is not None and data.employment_status != employee.employment_status:
        db.add(
            EmploymentHistory(
                employee_id=employee.id,
                change_type=EmploymentChangeType.status_change,
                old_value=employee.employment_status.value,
                new_value=data.employment_status.value,
                effective_date=today,
            )
        )
        employee.employment_status = data.employment_status

    if data.first_name is not None:
        employee.first_name = data.first_name
    if data.last_name is not None:
        employee.last_name = data.last_name
    if data.contact_info is not None:
        employee.contact_info = data.contact_info
    if data.sss_number is not None:
        employee.sss_number_encrypted = _encrypt_or_none(data.sss_number)
    if data.philhealth_number is not None:
        employee.philhealth_number_encrypted = _encrypt_or_none(data.philhealth_number)
    if data.pagibig_number is not None:
        employee.pagibig_number_encrypted = _encrypt_or_none(data.pagibig_number)
    if data.tin is not None:
        employee.tin_encrypted = _encrypt_or_none(data.tin)

    await record_audit(
        db,
        entity_name="employee",
        entity_id=str(employee.id),
        changed_by=changed_by,
        reason="Employee record updated",
    )
    await db.commit()
    await db.refresh(employee)
    return employee
