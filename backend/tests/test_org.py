import pyotp
import pytest
from sqlalchemy import delete

from app.auth.models import User, UserRole
from app.core.crypto import encrypt_field
from app.core.db import AsyncSessionLocal
from app.core.security import generate_mfa_secret, hash_password
from app.employees.models import Employee, EmploymentHistory
from app.org.models import Department, Position
from tests.conftest import requires_db

pytestmark = requires_db


@pytest.fixture(autouse=True)
async def _clean_tables():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(EmploymentHistory))
        await db.execute(delete(Employee))
        await db.execute(delete(Position))
        await db.execute(delete(Department))
        await db.commit()
    yield
    async with AsyncSessionLocal() as db:
        await db.execute(delete(EmploymentHistory))
        await db.execute(delete(Employee))
        await db.execute(delete(Position))
        await db.execute(delete(Department))
        await db.commit()


@pytest.fixture
async def hr_admin_token(client):
    secret = generate_mfa_secret()
    password = "correct horse battery staple"
    async with AsyncSessionLocal() as db:
        user = User(
            username="test.hradmin.org",
            email="test.hradmin.org@example.com",
            password_hash=hash_password(password),
            mfa_secret_encrypted=encrypt_field(secret),
            role=UserRole.hr_admin,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    login = await client.post("/auth/login", json={"username": user.username, "password": password})
    mfa_pending_token = login.json()["mfa_pending_token"]
    verify = await client.post(
        "/auth/mfa/verify",
        json={"mfa_pending_token": mfa_pending_token, "code": pyotp.TOTP(secret).now()},
    )
    token = verify.json()["access_token"]

    yield token

    async with AsyncSessionLocal() as db:
        await db.delete(await db.get(User, user.id))
        await db.commit()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_create_and_list_department(client, hr_admin_token):
    resp = await client.post(
        "/org/departments", json={"name": "Engineering"}, headers=_auth(hr_admin_token)
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Engineering"

    list_resp = await client.get("/org/departments", headers=_auth(hr_admin_token))
    assert list_resp.status_code == 200
    assert [d["name"] for d in list_resp.json()] == ["Engineering"]


async def test_position_hierarchy_resolves_names(client, hr_admin_token):
    dept = await client.post(
        "/org/departments", json={"name": "Engineering"}, headers=_auth(hr_admin_token)
    )
    dept_id = dept.json()["id"]

    manager_pos = await client.post(
        "/org/positions",
        json={
            "title": "Engineering Manager",
            "department_id": dept_id,
            "reports_to_position_id": None,
        },
        headers=_auth(hr_admin_token),
    )
    assert manager_pos.status_code == 200, manager_pos.text
    manager_id = manager_pos.json()["id"]

    report_pos = await client.post(
        "/org/positions",
        json={
            "title": "Software Engineer",
            "department_id": dept_id,
            "reports_to_position_id": manager_id,
        },
        headers=_auth(hr_admin_token),
    )
    assert report_pos.status_code == 200, report_pos.text
    body = report_pos.json()
    assert body["department_name"] == "Engineering"
    assert body["reports_to_title"] == "Engineering Manager"

    positions = (await client.get("/org/positions", headers=_auth(hr_admin_token))).json()
    manager_entry = next(p for p in positions if p["id"] == manager_id)
    assert manager_entry["reports_to_position_id"] is None
    assert manager_entry["reports_to_title"] is None


async def test_headcount_correct_per_department_and_position(client, hr_admin_token):
    dept_a = (
        await client.post(
            "/org/departments", json={"name": "Engineering"}, headers=_auth(hr_admin_token)
        )
    ).json()
    dept_b = (
        await client.post("/org/departments", json={"name": "Sales"}, headers=_auth(hr_admin_token))
    ).json()
    pos_a = (
        await client.post(
            "/org/positions",
            json={
                "title": "Engineer",
                "department_id": dept_a["id"],
                "reports_to_position_id": None,
            },
            headers=_auth(hr_admin_token),
        )
    ).json()
    pos_b = (
        await client.post(
            "/org/positions",
            json={
                "title": "Sales Rep",
                "department_id": dept_b["id"],
                "reports_to_position_id": None,
            },
            headers=_auth(hr_admin_token),
        )
    ).json()

    for i in range(2):
        await client.post(
            "/employees",
            json={
                "first_name": f"Eng{i}",
                "last_name": "Person",
                "employment_status": "regular",
                "hire_date": "2024-01-01",
                "position_id": pos_a["id"],
            },
            headers=_auth(hr_admin_token),
        )
    await client.post(
        "/employees",
        json={
            "first_name": "Sales0",
            "last_name": "Person",
            "employment_status": "regular",
            "hire_date": "2024-01-01",
            "position_id": pos_b["id"],
        },
        headers=_auth(hr_admin_token),
    )

    headcount = (await client.get("/org/headcount", headers=_auth(hr_admin_token))).json()
    by_position = {h["position_id"]: h["headcount"] for h in headcount}
    assert by_position[pos_a["id"]] == 2
    assert by_position[pos_b["id"]] == 1


async def test_org_endpoints_require_hr_admin_role(client):
    secret = generate_mfa_secret()
    password = "correct horse battery staple"
    async with AsyncSessionLocal() as db:
        user = User(
            username="test.employee.org",
            email="test.employee.org@example.com",
            password_hash=hash_password(password),
            mfa_secret_encrypted=encrypt_field(secret),
            role=UserRole.employee,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    login = await client.post("/auth/login", json={"username": user.username, "password": password})
    mfa_pending_token = login.json()["mfa_pending_token"]
    verify = await client.post(
        "/auth/mfa/verify",
        json={"mfa_pending_token": mfa_pending_token, "code": pyotp.TOTP(secret).now()},
    )
    token = verify.json()["access_token"]

    resp = await client.get("/org/departments", headers=_auth(token))
    assert resp.status_code == 403

    async with AsyncSessionLocal() as db:
        await db.delete(await db.get(User, user.id))
        await db.commit()
