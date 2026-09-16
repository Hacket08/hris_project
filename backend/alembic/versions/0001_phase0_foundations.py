"""Phase 0 foundations: users, audit_log + audit-log lockdown

Revision ID: 0001
Revises:
Create Date: 2026-09-16

Creates the minimal schema needed to satisfy the Phase 0 exit criteria in
12_development_plan.md §10: "A user can log in with MFA; REVOKE on audit_log
verified in CI." Employee/org/attendance/leave/benefits/etc. tables (§4) are
Phase 1+ and land in later migrations — deliberately not built here, matching
what Payroll's own Phase 0 migration actually scoped itself to (verified by
reading payroll-system/backend/alembic/versions/0001_phase0_foundations.py
directly rather than trusting its README's "18 tables" claim, which does not
match its actual committed code).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.core.config import get_settings

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_DB_ROLE = get_settings().app_db_role


def upgrade() -> None:
    user_role = postgresql.ENUM(
        "hr_admin",
        "hr_staff",
        "manager",
        "employee",
        "auditor_read",
        name="user_role",
        create_type=False,
    )
    user_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(150), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("mfa_secret_encrypted", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "audit_log",
        sa.Column("log_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_name", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("field_changed", sa.String(100), nullable=True),
        sa.Column("old_value", sa.String(), nullable=True),
        sa.Column("new_value", sa.String(), nullable=True),
        sa.Column(
            "changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("reason", sa.String(), nullable=True),
    )

    # --- Audit-log lockdown (dev plan §5.3) ---
    # Idempotent, NOLOGIN role creation: the app's actual LOGIN + password is
    # provisioned out-of-band (docker/init-db.sh locally; the org's secrets
    # manager/IaC in real environments) so no credential ever lives in a
    # migration file. This block only guarantees the role exists to grant to.
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{APP_DB_ROLE}') THEN
            CREATE ROLE {APP_DB_ROLE} NOLOGIN;
          END IF;
        END
        $$;
        """
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON users TO {APP_DB_ROLE};")

    # audit_log: INSERT + SELECT only. This is the enforcement that matters —
    # even a bug or a compromised app credential cannot rewrite history.
    op.execute(f"GRANT SELECT, INSERT ON audit_log TO {APP_DB_ROLE};")
    op.execute(f"REVOKE UPDATE, DELETE ON audit_log FROM {APP_DB_ROLE};")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON audit_log FROM {APP_DB_ROLE};")
    op.execute(f"REVOKE ALL ON users FROM {APP_DB_ROLE};")

    op.drop_table("audit_log")
    op.drop_table("users")
    op.execute("DROP TYPE user_role;")
