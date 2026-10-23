"""Actual0017 PostgreSQL schema, ownership audit, rollback and retained evidence.

Only the explicit disposable Intercom test URL admits these destructive empty
schema checks. Metadata creates the expected catalog oracle, never the migrated
application schema. Column comparison is by name because ALTER appends fields.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest
from advanced_alchemy.base import orm_registry
from alembic import command, op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import AddConstraint, CreateSchema, DropSchema

from tests.integration import test_intercom_migrations_pg as previous
from tests.integration import test_privacy_disclosure_migrations_pg as catalog

pytestmark = [pytest.mark.integration, pytest.mark.container]
pg_url = previous.pg_url
_config = previous._config  # pyright: ignore[reportPrivateUsage] - same explicit disposable lineage
_run = previous._run  # pyright: ignore[reportPrivateUsage]
_version = previous._version  # pyright: ignore[reportPrivateUsage]


def _empty(url: str) -> None:
    assert _run(url, 'SELECT count(*) FROM "run"') == [(0,)]
    previous._empty(url)  # pyright: ignore[reportPrivateUsage]


async def _compare_catalogs(url: str) -> None:
    schema = "native_peer_expected_" + uuid4().hex
    engine = create_async_engine(url, execution_options={"schema_translate_map": {None: schema}})
    created = False
    try:
        async with engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            created = True
            # The current Run FK has a deliberate cycle through native peer tasks;
            # the expected oracle admits its complete metadata dependency closure.
            await connection.run_sync(orm_registry.metadata.create_all)
        async with engine.connect() as connection:
            for table in ("run", "intercom_task"):
                actual = await catalog._catalog(connection, "public", table)  # pyright: ignore[reportPrivateUsage]
                expected = await catalog._catalog(connection, schema, table)  # pyright: ignore[reportPrivateUsage]
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


def _seed_run(url: str, *, source: str = "cli", status: str = "running", intent: str = "{}") -> str:
    identity = str(uuid4())
    _run(
        url,
        """INSERT INTO run
(id,workflow_name,source,status,priority,sigil_name,intent,pattern_manifest,queue_name,attempt,enqueue_seq,created_at,updated_at)
VALUES(CAST(:id AS uuid),'migration-proof',:source,:status,50,'test:operator',CAST(:intent AS jsonb),
'{}','runs',0,0,now(),now())""",
        {"id": identity, "source": source, "status": status, "intent": intent},
    )
    return identity


def _seed_custody(url: str) -> dict[str, str]:
    ids = {key: str(uuid4()) for key in ("peer", "declaration", "operation", "task")}
    _run(
        url,
        """INSERT INTO intercom_peer
(id,enrollment,enrollment_digest,key_version,policy_generation,revocation_generation,revoked,policy,created_at,updated_at)
VALUES(CAST(:peer AS uuid),'{}',repeat('a',64),1,1,0,false,'{}',now(),now())""",
        ids,
    )
    _run(
        url,
        """INSERT INTO intercom_declaration
(id,peer_id,operation_id,policy_generation,record,record_digest,created_at,updated_at)
VALUES(CAST(:declaration AS uuid),CAST(:peer AS uuid),CAST(:operation AS uuid),1,'{}',repeat('b',64),now(),now())""",
        ids,
    )
    _run(
        url,
        """INSERT INTO intercom_task
(id,peer_id,declaration_id,operation_id,purpose,task_schema,expires_at,policy_generation,key_version,
revocation_generation,record,record_digest,local_status,created_at,updated_at)
VALUES(CAST(:task AS uuid),CAST(:peer AS uuid),CAST(:declaration AS uuid),CAST(:operation AS uuid),
'migration-proof','public-text@1',now()+interval '1 hour',1,1,0,'{}',repeat('c',64),'prepared',now(),now())""",
        ids,
    )
    return ids


def _delete_custody(url: str, ids: dict[str, str]) -> None:
    _run(url, "DELETE FROM intercom_task WHERE id=CAST(:task AS uuid)", ids)
    _run(url, "DELETE FROM intercom_declaration WHERE id=CAST(:declaration AS uuid)", ids)
    _run(url, "DELETE FROM intercom_peer WHERE id=CAST(:peer AS uuid)", ids)


def test_native_migration_matches_actual_orm_columns_checks_indexes_and_foreign_keys(pg_url: str) -> None:
    command.upgrade(_config(pg_url), "0017")
    asyncio.run(_compare_catalogs(pg_url))
    command.check(_config(pg_url))


def test_late_native_upgrade_failure_rolls_back_columns_constraints_and_version(
    pg_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    command.upgrade(_config(pg_url), "0017")
    _empty(pg_url)
    command.downgrade(_config(pg_url), "0016")
    original = op.create_check_constraint

    def fail_late(name: Any, *args: Any, **kwargs: Any) -> Any:
        if str(name) == "ck_run_waiting_peer_owner":
            message = "Injected final native peer DDL failure"
            raise RuntimeError(message)
        return original(name, *args, **kwargs)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(op, "create_check_constraint", fail_late)
            with pytest.raises(RuntimeError, match="Injected final native"):
                command.upgrade(_config(pg_url), "0017")
        assert _version(pg_url) == "0016"
        assert (
            _run(
                pg_url,
                """SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND ((table_name='run' AND column_name='peer_task_id')
OR (table_name='intercom_task' AND column_name LIKE 'native_%'))""",
            )
            == []
        )
    finally:
        command.upgrade(_config(pg_url), "0017")


@pytest.mark.parametrize("invalid", ["multiple", "ownerless", "unexplained-peer"])
def test_upgrade_refuses_ambiguous_legacy_ownership_without_inference(pg_url: str, invalid: str) -> None:
    command.upgrade(_config(pg_url), "0017")
    _empty(pg_url)
    command.downgrade(_config(pg_url), "0016")
    identity = _seed_run(pg_url, status="awaiting_delegate" if invalid == "ownerless" else "running")
    consent = str(uuid4())
    try:
        if invalid == "multiple":
            _run(
                pg_url,
                """INSERT INTO consent
