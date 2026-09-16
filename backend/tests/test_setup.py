import pyotp
import pytest
from sqlalchemy import delete, select

from app.auth.models import User, UserRole
from app.auth.setup import (
    InvalidSetupCodeError,
    InvalidSetupTokenError,
    SetupNotAllowedError,
    _pending_setups,
    complete_setup,
    is_setup_required,
    start_setup,
)
from app.core.db import AsyncSessionLocal
from app.core.security import hash_password
from tests.conftest import requires_db

pytestmark = requires_db


@pytest.fixture(autouse=True)
async def _empty_users_and_pending_setups():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User))
        await db.commit()
    _pending_setups.clear()
    yield
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User))
        await db.commit()
    _pending_setups.clear()


async def test_setup_required_true_when_empty():
    async with AsyncSessionLocal() as db:
        assert await is_setup_required(db) is True


async def test_setup_required_false_once_a_user_exists():
    async with AsyncSessionLocal() as db:
        db.add(
            User(
                username="someone",
                email="someone@example.com",
                password_hash=hash_password("whatever12345"),
                mfa_secret_encrypted="not-checked-here",
                role=UserRole.hr_admin,
            )
        )
        await db.commit()
        assert await is_setup_required(db) is False


async def test_init_returns_secret_and_matching_provisioning_uri():
    async with AsyncSessionLocal() as db:
        setup_token, mfa_secret, provisioning_uri = await start_setup(
            db, "jane.owner", "jane@example.com", "a-real-password-123"
        )
    assert setup_token
    assert mfa_secret
    assert mfa_secret in provisioning_uri
    assert "jane.owner" in provisioning_uri


async def test_init_rejects_too_short_password():
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError):
            await start_setup(db, "jane.owner", "jane@example.com", "short")


async def test_confirm_with_correct_code_creates_real_account_no_forced_change():
    async with AsyncSessionLocal() as db:
        setup_token, mfa_secret, _uri = await start_setup(
            db, "jane.owner", "jane@example.com", "a-real-password-123"
        )
        code = pyotp.TOTP(mfa_secret).now()
        user = await complete_setup(db, setup_token, code)

    assert user.username == "jane.owner"
    assert user.role.value == "hr_admin"
    assert user.must_change_password is False  # a real, self-chosen password

    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(User))).scalars().all()
    assert len(count) == 1


async def test_confirm_with_wrong_code_rejected_but_stays_retryable():
    async with AsyncSessionLocal() as db:
        setup_token, mfa_secret, _uri = await start_setup(
            db, "jane.owner", "jane@example.com", "a-real-password-123"
        )
        with pytest.raises(InvalidSetupCodeError):
            await complete_setup(db, setup_token, "000000")

        # Pending state survives a wrong attempt — the real code still works.
        code = pyotp.TOTP(mfa_secret).now()
        user = await complete_setup(db, setup_token, code)
    assert user.username == "jane.owner"


async def test_confirm_with_unknown_token_rejected():
    async with AsyncSessionLocal() as db:
        with pytest.raises(InvalidSetupTokenError):
            await complete_setup(db, "not-a-real-token", "123456")


async def test_init_rejected_once_a_user_already_exists():
    async with AsyncSessionLocal() as db:
        db.add(
            User(
                username="someone",
                email="someone@example.com",
                password_hash=hash_password("whatever12345"),
                mfa_secret_encrypted="not-checked-here",
                role=UserRole.hr_admin,
            )
        )
        await db.commit()

        with pytest.raises(SetupNotAllowedError):
            await start_setup(db, "jane.owner", "jane@example.com", "a-real-password-123")


async def test_confirm_rejected_if_another_account_appeared_while_pending():
    """A pending setup (valid token, right code) must still be refused if
    someone else already completed setup (or scripts.create_user ran) in
    the meantime — one-time-first-run means exactly one winner."""
    async with AsyncSessionLocal() as db:
        setup_token, mfa_secret, _uri = await start_setup(
            db, "jane.owner", "jane@example.com", "a-real-password-123"
        )
        db.add(
            User(
                username="someone.else",
                email="someone.else@example.com",
                password_hash=hash_password("whatever12345"),
                mfa_secret_encrypted="not-checked-here",
                role=UserRole.hr_admin,
            )
        )
        await db.commit()

        code = pyotp.TOTP(mfa_secret).now()
        with pytest.raises(SetupNotAllowedError):
            await complete_setup(db, setup_token, code)


async def test_full_http_flow(client):
    status_resp = await client.get("/auth/setup-status")
    assert status_resp.status_code == 200
    assert status_resp.json()["setup_required"] is True

    init_resp = await client.post(
        "/auth/setup/init",
        json={
            "username": "jane.owner",
            "email": "jane@example.com",
            "password": "a-real-password-123",
        },
    )
    assert init_resp.status_code == 200, init_resp.text
    body = init_resp.json()
    setup_token = body["setup_token"]
    mfa_secret = body["mfa_secret"]

    bad_confirm = await client.post(
        "/auth/setup/confirm", json={"setup_token": setup_token, "code": "000000"}
    )
    assert bad_confirm.status_code == 400

    code = pyotp.TOTP(mfa_secret).now()
    confirm_resp = await client.post(
        "/auth/setup/confirm", json={"setup_token": setup_token, "code": code}
    )
    assert confirm_resp.status_code == 204, confirm_resp.text

    status_after = await client.get("/auth/setup-status")
    assert status_after.json()["setup_required"] is False

    # Setup is now permanently closed, even with a fresh init attempt.
    reinit_resp = await client.post(
        "/auth/setup/init",
        json={"username": "someone.else", "email": "x@example.com", "password": "whateverabc123"},
    )
    assert reinit_resp.status_code == 410

    # The real chosen credentials work exactly like a normal account: full
    # password + MFA, every time, no forced password change.
    login_resp = await client.post(
        "/auth/login", json={"username": "jane.owner", "password": "a-real-password-123"}
    )
    assert login_resp.status_code == 200
    mfa_pending_token = login_resp.json()["mfa_pending_token"]

    verify_resp = await client.post(
        "/auth/mfa/verify",
        json={"mfa_pending_token": mfa_pending_token, "code": pyotp.TOTP(mfa_secret).now()},
    )
    assert verify_resp.status_code == 200, verify_resp.text
    tokens = verify_resp.json()
    assert tokens["must_change_password"] is False

    me_resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "jane.owner"
