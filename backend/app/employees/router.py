import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.auth.models import User, UserRole
from app.core.db import get_db
from app.employees.schemas import EmployeeCreate, EmployeeDetail, EmployeeListItem, EmployeeUpdate
from app.employees.service import (
    build_employee_detail,
    create_employee,
    get_employee,
    list_employees,
    update_employee,
)

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeListItem])
async def get_employees(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.hr_admin)),
) -> list[EmployeeListItem]:
    return [EmployeeListItem.model_validate(e) for e in await list_employees(db)]


@router.post("", response_model=EmployeeDetail)
async def post_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.hr_admin)),
) -> EmployeeDetail:
    employee = await create_employee(db, payload, current_user.id)
    return await build_employee_detail(db, employee)


@router.get("/{employee_id}", response_model=EmployeeDetail)
async def get_employee_detail(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.hr_admin)),
) -> EmployeeDetail:
    employee = await get_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return await build_employee_detail(db, employee)


@router.patch("/{employee_id}", response_model=EmployeeDetail)
async def patch_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.hr_admin)),
) -> EmployeeDetail:
    employee = await get_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    employee = await update_employee(db, employee, payload, current_user.id)
    return await build_employee_detail(db, employee)
