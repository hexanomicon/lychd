"""Serialized recovery across consent, delivery publication, and terminal cleanup.

Each image captures committed rows at a real worker boundary and reconstructs
entirely new memory adapters and runtime objects from JSON. These are controlled
crash-window simulations, not PostgreSQL transactions, SAQ process-crash receipts,
or proof of exactly-once external effects. The only tool appends to a test list.
"""

# The image adapter deliberately serializes the memory profile's private rows;
# no production persistence API or alternate production recovery path is added.
# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pydantic_ai.models
import pytest
from pydantic import BaseModel
from pydantic_ai.messages import ModelResponse
from pydantic_ai.models.function import DeltaToolCall, FunctionModel
from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.deps import LychDDeps
from lychd.agents.router import Intent
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.agents.workflows.nodes import CONSENT_EFFECT_ID_KEY, CONSENT_EFFECT_REVISION_KEY
from lychd.domain.codex.ledger import InMemoryConsentLedger, _ConsentRow
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine, run_job_key
from lychd.domain.cortex.events import InProcessEventBus, RunEvent, RunEventKind
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunDeliveryRecord, RunDeliveryState, RunRecord, RunStatus
from lychd.domain.cortex.stasis import InMemoryStasisStore
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.web.sessions import BridgeSessionStore, SessionRecord
from lychd.ghouls.runs import perform_run, reconcile_consents, reconcile_runs
from lychd.interface.web.lifespan import _reconcile_terminal_checkpoints_at_startup
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.models.function import AgentInfo


class _SessionImage(BaseModel):
    id: str
    title: str
    created_at: datetime
    turns: list[BridgeTurn]
    message_history: list[Any]


class _CommittedImage(BaseModel):
    runs: list[RunRecord]
    idempotency_keys: dict[str, str]
    deliveries: list[RunDeliveryRecord]
    events: dict[str, list[RunEvent]]
    consents: list[_ConsentRow]
    checkpoints: dict[str, list[Any]]
    sessions: list[_SessionImage]


@dataclass
class _QueueJob:
    key: str
    status: str = "queued"


@dataclass
class _Queue:
    """An inert, idempotent broker boundary with explicit publication failure."""

    fail_publication: bool = False
    jobs: dict[str, _QueueJob] = field(default_factory=dict)
    attempts: list[dict[str, Any]] = field(default_factory=list)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> _QueueJob:
        self.attempts.append({"func": job_or_func, **kwargs})
        if self.fail_publication:
            msg = "offline broker publication unavailable"
            raise ConnectionError(msg)
        key = str(kwargs["key"])
        return self.jobs.setdefault(key, _QueueJob(key))

    async def job(self, job_key: str, /) -> _QueueJob | None:
        return self.jobs.get(job_key)

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (error, ttl)
        job.status = "aborted"


@dataclass
class _Boot:
    ledger: InMemoryRunLedger
    consents: InMemoryConsentLedger
    checkpoints: InMemoryStasisStore
    sessions: BridgeSessionStore
    bus: InProcessEventBus
    queue: _Queue
    substrate: RunSubstrate
    engine: RunEngine

    async def image(self, path: Path, *, run_id: str) -> None:
        """Capture plain persisted data; no locks, tasks, grants, or SDK objects."""
        await self.bus.wait_persisted(run_id)
        image = _CommittedImage(
            runs=list(self.ledger._runs.values()),
            idempotency_keys=self.ledger._idempotency_keys,
            deliveries=list(self.ledger._deliveries.values()),
            events=self.ledger._events,
            consents=list(self.consents._rows.values()),
            checkpoints=self.checkpoints._documents,
            sessions=[
                _SessionImage(
                    id=session.id,
                    title=session.title,
                    created_at=session.created_at,
                    turns=session.turns,
                    message_history=session.message_history,
                )
                for session in await self.sessions.list_sessions()
            ],
        )
        await asyncio.to_thread(path.write_text, image.model_dump_json(), encoding="utf-8")


