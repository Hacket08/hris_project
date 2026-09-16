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
            username="test.hradmin.emp",
            email="test.hradmin.emp@example.com",
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


@pytest.fixture
async def two_positions(client, hr_admin_token):
    dept = (
        await client.post(
            "/org/departments", json={"name": "Engineering"}, headers=_auth(hr_admin_token)
        )
    ).json()
    pos_a = (
        await client.post(
            "/org/positions",
            json={
                "title": "Engineer I",
                "department_id": dept["id"],
                "reports_to_position_id": None,
            },
            headers=_auth(hr_admin_token),
        )
    ).json()
    pos_b = (
        await client.post(
            "/org/positions",
            json={
                "title": "Engineer II",
                "department_id": dept["id"],
                "reports_to_position_id": None,
            },
            headers=_auth(hr_admin_token),
        )
    ).json()
    return pos_a, pos_b


async def test_ac01_create_employee_appears_with_matching_fields(
    client, hr_admin_token, two_positions
):
    pos_a, _ = two_positions
    resp = await client.post(
        "/employees",
        json={
            "first_name": "Jane",
            "last_name": "Dela Cruz",
            "contact_info": "jane@example.com",
            "employment_status": "probationary",
            "hire_date": "2026-09-16",
            "position_id": pos_a["id"],
            "sss_number": "34-1234567-8",
        },
        headers=_auth(hr_admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["first_name"] == "Jane"
    assert body["last_name"] == "Dela Cruz"
    assert body["employment_status"] == "probationary"
    assert body["hire_date"] == "2026-09-16"
    assert body["position_id"] == pos_a["id"]
    # Round-trips through real encryption, not stored/returned as plaintext-passthrough.
    assert body["sss_number"] == "34-1234567-8"

    list_resp = await client.get("/employees", headers=_auth(hr_admin_token))
    assert list_resp.status_code == 200
    listed = list_resp.json()[0]
    assert listed["first_name"] == "Jane"
    # List view must not leak government-ID fields.
    assert "sss_number" not in listed


async def test_government_id_actually_encrypted_at_rest(client, hr_admin_token, two_positions):
    pos_a, _ = two_positions
    resp = await client.post(
        "/employees",
        json={
            "first_name": "Jane",
            "last_name": "Dela Cruz",
            "employment_status": "regular",
            "hire_date": "2026-09-16",
            "position_id": pos_a["id"],
            "tin": "123-456-789-000",
        },
        headers=_auth(hr_admin_token),
    )
    employee_id = resp.json()["id"]

    import uuid as uuid_mod

    async with AsyncSessionLocal() as db:
        row = await db.get(Employee, uuid_mod.UUID(employee_id))
        assert row.tin_encrypted is not None
        assert row.tin_encrypted != "123-456-789-000"  # not plaintext in the DB


async def test_ac02_position_change_creates_history_row_without_overwriting(
    client, hr_admin_token, two_positions
):
    pos_a, pos_b = two_positions
    created = await client.post(
        "/employees",
        json={
            "first_name": "Jane",
            "last_name": "Dela Cruz",
            "employment_status": "regular",
            "hire_date": "2026-09-16",
            "position_id": pos_a["id"],
        },
        headers=_auth(hr_admin_token),
    )
    employee_id = created.json()["id"]
    assert len(created.json()["history"]) == 1  # the hire event
    assert created.json()["history"][0]["change_type"] == "hire"

    patched = await client.patch(
        f"/employees/{employee_id}",
        json={"position_id": pos_b["id"]},
        headers=_auth(hr_admin_token),
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["position_id"] == pos_b["id"]
    assert len(body["history"]) == 2  # hire + transfer, nothing overwritten
    transfer_entries = [h for h in body["history"] if h["change_type"] == "transfer"]
    assert len(transfer_entries) == 1
    assert transfer_entries[0]["old_value"] == pos_a["id"]
    assert transfer_entries[0]["new_value"] == pos_b["id"]

    # Fetching the detail again independently confirms it's persisted, not just echoed back.
    refetched = await client.get(f"/employees/{employee_id}", headers=_auth(hr_admin_token))
    assert len(refetched.json()["history"]) == 2


async def test_status_change_also_creates_history_row(client, hr_admin_token, two_positions):
    pos_a, _ = two_positions
    created = await client.post(
        "/employees",
        json={
            "first_name": "Jane",
            "last_name": "Dela Cruz",
            "employment_status": "probationary",
            "hire_date": "2026-09-16",
            "position_id": pos_a["id"],
        },
        headers=_auth(hr_admin_token),
    )
    employee_id = created.json()["id"]

    patched = await client.patch(
        f"/employees/{employee_id}",
        json={"employment_status": "regular"},
        headers=_auth(hr_admin_token),
    )
    assert patched.status_code == 200
    status_changes = [h for h in patched.json()["history"] if h["change_type"] == "status_change"]
    assert len(status_changes) == 1
    assert status_changes[0]["old_value"] == "probationary"
    assert status_changes[0]["new_value"] == "regular"


async def test_get_nonexistent_employee_404s(client, hr_admin_token):
    import uuid

    resp = await client.get(f"/employees/{uuid.uuid4()}", headers=_auth(hr_admin_token))
    assert resp.status_code == 404


async def test_employees_endpoints_require_hr_admin_role(client):
    secret = generate_mfa_secret()
    password = "correct horse battery staple"
    async with AsyncSessionLocal() as db:
        user = User(
            username="test.employee.emp",
            email="test.employee.emp@example.com",
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

    resp = await client.get("/employees", headers=_auth(token))
    assert resp.status_code == 403

    async with AsyncSessionLocal() as db:
        await db.delete(await db.get(User, user.id))
        await db.commit()
