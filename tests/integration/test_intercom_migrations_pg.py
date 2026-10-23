"""Opt-in actual PostgreSQL0016 lineage, catalog, retention and DDL rollback.

Only LYCHD_INTERCOM_TEST_DATABASE_URL admits an explicitly disposable database.
The public Intercom tables must be empty before destructive empty-schema tests.
"""

from __future__ import annotations

import asyncio
from typing import Any, cast
from uuid import uuid4

import pytest
from advanced_alchemy.alembic.commands import AlembicCommandConfig
from alembic import command, op
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from lychd.config.constants import DB_MIGRATION_VERSION_TABLE, PATH_MIGRATION_DIR
from lychd.db.models.intercom import IntercomPeer
from tests.integration import test_intercom_pg as custody
from tests.integration import test_privacy_disclosure_migrations_pg as existing
from tests.postgres_model_tables import with_referenced_tables

pytestmark = [pytest.mark.integration, pytest.mark.container]
pg_url = custody.pg_url
_TABLES = tuple(sorted(name for name in IntercomPeer.metadata.tables if name.startswith("intercom_")))


def _config(url: str) -> AlembicCommandConfig:
    configuration = AlembicCommandConfig(
        engine=create_async_engine(url),
        version_table_name=DB_MIGRATION_VERSION_TABLE,
        render_as_batch=False,
        compare_type=True,
    )
    configuration.set_main_option("script_location", str(PATH_MIGRATION_DIR))
    return configuration


async def _execute(url: str, statement: str, parameters: dict[str, Any] | None = None) -> list[tuple[Any, ...]]:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            result = await connection.execute(text(statement), parameters or {})
            return list(result.tuples()) if result.returns_rows else []
    finally:
        await engine.dispose()


def _run(url: str, statement: str, parameters: dict[str, Any] | None = None) -> list[tuple[Any, ...]]:
    return asyncio.run(_execute(url, statement, parameters))


def _empty(url: str) -> None:
    for table in _TABLES:
        statement = "SELECT count(*) FROM " + table  # noqa: S608 - exact metadata-owned names
        assert _run(url, statement) == [(0,)], "Disposable Intercom tables must be empty."


def _version(url: str) -> str:
    return cast("str", _run(url, "SELECT version_num FROM lychd_db_version")[0][0])


async def _compare_catalogs(url: str) -> None:
    schema = "intercom_expected_" + uuid4().hex
    engine = create_async_engine(url, execution_options={"schema_translate_map": {None: schema}})
    tables = with_referenced_tables(IntercomPeer.metadata.tables[name] for name in _TABLES)
    created = False
    try:
        async with engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            created = True
            await connection.run_sync(IntercomPeer.metadata.create_all, tables=tables)
        async with engine.connect() as connection:
            for table in _TABLES:
                actual = await existing._catalog(connection, "public", table)  # pyright: ignore[reportPrivateUsage]
                expected = await existing._catalog(connection, schema, table)  # pyright: ignore[reportPrivateUsage]
                # ALTER appends native columns; compare every attribute by logical name.
                actual["columns"] = sorted(actual["columns"])
                expected["columns"] = sorted(expected["columns"])
                assert actual == expected, table
    finally:
        try:
            if created:
                async with engine.begin() as connection:
                    await connection.execute(DropSchema(schema, cascade=True))
        finally:
            await engine.dispose()


def _check_head_compatibility(url: str) -> None:
    """Compare current metadata at head, then restore the historical Intercom boundary."""
    command.upgrade(_config(url), "head")
    try:
        asyncio.run(_compare_catalogs(url))
        command.check(_config(url))
    finally:
        command.downgrade(_config(url), "0016")