def _boot(*, executed: list[str], model_rounds: list[bool], image_path: Path | None = None) -> _Boot:
    ledger = InMemoryRunLedger()
    consents = InMemoryConsentLedger()
    checkpoints = InMemoryStasisStore()
    sessions = BridgeSessionStore()
    if image_path is not None:
        image = _CommittedImage.model_validate_json(image_path.read_text(encoding="utf-8"))
        ledger._runs = {run.run_id: run for run in image.runs}
        ledger._idempotency_keys = image.idempotency_keys
        ledger._deliveries = {(hop.run_id, hop.enqueue_seq): hop for hop in image.deliveries}
        ledger._events = image.events
        consents._rows = {consent.id: consent for consent in image.consents}
        checkpoints._documents = image.checkpoints
        sessions._sessions = {
            session.id: SessionRecord(
                id=session.id,
                title=session.title,
                created_at=session.created_at,
                turns=session.turns,
                message_history=session.message_history,
            )
            for session in image.sessions
        }
        sessions._run_to_session = {
            turn.run_id: session.id for session in image.sessions for turn in session.turns if turn.run_id is not None
        }

    async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[dict[int, DeltaToolCall]]:
        resumed = any(isinstance(message, ModelResponse) for message in messages)
        model_rounds.append(resumed)
        if resumed:
            yield {0: DeltaToolCall(name=info.output_tools[0].name, json_args='{"answer":"settled","fragments":[]}')}
        else:
            yield {0: DeltaToolCall(name="record_note", json_args='{"note":"reviewed"}', tool_call_id="call-1")}

    async def record_note(note: str) -> str:
        executed.append(note)
        return "recorded by the inert test tool"

    toolset: FunctionToolset[LychDDeps] = FunctionToolset(id="offline-recovery-tool")
    toolset.add_function(
        record_note,
        requires_approval=True,
        metadata={CONSENT_EFFECT_ID_KEY: "test.record-note", CONSENT_EFFECT_REVISION_KEY: "1"},
    )
    bus = InProcessEventBus(ledger=ledger)
    queue = _Queue()
    workflows = builtin_workflow_registry()
    substrate = RunSubstrate(
        ledger=ledger,
        bus=bus,
        workflows=workflows,
        orchestrator=FakeOrchestrator(),
        dispatcher=FakeDispatcher(model=FunctionModel(stream_function=stream), toolsets=(toolset,)),
        context=ContextOrchestrator(registry=FakeRegistry()),
        fragments=build_fragment_registry(),
        turns=sessions,
        consents=consents,
        forge=default_forge(),
        stasis_store=checkpoints,
        queues={"runs": queue},
    )
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=workflows,
        queue_router=QueueRouter({"default": RouteRule(queue="runs", priority=70)}),
        queues=substrate.queues,
        stasis_store=checkpoints,
        consents=consents,
        release_context=substrate.context.release,
    )
    return _Boot(ledger, consents, checkpoints, sessions, bus, queue, substrate, engine)


