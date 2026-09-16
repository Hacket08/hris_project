import pyotp
import pytest
from sqlalchemy import delete

from app.auth.mfa_reset import (
    InvalidResetCodeError,
    InvalidResetTokenError,
    complete_mfa_reset,
    start_mfa_reset,
)
from app.auth.models import User, UserRole
from app.core.crypto import decrypt_field, encrypt_field
from app.core.db import AsyncSessionLocal
from app.core.security import generate_mfa_secret, hash_password
from tests.conftest import requires_db

pytestmark = requires_db


@pytest.fixture(autouse=True)
async def _empty_users():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User))
        await db.commit()
    yield
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User))
        await db.commit()


@pytest.fixture
async def seeded_user():
    old_secret = generate_mfa_secret()
    async with AsyncSessionLocal() as db:
        user = User(
            username="jane.owner",
            email="jane@example.com",
            password_hash=hash_password("whatever-real-1234"),
            mfa_secret_encrypted=encrypt_field(old_secret),
            role=UserRole.hr_admin,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user, old_secret


async def test_reset_replaces_secret_only_after_valid_code(seeded_user):
    user, old_secret = seeded_user

    async with AsyncSessionLocal() as db:
        reset_token, new_secret, uri = await start_mfa_reset(db, str(user.id))
    assert new_secret != old_secret
    assert new_secret in uri

    # Wrong code doesn't touch the stored secret at all.
    async with AsyncSessionLocal() as db:
        with pytest.raises(InvalidResetCodeError):
            await complete_mfa_reset(db, reset_token, "000000")
        refetched = await db.get(User, user.id)
        assert decrypt_field(refetched.mfa_secret_encrypted) == old_secret

    # Real code from the NEW secret actually replaces it.
    async with AsyncSessionLocal() as db:
        code = pyotp.TOTP(new_secret).now()
        updated = await complete_mfa_reset(db, reset_token, code)
    assert decrypt_field(updated.mfa_secret_encrypted) == new_secret
    assert decrypt_field(updated.mfa_secret_encrypted) != old_secret


async def test_unknown_reset_token_rejected():
    async with AsyncSessionLocal() as db:
        with pytest.raises(InvalidResetTokenError):
            await complete_mfa_reset(db, "not-a-real-token", "123456")


async def test_full_http_flow_recovers_a_broken_account(client, seeded_user):
    user, _old_secret = seeded_user

    login_resp = await client.post(
        "/auth/login", json={"username": "jane.owner", "password": "whatever-real-1234"}
    )
    assert login_resp.status_code == 200
    mfa_pending_token = login_resp.json()["mfa_pending_token"]

    # Simulate the exact real-world failure: old secret no longer verifies
    # (e.g. undecryptable after a key change) — reset instead of normal verify.
    init_resp = await client.post(
        "/auth/mfa/reset/init", json={"mfa_pending_token": mfa_pending_token}
    )
    assert init_resp.status_code == 200, init_resp.text
    body = init_resp.json()
    reset_token, new_secret = body["reset_token"], body["mfa_secret"]

    bad_confirm = await client.post(
        "/auth/mfa/reset/confirm", json={"reset_token": reset_token, "code": "000000"}
    )
    assert bad_confirm.status_code == 400

    code = pyotp.TOTP(new_secret).now()
    confirm_resp = await client.post(
        "/auth/mfa/reset/confirm", json={"reset_token": reset_token, "code": code}
    )
    assert confirm_resp.status_code == 200, confirm_resp.text
    tokens = confirm_resp.json()
    access_token = tokens["access_token"]

    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "jane.owner"

    # And a completely fresh login now uses the new secret via the normal path.
    login2 = await client.post(
        "/auth/login", json={"username": "jane.owner", "password": "whatever-real-1234"}
    )
    mfa_pending_token2 = login2.json()["mfa_pending_token"]
    verify2 = await client.post(
        "/auth/mfa/verify",
        json={"mfa_pending_token": mfa_pending_token2, "code": pyotp.TOTP(new_secret).now()},
    )
    assert verify2.status_code == 200, verify2.text
