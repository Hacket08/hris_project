import pyotp
import pytest

from app.auth.models import User, UserRole
from app.core.crypto import encrypt_field
from app.core.db import AsyncSessionLocal
from app.core.security import generate_mfa_secret, hash_password
from tests.conftest import requires_db

pytestmark = requires_db


@pytest.fixture
async def seeded_user():
    secret = generate_mfa_secret()
    password = "correct horse battery staple"
    async with AsyncSessionLocal() as db:
        user = User(
            username="test.hrstaff",
            email="test.hrstaff@example.com",
            password_hash=hash_password(password),
            mfa_secret_encrypted=encrypt_field(secret),
            role=UserRole.hr_staff,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    yield user, password, secret
    async with AsyncSessionLocal() as db:
        await db.delete(await db.get(User, user.id))
        await db.commit()


async def test_login_then_mfa_verify_issues_access_token(client, seeded_user):
    user, password, secret = seeded_user

    login_resp = await client.post(
        "/auth/login", json={"username": user.username, "password": password}
    )
    assert login_resp.status_code == 200
    mfa_pending_token = login_resp.json()["mfa_pending_token"]

    code = pyotp.TOTP(secret).now()
    verify_resp = await client.post(
        "/auth/mfa/verify", json={"mfa_pending_token": mfa_pending_token, "code": code}
    )
    assert verify_resp.status_code == 200
    access_token = verify_resp.json()["access_token"]

    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == user.username


async def test_wrong_password_rejected(client, seeded_user):
    user, _password, _secret = seeded_user
    resp = await client.post(
        "/auth/login", json={"username": user.username, "password": "not the password"}
    )
    assert resp.status_code == 401


async def test_wrong_mfa_code_rejected(client, seeded_user):
    user, password, _secret = seeded_user
    login_resp = await client.post(
        "/auth/login", json={"username": user.username, "password": password}
    )
    mfa_pending_token = login_resp.json()["mfa_pending_token"]

    resp = await client.post(
        "/auth/mfa/verify", json={"mfa_pending_token": mfa_pending_token, "code": "000000"}
    )
    assert resp.status_code == 401


async def test_access_requires_mfa_step_not_just_password(client, seeded_user):
    """An mfa_pending token must not work as a bearer access token anywhere."""
    user, password, _secret = seeded_user
    login_resp = await client.post(
        "/auth/login", json={"username": user.username, "password": password}
    )
    mfa_pending_token = login_resp.json()["mfa_pending_token"]

    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {mfa_pending_token}"})
    assert resp.status_code == 401
