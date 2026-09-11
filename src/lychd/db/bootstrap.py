"""Explicit, repeatable PostgreSQL provisioning without resetting existing data.

The legacy database owner remains the administrative migration identity. Separate
marked roles receive only runtime or Phoenix authority. No unmarked role is adopted.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, LiteralString

import psycopg
from psycopg.sql import SQL, Identifier, Literal
from saq.queue.postgres import PostgresQueue

from lychd.config.constants import DB_MIGRATION_VERSION_TABLE, PATH_MIGRATION_CONFIG, PATH_MIGRATION_DIR
from lychd.db.authority import RuntimePostgresQueue
from lychd.db.factory import create_db_engine, database_saq_dsn

if TYPE_CHECKING:
    from pydantic import SecretStr

    from lychd.config.settings.root import Settings
    from lychd.config.settings.server import DatabaseSettings

_ROLE_MARKER = "lychd:database-role:v1:"
_BOOTSTRAP_LOCK = 736249818645


def _prepare_role(connection: psycopg.Connection[Any], name: str, password: SecretStr | None, kind: str) -> None:
    """Verify existing authority before password changes, after transactional PUBLIC repair."""
    if password is None:
        msg = f"Missing {kind} database credential; bind must provision it before bootstrap"
        raise ValueError(msg)
    row = connection.execute(
        """SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,
                  shobj_description(oid, 'pg_authid'),
                  EXISTS (SELECT FROM pg_auth_members WHERE member = r.oid OR roleid = r.oid),
                  %s = 'runtime' AND (
                      EXISTS (SELECT FROM pg_database WHERE datname = current_database() AND datdba = r.oid)
                      OR EXISTS (SELECT FROM pg_class
                                 WHERE relnamespace = 'public'::regnamespace AND relowner = r.oid)
                      OR has_schema_privilege(r.oid, 'public', 'CREATE'))
           FROM pg_roles r WHERE rolname = %s""",
        (kind, name),
    ).fetchone()
    if row is None:
        connection.execute(
            SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT").format(
                Identifier(name)
            )
        )
        connection.execute(SQL("COMMENT ON ROLE {} IS {}").format(Identifier(name), Literal(_ROLE_MARKER + kind)))
    elif not row[0] or any(row[1:6]) or row[6] != _ROLE_MARKER + kind or row[7] or row[8]:
        msg = f"Existing database role {name!r} is not an admitted LychD {kind} role; preserved unchanged"
        raise ValueError(msg)
    connection.execute(SQL("ALTER ROLE {} PASSWORD {}").format(Identifier(name), Literal(password.get_secret_value())))


def _verify_administrator(connection: psycopg.Connection[Any], settings: DatabaseSettings) -> None:
    """Verify the configured owner and effective TCP authentication before mutation."""
    row = connection.execute("SELECT current_user, rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()
    if row != (settings.user, True):
        msg = "Database bootstrap requires the configured administrative owner; runtime authority is insufficient"
        raise ValueError(msg)
    rules = connection.execute("SELECT type, auth_method, error FROM pg_hba_file_rules").fetchall()
    if not rules or any(
        error or (kind != "local" and method not in {"scram-sha-256", "reject"}) for kind, method, error in rules
    ):
        msg = "PostgreSQL TCP authentication is unsafe; install the generated SCRAM HBA policy before bootstrap"
        raise ValueError(msg)


def _prepare_databases(settings: DatabaseSettings) -> None:
    dsn = database_saq_dsn(settings)
    with psycopg.connect(dsn, autocommit=True) as connection:
        _verify_administrator(connection, settings)
        with connection.transaction():
            connection.execute("SELECT pg_advisory_xact_lock(%s)", (_BOOTSTRAP_LOCK,))
            existing_phoenix = connection.execute(
                """SELECT pg_get_userbyid(datdba), shobj_description(datdba, 'pg_authid')
                   FROM pg_database WHERE datname = 'phoenix'"""
            ).fetchone()
            if existing_phoenix is not None and not (
                existing_phoenix[0] == settings.user
                or existing_phoenix == (settings.phoenix_user, _ROLE_MARKER + "phoenix")
            ):
                msg = "Existing Phoenix database has an unrelated owner; preserved unchanged"
                raise ValueError(msg)
            # Legacy PUBLIC CREATE is an admitted repair, not authority belonging
            # to the runtime role. Refusal below rolls this preliminary repair
            # back with every role change in the same transaction.
            connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            _prepare_role(connection, settings.runtime_user, settings.runtime_password, "runtime")
            _prepare_role(connection, settings.phoenix_user, settings.phoenix_password, "phoenix")
            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.execute(SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(Identifier(settings.database)))
        if connection.execute("SELECT 1 FROM pg_database WHERE datname = 'phoenix'").fetchone() is None:
            connection.execute("CREATE DATABASE phoenix")
    with psycopg.connect(dsn, dbname="phoenix", autocommit=True) as connection, connection.transaction():
        connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
        connection.execute("REVOKE ALL ON DATABASE phoenix FROM PUBLIC")
        connection.execute(SQL("ALTER DATABASE phoenix OWNER TO {}").format(Identifier(settings.phoenix_user)))
        connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        connection.execute(SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(Identifier(settings.phoenix_user)))
        # Transfer only Phoenix's existing public relations, never shared cluster
        # objects or the application owner's objects in another database.
        rows = connection.execute(
            """
            SELECT c.relname, c.relkind FROM pg_class c
            WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p', 'v', 'm', 'S')
              AND c.relowner = (SELECT oid FROM pg_roles WHERE rolname = %s)
              AND NOT EXISTS (SELECT FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
                              AND d.objid = c.oid AND d.deptype = 'e')
            ORDER BY CASE WHEN c.relkind = 'S' THEN 1 ELSE 0 END
        """,
            (settings.user,),
        ).fetchall()
        kinds: dict[str, LiteralString] = {
            "r": "TABLE",
            "p": "TABLE",
            "v": "VIEW",
            "m": "MATERIALIZED VIEW",
            "S": "SEQUENCE",
        }
        for name, kind in rows:
            connection.execute(
                SQL("ALTER {} {} OWNER TO {}").format(
                    SQL(kinds[kind]), Identifier("public", name), Identifier(settings.phoenix_user)
                )
            )
        enums = connection.execute(
            """
            SELECT typname FROM pg_type WHERE typnamespace = 'public'::regnamespace AND typtype = 'e'
              AND typowner = (SELECT oid FROM pg_roles WHERE rolname = %s)
        """,
            (settings.user,),
        ).fetchall()
        for (name,) in enums:
            connection.execute(
                SQL("ALTER TYPE {} OWNER TO {}").format(Identifier("public", name), Identifier(settings.phoenix_user))
            )


def _grant_runtime(settings: DatabaseSettings) -> None:
    """Grant data operations while keeping migration/version records read-only."""
    role = Identifier(settings.runtime_user)
    with psycopg.connect(database_saq_dsn(settings)) as connection:
        connection.execute(SQL("GRANT CONNECT ON DATABASE {} TO {}").format(Identifier(settings.database), role))
        connection.execute(SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
        connection.execute(
            SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(role)
        )
        connection.execute(SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(role))
        for table in (DB_MIGRATION_VERSION_TABLE, "saq_versions"):
            connection.execute(
                SQL("REVOKE INSERT, UPDATE, DELETE ON TABLE {} FROM {}").format(Identifier("public", table), role)
            )


async def _initialize_saq(settings: DatabaseSettings) -> None:
    queue = PostgresQueue(url=database_saq_dsn(settings))
    try:
        await queue.pool.open()
        await queue.init_db()
    finally:
        await queue.pool.close()


async def _verify_runtime(settings: DatabaseSettings) -> None:
    """Finish the gate by proving actual runtime credentials and queue schema."""
    queue = RuntimePostgresQueue(url=database_saq_dsn(settings, runtime=True))
    try:
        await queue.pool.open()
        await queue.init_db()
    finally:
        await queue.pool.close()


def bootstrap_database(settings: Settings) -> None:
    """Provision roles, migrate both schemas, then enable bounded runtime access.

    Failure preserves data and prevents the dependent Vessel/Phoenix from starting.
    Existing volumes retain their administrator and database ownership.
    """
    from advanced_alchemy.alembic.commands import AlembicCommands
    from advanced_alchemy.extensions.litestar import AlembicAsyncConfig, SQLAlchemyAsyncConfig

    db = settings.server.database
    try:
        _prepare_databases(db)
        engine = create_db_engine(db)
        config = SQLAlchemyAsyncConfig(
            engine_instance=engine,
            alembic_config=AlembicAsyncConfig(
                version_table_name=DB_MIGRATION_VERSION_TABLE,
                script_config=str(PATH_MIGRATION_CONFIG),
                script_location=str(PATH_MIGRATION_DIR),
            ),
        )
        try:
            AlembicCommands(config).upgrade("head")
        finally:
            asyncio.run(engine.dispose())
        asyncio.run(_initialize_saq(db))
        _grant_runtime(db)
        asyncio.run(_verify_runtime(db))
    except psycopg.Error:
        msg = "Database bootstrap failed; data was preserved. Verify the administrative credential and HBA policy"
        raise RuntimeError(msg) from None
