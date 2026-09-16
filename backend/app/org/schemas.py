import uuid

from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str


class DepartmentRead(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class PositionCreate(BaseModel):
    title: str
    department_id: uuid.UUID
    reports_to_position_id: uuid.UUID | None = None


class PositionRead(BaseModel):
    id: uuid.UUID
    title: str
    department_id: uuid.UUID
    department_name: str
    reports_to_position_id: uuid.UUID | None
    reports_to_title: str | None

    model_config = {"from_attributes": True}


class HeadcountEntry(BaseModel):
    department_id: uuid.UUID
    department_name: str
    position_id: uuid.UUID
    position_title: str
    headcount: int
