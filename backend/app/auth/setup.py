"""First-run setup wizard (BR-18/FR-23/AC-23).

Replaces the earlier auto-bootstrap-with-printed-credential approach, which
required terminal access the business owner doesn't have. This flow needs
nothing but a browser: the very first visitor picks their own real username
and password, and the account is only actually created after they prove
they've enrolled the shown TOTP secret in an authenticator app — never
before. There is no system-generated credential to relay anywhere, and no
special-cased account or bypass logic in the login path (see
app/auth/service.py — it has none).

Pending state lives in-memory only (module-level dict), consistent with
Phase 0 having no Redis/session store yet. This is fine because the window
between "pick a password" and "confirm the TOTP code" is a single sitting
by one person at one point in the system's whole lifetime, and a restart
during that window just means starting the wizard over — no data is lost
since the account doesn't exist until confirm succeeds.
"""

import time
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.core.crypto import encrypt_field
from app.core.security import (
    generate_mfa_secret,
    get_totp_provisioning_uri,
    hash_password,
    verify_totp_code,
)

SETUP_TOKEN_TTL_SECONDS = 15 * 60
MIN_PASSWORD_LENGTH = 8


class SetupNotAllowedError(Exception):
    """Raised once any user already exists — setup is a one-time, first-run-only path."""


class InvalidSetupTokenError(Exception):
    pass


class InvalidSetupCodeError(Exception):
    pass


@dataclass
class _PendingSetup:
    username: str
    email: str
    password_hash: str
    mfa_secret: str
    expires_at: float


_pending_setups: dict[str, _PendingSetup] = {}


def _prune_expired() -> None:
    now = time.time()
    expired = [token for token, p in _pending_setups.items() if p.expires_at < now]
    for token in expired:
        del _pending_setups[token]


async def is_setup_required(db: AsyncSession) -> bool:
    count = await db.scalar(select(func.count()).select_from(User))
    return count == 0


async def start_setup(
    db: AsyncSession, username: str, email: str, password: str
) -> tuple[str, str, str]:
    """Returns (setup_token, mfa_secret, provisioning_uri). Raises
    SetupNotAllowedError if a user already exists."""
    if not await is_setup_required(db):
        raise SetupNotAllowedError("Setup has already been completed")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    _prune_expired()
    mfa_secret = generate_mfa_secret()
    setup_token = uuid.uuid4().hex
    _pending_setups[setup_token] = _PendingSetup(
        username=username,
        email=email,
        password_hash=hash_password(password),
        mfa_secret=mfa_secret,
        expires_at=time.time() + SETUP_TOKEN_TTL_SECONDS,
    )
    provisioning_uri = get_totp_provisioning_uri(mfa_secret, username)
    return setup_token, mfa_secret, provisioning_uri


async def complete_setup(db: AsyncSession, setup_token: str, code: str) -> User:
    """Creates the real account only after the TOTP code proves enrollment
    succeeded. Raises InvalidSetupTokenError (unknown/expired token or setup
    already completed by someone else), InvalidSetupCodeError (wrong code,
    pending state kept so they can retry), or SetupNotAllowedError (a user
    was created by another path — e.g. scripts.create_user — while this
    setup was pending)."""
    _prune_expired()
    pending = _pending_setups.get(setup_token)
    if pending is None:
        raise InvalidSetupTokenError("Unknown or expired setup token")

    # Known, accepted Phase 0 scope limit: this check-then-insert isn't
    # atomic against a second concurrent completion (no DB-level lock/unique
    # gate beyond the users table's own PK/unique constraints). Acceptable
    # here because this flow is inherently a single person, single sitting,
    # once per system lifetime — add a real lock if that ever stops holding.
    if not await is_setup_required(db):
        del _pending_setups[setup_token]
        raise SetupNotAllowedError("Setup has already been completed")

    if not verify_totp_code(pending.mfa_secret, code):
        raise InvalidSetupCodeError("Invalid authenticator code")

    user = User(
        username=pending.username,
        email=pending.email,
        password_hash=pending.password_hash,
        mfa_secret_encrypted=encrypt_field(pending.mfa_secret),
        role=UserRole.hr_admin,
        must_change_password=False,  # a real, self-chosen password — nothing to force-change
    )
    db.add(user)
    await db.commit()
    del _pending_setups[setup_token]
    return user
