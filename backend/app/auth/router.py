from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, get_current_user_allow_pending_password_change
from app.auth.models import User
from app.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MFAVerifyRequest,
    TokenResponse,
    UserRead,
)
from app.auth.service import (
    InvalidPasswordChangeError,
    authenticate_password,
    change_password,
    get_user_by_id,
    verify_user_totp,
)
from app.core.db import get_db
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_mfa_pending_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    user = await authenticate_password(db, payload.username, payload.password)
    if user is None:
        # Same error for "no such user" and "wrong password" — do not leak which.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    return LoginResponse(mfa_pending_token=create_mfa_pending_token(str(user.id)))


@router.post("/mfa/verify", response_model=TokenResponse)
async def verify_mfa(
    payload: MFAVerifyRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    try:
        user_id = decode_token(payload.mfa_pending_token, expected_type="mfa_pending")
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired MFA challenge"
        ) from exc

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA challenge"
        )

    if not verify_user_totp(user, payload.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        must_change_password=user.must_change_password,
    )


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user=Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_allow_pending_password_change),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await change_password(db, current_user, payload.current_password, payload.new_password)
    except InvalidPasswordChangeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
