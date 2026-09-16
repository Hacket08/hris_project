"""Verifies the audit_log grant lockdown from
alembic/versions/0001_phase0_foundations.py is real at the database level —
not just application-layer discipline (dev plan §5.3).

Connects directly as the restricted app role (DATABASE_URL) and asserts
Postgres itself refuses UPDATE/DELETE, while INSERT/SELECT still work.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from tests.conftest import requires_db

pytestmark = requires_db

settings = get_settings()


@pytest.fixture
async def app_role_engine():
    engine = create_async_engine(settings.database_url)
    yield engine
    await engine.dispose()


async def test_app_role_can_insert_and_select_audit_log(app_role_engine):
    log_id = str(uuid.uuid4())
    async with app_role_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO audit_log (log_id, entity_name, entity_id) "
                "VALUES (:log_id, 'test_entity', 'test-1')"
            ),
            {"log_id": log_id},
        )
        result = await conn.execute(
            text("SELECT entity_name FROM audit_log WHERE log_id = :log_id"), {"log_id": log_id}
        )
        assert result.scalar_one() == "test_entity"


async def test_app_role_cannot_update_audit_log(app_role_engine):
    log_id = str(uuid.uuid4())
    async with app_role_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO audit_log (log_id, entity_name, entity_id) "
                "VALUES (:log_id, 'test_entity', 'test-2')"
            ),
            {"log_id": log_id},
        )

    with pytest.raises(DBAPIError, match="permission denied"):
        async with app_role_engine.begin() as conn:
            await conn.execute(
                text("UPDATE audit_log SET entity_name = 'tampered' WHERE log_id = :log_id"),
                {"log_id": log_id},
            )


async def test_app_role_cannot_delete_audit_log(app_role_engine):
    log_id = str(uuid.uuid4())
    async with app_role_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO audit_log (log_id, entity_name, entity_id) "
                "VALUES (:log_id, 'test_entity', 'test-3')"
            ),
            {"log_id": log_id},
        )

    with pytest.raises(DBAPIError, match="permission denied"):
        async with app_role_engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM audit_log WHERE log_id = :log_id"), {"log_id": log_id}
            )
