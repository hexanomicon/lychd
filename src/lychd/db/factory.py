from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine

from litestar.serialization import decode_json, encode_json

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine
    from lychd.config.settings import DatabaseSettings


def create_db_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Create and configure a SQLAlchemy AsyncEngine instance with LychD optimizations.

    This factory configures the engine with:
    1. Connection pooling optimized for PostgreSQL.
    2. High-performance binary JSONB serialization using msgspec.
    3. LIFO pooling to reuse hot connections.
    """
    engine = create_async_engine(
        url=settings.url,
        echo=settings.echo,
        echo_pool=settings.echo_pool,
        # --- POOLING OPTIMIZATIONS ---
        max_overflow=settings.max_overflow,
        pool_size=settings.pool_size,
        pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle,
        pool_pre_ping=settings.pool_pre_ping,
        # LIFO: Better for performance (reuses hot connections)
        pool_use_lifo=True,
        # --- SERIALIZATION via litestars msgspec ---
        json_serializer=encode_json,
        json_deserializer=decode_json,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _sqla_on_connect(dbapi_connection: Any, _: Any) -> Any:  # pyright: ignore [reportUnusedFunction]
        r"""Hooks into the DBAPI connection to enable direct binary JSON serialization.

        Standard SQLAlchemy dialects expect JSON serializers to return `str`.
        Since LychD uses `msgspec` for high-performance binary serialization (`bytes`),
        this hook configures `asyncpg` to bypass the standard string-conversion overhead.

        It injects a custom codec that:
        1. Accepts already-serialized `bytes` from msgspec (Zero-Copy).
        2. Prepends the PostgreSQL `\x01` version prefix for JSONB.
        3. Decodes raw binary responses directly via `msgspec`.

        Optimization:
            Avoids the double-encoding redundancy (`bytes` -> `str` -> `bytes`)
            found in standard implementations.

        Ref:
            Adapted from connection hooks in `litestar-fullstack` (MIT).
            https://github.com/litestar-org/litestar-fullstack/blob/main/src/py/app/utils/engine_factory.py#L43
        """

        # The encoder receives the data that is ALREADY serialized to bytes.
        def encoder(already_serialized_bytes: bytes) -> bytes:
            # Add the required binary prefix. DO NOT call encode_json again.
            return b"\x01" + already_serialized_bytes

        def decoder(bytes_to_decode: bytes) -> Any:
            # Strip the prefix and decode using msgspec.
            return decode_json(bytes_to_decode[1:])

        # Register for both jsonb and json types for robustness.
        dbapi_connection.await_(
            dbapi_connection.driver_connection.set_type_codec(
                "jsonb",
                encoder=encoder,
                decoder=decoder,
                schema="pg_catalog",
                format="binary",
            ),
        )

        dbapi_connection.await_(
            dbapi_connection.driver_connection.set_type_codec(
                "json",
                encoder=encoder,
                decoder=decoder,
                schema="pg_catalog",
                format="binary",
            ),
        )

    return engine
