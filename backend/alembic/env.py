import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.core.db import Base

# Import every model module so Base.metadata is fully populated for autogenerate.
from app.audit import models as audit_models  # noqa: F401
from app.auth import models as auth_models  # noqa: F401

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Migrations run as the admin role (grant/role privileges) — never the restricted
# app role that the running application uses. Passed directly to the engine,
# NOT through config.set_main_option()/get_section(): those round-trip through
# ConfigParser, which treats a literal "%" in the URL (common in a URL-encoded
# password, e.g. "%40" for "@") as interpolation syntax and raises.

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_admin_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        {"sqlalchemy.url": settings.database_admin_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
