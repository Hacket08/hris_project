from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.auth.models import User, UserRole
from app.auth.service import get_user_by_id
from app.core.db import get_db
from app.core.security import InvalidTokenError, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_error
    try:
        user_id = decode_token(token, expected_type="access")
    except InvalidTokenError as exc:
        raise credentials_error from exc

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_role(*allowed_roles: UserRole) -> Callable:
    """RBAC dependency. This — not the Angular route guard — is the real
    security boundary (dev plan §5.2). Every denied attempt is written to
    audit_log, mirroring Payroll's AC-19 pattern."""

    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.role not in allowed_roles:
            await record_audit(
                db,
                entity_name="authz_denial",
                entity_id=str(current_user.id),
                changed_by=current_user.id,
                reason=(
                    f"role={current_user.role.value} attempted an action requiring "
                    f"one of {[r.value for r in allowed_roles]}"
                ),
            )
            await db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user

    return dependency
