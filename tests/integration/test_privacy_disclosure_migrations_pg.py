"""Opt-in transactional disclosure DDL, schema parity and retained-custody law.

LYCHD_PRIVACY_TEST_DATABASE_URL selects an externally supplied disposable database;
the explicit container profile otherwise supplies a bounded PostgreSQL container.
Only explicitly inserted synthetic rows are deleted during cleanup.
"""

from __future__ import annotations

import asyncio
from typing import Any, cast
from uuid import uuid4

import pytest
from advanced_alchemy.alembic.commands import AlembicCommandConfig
from alembic import command, op
from sqlalchemy import Table, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from lychd.config.constants import DB_MIGRATION_VERSION_TABLE, PATH_MIGRATION_DIR
from lychd.db.models import Consent, Run, RunDelivery, Session
from lychd.db.models.privacy import DisclosureCapacityRecord, DisclosureTransmission
from tests.integration import test_privacy_disclosure_pg as disclosure
from tests.postgres_model_tables import with_referenced_tables

pytestmark = [pytest.mark.integration, pytest.mark.container]
pg_url = disclosure.pg_url

_CAPACITY_INSERT = """INSERT INTO privacy_disclosure_capacity
(id,scope,scope_id,configuration_digest,uses_limit,bytes_limit,uses_charged,bytes_charged,created_at,updated_at)
VALUES (CAST(:id AS uuid),'host','host',repeat('a',64),1,4096,0,0,now(),now())"""


def _config(url: str) -> AlembicCommandConfig:
    configuration = AlembicCommandConfig(
        engine=create_async_engine(url),
        version_table_name=DB_MIGRATION_VERSION_TABLE,
        render_as_batch=False,
        compare_type=True,
    )
    configuration.set_main_option("script_location", str(PATH_MIGRATION_DIR))
    return configuration


async def _execute(url: str, statement: str, parameters: dict[str, Any] | None) -> list[tuple[Any, ...]]:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            result = await connection.execute(text(statement), parameters or {})
            return list(result.tuples()) if result.returns_rows else []
    finally:
        await engine.dispose()


def _run(url: str, statement: str, parameters: dict[str, Any] | None = None) -> list[tuple[Any, ...]]:
    return asyncio.run(_execute(url, statement, parameters))


def _version_and_tables(url: str) -> list[tuple[Any, ...]]:
    return _run(
        url,
        """SELECT version_num,to_regclass('public.privacy_disclosure_capacity')::text,
to_regclass('public.privacy_disclosure_transmission')::text FROM lychd_db_version""",
    )


def _check_head_compatibility(url: str) -> None:
    """Compare current metadata at head, then restore this revision's test boundary."""
    command.upgrade(_config(url), "head")
    try:
        command.check(_config(url))
    finally:
        command.downgrade(_config(url), "0015")


