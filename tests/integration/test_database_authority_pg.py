"""Disposable PostgreSQL proof of production authentication and role separation."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from contextlib import suppress
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
import pytest
from psycopg.sql import SQL, Identifier
from pydantic import SecretStr
from sqlalchemy import text

from lychd.config.settings.root import Settings
from lychd.config.settings.server import DatabaseSettings, ServerSettings
from lychd.db.authority import RuntimePostgresQueue
from lychd.db.bootstrap import bootstrap_database
from lychd.db.factory import create_db_engine, database_saq_dsn

pytestmark = [pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def database(tmp_path_factory: pytest.TempPathFactory) -> Generator[Settings]:
    """Use the exact generated HBA and real bootstrap against one disposable image."""
    pytest.importorskip("testcontainers")
    from testcontainers.community.postgres import PostgresContainer

    hba = tmp_path_factory.mktemp("database-authority") / "pg_hba.conf"
    template = Path(__file__).parents[2] / "src/lychd/system/templates/pg_hba_v1.conf.jinja"
    hba.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    hba.chmod(0o644)
    postgres = PostgresContainer("docker.io/pgvector/pgvector:pg18-trixie", driver="asyncpg")
    postgres.with_env("POSTGRES_INITDB_ARGS", "--auth-host=scram-sha-256")
    postgres.with_volume_mapping(str(hba), "/etc/lychd-pg_hba.conf", "ro,Z")
    postgres.with_command("postgres -c hba_file=/etc/lychd-pg_hba.conf -c password_encryption=scram-sha-256")
    try:
        postgres.start()
    except Exception as error:
        with suppress(Exception):
            stdout, stderr = postgres.get_logs()
            log_path = hba.with_name("postgres-startup.log")
            log_path.write_bytes(stdout + b"\n" + stderr)
            error.add_note(f"Disposable PostgreSQL startup log: {log_path}")
        with suppress(Exception):
            postgres.stop()
        raise
    try:
        url = urlsplit(postgres.get_connection_url())
        settings = Settings(
            server=ServerSettings(
                database=DatabaseSettings(
                    host=url.hostname or "localhost",
                    port=url.port or 5432,
                    user=unquote(url.username or "test"),
                    database=url.path.lstrip("/"),
                    password=SecretStr(unquote(url.password or "test")),
                    runtime_password=SecretStr("synthetic-runtime-db-password"),
                    phoenix_password=SecretStr("synthetic-phoenix-db-password"),
                )
            )
        )
        with psycopg.connect(database_saq_dsn(settings.server.database)) as connection:
            connection.execute("CREATE TABLE public.security_receipt_probe(id integer PRIMARY KEY, value text)")
            connection.execute("INSERT INTO public.security_receipt_probe VALUES (1, 'preserved')")
        bootstrap_database(settings)
        yield settings
    finally:
        postgres.stop()


def test_tcp_requires_password_and_runtime_cannot_gain_cluster_or_schema_authority(database: Settings) -> None:
    db = database.server.database
    dsn = database_saq_dsn(db, runtime=True)
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(dsn, password="", passfile="/dev/null", connect_timeout=3)
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(dsn, password="incorrect", passfile="/dev/null", connect_timeout=3)  # noqa: S106 - denial probe
    for statement in (
        "CREATE TABLE public.forbidden(id integer)",
        "CREATE ROLE forbidden SUPERUSER",
        "ALTER ROLE lychd_runtime SUPERUSER",
        "UPDATE saq_versions SET version = 0",
    ):
        with psycopg.connect(dsn, autocommit=True) as connection, pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(statement)
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(dsn, dbname="phoenix", connect_timeout=3)
    assert db.phoenix_password is not None
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(dsn, user=db.phoenix_user, password=db.phoenix_password.get_secret_value(), connect_timeout=3)


def test_bootstrap_repeat_preserves_data_and_runtime_sqlalchemy_and_saq_work(database: Settings) -> None:
    db = database.server.database
    bootstrap_database(database)
    bootstrap_database(database)

    async def exercise_runtime() -> None:
        engine = create_db_engine(db, runtime=True)
        try:
            async with engine.begin() as connection:
                assert (
                    await connection.execute(text("SELECT value FROM security_receipt_probe WHERE id=1"))
                ).scalar_one() == "preserved"
                await connection.execute(text("INSERT INTO security_receipt_probe VALUES (2, 'runtime')"))
                await connection.execute(text("UPDATE security_receipt_probe SET value='changed' WHERE id=2"))
                await connection.execute(text("DELETE FROM security_receipt_probe WHERE id=2"))
        finally:
            await engine.dispose()
        queue = RuntimePostgresQueue(url=database_saq_dsn(db, runtime=True), name="security-receipt")
        try:
            await queue.connect()
            job = await queue.enqueue("synthetic_receipt", key="authority-receipt")
            assert job is not None
            assert await queue.job(job.key) is not None
        finally:
            await queue.disconnect()

    asyncio.run(exercise_runtime())


def test_unrelated_existing_phoenix_owner_and_role_credentials_are_preserved(database: Settings) -> None:
    db = database.server.database
    with psycopg.connect(database_saq_dsn(db), autocommit=True) as connection:
        connection.execute("CREATE ROLE unrelated_owner")
        connection.execute("ALTER DATABASE phoenix OWNER TO unrelated_owner")
        before = connection.execute("SELECT rolpassword FROM pg_authid WHERE rolname='lychd_runtime'").fetchone()
        try:
            with pytest.raises(ValueError, match="unrelated owner"):
                bootstrap_database(database)
            assert connection.execute(
                "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='phoenix'"
            ).fetchone() == ("unrelated_owner",)
            assert (
                connection.execute("SELECT rolpassword FROM pg_authid WHERE rolname='lychd_runtime'").fetchone()
                == before
            )
            assert connection.execute("SELECT value FROM security_receipt_probe WHERE id=1").fetchone() == (
                "preserved",
            )
        finally:
            connection.execute("ALTER DATABASE phoenix OWNER TO lychd_phoenix")
            connection.execute("DROP ROLE unrelated_owner")


@pytest.mark.parametrize(
    ("grant", "revoke"),
    [
        (SQL("GRANT CREATE ON SCHEMA public TO {role}"), SQL("REVOKE CREATE ON SCHEMA public FROM {role}")),
        (
            SQL("ALTER TABLE security_receipt_probe OWNER TO {role}"),
            SQL("ALTER TABLE security_receipt_probe OWNER TO {owner}"),
        ),
        (SQL("ALTER SCHEMA public OWNER TO {role}"), SQL("ALTER SCHEMA public OWNER TO {schema_owner}")),
        (SQL("ALTER DATABASE {database} OWNER TO {role}"), SQL("ALTER DATABASE {database} OWNER TO {owner}")),
    ],
    ids=["direct-schema-create", "table-ownership", "schema-ownership", "database-ownership"],
)
def test_unsafe_runtime_refusal_preserves_credentials_and_rolls_back_public_repair(
    database: Settings, grant: SQL, revoke: SQL
) -> None:
    """A failed gate cannot rotate secrets or commit even the admitted PUBLIC repair."""
    db = database.server.database
    with psycopg.connect(database_saq_dsn(db), autocommit=True) as connection:
        schema_owner = connection.execute(
            "SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='public'"
        ).fetchone()
        assert schema_owner is not None
        identities = {
            "role": Identifier(db.runtime_user),
            "owner": Identifier(db.user),
            "database": Identifier(db.database),
            "schema_owner": Identifier(schema_owner[0]),
        }
        connection.execute(grant.format(**identities))
        connection.execute("GRANT CREATE ON SCHEMA public TO PUBLIC")
        credentials = connection.execute(
            "SELECT rolname, rolpassword FROM pg_authid WHERE rolname IN (%s, %s) ORDER BY rolname",
            (db.runtime_user, db.phoenix_user),
        ).fetchall()
        schema_acl = connection.execute("SELECT nspacl FROM pg_namespace WHERE nspname='public'").fetchone()
        try:
            with pytest.raises(ValueError, match="runtime role; preserved unchanged"):
                bootstrap_database(database)
            assert (
                connection.execute(
                    "SELECT rolname, rolpassword FROM pg_authid WHERE rolname IN (%s, %s) ORDER BY rolname",
                    (db.runtime_user, db.phoenix_user),
                ).fetchall()
                == credentials
            )
            assert connection.execute("SELECT nspacl FROM pg_namespace WHERE nspname='public'").fetchone() == schema_acl
            assert connection.execute("SELECT value FROM security_receipt_probe WHERE id=1").fetchone() == (
                "preserved",
            )
        finally:
            connection.execute(revoke.format(**identities))
            connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")


def test_bootstrap_repairs_legacy_public_create_without_rejecting_runtime(database: Settings) -> None:
    """PUBLIC's old grant is remediable; it is not a direct runtime role privilege."""
    db = database.server.database
    with psycopg.connect(database_saq_dsn(db), autocommit=True) as connection:
        connection.execute("GRANT CREATE ON SCHEMA public TO PUBLIC")
        try:
            bootstrap_database(database)
            assert connection.execute(
                "SELECT has_schema_privilege(%s, 'public', 'CREATE')", (db.runtime_user,)
            ).fetchone() == (False,)
            assert connection.execute("SELECT value FROM security_receipt_probe WHERE id=1").fetchone() == (
                "preserved",
            )
        finally:
            connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
