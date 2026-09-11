"""Process-memoized engine + session factory — the ONLY module that memoizes engine state.

This is the single low-level seat behind ``db.factory.create_db_engine``. The app
composition root, SAQ workers, graph nodes, and CLI all obtain their engine and
session factory from here so there is exactly one connection pool per process.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from lychd.config.settings.root import get_settings
from lychd.db.factory import create_db_engine

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

    from lychd.config.settings.server import DatabaseSettings

_state: dict[str, Any] = {"engine": None, "session_factory": None, "migration": None}
_migration_scope: ContextVar[bool] = ContextVar("lychd_database_migration", default=False)


@contextmanager
def database_migration_scope() -> Generator[None]:
    """Select administrative SQL authority only around an explicit operator CLI command."""
    token = _migration_scope.set(True)
    try:
        yield
    finally:
        _migration_scope.reset(token)


def get_engine(settings: DatabaseSettings | None = None) -> AsyncEngine:
    """Return the process-memoized engine, creating it on first call.

    Args:
        settings: Database settings. Defaults to ``get_settings().server.database``.

    """
    if _state["engine"] is None:
        db_settings = settings or get_settings().server.database
        _state["engine"] = create_db_engine(db_settings, runtime=not _migration_scope.get())
        _state["migration"] = _migration_scope.get()
        _state["session_factory"] = None
    elif _state["migration"] != _migration_scope.get():
        msg = "A cached database engine cannot cross the runtime/migration authority boundary"
        raise RuntimeError(msg)
    return _state["engine"]


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the memoized ``async_sessionmaker`` bound to the process engine."""
    engine = get_engine()
    if _state["session_factory"] is None:
        _state["session_factory"] = async_sessionmaker(engine, expire_on_commit=False)
    return _state["session_factory"]


async def dispose_engine() -> None:
    """Dispose the memoized engine and clear the memo."""
    engine: AsyncEngine | None = _state["engine"]
    if engine is not None:
        await engine.dispose()
    _state["engine"] = None
    _state["session_factory"] = None
    _state["migration"] = None
