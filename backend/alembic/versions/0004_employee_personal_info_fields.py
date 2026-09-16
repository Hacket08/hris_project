"""Expand employee with personal-info/employment fields (05_data_model.md, 2026-09-16)

Grounded in standard Philippine 201-file/HR recordkeeping conventions — see
that doc's provenance note for why this is NOT derived from any specific
third-party system's research.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employee", sa.Column("middle_name", sa.String(150), nullable=True))
    op.add_column("employee", sa.Column("suffix", sa.String(20), nullable=True))
    op.add_column("employee", sa.Column("nickname", sa.String(100), nullable=True))
    op.add_column("employee", sa.Column("maiden_name", sa.String(150), nullable=True))
    op.add_column("employee", sa.Column("gender", sa.String(30), nullable=True))
    op.add_column("employee", sa.Column("birthdate", sa.Date(), nullable=True))
    op.add_column("employee", sa.Column("birth_place", sa.String(255), nullable=True))
    op.add_column("employee", sa.Column("civil_status", sa.String(30), nullable=True))
    op.add_column("employee", sa.Column("spouse_name", sa.String(150), nullable=True))
    op.add_column(
        "employee",
        sa.Column("is_solo_parent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "employee",
        sa.Column(
            "is_minimum_wage_earner", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("employee", sa.Column("religion", sa.String(100), nullable=True))
    op.add_column("employee", sa.Column("nationality", sa.String(100), nullable=True))
    op.add_column("employee", sa.Column("corporate_email", sa.String(255), nullable=True))
    op.add_column("employee", sa.Column("personal_email", sa.String(255), nullable=True))
    op.add_column("employee", sa.Column("permanent_address", sa.String(500), nullable=True))
    op.add_column("employee", sa.Column("current_address", sa.String(500), nullable=True))
    op.add_column("employee", sa.Column("regularization_date", sa.Date(), nullable=True))
    op.add_column("employee", sa.Column("position_title", sa.String(150), nullable=True))
    # Placeholder only — no `schedule` table exists yet (Phase 2), so this is
    # a plain column, not a real FK constraint. Add the constraint once that
    # table exists rather than requiring a second migration on this table.
    op.add_column(
        "employee",
        sa.Column("default_schedule_id", postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("employee", "default_schedule_id")
    op.drop_column("employee", "position_title")
    op.drop_column("employee", "regularization_date")
    op.drop_column("employee", "current_address")
    op.drop_column("employee", "permanent_address")
    op.drop_column("employee", "personal_email")
    op.drop_column("employee", "corporate_email")
    op.drop_column("employee", "nationality")
    op.drop_column("employee", "religion")
    op.drop_column("employee", "is_minimum_wage_earner")
    op.drop_column("employee", "is_solo_parent")
    op.drop_column("employee", "spouse_name")
    op.drop_column("employee", "civil_status")
    op.drop_column("employee", "birth_place")
    op.drop_column("employee", "birthdate")
    op.drop_column("employee", "gender")
    op.drop_column("employee", "maiden_name")
    op.drop_column("employee", "nickname")
    op.drop_column("employee", "suffix")
    op.drop_column("employee", "middle_name")
