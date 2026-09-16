from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database — this app connects with the *restricted* role (see alembic/versions/
    # 0001_phase0_foundations.py). Migrations run separately with DATABASE_ADMIN_URL,
    # which must have grant/role privileges the app itself never holds. Distinct
    # port/db/role names from Payroll (payroll/payroll_app) so both systems' local
    # Postgres instances can run side by side without collision.
    database_url: str = "postgresql+asyncpg://hris_app:hris_app@localhost:5433/hris"
    database_admin_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/hris"
    app_db_role: str = "hris_app"

    # JWT — access tokens issued only after MFA is verified (dev plan §5.2, pending
    # open question #8 on SSO — internal+MFA is the confirmed MVP default).
    jwt_secret_key: str = "CHANGE_ME_IN_ENV"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    mfa_pending_token_expire_minutes: int = 5

    # Fernet key for application-level encryption of restricted fields (MFA secrets
    # now; government ID numbers later IF this system ends up owning them — see
    # open question #7). The default below is a dev-only placeholder, NOT a real
    # secret; production must override via .env / secrets manager.
    field_encryption_key: str = "2G57skzjnVleVX9tnbApwvRigL6r9e5dS9yNbRsj6Tg="

    cors_allow_origins: list[str] = ["http://localhost:4201"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