(id,run_id,tool_name,tool_call_id,payload,status,created_at,updated_at)
VALUES(CAST(:consent AS uuid),CAST(:id AS uuid),'proof','proof','{}','pending',now(),now())""",
                {"id": identity, "consent": consent},
            )
            _run(
                pg_url,
                "UPDATE run SET consent_id=CAST(:consent AS uuid),delegated_job_id='legacy-job' WHERE id=CAST(:id AS uuid)",
                {"id": identity, "consent": consent},
            )
        elif invalid == "unexplained-peer":
            _run(pg_url, "UPDATE run SET source='peer_public' WHERE id=CAST(:id AS uuid)", {"id": identity})
        with pytest.raises(DBAPIError, match="Native peer migration"):
            command.upgrade(_config(pg_url), "0017")
        assert _version(pg_url) == "0016"
        assert _run(pg_url, "SELECT count(*) FROM run WHERE id=CAST(:id AS uuid)", {"id": identity}) == [(1,)]
    finally:
        _run(pg_url, "UPDATE run SET consent_id=NULL WHERE id=CAST(:id AS uuid)", {"id": identity})
        _run(pg_url, "DELETE FROM consent WHERE id=CAST(:consent AS uuid)", {"consent": consent})
        _run(pg_url, "DELETE FROM run WHERE id=CAST(:id AS uuid)", {"id": identity})
        command.upgrade(_config(pg_url), "0017")


@pytest.mark.parametrize("retained", ["admission", "native-task", "closure", "reauthorization"])
def test_downgrade_refuses_every_retained_native_history_even_after_terminal_run(pg_url: str, retained: str) -> None:
    command.upgrade(_config(pg_url), "0017")
    _empty(pg_url)
    run_id = _seed_run(pg_url, source="peer_public" if retained == "admission" else "cli", status="done")
    ids = None
    try:
        if retained != "admission":
            ids = _seed_custody(pg_url)
            if retained == "native-task":
                _run(
                    pg_url,
                    """UPDATE intercom_task SET native_run_id=CAST(:run AS uuid),native_station='peer_wait',
native_request_id=CAST(:operation AS uuid),native_binding_digest=repeat('d',64),native_pattern_digest=repeat('e',64),
native_enqueue_seq=0,native_step_id='step',native_occurrence_id='occurrence' WHERE id=CAST(:task AS uuid)""",
                    {**ids, "run": run_id},
                )
            elif retained == "closure":
                _run(
                    pg_url,
                    "UPDATE intercom_task SET adoption_closed=true,closure_reason='cancelled' WHERE id=CAST(:task AS uuid)",
                    ids,
                )
            else:
                _run(
                    pg_url,
                    "UPDATE intercom_task SET native_reauthorizations=CAST(:evidence AS jsonb) WHERE id=CAST(:task AS uuid)",
                    {**ids, "evidence": '[{"subject":"test"}]'},
                )
        with pytest.raises(DBAPIError, match="Retained native peer custody"):
            command.downgrade(_config(pg_url), "0016")
        assert _version(pg_url) == "0017"
        assert _run(pg_url, "SELECT count(*) FROM run WHERE id=CAST(:id AS uuid)", {"id": run_id}) == [(1,)]
    finally:
        if ids is not None:
            _delete_custody(pg_url, ids)
        _run(pg_url, "DELETE FROM run WHERE id=CAST(:id AS uuid)", {"id": run_id})


def test_empty_native_downgrade_holds_run_and_task_exclusive_locks_before_guard(
    pg_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    command.upgrade(_config(pg_url), "0017")
    _empty(pg_url)
    original = op.execute
    observed: list[str] = []

    def observe(statement: Any, *args: Any, **kwargs: Any) -> Any:
        if "DO $$" in str(statement):
            rows = (
                op.get_bind()
                .execute(
                    text("""SELECT c.relname FROM pg_locks l JOIN pg_class c ON c.oid=l.relation
WHERE c.relname IN ('run','intercom_task') AND l.mode='AccessExclusiveLock' AND l.granted
AND l.pid=pg_backend_pid() ORDER BY c.relname""")
                )
                .scalars()
                .all()
            )
            observed.extend(rows)
        return original(statement, *args, **kwargs)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(op, "execute", observe)
            command.downgrade(_config(pg_url), "0016")
        assert observed == ["intercom_task", "run"]
        assert _version(pg_url) == "0016"
    finally:
        command.upgrade(_config(pg_url), "0017")


def test_catalog_oracle_detects_missing_actual_peer_owner_check(pg_url: str) -> None:
    command.upgrade(_config(pg_url), "0017")
    _empty(pg_url)
    _run(pg_url, "ALTER TABLE run DROP CONSTRAINT ck_run_single_wait_owner")
    try:
        with pytest.raises(AssertionError, match="run"):
            asyncio.run(_compare_catalogs(pg_url))
    finally:
        constraint = next(
            item for item in orm_registry.metadata.tables["run"].constraints if item.name == "ck_run_single_wait_owner"
        )
        _run(pg_url, str(AddConstraint(constraint).compile(dialect=dialect())))
        command.downgrade(_config(pg_url), "0016")
        command.upgrade(_config(pg_url), "0017")
