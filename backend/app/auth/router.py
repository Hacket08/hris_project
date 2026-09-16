from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, get_current_user_allow_pending_password_change
from app.auth.mfa_reset import (
    InvalidMfaPendingTokenError,
    InvalidResetCodeError,
    InvalidResetTokenError,
    complete_mfa_reset,
    start_mfa_reset,
)
from app.auth.models import User
from app.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MfaResetConfirmRequest,
    MfaResetInitRequest,
    MfaResetInitResponse,
    MFAVerifyRequest,
    SetupConfirmRequest,
    SetupInitRequest,
    SetupInitResponse,
    SetupStatusResponse,
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
from app.auth.setup import (
    InvalidSetupCodeError,
    InvalidSetupTokenError,
    SetupNotAllowedError,
    complete_setup,
    is_setup_required,
    start_setup,
)
from app.core.db import get_db
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_mfa_pending_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/setup-status", response_model=SetupStatusResponse)
async def setup_status(db: AsyncSession = Depends(get_db)) -> SetupStatusResponse:
    return SetupStatusResponse(setup_required=await is_setup_required(db))


@router.post("/setup/init", response_model=SetupInitResponse)
async def setup_init(
    payload: SetupInitRequest, db: AsyncSession = Depends(get_db)
) -> SetupInitResponse:
    try:
        setup_token, mfa_secret, provisioning_uri = await start_setup(
            db, payload.username, payload.email, payload.password
        )
    except SetupNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SetupInitResponse(
        setup_token=setup_token, mfa_secret=mfa_secret, provisioning_uri=provisioning_uri
    )


@router.post("/setup/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def setup_confirm(payload: SetupConfirmRequest, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await complete_setup(db, payload.setup_token, payload.code)
    except InvalidSetupTokenError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SetupNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except InvalidSetupCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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


@router.post("/mfa/reset/init", response_model=MfaResetInitResponse)
async def mfa_reset_init(
    payload: MfaResetInitRequest, db: AsyncSession = Depends(get_db)
) -> MfaResetInitResponse:
    """For an account whose enrolled TOTP secret stopped working. Requires
    the same proof of password knowledge as normal MFA verify — a valid
    mfa_pending_token — nothing weaker."""
    try:
        user_id = decode_token(payload.mfa_pending_token, expected_type="mfa_pending")
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired MFA challenge"
        ) from exc

    try:
        reset_token, mfa_secret, provisioning_uri = await start_mfa_reset(db, user_id)
    except InvalidMfaPendingTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return MfaResetInitResponse(
        reset_token=reset_token, mfa_secret=mfa_secret, provisioning_uri=provisioning_uri
    )


@router.post("/mfa/reset/confirm", response_model=TokenResponse)
async def mfa_reset_confirm(
    payload: MfaResetConfirmRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Only replaces the stored secret once a real code from the new one
    proves enrollment worked — same principle as the setup wizard. Issues a
    normal access token, since this also completes login."""
    try:
        user = await complete_mfa_reset(db, payload.reset_token, payload.code)
    except InvalidResetTokenError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidResetCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidMfaPendingTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

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
