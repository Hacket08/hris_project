"""MFA reset — for an authenticated-by-password user whose enrolled TOTP
secret has stopped working (e.g. lost device, or the server-side
FIELD_ENCRYPTION_KEY changed and an old secret can no longer be decrypted,
as happened for real on 2026-09-16).

Same security model and no-relayed-credential pattern as the first-run
setup wizard (app/auth/setup.py): a fresh secret is generated, shown only
in the browser of whoever is holding a valid mfa_pending_token (i.e.
already proved they know the password — the same trust bar the normal
login flow already requires to reach the MFA step), and the account's
stored secret is only actually replaced once a real code from the new
secret proves enrollment worked. No AI ever sees or generates a credential
that gets relayed to the account owner.
"""

import time
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.auth.models import User
from app.auth.service import get_user_by_id
from app.core.crypto import encrypt_field
from app.core.security import generate_mfa_secret, get_totp_provisioning_uri, verify_totp_code

RESET_TOKEN_TTL_SECONDS = 15 * 60


class InvalidMfaPendingTokenError(Exception):
    pass


class InvalidResetTokenError(Exception):
    pass


class InvalidResetCodeError(Exception):
    pass


@dataclass
class _PendingReset:
    user_id: str
    mfa_secret: str
    expires_at: float


_pending_resets: dict[str, _PendingReset] = {}


def _prune_expired() -> None:
    now = time.time()
    expired = [token for token, p in _pending_resets.items() if p.expires_at < now]
    for token in expired:
        del _pending_resets[token]


async def start_mfa_reset(db: AsyncSession, user_id: str) -> tuple[str, str, str]:
    """Returns (reset_token, mfa_secret, provisioning_uri). Caller must have
    already validated the mfa_pending_token this user_id came from."""
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise InvalidMfaPendingTokenError("Invalid or expired MFA challenge")

    _prune_expired()
    mfa_secret = generate_mfa_secret()
    reset_token = uuid.uuid4().hex
    _pending_resets[reset_token] = _PendingReset(
        user_id=user_id, mfa_secret=mfa_secret, expires_at=time.time() + RESET_TOKEN_TTL_SECONDS
    )
    provisioning_uri = get_totp_provisioning_uri(mfa_secret, user.username)
    return reset_token, mfa_secret, provisioning_uri


async def complete_mfa_reset(db: AsyncSession, reset_token: str, code: str) -> User:
    """Only actually replaces the stored secret once `code` proves the new
    one was really enrolled. Returns the updated user."""
    _prune_expired()
    pending = _pending_resets.get(reset_token)
    if pending is None:
        raise InvalidResetTokenError("Unknown or expired reset token")

    if not verify_totp_code(pending.mfa_secret, code):
        raise InvalidResetCodeError("Invalid authenticator code")

    user = await get_user_by_id(db, pending.user_id)
    if user is None or not user.is_active:
        del _pending_resets[reset_token]
        raise InvalidMfaPendingTokenError("Invalid or expired MFA challenge")

    user.mfa_secret_encrypted = encrypt_field(pending.mfa_secret)
    await record_audit(
        db,
        entity_name="users",
        entity_id=str(user.id),
        changed_by=user.id,
        field_changed="mfa_secret_encrypted",
        reason="MFA reset: previous secret could not be verified (see BR-18 follow-up)",
    )
    await db.commit()
    del _pending_resets[reset_token]
    return user
