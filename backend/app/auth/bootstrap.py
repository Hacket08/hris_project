"""Auto-creates a default admin account on startup if no users exist yet.

This exists specifically to remove the manual `scripts.create_user` CLI step
for the very first account, since that step has proven fragile in some
environments (e.g. Python's `getpass` on Windows reads directly from the
console and ignores redirected/piped input). No AI or human other than
whoever reads this process's own stdout ever sees the generated credential:
it is never written to a file, never returned by any API, and never logged
anywhere except this one-time startup print.

Security note: the password and MFA secret are generated fresh with
`secrets`/`pyotp` on every trigger (i.e. only when the `users` table is
genuinely empty) — never a fixed/hardcoded value. This only ever creates
an account when the table is empty, so it cannot silently reset or expose
an existing account's credentials.
"""

import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.core.crypto import encrypt_field
from app.core.security import generate_mfa_secret, get_totp_provisioning_uri, hash_password

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@example.com"  # must pass EmailStr (needs a TLD) — see UserRead


async def bootstrap_default_admin_if_empty(db: AsyncSession) -> None:
    user_count = await db.scalar(select(func.count()).select_from(User))
    if user_count:
        return

    password = secrets.token_urlsafe(24)
    mfa_secret = generate_mfa_secret()

    user = User(
        username=DEFAULT_ADMIN_USERNAME,
        email=DEFAULT_ADMIN_EMAIL,
        password_hash=hash_password(password),
        mfa_secret_encrypted=encrypt_field(mfa_secret),
        role=UserRole.hr_admin,
        must_change_password=True,
    )
    db.add(user)
    await db.commit()

    provisioning_uri = get_totp_provisioning_uri(mfa_secret, DEFAULT_ADMIN_USERNAME)
    banner = "=" * 78
    print(  # noqa: T201 — deliberate: this is the only place this credential is ever surfaced
        f"\n{banner}\n"
        f"FIRST RUN: no users existed, so a default admin account was created.\n"
        f"This is printed ONCE, here, and nowhere else (not logged, not stored in a\n"
        f"file, not returned by any API). Save it now.\n\n"
        f"  Username: {DEFAULT_ADMIN_USERNAME}\n"
        f"  Password: {password}\n"
        f"  TOTP secret: {mfa_secret}\n"
        f"  Provisioning URI: {provisioning_uri}\n\n"
        f"Scan the provisioning URI (or enter the secret) into an authenticator app,\n"
        f"then log in at the frontend with the username/password above.\n"
        f"{banner}\n"
    )
