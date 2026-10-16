"""Scout transactional DDL, exact schema parity and retained-custody rollback law."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast
from uuid import uuid4

import pytest
from alembic import command, op
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from testcontainers.community.postgres import PostgresContainer

from lychd.db.models.scout import ScoutAttempt, ScoutBudget
from tests.integration import test_archive_migrations_pg as migration

pytestmark = [pytest.mark.integration, pytest.mark.container]

_BUDGET_INSERT = """INSERT INTO scout_budget
(id,scope,configuration_digest,active_claims,connects_limit,transmissions_limit,wire_bytes_limit,
 connects_reserved,transmissions_reserved,wire_bytes_reserved,connects_used,transmissions_used,wire_bytes_used,created_at,updated_at)
VALUES (CAST(:id AS uuid),'binding',repeat('a',64),0,6,40,20000,0,0,0,0,0,0,now(),now())"""


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    with PostgresContainer(
        "pgvector/pgvector:pg18-trixie", driver="asyncpg", mem_limit="512m", nano_cpus=1_000_000_000
    ) as postgres:
        yield postgres.get_connection_url()


def test_upgrade_is_atomic_and_empty_round_trip_has_no_schema_drift(
    pg_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    command.upgrade(migration.config(pg_url), "0013")
    original = op.create_table

    def fail_late(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "scout_attempt":
            message = "Injected late Scout DDL failure."
            raise RuntimeError(message)
        return original(name, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(op, "create_table", fail_late)
        with pytest.raises(RuntimeError, match="Injected late Scout"):
            command.upgrade(migration.config(pg_url), "0014")
    assert migration.run(
        pg_url, "SELECT version_num,to_regclass('public.scout_budget')::text FROM lychd_db_version"
    ) == [("0013", None)]
    command.upgrade(migration.config(pg_url), "0014")
    command.upgrade(migration.config(pg_url), "head")
    command.check(migration.config(pg_url))
    command.downgrade(migration.config(pg_url), "0014")
    for model in (ScoutBudget, ScoutAttempt):
        columns = migration.run(
            pg_url,
            "SELECT column_name,is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name=:table",
            {"table": model.__tablename__},
        )
        assert dict(columns) == {column.name: "YES" if column.nullable else "NO" for column in model.__table__.columns}
    assert migration.run(
        pg_url,
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='ck_scout_budget_active_binding_limit'",
    )
    command.downgrade(migration.config(pg_url), "0013")
    assert migration.run(
        pg_url,
        "SELECT version_num,to_regclass('public.scout_budget')::text,to_regclass('public.scout_attempt')::text FROM lychd_db_version",
    ) == [("0013", None, None)]
    command.upgrade(migration.config(pg_url), "0014")
    command.upgrade(migration.config(pg_url), "head")
    command.check(migration.config(pg_url))
    command.downgrade(migration.config(pg_url), "0014")


def test_even_empty_budget_binding_prevents_downgrade(pg_url: str) -> None:
    command.upgrade(migration.config(pg_url), "0014")
    identity = str(uuid4())
    migration.run(pg_url, _BUDGET_INSERT, {"id": identity})
    try:
        with pytest.raises(DBAPIError, match="Retained Scout custody prevents downgrade"):
            command.downgrade(migration.config(pg_url), "0013")
        assert migration.run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0014",)]
        assert migration.run(pg_url, "SELECT scope,active_claims,connects_used FROM scout_budget") == [
            ("binding", 0, 0)
        ]
    finally:
        # Explicit removal of this test's own synthetic row in its disposable DB.
        migration.run(pg_url, "DELETE FROM scout_budget WHERE id=CAST(:id AS uuid)", {"id": identity})


def _retained_attempt(pg_url: str) -> dict[str, str]:
    values = {name: str(uuid4()) for name in ("run", "consent", "attempt", "request", "claim", "receipt")}
    migration.run(
        pg_url,
        """INSERT INTO run
(id,workflow_name,pattern_manifest,source,status,sigil_name,intent,queue_name,created_at,updated_at)
VALUES (CAST(:run AS uuid),'scout-page-answer@1','{}','bridge','done','fixture','{}','runs',now(),now())""",
        values,
    )
    migration.run(
        pg_url,
        """INSERT INTO consent
