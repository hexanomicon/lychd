"""Real PostgreSQL upgrade/refusal/downgrade coverage for the linear schema head."""

# pyright: reportMissingImports=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from advanced_alchemy.alembic.commands import AlembicCommandConfig
from alembic import command
from sqlalchemy import DDL, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from lychd.config.constants import DB_MIGRATION_VERSION_TABLE, PATH_MIGRATION_CONFIG

pytestmark = [pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    """Keep one disposable PostgreSQL container alive for this module."""
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as pg:
        yield pg.get_connection_url()


def _migration_config(url: str) -> AlembicCommandConfig:
    """Build the same async Advanced Alchemy configuration used by the application."""
    engine = create_async_engine(url, poolclass=NullPool)
    return AlembicCommandConfig(
        engine=engine,
        version_table_name=DB_MIGRATION_VERSION_TABLE,
        file_=PATH_MIGRATION_CONFIG,
        render_as_batch=False,
    )


async def _execute(
    url: str,
    statement: str,
    parameters: dict[str, object] | None = None,
) -> list[tuple[object, ...]]:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            result = await connection.execute(text(statement), parameters or {})
            return list(result.tuples()) if result.returns_rows else []
    finally:
        await engine.dispose()


def _run(
    url: str,
    statement: str,
    parameters: dict[str, object] | None = None,
) -> list[tuple[object, ...]]:
    return asyncio.run(_execute(url, statement, parameters))


async def _owned_migration_database(url: str, database: str, *, create: bool) -> None:
    """Create or remove only a generated database on the disposable fixture server."""
    if re.fullmatch(r"delegated_migrations_[0-9a-f]{32}", database) is None:
        msg = "Refusing an unowned migration database name."
        raise ValueError(msg)
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.execute(
                DDL(
                    "CREATE DATABASE %(database)s" if create else "DROP DATABASE %(database)s",
                    context={"database": database},
                )
            )
    finally:
        await engine.dispose()


@pytest.fixture
def delegated_migration_pg_url(pg_url: str) -> Iterator[str]:
    """Isolate delegated receipts from the existing module's retained rows and revision."""
    database = f"delegated_migrations_{uuid4().hex}"
    asyncio.run(_owned_migration_database(pg_url, database, create=True))
    try:
        yield make_url(pg_url).set(database=database).render_as_string(hide_password=False)
    finally:
        asyncio.run(_owned_migration_database(pg_url, database, create=False))


def _insert_delegated_migration_run(url: str, run_id: str) -> None:
    _run(
        url,
        """
        INSERT INTO run (
            id, workflow_name, pattern_manifest, source, status, priority,
            sigil_name, intent, queue_name, attempt, enqueue_seq, created_at, updated_at
        ) VALUES (
            CAST(:run_id AS uuid), 'migration_receipt', '{}'::jsonb, 'bridge', 'done', 70,
            'fixture', '{}'::jsonb, 'runs', 0, 0, now(), now()
        )
        """,
        {"run_id": run_id},
    )


def _insert_delegated_migration_job(
    url: str,
    *,
    run_id: str,
    record_id: str,
    job_id: str,
    status: str,
    result: str | None,
) -> None:
    _run(
        url,
        """
        INSERT INTO delegated_agent_job (
            id, job_id, request_id, run_id, runtime, profile, status,
            request, result, created_at, updated_at
        ) VALUES (
            CAST(:record_id AS uuid), :job_id, :job_id, CAST(:run_id AS uuid),
            'reference', 'read', :status, '{}'::jsonb, CAST(:result AS jsonb), now(), now()
        )
        """,
        {"run_id": run_id, "record_id": record_id, "job_id": job_id, "status": status, "result": result},
    )


def _invalid_delegated_migration_result(case: str, job_id: str, status: str) -> str | None:
    return {
        "sql-null": None,
        "json-null": "null",
        "nonobject": "[]",
        "missing-job": json.dumps({"status": status}),
        "missing-status": json.dumps({"job_id": job_id}),
        "wrong-job": json.dumps({"job_id": "another-job", "status": status}),
        "wrong-status": json.dumps({"job_id": job_id, "status": "running"}),
    }[case]


@pytest.mark.parametrize("status", ["succeeded", "failed", "cancelled", "timed_out", "lost"])
@pytest.mark.parametrize(
    "result_case", ["sql-null", "json-null", "nonobject", "missing-job", "missing-status", "wrong-job", "wrong-status"]
)
def test_delegated_terminal_result_migration_refuses_until_explicit_repair(
    delegated_migration_pg_url: str, status: str, result_case: str
) -> None:
    """0008 preserves legacy terminal rows and its pre-DDL schema on refusal."""
    url = delegated_migration_pg_url
    command.upgrade(_migration_config(url), "0007")
    run_id, record_id = str(uuid4()), str(uuid4())
    job_id = f"migration-{record_id}"
    _insert_delegated_migration_run(url, run_id)
    _insert_delegated_migration_job(
        url,
        run_id=run_id,
        record_id=record_id,
        job_id=job_id,
        status=status,
        result=_invalid_delegated_migration_result(result_case, job_id, status),
    )
    before = _run(
        url,
        """
        SELECT to_jsonb(r), to_jsonb(j), j.result IS NULL
        FROM run r JOIN delegated_agent_job j ON j.run_id = r.id
        WHERE j.id = CAST(:record_id AS uuid)
        """,
        {"record_id": record_id},
    )

    with pytest.raises(DBAPIError, match="requires exact result evidence for terminal delegated jobs"):
        command.upgrade(_migration_config(url), "0008")

    assert _run(url, "SELECT version_num FROM lychd_db_version") == [("0007",)]
    assert _run(
        url,
        """
        SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'run' AND column_name = 'consent_id'
        """,
    ) == [(0,)]
    assert _run(
        url,
        """
        SELECT count(*) FROM pg_constraint
        WHERE conrelid = 'delegated_agent_job'::regclass
          AND conname = 'ck_delegated_agent_job_terminal_result'
        """,
    ) == [(0,)]
    assert (
        _run(
            url,
            """
        SELECT to_jsonb(r), to_jsonb(j), j.result IS NULL
        FROM run r JOIN delegated_agent_job j ON j.run_id = r.id
        WHERE j.id = CAST(:record_id AS uuid)
        """,
            {"record_id": record_id},
        )
        == before
    )

    repaired = {"job_id": job_id, "status": status}
    _run(
        url,
        "UPDATE delegated_agent_job SET result = CAST(:result AS jsonb) WHERE id = CAST(:record_id AS uuid)",
        {"record_id": record_id, "result": json.dumps(repaired)},
    )
    command.upgrade(_migration_config(url), "0008")
    assert _run(url, "SELECT version_num FROM lychd_db_version") == [("0008",)]
    assert _run(
        url,
        """
        SELECT j.job_id, j.status, j.result, r.consent_id
        FROM delegated_agent_job j JOIN run r ON r.id = j.run_id
        WHERE j.id = CAST(:record_id AS uuid)
        """,
        {"record_id": record_id},
    ) == [(job_id, status, repaired, None)]
    command.upgrade(_migration_config(url), "head")
    assert _run(url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
    assert _run(
        url,
        """
        SELECT j.job_id, j.status, j.result, r.consent_id,
               NOT EXISTS (SELECT 1 FROM delegated_host_disposition)
        FROM delegated_agent_job j JOIN run r ON r.id = j.run_id
        WHERE j.id = CAST(:record_id AS uuid)
        """,
        {"record_id": record_id},
    ) == [(job_id, status, repaired, None, True)]


@pytest.mark.parametrize("status", ["succeeded", "failed", "cancelled", "timed_out", "lost"])
@pytest.mark.parametrize(
    "result_case", ["sql-null", "json-null", "nonobject", "missing-job", "missing-status", "wrong-job", "wrong-status"]
)
def test_delegated_terminal_result_constraint_refuses_invalid_head_writes(
    delegated_migration_pg_url: str, status: str, result_case: str
) -> None:
    """Migrated head enforces exact evidence for both INSERT and terminal UPDATE."""
    url = delegated_migration_pg_url
    command.upgrade(_migration_config(url), "head")
    run_id, record_id = str(uuid4()), str(uuid4())
    job_id = f"migration-{record_id}"
    invalid = _invalid_delegated_migration_result(result_case, job_id, status)
    _insert_delegated_migration_run(url, run_id)

    with pytest.raises(DBAPIError, match="ck_delegated_agent_job_terminal_result"):
        _insert_delegated_migration_job(
            url, run_id=run_id, record_id=record_id, job_id=job_id, status=status, result=invalid
        )
    assert _run(url, "SELECT count(*) FROM delegated_agent_job WHERE id = CAST(:id AS uuid)", {"id": record_id}) == [
        (0,)
    ]

    _insert_delegated_migration_job(
        url, run_id=run_id, record_id=record_id, job_id=job_id, status="running", result=None
    )
    row_query = "SELECT to_jsonb(j), j.result IS NULL FROM delegated_agent_job j WHERE id = CAST(:id AS uuid)"
    before = _run(url, row_query, {"id": record_id})
    with pytest.raises(DBAPIError, match="ck_delegated_agent_job_terminal_result"):
        _run(
            url,
            """
            UPDATE delegated_agent_job SET status = :status, result = CAST(:result AS jsonb), updated_at = now()
            WHERE id = CAST(:id AS uuid)
            """,
            {"id": record_id, "status": status, "result": invalid},
        )
    assert _run(url, row_query, {"id": record_id}) == before

    valid = {"job_id": job_id, "status": status}
    _run(
        url,
        """
        UPDATE delegated_agent_job SET status = :status, result = CAST(:result AS jsonb)
        WHERE id = CAST(:id AS uuid)
        """,
        {"id": record_id, "status": status, "result": json.dumps(valid)},
    )
    assert _run(
        url, "SELECT status, result FROM delegated_agent_job WHERE id = CAST(:id AS uuid)", {"id": record_id}
    ) == [(status, valid)]
    assert _run(url, "SELECT version_num FROM lychd_db_version") == [("0017",)]


def test_delegated_empty_migration_cycle_removes_and_restores_tables_and_run_pointer(
    delegated_migration_pg_url: str,
) -> None:
    """An empty 0003 round trip proves schema reversibility, not retained-history safety."""
    url = delegated_migration_pg_url
    command.upgrade(_migration_config(url), "head")
    schema_query = """
        SELECT table_name, column_name, data_type, is_nullable, character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND (table_name IN ('delegated_agent_job', 'delegated_agent_event', 'delegated_host_disposition')
               OR (table_name = 'run' AND column_name = 'delegated_job_id'))
        ORDER BY table_name, ordinal_position
    """
    before = _run(url, schema_query)
    assert {row[0] for row in before} == {
        "delegated_agent_job",
        "delegated_agent_event",
        "delegated_host_disposition",
        "run",
    }
    assert ("run", "delegated_job_id", "character varying", "YES", 128) in before
    assert _run(url, "SELECT count(*) FROM delegated_agent_job") == [(0,)]
    assert _run(url, "SELECT count(*) FROM delegated_agent_event") == [(0,)]
    assert _run(url, "SELECT count(*) FROM delegated_host_disposition") == [(0,)]

    command.downgrade(_migration_config(url), "0002")
    assert _run(
        url,
        """
        SELECT version_num, to_regclass('public.delegated_agent_job')::text,
               to_regclass('public.delegated_agent_event')::text,
               to_regclass('public.ix_run_delegated_job_id')::text
        FROM lychd_db_version
        """,
    ) == [("0002", None, None, None)]
    assert _run(url, schema_query) == []

    command.upgrade(_migration_config(url), "head")
    assert _run(url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
    assert _run(url, schema_query) == before
    assert _run(url, "SELECT to_regclass('public.ix_run_delegated_job_id')::text") == [("ix_run_delegated_job_id",)]


async def _hold_nexus_reader_lock(
    url: str,
    *,
    acquired: threading.Event,
    release: threading.Event,
) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("LOCK TABLE nexus_swap_request IN ACCESS SHARE MODE"))
            acquired.set()
            await asyncio.to_thread(release.wait)
    finally:
        await engine.dispose()


def _wait_for_table_lock(url: str, *, mode: str, granted: bool, table: str = "nexus_swap_request") -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        rows = _run(
            url,
            """
            SELECT count(*)
            FROM pg_locks
            WHERE relation = CAST(:table AS regclass)
              AND mode = :mode
              AND granted = :granted
            """,
            {"mode": mode, "granted": granted, "table": table},
        )
        if rows == [(1,)]:
            return
        time.sleep(0.01)
    msg = f"Timed out waiting for {mode} granted={granted}."
    raise AssertionError(msg)


def test_run_delivery_migration_refuses_ambiguous_work_and_cycles(pg_url: str) -> None:
    """0004 is atomic on refusal and remains reversible after the operator drains work."""
    assert DB_MIGRATION_VERSION_TABLE == "lychd_db_version"
    command.upgrade(_migration_config(pg_url), "0003")
    _run(
        pg_url,
        """
        INSERT INTO run (
            id, workflow_name, pattern_manifest, source, status, priority,
            sigil_name, intent, queue_name, attempt, enqueue_seq, created_at, updated_at
        ) VALUES (
            '00000000-0000-0000-0000-000000000004',
            'bridge_chat',
            '{"schema_version": 1}'::jsonb,
            'bridge',
            'queued',
            70,
            'magus',
            '{}'::jsonb,
            'runs',
            0,
            0,
            now(),
            now()
        )
        """,
    )

    with pytest.raises(DBAPIError, match="nonterminal Runs"):
        command.upgrade(_migration_config(pg_url), "0004")

    refused_state = _run(
        pg_url,
        """
        SELECT version_num, to_regclass('public.run_delivery')::text
        FROM lychd_db_version
        """,
    )
    assert refused_state == [("0003", None)]

    _run(
        pg_url,
        """
        UPDATE run
        SET status = 'failed', finished_at = now(), updated_at = now()
        WHERE id = '00000000-0000-0000-0000-000000000004'
        """,
    )
    command.upgrade(_migration_config(pg_url), "0004")

    upgraded_state = _run(
        pg_url,
        """
        SELECT version_num, to_regclass('public.run_delivery')::text
        FROM lychd_db_version
        """,
    )
    assert upgraded_state == [("0004", "run_delivery")]
    indexes = _run(
        pg_url,
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'run_delivery'
        ORDER BY indexname
        """,
    )
    assert {row[0] for row in indexes} >= {
        "ix_run_delivery_state_queue_name",
        "uq_run_delivery_one_active",
        "uq_run_delivery_run_enqueue_seq",
    }

    _run(
        pg_url,
        """
        INSERT INTO run (
            id, workflow_name, pattern_manifest, source, status, priority,
            sigil_name, intent, queue_name, attempt, enqueue_seq, created_at, updated_at
        ) VALUES (
            '00000000-0000-0000-0000-000000000005',
            'bridge_chat',
            '{"schema_version": 1}'::jsonb,
            'bridge',
            'queued',
            70,
            'magus',
            '{}'::jsonb,
            'runs',
            0,
            0,
            now(),
            now()
        )
        """,
    )
    _run(
        pg_url,
        """
        INSERT INTO run_delivery (
            id, run_id, enqueue_seq, queue_name, priority, created_at, updated_at
        ) VALUES (
            '00000000-0000-0000-0000-000000000105',
            '00000000-0000-0000-0000-000000000005',
            0,
            'runs',
            70,
            now(),
            now()
        )
        """,
    )

    with pytest.raises(DBAPIError, match="downgrade requires all nonterminal Runs"):
        command.downgrade(_migration_config(pg_url), "0003")

    assert _run(
        pg_url,
        """
        SELECT version_num, to_regclass('public.run_delivery')::text
        FROM lychd_db_version
        """,
    ) == [("0004", "run_delivery")]

    _run(
        pg_url,
        """
        UPDATE run
        SET status = 'failed', finished_at = now(), updated_at = now()
        WHERE id = '00000000-0000-0000-0000-000000000005';
        """,
    )
    _run(
        pg_url,
        """
        UPDATE run_delivery
        SET state = 'settled', settled_at = now(), updated_at = now()
        WHERE run_id = '00000000-0000-0000-0000-000000000005'
        """,
    )

    command.downgrade(_migration_config(pg_url), "0003")
    assert _run(pg_url, "SELECT to_regclass('public.run_delivery')::text") == [(None,)]

    command.upgrade(_migration_config(pg_url), "0004")
    assert _run(pg_url, "SELECT to_regclass('public.run_delivery')::text") == [("run_delivery",)]


def test_run_delivery_mid_ddl_failure_rolls_back_the_whole_revision(pg_url: str) -> None:
    """A late index conflict cannot strand an unversioned partial outbox table."""
    command.downgrade(_migration_config(pg_url), "0003")
    _run(
        pg_url,
        "CREATE TABLE migration_0004_conflict (state text, queue_name text)",
    )
    _run(
        pg_url,
        """
        CREATE INDEX ix_run_delivery_state_queue_name
            ON migration_0004_conflict (state, queue_name)
        """,
    )

    with pytest.raises(DBAPIError):
        command.upgrade(_migration_config(pg_url), "0004")

    assert _run(
        pg_url,
        """
        SELECT version_num, to_regclass('public.run_delivery')::text
        FROM lychd_db_version
        """,
    ) == [("0003", None)]

    _run(pg_url, "DROP TABLE migration_0004_conflict CASCADE")
    command.upgrade(_migration_config(pg_url), "0004")


def test_preauth_nexus_and_wait_owner_migrations_reach_linear_head(pg_url: str) -> None:
    command.upgrade(_migration_config(pg_url), "head")

    assert _run(
        pg_url,
        """
        SELECT version_num
        FROM lychd_db_version
        """,
    ) == [("0017",)]
    assert _run(
        pg_url,
        """
        SELECT column_default, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'codex_preauthorization'
          AND column_name = 'priority'
        """,
    ) == [("50", "NO")]
    assert _run(
        pg_url,
        """
        SELECT column_default, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'codex_preauthorization'
          AND column_name = 'source_present'
        """,
    ) == [("true", "NO")]
    assert _run(
        pg_url,
        "SELECT to_regclass('public.nexus_swap_request')::text",
    ) == [("nexus_swap_request",)]
    assert _run(
        pg_url,
        """
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'run'
          AND column_name = 'consent_id'
        """,
    ) == [("YES",)]
    assert {
        row[0]
        for row in _run(
            pg_url,
            """
            SELECT conname
            FROM pg_constraint
            WHERE conname IN (
                'ck_run_waiting_consent_owner',
                'ck_consent_decision_receipt',
                'ck_delegated_agent_job_terminal_result'
            )
            """,
        )
    } == {
        "ck_run_waiting_consent_owner",
        "ck_consent_decision_receipt",
        "ck_delegated_agent_job_terminal_result",
    }
    assert _run(
        pg_url,
        """
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'codex_preauthorization'::regclass
          AND contype = 'c'
        """,
    ) == [("ck_codex_preauthorization_priority_range",)]


def test_wait_owner_migration_refuses_ambiguous_live_work_and_downgrade(pg_url: str) -> None:
    command.downgrade(_migration_config(pg_url), "0007")
    run_id = "00000000-0000-0000-0000-000000000808"
    consent_id = "00000000-0000-0000-0000-000000000818"
    _run(
        pg_url,
        """
        INSERT INTO run (
            id, workflow_name, pattern_manifest, source, status, priority,
            sigil_name, intent, queue_name, attempt, enqueue_seq, created_at, updated_at
        ) VALUES (
            CAST(:run_id AS uuid),
            'bridge_chat',
            '{"schema_version": 1}'::jsonb,
            'bridge',
            'awaiting_consent',
            70,
            'magus',
            '{}'::jsonb,
            'runs',
            0,
            0,
            now(),
            now()
        )
        """,
        {"run_id": run_id},
    )

    with pytest.raises(DBAPIError, match="cannot infer owners"):
        command.upgrade(_migration_config(pg_url), "head")
    assert _run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0007",)]
    assert _run(
        pg_url,
        """
        SELECT count(*)
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'run' AND column_name = 'consent_id'
        """,
    ) == [(0,)]

    _run(
        pg_url,
        "UPDATE run SET status = 'failed', finished_at = now() WHERE id = CAST(:run_id AS uuid)",
        {"run_id": run_id},
    )
    command.upgrade(_migration_config(pg_url), "head")
    _run(
        pg_url,
        """
        INSERT INTO consent (
            id, run_id, tool_name, tool_call_id, payload, status,
            decided_by, decided_at, created_at, updated_at
        ) VALUES (
            CAST(:consent_id AS uuid),
            CAST(:run_id AS uuid),
            'request_coven_swap',
            'call-0008',
            '{"args": {}}'::jsonb,
            'granted',
            'magus:migration-test',
            now(),
            now(),
            now()
        )
        """,
        {"consent_id": consent_id, "run_id": run_id},
    )
    _run(
        pg_url,
        """
        UPDATE run
        SET status = 'awaiting_consent', consent_id = CAST(:consent_id AS uuid), finished_at = NULL
        WHERE id = CAST(:run_id AS uuid)
        """,
        {"consent_id": consent_id, "run_id": run_id},
    )

    with pytest.raises(DBAPIError, match="requires no awaiting_consent Runs"):
        command.downgrade(_migration_config(pg_url), "0007")
    assert _run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]

    _run(
        pg_url,
        "UPDATE run SET status = 'failed', finished_at = now() WHERE id = CAST(:run_id AS uuid)",
        {"run_id": run_id},
    )
    command.downgrade(_migration_config(pg_url), "0007")
    assert _run(
        pg_url,
        """
        SELECT count(*)
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'run' AND column_name = 'consent_id'
        """,
    ) == [(0,)]
    command.upgrade(_migration_config(pg_url), "head")


def test_nexus_fence_downgrade_refuses_retained_request_identities(pg_url: str) -> None:
    command.upgrade(_migration_config(pg_url), "head")
    _run(
        pg_url,
        """
        INSERT INTO nexus_swap_request (
            id, request_id, target, created_at, updated_at
        ) VALUES (
            '00000000-0000-0000-0000-000000000701',
            'retained-request',
            'chat:local',
            now(),
            now()
        )
        """,
    )

    with pytest.raises(DBAPIError, match="requires an empty nexus_swap_request fence"):
        command.downgrade(_migration_config(pg_url), "0006")

    assert _run(
        pg_url,
        """
        SELECT version_num, to_regclass('public.nexus_swap_request')::text
        FROM lychd_db_version
        """,
    ) == [("0017", "nexus_swap_request")]

    _run(pg_url, "DELETE FROM nexus_swap_request")
    command.downgrade(_migration_config(pg_url), "0006")
    assert _run(pg_url, "SELECT to_regclass('public.nexus_swap_request')::text") == [(None,)]
    command.upgrade(_migration_config(pg_url), "head")


def test_atlas_migration_retains_projects_on_refused_downgrade(pg_url: str) -> None:
    command.upgrade(_migration_config(pg_url), "head")
    assert _run(
        pg_url, "SELECT to_regclass('public.atlas_project')::text, to_regclass('public.atlas_request')::text"
    ) == [
        ("atlas_project", "atlas_request"),
    ]
    _run(
        pg_url,
        """
        INSERT INTO atlas_project (id, sigil_name, version, document, creation_digest, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000000909', 'magus', 1, '{}'::jsonb, 'test', now(), now())
        """,
    )
    with pytest.raises(DBAPIError, match="requires empty atlas_project"):
        command.downgrade(_migration_config(pg_url), "0008")
    assert _run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
    assert _run(pg_url, "SELECT count(*) FROM atlas_project") == [(1,)]
    _run(pg_url, "DELETE FROM atlas_project WHERE id = '00000000-0000-0000-0000-000000000909'")
    command.downgrade(_migration_config(pg_url), "0008")
    assert _run(pg_url, "SELECT to_regclass('public.atlas_project')::text") == [(None,)]
    command.upgrade(_migration_config(pg_url), "head")


def test_nexus_downgrade_lock_fences_a_late_writer(pg_url: str) -> None:
    command.upgrade(_migration_config(pg_url), "head")
    command.downgrade(_migration_config(pg_url), "0007")
    acquired = threading.Event()
    release = threading.Event()

    with ThreadPoolExecutor(max_workers=3) as pool:
        holder = pool.submit(
            asyncio.run,
            _hold_nexus_reader_lock(
                pg_url,
                acquired=acquired,
                release=release,
            ),
        )
        assert acquired.wait(timeout=5)
        downgrade = pool.submit(command.downgrade, _migration_config(pg_url), "0006")
        _wait_for_table_lock(pg_url, mode="AccessExclusiveLock", granted=False)
        late_writer = pool.submit(
            _run,
            pg_url,
            """
            INSERT INTO nexus_swap_request (
                id, request_id, target, created_at, updated_at
            ) VALUES (
                '00000000-0000-0000-0000-000000000702',
                'late-request',
                'chat:late',
                now(),
                now()
            )
            """,
        )
        _wait_for_table_lock(pg_url, mode="RowExclusiveLock", granted=False)
        release.set()
        holder.result(timeout=5)
        downgrade.result(timeout=5)
        with pytest.raises(DBAPIError, match="nexus_swap_request"):
            late_writer.result(timeout=5)

    assert _run(pg_url, "SELECT to_regclass('public.nexus_swap_request')::text") == [(None,)]
    command.upgrade(_migration_config(pg_url), "head")


def test_native_binding_upgrade_preserves_legacy_and_downgrade_preserves_native_history(pg_url: str) -> None:
    command.upgrade(_migration_config(pg_url), "head")
    command.downgrade(_migration_config(pg_url), "0009")
    _run(
        pg_url,
        """
        INSERT INTO run (id, workflow_name, pattern_manifest, source, status, priority, sigil_name,
                         intent, queue_name, attempt, enqueue_seq, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000001010', 'bridge_chat', '{}'::jsonb, 'bridge',
                'done', 70, 'magus', '{}'::jsonb, 'runs', 0, 0, now(), now())
    """,
    )
    _run(
        pg_url,
        """
        INSERT INTO consent (id, run_id, tool_name, tool_call_id, payload, status, decided_by, decided_at, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000001011', '00000000-0000-0000-0000-000000001010',
                'place', 'legacy', '{}'::jsonb, 'denied', 'first', now(), now(), now())
    """,
    )
    before = _run(pg_url, "SELECT status, decided_by, decided_at FROM consent WHERE tool_call_id = 'legacy'")
    command.upgrade(_migration_config(pg_url), "head")
    assert _run(pg_url, "SELECT status, decided_by, decided_at FROM consent WHERE tool_call_id = 'legacy'") == before
    assert _run(
        pg_url, "SELECT native_review_required, native_binding IS NULL FROM consent WHERE tool_call_id = 'legacy'"
    ) == [(False, True)]
    with pytest.raises(DBAPIError, match="native_binding_requirement"):
        _run(pg_url, "UPDATE consent SET native_review_required = true WHERE tool_call_id = 'legacy'")
    with pytest.raises(DBAPIError, match="native_binding_requirement"):
        _run(pg_url, "UPDATE consent SET native_binding = 'null'::jsonb WHERE tool_call_id = 'legacy'")
    _run(
        pg_url,
        "UPDATE consent SET native_review_required = true, native_binding = '{}'::jsonb WHERE tool_call_id = 'legacy'",
    )
    with pytest.raises(DBAPIError, match="requires no native Consent bindings"):
        command.downgrade(_migration_config(pg_url), "0009")
    assert _run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
    assert _run(pg_url, "SELECT native_review_required, native_binding FROM consent WHERE tool_call_id = 'legacy'") == [
        (True, {})
    ]
    _run(pg_url, "DELETE FROM consent WHERE id = '00000000-0000-0000-0000-000000001011'")
    _run(pg_url, "DELETE FROM run WHERE id = '00000000-0000-0000-0000-000000001010'")
    command.downgrade(_migration_config(pg_url), "0009")
    command.upgrade(_migration_config(pg_url), "head")


def _insert_blockworld_mission(url: str) -> None:
    _run(
        url,
        """INSERT INTO blockworld_placement_mission
        (id,request_id,action_id,run_id,admission_bytes,admission_digest,request_bytes,request_digest,
         pattern_snapshot,pattern_digest,cursor,placements_remaining,pending_action_id,result_bytes,created_at,updated_at)
        VALUES ('00000000-0000-0000-0000-000000001101','00000000-0000-0000-0000-000000001102',
                '00000000-0000-0000-0000-000000001103',NULL,decode('7b7d','hex'),'fixture',decode('7b7d','hex'),'fixture',
                '{}'::jsonb,'fixture',0,1,NULL,NULL,now(),now())""",
    )


def test_blockworld_empty_migration_cycle_matches_orm_schema(pg_url: str) -> None:
    from lychd.db.models.blockworld import BlockworldPlacementAction, BlockworldPlacementMission

    command.upgrade(_migration_config(pg_url), "head")
    for model in (BlockworldPlacementMission, BlockworldPlacementAction):
        columns = _run(
            pg_url,
            "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:table",
            {"table": model.__tablename__},
        )
        assert {row[0] for row in columns} == {column.name for column in model.__table__.columns}
        assert _run(
            pg_url,
            "SELECT data_type,is_nullable FROM information_schema.columns WHERE table_name=:table AND column_name='sa_orm_sentinel'",
            {"table": model.__tablename__},
        ) == [("integer", "YES")]
    assert _run(
        pg_url,
        """SELECT confrelid::regclass::text, confdeltype::text FROM pg_constraint
                          WHERE conrelid='blockworld_placement_action'::regclass AND contype='f'""",
    ) == [("blockworld_placement_mission", "r")]
    command.downgrade(_migration_config(pg_url), "0010")
    assert _run(
        pg_url, "SELECT version_num,to_regclass('public.blockworld_placement_mission')::text FROM lychd_db_version"
    ) == [("0010", None)]
    command.upgrade(_migration_config(pg_url), "head")
    assert _run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]


@pytest.mark.parametrize("status", [None, "prepared", "pending", "unverified_effect", "not_issued", "verified"])
def test_blockworld_downgrade_refuses_every_retained_disposition(pg_url: str, status: str | None) -> None:
    command.upgrade(_migration_config(pg_url), "head")
    _insert_blockworld_mission(pg_url)
    if status is not None:
        claimed = status in {"pending", "unverified_effect", "verified"}
        _run(
            pg_url,
            """INSERT INTO blockworld_placement_action
            (id,mission_id,run_id,consent_id,expected_cursor,command_bytes,preparation_digest,review_bytes,
             native_binding,native_binding_digest,status,claim_id,issuance_judgment,claimed_at,reason,
             receipt_bytes,receipt_digest,created_at,updated_at)
            VALUES ('00000000-0000-0000-0000-000000001103','00000000-0000-0000-0000-000000001101',
                    '00000000-0000-0000-0000-000000001104','00000000-0000-0000-0000-000000001105',0,
                    decode('7b7d','hex'),'fixture',decode('7b7d','hex'),'{"review_digest":"fixture","preparation_digest":"fixture"}'::jsonb,
                    'fixture',:status,CAST(:claim_id AS uuid),CAST(:judgment AS jsonb),
                    CASE WHEN :claimed THEN now() ELSE NULL END,NULL,
                    CASE WHEN :verified THEN decode('7b7d','hex') ELSE NULL END,
                    CASE WHEN :verified THEN 'fixture' ELSE NULL END,now(),now())""",
            {
                "status": status,
                "claim_id": "00000000-0000-0000-0000-000000001106" if claimed else None,
                "judgment": "{}" if claimed else None,
                "claimed": claimed,
                "verified": status == "verified",
            },
        )
    try:
        with pytest.raises(DBAPIError, match="custody requires explicit retirement"):
            command.downgrade(_migration_config(pg_url), "0010")
        assert _run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
        assert _run(pg_url, "SELECT count(*) FROM blockworld_placement_mission") == [(1,)]
    finally:
        # Explicit test teardown is not a production retirement operation.
        _run(pg_url, "DELETE FROM blockworld_placement_action")
        _run(pg_url, "DELETE FROM blockworld_placement_mission")


async def _hold_blockworld_reader_lock(url: str, acquired: threading.Event, release: threading.Event) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("LOCK TABLE blockworld_placement_mission IN ACCESS SHARE MODE"))
            acquired.set()
            await asyncio.to_thread(release.wait)
    finally:
        await engine.dispose()


def test_blockworld_downgrade_lock_prevents_late_fixture_loss(pg_url: str) -> None:
    command.upgrade(_migration_config(pg_url), "head")
    acquired, release = threading.Event(), threading.Event()
    with ThreadPoolExecutor(max_workers=3) as pool:
        holder = pool.submit(asyncio.run, _hold_blockworld_reader_lock(pg_url, acquired, release))
        assert acquired.wait(timeout=5)
        downgrade = pool.submit(command.downgrade, _migration_config(pg_url), "0010")
        try:
            _wait_for_table_lock(
                pg_url, mode="AccessExclusiveLock", granted=False, table="blockworld_placement_mission"
            )
            writer = pool.submit(_insert_blockworld_mission, pg_url)
            _wait_for_table_lock(pg_url, mode="RowExclusiveLock", granted=False, table="blockworld_placement_mission")
        finally:
            release.set()
        holder.result(timeout=5)
        downgrade.result(timeout=5)
        with pytest.raises(DBAPIError):
            writer.result(timeout=5)
    assert _run(
        pg_url, "SELECT version_num,to_regclass('public.blockworld_placement_mission')::text FROM lychd_db_version"
    ) == [("0010", None)]
    command.upgrade(_migration_config(pg_url), "head")


def test_creation_empty_cycle_and_retained_custody_refuses_downgrade(pg_url: str) -> None:
    """Generated tables round-trip only while no investigation custody exists."""
    command.upgrade(_migration_config(pg_url), "head")
    assert _run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
    table_query = "SELECT to_regclass('public.creation_case')::text, to_regclass('public.creation_admission')::text, to_regclass('public.creation_attempt')::text"
    assert _run(pg_url, table_query) == [("creation_case", "creation_admission", "creation_attempt")]
    request_id = str(uuid4())
    _run(
        pg_url,
        """INSERT INTO creation_case
        (id, request_bytes, request_digest, profile_bytes, profile_digest, deadline, slot, status, cancelled,
         current_admission_id, created_at, updated_at)
        VALUES (CAST(:id AS uuid), decode('7b7d','hex'), repeat('a',64), decode('7b7d','hex'), repeat('b',64),
                now() + interval '180 seconds', 1, 'reserved', false, CAST(:id AS uuid), now(), now())""",
        {"id": request_id},
    )
    try:
        with pytest.raises(DBAPIError, match="Retained Creation investigation custody prevents downgrade"):
            command.downgrade(_migration_config(pg_url), "0015")
        assert _run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
        assert _run(pg_url, "SELECT count(*) FROM creation_case WHERE id=CAST(:id AS uuid)", {"id": request_id}) == [
            (1,)
        ]
    finally:
        # Explicit disposable-fixture teardown does not define production retirement.
        _run(pg_url, "DELETE FROM creation_case WHERE id=CAST(:id AS uuid)", {"id": request_id})
    command.downgrade(_migration_config(pg_url), "0015")
    assert _run(pg_url, table_query) == [(None, None, None)]
    command.upgrade(_migration_config(pg_url), "head")
    assert _run(pg_url, table_query) == [("creation_case", "creation_admission", "creation_attempt")]


def test_creation_feedback_empty_cycle_retained_refusal_and_original_custody(pg_url: str) -> None:
    command.upgrade(_migration_config(pg_url), "head")
    command.downgrade(_migration_config(pg_url), "0016")
    assert _run(pg_url, "SELECT to_regclass('public.creation_feedback')::text") == [(None,)]
    command.upgrade(_migration_config(pg_url), "head")
    case_id, assessment_id = str(uuid4()), str(uuid4())
    _run(
        pg_url,
        """INSERT INTO creation_case (id,request_bytes,request_digest,profile_bytes,profile_digest,deadline,slot,status,cancelled,current_admission_id,created_at,updated_at) VALUES (CAST(:id AS uuid),decode('7b7d','hex'),repeat('a',64),decode('7b7d','hex'),repeat('b',64),now(),NULL,'accepted',false,CAST(:id AS uuid),now(),now())""",
        {"id": case_id},
    )
    _run(
        pg_url,
        """INSERT INTO creation_feedback (id,case_id,sequence,kind,body_bytes,body_digest,report_bytes,report_digest,attribution_bytes,created_at,updated_at) VALUES (CAST(:id AS uuid),CAST(:case AS uuid),1,'assessment',decode('7b7d','hex'),repeat('a',64),decode('6869','hex'),repeat('b',64),decode('7b7d','hex'),now(),now())""",
        {"id": assessment_id, "case": case_id},
    )
    try:
        with pytest.raises(DBAPIError, match="Retained Creation feedback custody prevents downgrade"):
            command.downgrade(_migration_config(pg_url), "0016")
        assert _run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
        assert _run(
            pg_url,
            "SELECT encode(request_bytes,'hex'),status FROM creation_case WHERE id=CAST(:id AS uuid)",
            {"id": case_id},
        ) == [("7b7d", "accepted")]
    finally:
        _run(pg_url, "DELETE FROM creation_feedback WHERE id=CAST(:id AS uuid)", {"id": assessment_id})
        _run(pg_url, "DELETE FROM creation_case WHERE id=CAST(:id AS uuid)", {"id": case_id})
