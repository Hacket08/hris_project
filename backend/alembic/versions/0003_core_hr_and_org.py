"""Phase 1: Core HR + Org Management (department, position, employee, employment_history)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-16

Scope: AC-01 through AC-04 only, per 12_development_plan.md §10's Phase 1 row.
Government-ID columns on `employee` per 05_data_model.md (updated 2026-09-16,
open question #7 resolved: HRIS is the sole system of record) — encrypted the
same way MFA secrets already are (app/core/crypto.py), never plaintext.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.core.config import get_settings

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_DB_ROLE = get_settings().app_db_role


def upgrade() -> None:
    op.create_table(
        "department",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
    )

    op.create_table(
        "position",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "department_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("department.id"),
            nullable=False,
        ),
        sa.Column(
            "reports_to_position_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("position.id"),
            nullable=True,
        ),
    )

    employment_status = postgresql.ENUM(
        "probationary", "regular", "separated", name="employment_status", create_type=False
    )
    employment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "employee",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_name", sa.String(150), nullable=False),
        sa.Column("last_name", sa.String(150), nullable=False),
        sa.Column("contact_info", sa.String(255), nullable=True),
        sa.Column("employment_status", employment_status, nullable=False),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column(
            "position_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("position.id"), nullable=False
        ),
        sa.Column("sss_number_encrypted", sa.String(255), nullable=True),
        sa.Column("philhealth_number_encrypted", sa.String(255), nullable=True),
        sa.Column("pagibig_number_encrypted", sa.String(255), nullable=True),
        sa.Column("tin_encrypted", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    employment_change_type = postgresql.ENUM(
        "hire",
        "transfer",
        "promotion",
        "status_change",
        name="employment_change_type",
        create_type=False,
    )
    employment_change_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "employment_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employee.id"), nullable=False
        ),
        sa.Column("change_type", employment_change_type, nullable=False),
        sa.Column("old_value", sa.String(), nullable=True),
        sa.Column("new_value", sa.String(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    for table in ("department", "position", "employee", "employment_history"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {APP_DB_ROLE};")


def downgrade() -> None:
    for table in ("employment_history", "employee", "position", "department"):
        op.execute(f"REVOKE ALL ON {table} FROM {APP_DB_ROLE};")

    op.drop_table("employment_history")
    op.execute("DROP TYPE employment_change_type;")
    op.drop_table("employee")
    op.execute("DROP TYPE employment_status;")
    op.drop_table("position")
    op.drop_table("department")