@pytest.mark.asyncio
@pytest.mark.parametrize("approved", [True, False], ids=["approved", "denied"])
@pytest.mark.parametrize("verdict_before_park", [True, False], ids=["early-verdict", "later-verdict"])
async def test_serialized_consent_delivery_and_terminal_recovery(  # noqa: PLR0915 - one history across three crash windows
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    approved: bool,
    verdict_before_park: bool,
) -> None:
    """Every reconstruction starts at committed truth, never the graph origin."""
    monkeypatch.setattr(pydantic_ai.models, "ALLOW_MODEL_REQUESTS", False)
    executed: list[str] = []
    model_rounds: list[bool] = []
    before_park = tmp_path / "before-park.json"
    before_publication = tmp_path / "before-publication.json"
    before_cleanup = tmp_path / "before-cleanup.json"
    first = _boot(executed=executed, model_rounds=model_rounds)
    session = await first.sessions.create_session(title="Offline recovery")
    handle = await first.engine.submit(Intent(session_id=session.id, prompt="record a note", source="bridge"))
    run_id = handle.run_id
    original_park = first.ledger.park_consent

    async def capture_before_park(captured_run_id: str, consent_id: str) -> None:
        if verdict_before_park:
            await first.consents.decide(consent_id, approved=approved, decided_by="magus")
        await first.image(before_park, run_id=captured_run_id)
        await original_park(captured_run_id, consent_id)

    with monkeypatch.context() as patch:
        patch.setattr(first.ledger, "park_consent", capture_before_park)
        await perform_run({"run_substrate": first.substrate}, run_id=run_id, enqueue_seq=0)
    await first.bus.wait_persisted(run_id)
    assert executed == []
    assert model_rounds == [False]

    # Reconstruct without reusing runtime objects or broker jobs after checkpoint
    # persistence, before the Run acquired its owner. The image is the crash cut.
    second = _boot(executed=executed, model_rounds=model_rounds, image_path=before_park)
    stranded = await second.ledger.get(run_id)
    assert stranded is not None
    assert stranded.status is RunStatus.RUNNING
    assert stranded.consent_id is None
    assert await second.checkpoints.exists(run_id)
    assert await second.ledger.latest_event(run_id, RunEventKind.CONSENT) is None
    result = await reconcile_runs({"run_substrate": second.substrate})
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0}
    parked = await second.ledger.get(run_id)
    assert parked is not None
    assert parked.status is RunStatus.AWAITING_CONSENT
    assert parked.consent_id is not None
    consent_id = parked.consent_id
    assert model_rounds == [False]
    assert executed == []

    if not verdict_before_park:
        await second.consents.decide(consent_id, approved=approved, decided_by="magus")
    # A contradictory click cannot replace the committed, attributable verdict.
    verdict = await second.consents.decide(consent_id, approved=not approved, decided_by="second-client")
    assert verdict is not None
    assert verdict.status == ("granted" if approved else "denied")
    assert verdict.decided_by == "magus"
    second.queue.fail_publication = True
    result = await reconcile_consents({"run_substrate": second.substrate}, engine=second.engine)
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0}
    admitted = await second.ledger.get(run_id)
    assert admitted is not None
    assert admitted.status is RunStatus.QUEUED
    assert admitted.enqueue_seq == 1
    pending = await second.ledger.get_delivery(run_id, enqueue_seq=1)
    assert pending is not None
    assert pending.resume is True
    assert pending.state is RunDeliveryState.PENDING
    assert pending.last_error == "offline broker publication unavailable"
    await second.engine.resume_consent(consent_id)
    assert len(second.queue.attempts) == 1
    await second.image(before_publication, run_id=run_id)

    # The consent CAS survives publication loss. Startup republishes its exact key
    # and mode; neither repeated decisions nor the legacy broker flag can alter it.
    third = _boot(executed=executed, model_rounds=model_rounds, image_path=before_publication)
    result = await reconcile_runs({"run_substrate": third.substrate})
    assert result["status"] == "reconciled"
    assert result["probe_errors"] == 0
    assert list(third.queue.jobs) == [run_job_key(run_id, 1)]
    assert third.queue.attempts[0]["enqueue_seq"] == 1
    assert third.queue.attempts[0]["priority"] == 30
    assert (await perform_run({"run_substrate": third.substrate}, run_id=run_id, enqueue_seq=0))["status"] == "skipped"

    async def capture_failed_cleanup(captured_run_id: str) -> None:
        await third.image(before_cleanup, run_id=captured_run_id)
        msg = "offline checkpoint deletion unavailable"
        raise OSError(msg)

    with monkeypatch.context() as patch:
        patch.setattr(third.checkpoints, "delete", capture_failed_cleanup)
        settled = await perform_run({"run_substrate": third.substrate}, run_id=run_id, enqueue_seq=1, resume=False)
    assert settled["status"] == "done"
    assert executed == (["reviewed"] if approved else [])
    assert model_rounds == [False, True]

    # Terminal truth precedes both cleanup and terminal projection. Repair is
    # idempotent and cannot re-enter the approved tool or regenerate the answer.
    fourth = _boot(executed=executed, model_rounds=model_rounds, image_path=before_cleanup)
    terminal = await fourth.ledger.get(run_id)
    assert terminal is not None
    assert terminal.status is RunStatus.DONE
    assert terminal.enqueue_seq == 1
    assert await fourth.checkpoints.exists(run_id)
    assert await fourth.ledger.latest_event(run_id, RunEventKind.DONE) is None
    for _ in range(2):
        await _reconcile_terminal_checkpoints_at_startup(fourth.engine, required=True)
    assert not await fourth.checkpoints.exists(run_id)
    assert (await perform_run({"run_substrate": fourth.substrate}, run_id=run_id, enqueue_seq=1))["status"] == "skipped"
    events = await fourth.ledger.list_events(run_id)
    terminals = [event for event in events if event.kind is RunEventKind.DONE]
    assert len(terminals) == 1
    assert terminals[0].data == "done"
    assert len({event.seq for event in events}) == len(events)
    restored_session = await fourth.sessions.get_session(session.id)
    assert restored_session is not None
    assert len([turn for turn in restored_session.turns if turn.role == "agent"]) == 1
    assert restored_session.message_history
    assert executed == (["reviewed"] if approved else [])
    assert model_rounds == [False, True]
