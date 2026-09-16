import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.employees.models import Employee
from app.org.models import Department, Position
from app.org.schemas import HeadcountEntry, PositionRead


async def create_department(db: AsyncSession, name: str, changed_by: uuid.UUID) -> Department:
    department = Department(name=name)
    db.add(department)
    await db.flush()
    await record_audit(
        db,
        entity_name="department",
        entity_id=str(department.id),
        changed_by=changed_by,
        reason="Department created",
    )
    await db.commit()
    await db.refresh(department)
    return department


async def list_departments(db: AsyncSession) -> list[Department]:
    result = await db.execute(select(Department).order_by(Department.name))
    return list(result.scalars().all())


async def create_position(
    db: AsyncSession,
    title: str,
    department_id: uuid.UUID,
    reports_to_position_id: uuid.UUID | None,
    changed_by: uuid.UUID,
) -> PositionRead:
    position = Position(
        title=title, department_id=department_id, reports_to_position_id=reports_to_position_id
    )
    db.add(position)
    await db.flush()
    await record_audit(
        db,
        entity_name="position",
        entity_id=str(position.id),
        changed_by=changed_by,
        reason="Position created",
    )
    await db.commit()
    await db.refresh(position)

    department = await db.get(Department, department_id)
    reports_to_title = None
    if reports_to_position_id is not None:
        reports_to = await db.get(Position, reports_to_position_id)
        reports_to_title = reports_to.title if reports_to else None

    return PositionRead(
        id=position.id,
        title=position.title,
        department_id=position.department_id,
        department_name=department.name if department else "",
        reports_to_position_id=position.reports_to_position_id,
        reports_to_title=reports_to_title,
    )


async def list_positions(db: AsyncSession) -> list[PositionRead]:
    """Flat list with department/manager names resolved server-side so the
    frontend can build the org-chart hierarchy (AC-03) without N further
    lookups. Headcount (<200, confirmed) makes the in-Python join below
    simpler and fast enough — revisit with real SQL joins if that changes."""
    positions = list((await db.execute(select(Position))).scalars().all())
    departments = {d.id: d.name for d in await list_departments(db)}
    titles_by_id = {p.id: p.title for p in positions}

    return [
        PositionRead(
            id=p.id,
            title=p.title,
            department_id=p.department_id,
            department_name=departments.get(p.department_id, ""),
            reports_to_position_id=p.reports_to_position_id,
            reports_to_title=(
                titles_by_id.get(p.reports_to_position_id) if p.reports_to_position_id else None
            ),
        )
        for p in positions
    ]


async def get_headcount(db: AsyncSession) -> list[HeadcountEntry]:
    """AC-04: headcount correct per department/position."""
    stmt = (
        select(
            Department.id,
            Department.name,
            Position.id,
            Position.title,
            func.count(Employee.id),
        )
        .select_from(Employee)
        .join(Position, Employee.position_id == Position.id)
        .join(Department, Position.department_id == Department.id)
        .group_by(Department.id, Department.name, Position.id, Position.title)
        .order_by(Department.name, Position.title)
    )
    rows = (await db.execute(stmt)).all()
    return [
        HeadcountEntry(
            department_id=dept_id,
            department_name=dept_name,
            position_id=pos_id,
            position_title=pos_title,
            headcount=count,
        )
        for dept_id, dept_name, pos_id, pos_title, count in rows
    ]
