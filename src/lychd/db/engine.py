"""Process-memoized engine + session factory — the ONLY module that memoizes engine state.

This is the single low-level seat behind ``db.factory.create_db_engine``. The app
composition root, SAQ workers, graph nodes, and CLI all obtain their engine and
session factory from here so there is exactly one connection pool per process.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from lychd.config.settings import get_settings
from lychd.db.factory import create_db_engine

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

    from lychd.config.settings import DatabaseSettings

_state: dict[str, Any] = {"engine": None, "session_factory": None}


def get_engine(settings: DatabaseSettings | None = None, *, fresh: bool = False) -> AsyncEngine:
    """Return the process-memoized engine, creating it on first call.

    Args:
        settings: Database settings. Defaults to ``get_settings().db``.
        fresh: When True, discard any memoized engine/session factory and build a
            new engine. REQUIRED in forked SAQ worker processes because asyncpg
            connections do not survive ``fork``.

    """
    if fresh or _state["engine"] is None:
        db_settings = settings or get_settings().db
        _state["engine"] = create_db_engine(db_settings)
        _state["session_factory"] = None
    return _state["engine"]


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the memoized ``async_sessionmaker`` bound to the process engine."""
    if _state["session_factory"] is None:
        _state["session_factory"] = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _state["session_factory"]


async def dispose_engine() -> None:
    """Dispose the memoized engine and clear the memo."""
    engine: AsyncEngine | None = _state["engine"]
    if engine is not None:
        await engine.dispose()
    _state["engine"] = None
    _state["session_factory"] = None
