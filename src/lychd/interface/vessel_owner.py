"""Fence production lifespan and reconciliation to one process per PostgreSQL database."""

from __future__ import annotations

import asyncio
import hmac
import secrets
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

import asyncpg

from lychd.config.settings import root as settings_root
from lychd.db.authority import RUNTIME_AUTHORITY_QUERY, require_runtime_authority
from lychd.db.factory import database_saq_dsn

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from litestar import Litestar


VESSEL_LOCK_CLASS = 727163
VESSEL_LOCK_KEY = 1
_LOCK_SQL = "SELECT pg_try_advisory_lock($1::int, $2::int)"
_OWNER_SQL = """
SELECT a.application_name FROM pg_locks l JOIN pg_stat_activity a ON a.pid = l.pid
WHERE l.locktype = 'advisory' AND l.database = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND l.classid = $1 AND l.objid = $2 AND l.objsubid = 2 AND l.granted
"""
_STOP_CHANNEL = "lychd_native_stop"
_NATIVE_PREFIX = "lychd-native-"


def _stop_proof(generation: str) -> str:
    secret = settings_root.get_settings().server.web.secret_key
    if secret is None:
        message = "The native Vessel requires the application signing key."
        raise ValueError(message)
    return hmac.digest(secret.get_secret_value().encode(), f"{_STOP_CHANNEL}/{generation}".encode(), "sha256").hex()


@asynccontextmanager
async def _runtime_session(application_name: str) -> AsyncGenerator[Any]:
    db = settings_root.get_settings().server.database
    connection = await cast("Any", asyncpg).connect(
        database_saq_dsn(db, runtime=True, libpq=False),
        timeout=10,
        command_timeout=10,
        server_settings={"application_name": application_name},
    )
    try:
        require_runtime_authority(await connection.fetchval(RUNTIME_AUTHORITY_QUERY))
        yield connection
    finally:
        await connection.close(timeout=5)


async def stop_native_vessel() -> bool:
    """Request retirement from the exact lock owner, then observe it relinquish ownership."""
    async with asyncio.timeout(90), _runtime_session("lychd-stop") as connection:
        generation = await connection.fetchval(_OWNER_SQL, VESSEL_LOCK_CLASS, VESSEL_LOCK_KEY)
        if generation is None:
            return False
        if not isinstance(generation, str) or not generation.startswith(_NATIVE_PREFIX):
            message = "This database belongs to a Vessel outside the native supervisor."
            raise RuntimeError(message)
        await connection.execute("SELECT pg_notify($1, $2)", _STOP_CHANNEL, _stop_proof(generation))
        while await connection.fetchval(_OWNER_SQL, VESSEL_LOCK_CLASS, VESSEL_LOCK_KEY) == generation:  # noqa: ASYNC110 - PostgreSQL owns the release observation.
            await asyncio.sleep(0.2)
        return True


@asynccontextmanager
async def vessel_database_owner(app: Litestar) -> AsyncGenerator[None]:
    """Keep a session advisory lock through worker retirement, including recovery."""
    owner = asyncio.current_task()
    if owner is None:
        message = "The Vessel lifespan requires an asyncio task."
        raise RuntimeError(message)
    request_stop: Callable[[], None] | None = getattr(app.state, "native_request_stop", None)
    generation = _NATIVE_PREFIX + secrets.token_hex(16) if request_stop is not None else "lychd-vessel"

    def lost_session(_connection: object) -> None:
        owner.cancel("The Vessel lost its exclusive database session.")

    async with _runtime_session(generation) as connection:
        if request_stop is not None:
            proof = _stop_proof(generation)

            def stop(_connection: object, _pid: int, _channel: str, payload: str) -> None:
                if payload.isascii() and hmac.compare_digest(proof, payload):
                    request_stop()

            # Subscribe before advertising ownership, so even a startup stop is received.
            await connection.add_listener(_STOP_CHANNEL, stop)
        if not await connection.fetchval(_LOCK_SQL, VESSEL_LOCK_CLASS, VESSEL_LOCK_KEY):
            message = "A Vessel already owns this PostgreSQL database."
            raise RuntimeError(message)
        connection.add_termination_listener(lost_session)
        try:
            yield
        finally:
            connection.remove_termination_listener(lost_session)
