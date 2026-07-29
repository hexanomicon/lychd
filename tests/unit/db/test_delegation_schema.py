"""Static schema contract for the durable AgentJob ledger."""

from __future__ import annotations

from importlib import import_module
from typing import cast

from sqlalchemy import String, Table, UniqueConstraint

from lychd.db.models import DelegatedAgentEventRecord, DelegatedAgentJobRecord, Run


def test_delegated_job_schema_binds_run_and_idempotency_identities() -> None:
    table = cast("Table", DelegatedAgentJobRecord.__table__)

    assert table.name == "delegated_agent_job"
    assert table.c.run_id.foreign_keys
    assert {foreign_key.target_fullname for foreign_key in table.c.run_id.foreign_keys} == {"run.id"}
    assert table.c.job_id.unique is True
    assert table.c.request_id.unique is True
    assert table.c.request.type.__class__.__name__ == "JSONB"
    assert table.c.result.nullable is True
    run_table = cast("Table", Run.__table__)
    assert isinstance(run_table.c.delegated_job_id.type, String)
    assert run_table.c.delegated_job_id.type.length == 128
    assert run_table.c.delegated_job_id.index is True


def test_delegated_event_schema_orders_events_per_job() -> None:
    table = cast("Table", DelegatedAgentEventRecord.__table__)
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("job_record_id", "seq") in unique_columns
    assert {foreign_key.target_fullname for foreign_key in table.c.job_record_id.foreign_keys} == {
        "delegated_agent_job.id"
    }
    assert table.c.payload.type.__class__.__name__ == "JSONB"


def test_delegated_ledger_migration_is_the_current_linear_head() -> None:
    migration = import_module("lychd.db.migrations.versions.0003_delegated_agent_ledger")

    assert migration.revision == "0003"
    assert migration.down_revision == "0002"
