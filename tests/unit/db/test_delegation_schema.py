"""Static schema contract for the durable AgentJob ledger."""
# pyright: reportArgumentType=false, reportPrivateUsage=false

from __future__ import annotations

from typing import cast

from sqlalchemy import Table, UniqueConstraint

from lychd.db.models import DelegatedAgentEventRecord, DelegatedAgentJobRecord, Run


def test_delegated_job_schema_binds_run_and_idempotency_identities() -> None:
    table = cast("Table", DelegatedAgentJobRecord.__table__)

    run_foreign_key = next(iter(table.c.run_id.foreign_keys))
    assert run_foreign_key.target_fullname == "run.id"
    assert run_foreign_key.ondelete == "CASCADE"
    assert table.c.job_id.unique is True
    assert table.c.request_id.unique is True
    assert Run.__table__.c.delegated_job_id is not None


def test_delegated_event_schema_orders_events_per_job() -> None:
    table = cast("Table", DelegatedAgentEventRecord.__table__)
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("job_record_id", "seq") in unique_columns
    job_foreign_key = next(iter(table.c.job_record_id.foreign_keys))
    assert job_foreign_key.target_fullname == "delegated_agent_job.id"
    assert job_foreign_key.ondelete == "CASCADE"
