from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.auth.models import User, UserRole
from app.core.db import get_db
from app.org.schemas import (
    DepartmentCreate,
    DepartmentRead,
    HeadcountEntry,
    PositionCreate,
    PositionRead,
)
from app.org.service import (
    create_department,
    create_position,
    get_headcount,
    list_departments,
    list_positions,
)

router = APIRouter(prefix="/org", tags=["org"])


@router.get("/departments", response_model=list[DepartmentRead])
async def get_departments(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.hr_admin)),
) -> list[DepartmentRead]:
    return [DepartmentRead.model_validate(d) for d in await list_departments(db)]


@router.post("/departments", response_model=DepartmentRead)
async def post_department(
    payload: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.hr_admin)),
) -> DepartmentRead:
    department = await create_department(db, payload.name, current_user.id)
    return DepartmentRead.model_validate(department)


@router.get("/positions", response_model=list[PositionRead])
async def get_positions(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.hr_admin)),
) -> list[PositionRead]:
    return await list_positions(db)


@router.post("/positions", response_model=PositionRead)
async def post_position(
    payload: PositionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.hr_admin)),
) -> PositionRead:
    return await create_position(
        db, payload.title, payload.department_id, payload.reports_to_position_id, current_user.id
    )


@router.get("/headcount", response_model=list[HeadcountEntry])
async def get_headcount_view(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.hr_admin)),
) -> list[HeadcountEntry]:
    return await get_headcount(db)
