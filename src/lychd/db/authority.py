"""Effect-time refusal of administrative database authority in the running Vessel."""

from __future__ import annotations

from typing import Any

from litestar_saq import QueueConfig
from psycopg.sql import SQL
from saq import Queue
from saq.queue.postgres import PostgresQueue
from saq.queue.postgres_migrations import get_migrations

RUNTIME_AUTHORITY_QUERY = """
SELECT r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls
       OR EXISTS (SELECT FROM pg_auth_members WHERE member = r.oid)
       OR EXISTS (SELECT FROM pg_database WHERE datname = current_database() AND datdba = r.oid)
       OR EXISTS (SELECT FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relowner = r.oid)
       OR has_schema_privilege(current_user, 'public', 'CREATE')
FROM pg_roles r WHERE rolname = current_user
"""


class DatabaseAuthorityError(RuntimeError):
    """Runtime database authority exceeds the admitted data-only role."""


def require_runtime_authority(unsafe: object) -> None:
    """Require positive evidence of a role without schema or administrative power."""
    if unsafe is not False:
        msg = "Runtime database authority is unsafe; run the explicit database bootstrap gate"
        raise DatabaseAuthorityError(msg)


def verify_sqlalchemy_connection(connection: Any, _record: Any) -> None:
    """Verify every newly created SQLAlchemy connection before application queries."""
    cursor = connection.cursor()
    try:
        cursor.execute(RUNTIME_AUTHORITY_QUERY)
        row = cursor.fetchone()
        require_runtime_authority(row[0] if row else None)
    finally:
        cursor.close()


class RuntimePostgresQueue(PostgresQueue):
    """SAQ's runtime transport verifies schema instead of creating or migrating it."""

    async def connect(self) -> None:
        """Close an owned pool if verification or startup is rejected."""
        try:
            await super().connect()
        except BaseException:
            if self._manage_pool_lifecycle:
                await self.pool.close()
            raise

    async def init_db(self) -> None:
        """Refuse missing/drifted schema or an overprivileged runtime connection."""
        async with self.pool.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(RUNTIME_AUTHORITY_QUERY)
            authority = await cursor.fetchone()
            require_runtime_authority(authority[0] if authority else None)
            await cursor.execute(SQL("SELECT version FROM {}").format(self.versions_table))
            rows = await cursor.fetchall()
            target = get_migrations(jobs_table=self.jobs_table, stats_table=self.stats_table)[-1][0]
            if rows != [(target,)]:
                msg = "SAQ schema is not current; run the explicit database bootstrap gate"
                raise DatabaseAuthorityError(msg)


class RuntimeQueueConfig(QueueConfig):
    """Select LychD's verification-only PostgreSQL queue at the plugin seam."""

    @property
    def queue_class(self) -> type[Queue]:
        return RuntimePostgresQueue
