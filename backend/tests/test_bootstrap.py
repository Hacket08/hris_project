import bcrypt
import pyotp
import pytest
from sqlalchemy import delete, func, select

from app.auth.bootstrap import DEFAULT_ADMIN_USERNAME, bootstrap_default_admin_if_empty
from app.auth.models import User, UserRole
from app.core.crypto import decrypt_field
from app.core.db import AsyncSessionLocal
from tests.conftest import requires_db

pytestmark = requires_db


@pytest.fixture(autouse=True)
async def _empty_users_table():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User))
        await db.commit()
    yield
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User))
        await db.commit()


async def test_creates_one_admin_when_table_empty():
    async with AsyncSessionLocal() as db:
        await bootstrap_default_admin_if_empty(db)

    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.username == DEFAULT_ADMIN_USERNAME))
        ).scalar_one()
        count = await db.scalar(select(func.count()).select_from(User))

    assert count == 1
    assert user.role == UserRole.hr_admin
    assert user.is_active is True
    # Password is never stored/derivable in plaintext, and the MFA secret round-trips
    # through the same encryption used everywhere else in the app.
    assert user.password_hash.startswith("$2b$")
    decrypt_field(user.mfa_secret_encrypted)  # raises if it isn't validly encrypted


async def test_does_not_duplicate_when_a_user_already_exists():
    async with AsyncSessionLocal() as db:
        await bootstrap_default_admin_if_empty(db)
    async with AsyncSessionLocal() as db:
        await bootstrap_default_admin_if_empty(db)  # second call, table no longer empty

    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(User))
    assert count == 1


async def test_generates_a_different_password_each_time_table_was_emptied():
    async with AsyncSessionLocal() as db:
        await bootstrap_default_admin_if_empty(db)
        first_hash = (
            (await db.execute(select(User).where(User.username == DEFAULT_ADMIN_USERNAME)))
            .scalar_one()
            .password_hash
        )

    async with AsyncSessionLocal() as db:
        await db.execute(delete(User))
        await db.commit()

    async with AsyncSessionLocal() as db:
        await bootstrap_default_admin_if_empty(db)
        second_hash = (
            (await db.execute(select(User).where(User.username == DEFAULT_ADMIN_USERNAME)))
            .scalar_one()
            .password_hash
        )

    assert first_hash != second_hash
    assert not bcrypt.checkpw(b"admin", first_hash.encode())  # never a guessable default


async def _login_and_verify_mfa(client, username: str, password: str, mfa_secret: str) -> dict:
    login_resp = await client.post("/auth/login", json={"username": username, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    mfa_pending_token = login_resp.json()["mfa_pending_token"]

    code = pyotp.TOTP(mfa_secret).now()
    verify_resp = await client.post(
        "/auth/mfa/verify", json={"mfa_pending_token": mfa_pending_token, "code": code}
    )
    assert verify_resp.status_code == 200, verify_resp.text
    return verify_resp.json()


async def test_bootstrapped_admin_must_change_password_before_using_anything_else(client):
    """Regression coverage for two real bugs caught during manual verification:
    (1) the placeholder email failed EmailStr validation only when /auth/me
    serialized its response — DB-only checks elsewhere in this file wouldn't
    have caught it; (2) the must-change-password gate has to be enforced
    server-side on every route but /auth/change-password, not just signaled
    to the frontend."""
    from app.core.security import hash_password

    known_password = "test-only-password-not-the-real-bootstrap-one"
    async with AsyncSessionLocal() as db:
        await bootstrap_default_admin_if_empty(db)
        user = (
            await db.execute(select(User).where(User.username == DEFAULT_ADMIN_USERNAME))
        ).scalar_one()
        mfa_secret = decrypt_field(user.mfa_secret_encrypted)
        db_user = await db.get(User, user.id)
        db_user.password_hash = hash_password(known_password)
        await db.commit()

    tokens = await _login_and_verify_mfa(client, DEFAULT_ADMIN_USERNAME, known_password, mfa_secret)
    assert tokens["must_change_password"] is True
    access_token = tokens["access_token"]
    auth_header = {"Authorization": f"Bearer {access_token}"}

    # Blocked everywhere except the change-password endpoint itself.
    me_resp = await client.get("/auth/me", headers=auth_header)
    assert me_resp.status_code == 403, me_resp.text

    # Wrong current password rejected.
    bad_resp = await client.post(
        "/auth/change-password",
        headers=auth_header,
        json={"current_password": "wrong", "new_password": "a-new-strong-password-1"},
    )
    assert bad_resp.status_code == 400

    # Too-short new password rejected.
    short_resp = await client.post(
        "/auth/change-password",
        headers=auth_header,
        json={"current_password": known_password, "new_password": "short"},
    )
    assert short_resp.status_code == 400

    change_resp = await client.post(
        "/auth/change-password",
        headers=auth_header,
        json={"current_password": known_password, "new_password": "a-new-strong-password-1"},
    )
    assert change_resp.status_code == 204

    # Flag cleared: /auth/me now works with the same access token.
    me_resp_after = await client.get("/auth/me", headers=auth_header)
    assert me_resp_after.status_code == 200, me_resp_after.text
    assert me_resp_after.json()["username"] == DEFAULT_ADMIN_USERNAME

    # And logging in again reflects the cleared flag.
    tokens_after = await _login_and_verify_mfa(
        client, DEFAULT_ADMIN_USERNAME, "a-new-strong-password-1", mfa_secret
    )
    assert tokens_after["must_change_password"] is False