def test_late_upgrade_failure_rolls_back_all_seven_tables_and_version(
    pg_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    command.upgrade(_config(pg_url), "0016")
    _empty(pg_url)
    command.downgrade(_config(pg_url), "0015")
    original = op.create_table

    def fail_late(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "intercom_transmission":
            message = "Injected final Intercom DDL failure."
            raise RuntimeError(message)
        return original(name, *args, **kwargs)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(op, "create_table", fail_late)
            with pytest.raises(RuntimeError, match="Injected final Intercom"):
                command.upgrade(_config(pg_url), "0016")
        assert _version(pg_url) == "0015"
        for table in _TABLES:
            assert _run(pg_url, "SELECT to_regclass(:relation)::text", {"relation": "public." + table}) == [(None,)]
    finally:
        command.upgrade(_config(pg_url), "0016")
    _check_head_compatibility(pg_url)


def test_migrated_all_columns_checks_foreign_keys_and_indexes_equal_actual_orm_catalog(pg_url: str) -> None:
    command.upgrade(_config(pg_url), "head")
    try:
        asyncio.run(_compare_catalogs(pg_url))
        foreign = _run(
            pg_url,
            """SELECT c.relname,k.confdeltype::text FROM pg_constraint k
JOIN pg_class c ON c.oid=k.conrelid WHERE c.relname LIKE 'intercom_%' AND k.contype='f'""",
        )
        assert foreign
        assert all(action == "r" for _, action in foreign)
        command.check(_config(pg_url))
    finally:
        command.downgrade(_config(pg_url), "0016")


@pytest.mark.parametrize("owner", ["capacity", "peer"])
def test_even_uncharged_capacity_or_peer_alone_refuses_downgrade(pg_url: str, owner: str) -> None:
    command.upgrade(_config(pg_url), "0016")
    _empty(pg_url)
    identity = str(uuid4())
    table = "intercom_" + owner
    if owner == "capacity":
        statement = """INSERT INTO intercom_capacity
(id,scope,scope_id,uses_limit,application_limit,network_limit,uses_charged,application_charged,network_charged,created_at,updated_at)
VALUES(CAST(:id AS uuid),'host','host',0,0,0,0,0,0,now(),now())"""
    else:
        statement = """INSERT INTO intercom_peer
(id,enrollment,enrollment_digest,key_version,policy_generation,revocation_generation,revoked,policy,created_at,updated_at)
VALUES(CAST(:id AS uuid),'{}',repeat('a',64),1,1,0,false,'{}',now(),now())"""
    _run(pg_url, statement, {"id": identity})
    try:
        with pytest.raises(DBAPIError, match="Retained Intercom custody prevents downgrade"):
            command.downgrade(_config(pg_url), "0015")
        assert _version(pg_url) == "0016"
        statement = "SELECT count(*) FROM " + table + " WHERE id=CAST(:id AS uuid)"  # noqa: S608 - two fixed owner tables
        assert _run(pg_url, statement, {"id": identity}) == [(1,)]
        for name in _TABLES:
            assert _run(pg_url, "SELECT to_regclass(:relation)::text", {"relation": "public." + name}) == [(name,)]
    finally:
        statement = "DELETE FROM " + table + " WHERE id=CAST(:id AS uuid)"  # noqa: S608 - two fixed owner tables
        _run(pg_url, statement, {"id": identity})


def test_empty_downgrade_locks_all_seven_tables_before_custody_check_then_round_trips(
    pg_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    command.upgrade(_config(pg_url), "0016")
    _empty(pg_url)
    original = op.execute
    observed: list[str] = []

    def observe(statement: Any, *args: Any, **kwargs: Any) -> Any:
        if "DO $$" in str(statement):
            rows = (
                op.get_bind()
                .execute(
                    text("""SELECT c.relname FROM pg_locks l JOIN pg_class c ON c.oid=l.relation
WHERE c.relname LIKE 'intercom_%' AND l.mode='AccessExclusiveLock' AND l.granted
AND l.pid=pg_backend_pid() ORDER BY c.relname""")
                )
                .scalars()
                .all()
            )
            observed.extend(cast("list[str]", list(rows)))
        return original(statement, *args, **kwargs)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(op, "execute", observe)
            command.downgrade(_config(pg_url), "0015")
        assert observed == list(_TABLES)
        assert _version(pg_url) == "0015"
    finally:
        command.upgrade(_config(pg_url), "0016")
    _check_head_compatibility(pg_url)


def test_catalog_oracle_detects_missing_real_check_then_restores_empty_schema(pg_url: str) -> None:
    command.upgrade(_config(pg_url), "head")
    _empty(pg_url)
    _run(pg_url, "ALTER TABLE intercom_capacity DROP CONSTRAINT ck_intercom_capacity_uses")
    try:
        with pytest.raises(AssertionError, match="intercom_capacity"):
            asyncio.run(_compare_catalogs(pg_url))
    finally:
        command.downgrade(_config(pg_url), "0015")
        command.upgrade(_config(pg_url), "0016")
