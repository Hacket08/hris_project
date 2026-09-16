from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
import pyotp

from app.core.config import get_settings

settings = get_settings()


# --- Password hashing --------------------------------------------------------


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


# --- TOTP (MFA) ----------------------------------------------------------------
# MFA is mandatory for every user in this MVP, mirroring Payroll's confirmed
# choice (dev plan §5.2), pending open question #8 (SSO).


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def get_totp_provisioning_uri(secret: str, username: str, issuer: str = "HRIS System") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


# --- JWT -------------------------------------------------------------------
# Two distinct token types, never accepted interchangeably by the dependencies
# in app/auth/deps.py:
#   "mfa_pending" — issued after username/password check, before MFA is verified.
#                   Only usable against POST /auth/mfa/verify.
#   "access"      — issued after MFA verification. Usable against every other route.


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_mfa_pending_token(user_id: str) -> str:
    return _create_token(
        user_id, "mfa_pending", timedelta(minutes=settings.mfa_pending_token_expire_minutes)
    )


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, "access", timedelta(minutes=settings.access_token_expire_minutes))


class InvalidTokenError(Exception):
    pass


def decode_token(token: str, expected_type: str) -> str:
    """Returns the subject (user id) if the token is valid and of the expected type."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(
            f"expected token type '{expected_type}', got '{payload.get('type')}'"
        )

    return payload["sub"]
