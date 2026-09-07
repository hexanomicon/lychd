from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from lychd.config.settings.server import DatabaseSettings


def database_url(settings: DatabaseSettings) -> str:
    """Build the SQLAlchemy async Postgres URL from the loaded settings."""
    if settings.password is None:
        msg = "Required database password is unavailable in Settings."
        raise ValueError(msg)
    return URL.create(
        "postgresql+asyncpg",
        username=settings.user,
        password=settings.password.get_secret_value(),
        host=settings.host,
        port=settings.port,
        database=settings.database,
    ).render_as_string(hide_password=False)


def database_saq_dsn(settings: DatabaseSettings) -> str:
    """Build the driverless Postgres DSN used by the local queue workers."""
    if settings.password is None:
        msg = "Required database password is unavailable in Settings."
        raise ValueError(msg)
    return URL.create(
        "postgresql",
        username=settings.user,
        password=settings.password.get_secret_value(),
        host=settings.host,
        port=settings.port,
        database=settings.database,
    ).render_as_string(hide_password=False)


def create_db_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Create the shared SQLAlchemy engine with the configured PostgreSQL pool."""
    return create_async_engine(
        url=database_url(settings),
        echo=settings.echo,
        echo_pool=settings.echo_pool,
        max_overflow=settings.max_overflow,
        pool_size=settings.pool_size,
        pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle,
        pool_pre_ping=settings.pool_pre_ping,
        pool_use_lifo=settings.pool_use_lifo,
    )
