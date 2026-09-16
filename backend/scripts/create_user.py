"""Bootstrap CLI for creating an HR staff user with MFA enrollment.

There is no self-registration in this MVP (internal staff tool for Phase 0 —
employee self-service lands in Phase 4). Every user, including the first
hr_admin, is provisioned this way.

Usage:
    python -m scripts.create_user --username jdoe --email jdoe@example.com \\
        --role hr_admin
"""

import argparse
import asyncio
import getpass

from app.auth.models import User, UserRole
from app.core.crypto import encrypt_field
from app.core.db import AsyncSessionLocal
from app.core.security import generate_mfa_secret, get_totp_provisioning_uri, hash_password


async def create_user(username: str, email: str, role: UserRole, password: str) -> None:
    mfa_secret = generate_mfa_secret()
    async with AsyncSessionLocal() as db:
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            mfa_secret_encrypted=encrypt_field(mfa_secret),
            role=role,
            must_change_password=True,  # someone other than the account owner chose this password
        )
        db.add(user)
        await db.commit()

    print(f"Created user '{username}' with role {role.value}.")
    print("Enroll this MFA secret in an authenticator app (e.g. Google Authenticator):")
    print(f"  Secret: {mfa_secret}")
    print(f"  Provisioning URI: {get_totp_provisioning_uri(mfa_secret, username)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", required=True, choices=[r.value for r in UserRole])
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")

    asyncio.run(create_user(args.username, args.email, UserRole(args.role), password))


if __name__ == "__main__":
    main()
