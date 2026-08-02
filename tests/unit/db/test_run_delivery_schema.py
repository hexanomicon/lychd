"""Static schema and migration contract for the Run delivery outbox."""

from __future__ import annotations

from importlib import import_module
from typing import cast

import pytest
from sqlalchemy import CheckConstraint, Table, UniqueConstraint

from lychd.db.models import RunDelivery


def test_run_delivery_model_owns_exact_hops_and_publication_state() -> None:
    table = cast("Table", RunDelivery.__table__)
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    indexes = {str(index.name): index for index in table.indexes}
    foreign_key = next(iter(table.c.run_id.foreign_keys))

    assert tuple(table.c) == (
        table.c.id,
        table.c.run_id,
        table.c.enqueue_seq,
        table.c.queue_name,
        table.c.priority,
        table.c.resume,
        table.c.state,
        table.c.publish_attempts,
        table.c.last_error,
        table.c.published_at,
        table.c.claimed_at,
        table.c.settled_at,
        table.c.sa_orm_sentinel,
        table.c.created_at,
        table.c.updated_at,
    )
    assert ("run_id", "enqueue_seq") in unique_columns
    assert foreign_key.target_fullname == "run.id"
    assert foreign_key.ondelete == "CASCADE"
    assert checks["ck_run_delivery_state"] == ("state IN ('held', 'pending', 'published', 'claimed', 'settled')")
    assert checks["ck_run_delivery_publish_attempts_nonnegative"] == "publish_attempts >= 0"
    assert checks["ck_run_delivery_enqueue_seq_nonnegative"] == "enqueue_seq >= 0"
    assert checks["ck_run_delivery_priority_range"] == "priority BETWEEN 0 AND 100"
    assert tuple(column.name for column in indexes["ix_run_delivery_state_queue_name"].columns) == (
        "state",
        "queue_name",
    )
    active_index = indexes["uq_run_delivery_one_active"]
    assert active_index.unique is True
    assert tuple(column.name for column in active_index.columns) == ("run_id",)
    assert str(active_index.dialect_options["postgresql"]["where"]) == "state <> 'settled'"
    assert table.c.resume.nullable is False
    assert table.c.state.nullable is False
    assert table.c.publish_attempts.nullable is False
    assert table.c.published_at.nullable is True
    assert table.c.claimed_at.nullable is True
    assert table.c.settled_at.nullable is True
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False


class _MigrationOperations:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: str) -> None:
        self.statements.append(statement)


def test_run_delivery_migration_refuses_ambiguous_legacy_work(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = import_module("lychd.db.migrations.versions.0004_run_delivery_outbox")
    operations = _MigrationOperations()
    monkeypatch.setattr(migration, "op", operations)

    migration.data_upgrades()

    assert migration.revision == "0004"
    assert migration.down_revision == "0003"
    assert operations.statements[0] == "LOCK TABLE run IN ACCESS EXCLUSIVE MODE"
    sql = " ".join(operations.statements[1].split())
    assert "WHERE status NOT IN ('done', 'failed', 'cancelled')" in sql
    assert "requires all nonterminal Runs to be drained" in sql
    assert "INSERT INTO run_delivery" not in sql

    operations.statements.clear()
    migration.data_downgrades()
    assert operations.statements[0] == "LOCK TABLE run IN ACCESS EXCLUSIVE MODE"
    assert "downgrade requires all nonterminal Runs to be drained" in " ".join(operations.statements[1].split())
