"""Static schema contract for the durable AgentJob ledger."""
# pyright: reportArgumentType=false, reportPrivateUsage=false

from __future__ import annotations

from importlib import import_module
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import String, Table, UniqueConstraint

from lychd.db.delegation import DbDelegatedAgentJobStore
from lychd.db.models import DelegatedAgentEventRecord, DelegatedAgentJobRecord, Run
from lychd.domain.delegation import DelegatedAgentJobStatus, DelegatedAgentRequest


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


@pytest.mark.asyncio
async def test_zero_event_limit_skips_the_per_job_event_query() -> None:
    class _NoEventQuerySession:
        async def scalars(self, _statement: object) -> Any:
            pytest.fail("event_limit=0 must not issue an event query")

    run_id = uuid4()
    request = DelegatedAgentRequest(
        request_id="request-no-events",
        run_id=str(run_id),
        step_id="delegate",
        runtime="reference",
        prompt="inspect",
    )
    row = SimpleNamespace(
        id=uuid4(),
        job_id="job-no-events",
        request_id=request.request_id,
        run_id=run_id,
        runtime=request.runtime,
        profile=request.profile.value,
        status=DelegatedAgentJobStatus.RUNNING.value,
        request=request.model_dump(mode="json"),
        result=None,
    )

    view = await DbDelegatedAgentJobStore._view(_NoEventQuerySession(), row, event_limit=0)

    assert view.events == ()


def test_delegated_ledger_migration_is_the_current_linear_head() -> None:
    migration = import_module("lychd.db.migrations.versions.0003_delegated_agent_ledger")

    assert migration.revision == "0003"
    assert migration.down_revision == "0002"
