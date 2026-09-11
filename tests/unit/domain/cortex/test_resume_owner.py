"""Initial durable re-entry binds typed checkpoints to the current Run wait owner."""

# The worker validator is intentionally exercised before a real persisted graph node.
# pyright: reportPrivateUsage=false

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from functools import partial
from typing import Any

import pytest
from pydantic import BaseModel
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.workflows.base import DelegatedAgentNode, Gate
from lychd.domain.cortex.graph import build_serial_graph
from lychd.domain.cortex.graph_runner import GraphRunner, NodeOccurrenceEvent
from lychd.domain.cortex.ledger import ConsentAdmissionEvidence, DelegateAdmissionEvidence, InMemoryRunLedger
from lychd.domain.cortex.runs import RunRecord, RunStatus
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore
from lychd.domain.delegation.models import DelegatedAgentJobStatus, DelegatedAgentResult
from lychd.ghouls.runs import _validate_resume_owner


class _State(BaseModel):
    run_id: str
    pending_consent_id: str | None = None
    job_id: str | None = None


@dataclass
class _ConsentStation(Gate, BaseNode[_State, list[str], str]):
    async def run(self, ctx: GraphRunContext[_State, list[str]]) -> End[str] | _DelegateStation:
        ctx.deps.append("consent-effect")
        return End("consent")


@dataclass
class _DelegateStation(DelegatedAgentNode, BaseNode[_State, list[str], str]):
    async def run(self, ctx: GraphRunContext[_State, list[str]]) -> End[str] | _ConsentStation:
        ctx.deps.append("delegate-effect")
        return End("delegate")


class _UnusedOrchestrator:
    async def handle_transition(self, *_args: Any, **_kwargs: Any) -> None:
        pytest.fail("wait owner validation must not request hardware")


async def _admit(ledger: InMemoryRunLedger, run: RunRecord) -> int:
    if run.consent_id is not None:
        seq = await ledger.try_admit_consent(
            run.run_id,
            consent_id=run.consent_id,
            evidence=ConsentAdmissionEvidence(
                run_id=run.run_id,
                consent_id=run.consent_id,
                status="denied",
                decided_by="test:operator",
                decided_at=datetime.now(UTC),
            ),
        )
    else:
        assert run.delegated_job_id is not None
        result = DelegatedAgentResult(job_id=run.delegated_job_id, status=DelegatedAgentJobStatus.SUCCEEDED)
        seq = await ledger.try_admit_delegate(
            run.run_id,
            job_id=run.delegated_job_id,
            evidence=DelegateAdmissionEvidence(
                run_id=run.run_id,
                job_id=run.delegated_job_id,
                status=result.status,
                result=result,
            ),
        )
    assert seq is not None
    return seq


@pytest.mark.parametrize("consent_first", [True, False], ids=["consent-to-delegate", "delegate-to-consent"])
@pytest.mark.parametrize("stale_checkpoint", [False, True], ids=["current", "stale-crosskind"])
@pytest.mark.asyncio
async def test_mixed_wait_sequence_replaces_owner_before_graph_reentry(
    *, consent_first: bool, stale_checkpoint: bool
) -> None:
    """Both legal wait orders survive; restoring the earlier kind never executes it."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    run = await ledger.create(
        Intent(session_id="session", run_id="run", prompt="mixed waits"),
        workflow_name="mixed",
        queue_name="runs",
        priority=50,
    )
    assert await ledger.try_claim_run(run.run_id, enqueue_seq=0)
    first_park = ledger.park_consent if consent_first else ledger.park_delegate
    second_park = ledger.park_delegate if consent_first else ledger.park_consent
    await first_park(run.run_id, "earlier-owner")
    first = await ledger.get(run.run_id)
    assert first is not None
    assert await ledger.try_claim_run(run.run_id, enqueue_seq=await _admit(ledger, first))
    await second_park(run.run_id, "current-owner")
    current = await ledger.get(run.run_id)
    assert current is not None
    assert (current.consent_id, current.delegated_job_id) == (
        (None, "current-owner") if consent_first else ("current-owner", None)
    )
    assert await ledger.try_claim_run(run.run_id, enqueue_seq=await _admit(ledger, current))

    checkpoint_owner = first if stale_checkpoint else current
    node = _ConsentStation() if checkpoint_owner.consent_id is not None else _DelegateStation()
    state = _State(
        run_id=run.run_id,
        pending_consent_id=checkpoint_owner.consent_id,
        job_id=checkpoint_owner.delegated_job_id,
    )
    graph = build_serial_graph(
        nodes=(_ConsentStation, _DelegateStation), state_type=_State, deps_type=list[str], output_type=str
    )
    persistence = DurableStasisPhylactery(job_id=run.run_id, store=InMemoryStasisStore())
    persistence.set_graph_types(graph)
    await persistence.snapshot_node(state, node)
    effects: list[str] = []
    events: list[NodeOccurrenceEvent] = []
    runner: GraphRunner[_State] = GraphRunner(
        orchestrator=_UnusedOrchestrator(),
        persistence=persistence,
        signal_priority=50,
        on_node_event=events.append,
        validate_resume=partial(_validate_resume_owner, current),
    )
    if stale_checkpoint:
        with pytest.raises(ValueError, match="checkpoint does not match the Run's current"):
            await runner.resume_graph(graph, deps=effects)
        assert effects == []
        assert events == []
    else:
        output = await runner.resume_graph(graph, deps=effects)
        assert output == ("delegate" if consent_first else "consent")
        assert effects == [f"{output}-effect"]


@pytest.mark.parametrize("owners", [(None, None), ("consent", "job")], ids=["missing", "ambiguous-legacy"])
def test_resume_refuses_missing_or_ambiguous_owner(owners: tuple[str | None, str | None]) -> None:
    run = RunRecord(
        run_id="run",
        session_id="session",
        workflow_name="mixed",
        pattern_manifest={},
        source="bridge",
        queue_name="runs",
        priority=50,
        status=RunStatus.RUNNING,
        prompt="mixed waits",
    )
    run = replace(run, consent_id=owners[0], delegated_job_id=owners[1])
    with pytest.raises(ValueError, match="exactly one current wait owner"):
        _validate_resume_owner(run, _State(run_id=run.run_id, pending_consent_id="consent"), _ConsentStation())
