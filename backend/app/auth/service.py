import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.auth.models import User
from app.core.crypto import decrypt_field
from app.core.security import hash_password, verify_password, verify_totp_code

MIN_PASSWORD_LENGTH = 8


class InvalidPasswordChangeError(Exception):
    pass


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == uid))
    return result.scalar_one_or_none()


async def authenticate_password(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def verify_user_totp(user: User, code: str) -> bool:
    secret = decrypt_field(user.mfa_secret_encrypted)
    return verify_totp_code(secret, code)


async def change_password(
    db: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise InvalidPasswordChangeError("Current password is incorrect")
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise InvalidPasswordChangeError(
            f"New password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    if verify_password(new_password, user.password_hash):
        raise InvalidPasswordChangeError("New password must be different from the current one")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await record_audit(
        db,
        entity_name="users",
        entity_id=str(user.id),
        changed_by=user.id,
        field_changed="password_hash",
        reason="Self-service password change",
    )
    await db.commit()