(id,run_id,tool_name,tool_call_id,payload,native_review_required,native_binding,status,created_at,updated_at)
VALUES (CAST(:consent AS uuid),CAST(:run AS uuid),'scout.fetch_extract',:attempt,'{}',true,'{"owner":"scout"}','pending',now(),now())""",
        values,
    )
    migration.run(
        pg_url,
        """INSERT INTO scout_attempt
(id,request_id,run_id,consent_id,preparation_enqueue_seq,preparation_bytes,preparation_digest,native_binding,review_bytes,status,created_at,updated_at)
VALUES (CAST(:attempt AS uuid),CAST(:request AS uuid),CAST(:run AS uuid),CAST(:consent AS uuid),0,decode('00','hex'),repeat('a',64),'{}',decode('00','hex'),'prepared',now(),now())""",
        values,
    )
    return values


def test_every_retained_attempt_disposition_refuses_history_loss(pg_url: str) -> None:
    command.upgrade(migration.config(pg_url), "0014")
    values = _retained_attempt(pg_url)
    try:
        for state in ("prepared", "claimed", "unknown_after_crash", "succeeded", "refused"):
            if state != "prepared":
                terminal = state in {"succeeded", "refused"}
                migration.run(
                    pg_url,
                    """UPDATE scout_attempt SET status=:state,claim_id=CAST(:claim AS uuid),execution_enqueue_seq=1,claimed_at=now(),
receipt_id=CAST(:terminal_receipt AS uuid),settlement_bytes=CASE WHEN :terminal THEN decode('00','hex') ELSE NULL END
WHERE id=CAST(:attempt AS uuid)""",
                    {
                        **values,
                        "state": state,
                        "terminal": terminal,
                        "terminal_receipt": values["receipt"] if terminal else None,
                    },
                )
            with pytest.raises(DBAPIError, match="Retained Scout custody prevents downgrade"):
                command.downgrade(migration.config(pg_url), "0013")
            assert migration.run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0014",)]
            assert migration.run(pg_url, "SELECT status FROM scout_attempt") == [(state,)]
        with pytest.raises(DBAPIError, match="foreign key constraint"):
            migration.run(pg_url, "DELETE FROM consent WHERE id=CAST(:consent AS uuid)", values)
        with pytest.raises(DBAPIError, match="foreign key constraint"):
            migration.run(pg_url, "DELETE FROM run WHERE id=CAST(:run AS uuid)", values)
    finally:
        migration.run(pg_url, "DELETE FROM scout_attempt WHERE id=CAST(:attempt AS uuid)", values)
        migration.run(pg_url, "DELETE FROM consent WHERE id=CAST(:consent AS uuid)", values)
        migration.run(pg_url, "DELETE FROM run WHERE id=CAST(:run AS uuid)", values)


def test_downgrade_holds_both_table_locks_until_removal(pg_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    command.upgrade(migration.config(pg_url), "0014")
    original = op.execute
    observations: list[tuple[str, str]] = []

    def observe(statement: Any, *args: Any, **kwargs: Any) -> Any:
        if "DO $$" in str(statement):
            rows = (
                op.get_bind()
                .execute(
                    text("""SELECT c.relname,l.mode FROM pg_locks l JOIN pg_class c ON c.oid=l.relation
WHERE c.relname IN ('scout_budget','scout_attempt') AND l.mode='AccessExclusiveLock'
AND l.granted AND l.pid=pg_backend_pid() ORDER BY c.relname""")
                )
                .tuples()
                .all()
            )
            observations.extend(cast("list[tuple[str, str]]", list(rows)))
        return original(statement, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(op, "execute", observe)
        command.downgrade(migration.config(pg_url), "0013")
    assert observations == [("scout_attempt", "AccessExclusiveLock"), ("scout_budget", "AccessExclusiveLock")]
    command.upgrade(migration.config(pg_url), "0014")
    command.upgrade(migration.config(pg_url), "head")
    command.check(migration.config(pg_url))
    command.downgrade(migration.config(pg_url), "0014")