def test_upgrade_late_failure_rolls_back_both_ddl_and_version_then_empty_round_trip_matches_orm(
    pg_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    command.upgrade(_config(pg_url), "0014")
    original = op.create_table

    def fail_late(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "privacy_disclosure_transmission":
            message = "Injected late disclosure DDL failure."
            raise RuntimeError(message)
        return original(name, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(op, "create_table", fail_late)
        with pytest.raises(RuntimeError, match="Injected late disclosure"):
            command.upgrade(_config(pg_url), "0015")
    assert _version_and_tables(pg_url) == [("0014", None, None)]
    command.upgrade(_config(pg_url), "0015")
    _check_head_compatibility(pg_url)
    assert _version_and_tables(pg_url) == [("0015", "privacy_disclosure_capacity", "privacy_disclosure_transmission")]
    for model in (DisclosureCapacityRecord, DisclosureTransmission):
        columns = _run(
            pg_url,
            """SELECT column_name,is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name=:table""",
            {"table": model.__tablename__},
        )
        assert dict(columns) == {column.name: "YES" if column.nullable else "NO" for column in model.__table__.columns}
    assert _run(
        pg_url,
        """SELECT conname,confdeltype::text FROM pg_constraint
WHERE conrelid='privacy_disclosure_transmission'::regclass AND contype='f' ORDER BY conname""",
    ) == [
        ("fk_privacy_disclosure_transmission_delivery_id_run_delivery", "r"),
        ("fk_privacy_disclosure_transmission_run_id_run", "r"),
    ]
    command.downgrade(_config(pg_url), "0014")
    assert _version_and_tables(pg_url) == [("0014", None, None)]
    command.upgrade(_config(pg_url), "0015")
    _check_head_compatibility(pg_url)


def test_even_uncharged_capacity_alone_refuses_downgrade_without_erasing_either_table(pg_url: str) -> None:
    command.upgrade(_config(pg_url), "0015")
    identity = str(uuid4())
    _run(pg_url, _CAPACITY_INSERT, {"id": identity})
    try:
        assert _run(pg_url, "SELECT count(*) FROM privacy_disclosure_transmission") == [(0,)]
        with pytest.raises(DBAPIError, match="Retained disclosure custody prevents downgrade"):
            command.downgrade(_config(pg_url), "0014")
        assert _version_and_tables(pg_url) == [
            ("0015", "privacy_disclosure_capacity", "privacy_disclosure_transmission")
        ]
        assert _run(
            pg_url,
            "SELECT scope,uses_charged,bytes_charged FROM privacy_disclosure_capacity WHERE id=CAST(:id AS uuid)",
            {"id": identity},
        ) == [("host", 0, 0)]
    finally:
        _run(pg_url, "DELETE FROM privacy_disclosure_capacity WHERE id=CAST(:id AS uuid)", {"id": identity})


def _retained_transmission(pg_url: str) -> dict[str, str]:
    values = {
        name: str(uuid4())
        for name in ("run", "delivery", "transmission", "request", "occurrence", "attempt", "claim", "receipt")
    }
    _run(
        pg_url,
        """INSERT INTO run
(id,workflow_name,pattern_manifest,source,status,sigil_name,intent,queue_name,created_at,updated_at)
VALUES (CAST(:run AS uuid),'synthetic-disclosure','{}','cli','running','fixture','{}','runs',now(),now())""",
        values,
    )
    _run(
        pg_url,
        """INSERT INTO run_delivery
(id,run_id,enqueue_seq,queue_name,priority,state,claimed_at,created_at,updated_at)
VALUES (CAST(:delivery AS uuid),CAST(:run AS uuid),0,'runs',50,'claimed',now(),now(),now())""",
        values,
    )
    _run(
        pg_url,
        """INSERT INTO privacy_disclosure_transmission
(id,request_id,run_id,delivery_id,occurrence_id,attempt_id,preparation_bytes,preparation_digest,status,created_at,updated_at)
VALUES (CAST(:transmission AS uuid),CAST(:request AS uuid),CAST(:run AS uuid),CAST(:delivery AS uuid),
CAST(:occurrence AS uuid),CAST(:attempt AS uuid),decode('00','hex'),repeat('a',64),'prepared',now(),now())""",
        values,
    )
    return values


def test_transmission_alone_in_every_disposition_refuses_downgrade_and_restricts_both_owners(pg_url: str) -> None:
    command.upgrade(_config(pg_url), "0015")
    values = _retained_transmission(pg_url)
    try:
        assert _run(pg_url, "SELECT count(*) FROM privacy_disclosure_capacity") == [(0,)]
        for state in ("prepared", "claimed", "recorded", "refused", "unknown"):
            if state != "prepared":
                _run(
                    pg_url,
                    """UPDATE privacy_disclosure_transmission
SET status=:state,claim_id=CAST(:claim AS uuid),claimed_at=now(),decision_bytes=decode('00','hex'),
receipt_id=CAST(:terminal_receipt AS uuid),settlement_bytes=CASE WHEN :terminal THEN decode('00','hex') ELSE NULL END
WHERE id=CAST(:transmission AS uuid)""",
                    {
                        **values,
                        "state": state,
                        "terminal": state in {"recorded", "refused"},
                        "terminal_receipt": values["receipt"] if state in {"recorded", "refused"} else None,
                    },
                )
            with pytest.raises(DBAPIError, match="Retained disclosure custody prevents downgrade"):
                command.downgrade(_config(pg_url), "0014")
            assert _version_and_tables(pg_url) == [
                ("0015", "privacy_disclosure_capacity", "privacy_disclosure_transmission")
            ]
            assert _run(
                pg_url,
                "SELECT status FROM privacy_disclosure_transmission WHERE id=CAST(:transmission AS uuid)",
                values,
            ) == [(state,)]
        with pytest.raises(DBAPIError, match="foreign key constraint"):
            _run(pg_url, "DELETE FROM run_delivery WHERE id=CAST(:delivery AS uuid)", values)
        with pytest.raises(DBAPIError, match="foreign key constraint"):
            _run(pg_url, "DELETE FROM run WHERE id=CAST(:run AS uuid)", values)
    finally:
        _run(pg_url, "DELETE FROM privacy_disclosure_transmission WHERE id=CAST(:transmission AS uuid)", values)
        _run(pg_url, "DELETE FROM run_delivery WHERE id=CAST(:delivery AS uuid)", values)
        _run(pg_url, "DELETE FROM run WHERE id=CAST(:run AS uuid)", values)


def test_downgrade_holds_both_access_exclusive_locks_before_testing_custody(
    pg_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    command.upgrade(_config(pg_url), "0015")
    original = op.execute
    observations: list[tuple[str, str]] = []

    def observe(statement: Any, *args: Any, **kwargs: Any) -> Any:
        if "DO $$" in str(statement):
            rows = (
                op.get_bind()
                .execute(
                    text("""SELECT c.relname,l.mode FROM pg_locks l JOIN pg_class c ON c.oid=l.relation
WHERE c.relname IN ('privacy_disclosure_capacity','privacy_disclosure_transmission')
AND l.mode='AccessExclusiveLock' AND l.granted AND l.pid=pg_backend_pid() ORDER BY c.relname""")
                )
                .tuples()
                .all()
            )
            observations.extend(cast("list[tuple[str, str]]", list(rows)))
        return original(statement, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(op, "execute", observe)
        command.downgrade(_config(pg_url), "0014")
    assert observations == [
        ("privacy_disclosure_capacity", "AccessExclusiveLock"),
        ("privacy_disclosure_transmission", "AccessExclusiveLock"),
    ]
    assert _version_and_tables(pg_url) == [("0014", None, None)]
    command.upgrade(_config(pg_url), "0015")
    _check_head_compatibility(pg_url)


async def _catalog(connection: AsyncConnection, schema: str, table: str) -> dict[str, list[tuple[Any, ...]]]:
    statements = {
        "columns": """SELECT a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,
pg_get_expr(d.adbin,d.adrelid),a.attidentity::text,a.attgenerated::text
FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
WHERE a.attrelid=to_regclass(:relation) AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum""",
        "constraints": """SELECT conname,contype::text,pg_get_constraintdef(oid,true)
FROM pg_constraint WHERE conrelid=to_regclass(:relation) ORDER BY conname""",
        "indexes": """SELECT c.relname,i.indisunique,i.indisprimary,pg_get_indexdef(i.indexrelid)
FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
WHERE i.indrelid=to_regclass(:relation) ORDER BY c.relname""",
    }
    result: dict[str, list[tuple[Any, ...]]] = {}
    for kind, statement in statements.items():
        rows = (await connection.execute(text(statement), {"relation": f"{schema}.{table}"})).tuples().all()
        result[kind] = [
            tuple(value.replace(f"{schema}.", "") if isinstance(value, str) else value for value in row) for row in rows
        ]
    return result


async def _compare_catalogs(url: str) -> None:
    schema = "disclosure_expected_" + uuid4().hex
    engine = create_async_engine(url, execution_options={"schema_translate_map": {None: schema}})
    tables = cast(
        "list[Table]",
        [
            Session.__table__,
            Run.__table__,
            Consent.__table__,
            RunDelivery.__table__,
            DisclosureCapacityRecord.__table__,
            DisclosureTransmission.__table__,
        ],
    )
    tables = with_referenced_tables(tables)
    created = False
    try:
        async with engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            await connection.run_sync(Run.metadata.create_all, tables=tables)
            created = True
        async with engine.connect() as connection:
            for model in (DisclosureCapacityRecord, DisclosureTransmission):
                table = model.__tablename__
                assert table is not None
                actual = await _catalog(connection, "public", table)
                expected = await _catalog(connection, schema, table)
                assert actual == expected, table
    finally:
        try:
            if created:
                async with engine.begin() as connection:
                    await connection.execute(DropSchema(schema, cascade=True))
        finally:
            await engine.dispose()


def test_migrated_columns_checks_foreign_keys_and_indexes_match_orm_catalog(pg_url: str) -> None:
    command.upgrade(_config(pg_url), "head")
    try:
        asyncio.run(_compare_catalogs(pg_url))
    finally:
        command.downgrade(_config(pg_url), "0015")


def test_catalog_comparison_detects_a_missing_check_constraint(pg_url: str) -> None:
    command.upgrade(_config(pg_url), "head")
    assert _run(
        pg_url,
        "SELECT (SELECT count(*) FROM privacy_disclosure_capacity), (SELECT count(*) FROM privacy_disclosure_transmission)",
    ) == [(0, 0)]
    _run(pg_url, "ALTER TABLE privacy_disclosure_capacity DROP CONSTRAINT ck_privacy_disclosure_capacity_uses_ceiling")
    try:
        with pytest.raises(AssertionError, match="privacy_disclosure_capacity"):
            asyncio.run(_compare_catalogs(pg_url))
    finally:
        # Restore only this empty, disposable proof schema from the migration.
        command.downgrade(_config(pg_url), "0014")
        command.upgrade(_config(pg_url), "0015")
