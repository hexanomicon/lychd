from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from litestar.serialization import decode_json, encode_json
from sqlalchemy import event
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine

from lychd.config.utils import read_secret_from_env_or_file

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from lychd.config.settings.server import DatabaseSettings


def resolve_database_password(settings: DatabaseSettings) -> str:
    """Resolve the database secret at the connection boundary, not while loading settings."""
    return read_secret_from_env_or_file(
        value_env_keys=("LYCHD_DB_PASSWORD",),
        file_env_keys=("LYCHD_DB_PASSWORD_FILE",),
        default_file=Path("/run/secrets") / settings.password_secret,
        secret_label=settings.password_secret,
    )


def database_url(settings: DatabaseSettings) -> str:
    """Build the SQLAlchemy async Postgres URL from settings and the resolved secret."""
    return URL.create(
        "postgresql+asyncpg",
        username=settings.user,
        password=resolve_database_password(settings),
        host=settings.host,
        port=settings.port,
        database=settings.database,
    ).render_as_string(hide_password=False)


def database_saq_dsn(settings: DatabaseSettings) -> str:
    """Build the driverless Postgres DSN used by the local queue workers."""
    return URL.create(
        "postgresql",
        username=settings.user,
        password=resolve_database_password(settings),
        host=settings.host,
        port=settings.port,
        database=settings.database,
    ).render_as_string(hide_password=False)


def create_db_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Create and configure a SQLAlchemy AsyncEngine instance with LychD optimizations.

    This factory configures the engine with:
    1. Connection pooling optimized for PostgreSQL.
    2. High-performance binary JSONB serialization using msgspec.
    3. LIFO pooling to reuse hot connections.
    """
    engine = create_async_engine(
        url=database_url(settings),
        echo=settings.echo,
        echo_pool=settings.echo_pool,
        # --- POOLING OPTIMIZATIONS ---
        max_overflow=settings.max_overflow,
        pool_size=settings.pool_size,
        pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle,
        pool_pre_ping=settings.pool_pre_ping,
        pool_use_lifo=settings.pool_use_lifo,
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

        It injects custom codecs that:
        1. Accepts already-serialized `bytes` from msgspec.
        2. Prepends PostgreSQL's `\x01` version prefix only for JSONB.
           Plain JSON uses its unversioned binary representation.
        3. Decodes raw binary responses directly via `msgspec`.

        Optimization:
            Avoids the double-encoding redundancy (`bytes` -> `str` -> `bytes`)
            found in standard implementations. This is not a zero-copy storage claim.

        Ref:
            Adapted from connection hooks in `litestar-fullstack` (MIT).
            https://github.com/litestar-org/litestar-fullstack/blob/main/src/py/app/utils/engine_factory.py#L43
        """

        # The encoder receives the data that is ALREADY serialized to bytes.
        def jsonb_encoder(already_serialized_bytes: bytes) -> bytes:
            # Add the required binary prefix. DO NOT call encode_json again.
            return b"\x01" + already_serialized_bytes

        def jsonb_decoder(bytes_to_decode: bytes) -> Any:
            # Strip the prefix and decode using msgspec.
            return decode_json(bytes_to_decode[1:])

        def json_encoder(already_serialized_bytes: bytes) -> bytes:
            return already_serialized_bytes

        def json_decoder(bytes_to_decode: bytes) -> Any:
            return decode_json(bytes_to_decode)

        dbapi_connection.await_(
            dbapi_connection.driver_connection.set_type_codec(
                "jsonb",
                encoder=jsonb_encoder,
                decoder=jsonb_decoder,
                schema="pg_catalog",
                format="binary",
            ),
        )

        dbapi_connection.await_(
            dbapi_connection.driver_connection.set_type_codec(
                "json",
                encoder=json_encoder,
                decoder=json_decoder,
                schema="pg_catalog",
                format="binary",
            ),
        )

    return engine
