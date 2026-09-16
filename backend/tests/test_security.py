"""Pure unit tests — no database needed. Covers the primitives the Phase 0
exit criteria ('a user can log in with MFA') is built on."""

import pyotp
import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_mfa_pending_token,
    decode_token,
    generate_mfa_secret,
    hash_password,
    verify_password,
    verify_totp_code,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_password_hash_is_not_plaintext():
    assert "s3cr3t" not in hash_password("s3cr3t")


def test_totp_valid_code_verifies():
    secret = generate_mfa_secret()
    code = pyotp.TOTP(secret).now()
    assert verify_totp_code(secret, code)


def test_totp_wrong_code_rejected():
    secret = generate_mfa_secret()
    other_secret = generate_mfa_secret()
    wrong_code = pyotp.TOTP(other_secret).now()
    assert not verify_totp_code(secret, wrong_code)


def test_access_token_roundtrip():
    token = create_access_token("user-123")
    assert decode_token(token, expected_type="access") == "user-123"


def test_mfa_pending_token_rejected_as_access_token():
    """The two token types must never be interchangeable — a stolen mfa_pending
    token must not grant API access on its own."""
    token = create_mfa_pending_token("user-123")
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type="access")


def test_expired_token_rejected():
    from datetime import timedelta

    from app.core.security import _create_token

    token = _create_token("user-123", "access", timedelta(seconds=-1))
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type="access")
