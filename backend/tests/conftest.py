"""Fixtures for the integration tests in test_auth_flow.py and
test_audit_log_lockdown.py. These need a real Postgres reachable at
DATABASE_ADMIN_URL/DATABASE_URL with migrations already applied — see
README.md 'Running tests'. They're skipped automatically if no DB is
reachable, so `pytest` still runs the pure-unit suite (test_security.py)
without any services running.
"""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings

settings = get_settings()


def _db_reachable() -> bool:
    async def _check() -> bool:
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect():
                return True
        except Exception:  # noqa: BLE001 — reachability probe, any failure means "not reachable"
            return False
        finally:
            await engine.dispose()

    try:
        return asyncio.run(_check())
    except Exception:  # noqa: BLE001 — reachability probe, any failure means "not reachable"
        return False


requires_db = pytest.mark.skipif(
    not _db_reachable(),
    reason="Postgres not reachable at DATABASE_URL — see README 'Running tests'",
)


@pytest_asyncio.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
