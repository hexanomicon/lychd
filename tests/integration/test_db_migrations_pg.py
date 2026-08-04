"""Real PostgreSQL upgrade/refusal/downgrade coverage for the linear schema head."""

# pyright: reportMissingImports=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from advanced_alchemy.alembic.commands import AlembicCommandConfig
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
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
    engine = create_async_engine(url)
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


def _wait_for_table_lock(url: str, *, mode: str, granted: bool) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        rows = _run(
            url,
            """
            SELECT count(*)
            FROM pg_locks
            WHERE relation = 'nexus_swap_request'::regclass
              AND mode = :mode
              AND granted = :granted
            """,
            {"mode": mode, "granted": granted},
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
    ) == [("0008",)]
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
    assert _run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0008",)]

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
    ) == [("0008", "nexus_swap_request")]

    _run(pg_url, "DELETE FROM nexus_swap_request")
    command.downgrade(_migration_config(pg_url), "0006")
    assert _run(pg_url, "SELECT to_regclass('public.nexus_swap_request')::text") == [(None,)]
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
