"""The ghoul plane: perform_run drives the graph offline; reconcile heals orphans.

Offline floor: no real model request is permitted (`ALLOW_MODEL_REQUESTS = False`);
the graph runs on a `TestModel` handed through the fake dispatcher's grant.
"""
# White-box assertions + structural fakes for GrantPort/registry.
# pyright: reportPrivateUsage=false
# pyright: reportArgumentType=false

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pydantic_ai.models
import pytest
from pydantic_ai.models.test import TestModel

from lychd.agents.router import Intent
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.events import InProcessEventBus, RunEventKind
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.ghouls.runs import perform_run, reconcile_runs
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


@dataclass
class _RaisingLease:
    family: Any

    async def __aenter__(self) -> Any:
        msg = f"no capability for {self.family}"
        raise RuntimeError(msg)

    async def __aexit__(self, *exc: object) -> None:
        """No-op teardown (entry always raised)."""


@dataclass
class _RaisingDispatcher:
    """A GrantPort whose lease CM always fails on entry (forces a run failure)."""

    def lease_grant(self, *, family: Any, run_id: str, **_kwargs: Any) -> _RaisingLease:
        _ = (run_id, _kwargs)
        return _RaisingLease(family)


def _substrate(*, dispatcher: Any) -> tuple[RunSubstrate, InMemoryRunLedger, BridgeSessionStore]:
    # honor_intent_run_id: test-only seam so these tests can key off stable seeded ids
    # (R4: production always mints; identity is the ledger's, not the advisory field).
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    sessions = BridgeSessionStore()
    substrate = RunSubstrate(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        orchestrator=FakeOrchestrator(),
        dispatcher=dispatcher,
        context=ContextOrchestrator(registry=FakeRegistry()),
        fragments=build_fragment_registry(),
        sessions=sessions,
        forge=default_forge(),
    )
    return substrate, ledger, sessions


async def _seed_run(ledger: InMemoryRunLedger, sessions: BridgeSessionStore, run_id: str) -> Intent:
    session = sessions.create_session(title="t")
    intent = Intent(session_id=session.id, run_id=run_id, prompt="hello", source="bridge")
    await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=70)
    return intent


@pytest.mark.asyncio
async def test_perform_run_happy_path_trail_and_terminal_done() -> None:
    """A claimed run goes QUEUED→RUNNING→DONE and emits exactly one terminal DONE."""
    model = TestModel(custom_output_args={"answer": "risen", "fragments": []}, call_tools=[])
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=model))
    await _seed_run(ledger, sessions, "run_1")

    # Hold the channel ref BEFORE the run: perform_run's finally closes + drops it
    # (H4), so a post-run `bus.open` would mint a fresh empty channel.
    channel = substrate.bus.open("run_1")

    result = await perform_run({"run_substrate": substrate}, run_id="run_1")
    assert result["status"] == "done"

    run = await ledger.get("run_1")
    assert run is not None
    assert run.status is RunStatus.DONE
    assert run.started_at is not None
    assert run.finished_at is not None

    dones = [e for e in list(channel._replay) if e.kind is RunEventKind.DONE]
    assert len(dones) == 1
    assert dones[0].data == "done"
    # the settled agent turn landed on the session
    settled = [t for t in sessions.get_session(run.session_id).turns if t.state == "settled"]  # type: ignore[union-attr]
    assert settled
    assert settled[0].content == "risen"


@pytest.mark.asyncio
async def test_perform_run_skips_non_queued() -> None:
    """A stale / duplicate claim (run not QUEUED) is skipped without side effects."""
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "run_2")
    await ledger.set_status("run_2", RunStatus.RUNNING)  # already claimed

    result = await perform_run({"run_substrate": substrate}, run_id="run_2")
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_perform_run_failure_marks_failed_and_emits_done() -> None:
    """A node failure marks FAILED, writes a fault turn, and still emits a terminal DONE."""
    substrate, ledger, sessions = _substrate(dispatcher=_RaisingDispatcher())
    await _seed_run(ledger, sessions, "run_3")
    channel = substrate.bus.open("run_3")  # hold the ref before the finally drops it (H4)
    # H6: seed a cached context floor; the failure path must release it (no leak).
    substrate.context._cache["run_3"] = object()

    with pytest.raises(RuntimeError):
        await perform_run({"run_substrate": substrate}, run_id="run_3")

    run = await ledger.get("run_3")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert run.error is not None

    dones = [e for e in list(channel._replay) if e.kind is RunEventKind.DONE]
    assert len(dones) == 1
    assert dones[0].data == "failed"
    # H6: the context floor was released on the failure path (no per-run leak).
    assert "run_3" not in substrate.context._cache


@pytest.mark.asyncio
async def test_cancel_racing_completion_yields_one_terminal_and_cancelled() -> None:
    """Cancel racing completion resolves to exactly ONE terminal event + a CANCELLED row (F2/H3).

    The race: the ghoul finishes its graph while `engine.cancel` has already written
    the terminal CANCELLED. The completion tail's DONE write hits the CAS/transition
    guard, is caught as benign (cancel won), and the finally's terminal re-emit is
    dropped by the channel's closed-guard — so the channel carries a single terminal
    (DONE carrying the CANCELLED status) and the row stays CANCELLED.
    """
    from lychd.domain.cortex.engine import QueueRouter, RunEngine
    from lychd.ghouls.runs import _settle_terminal

    class _CancelQueue:
        async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
            _ = (job_or_func, kwargs)

        async def job(self, job_key: str, /) -> Any:
            return {"key": job_key}

        async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
            _ = (job, error, ttl)

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "race")
    channel = substrate.bus.open("race")  # hold the ref before it is closed + dropped
    # perform_run captures its emitter EARLY (bound to this channel object); the
    # finally re-emits through that same emitter, so a re-emit after cancel closed the
    # channel is dropped by the closed-guard even though cancel dropped it from _channels.
    ghoul_emitter = substrate.bus.emitter("race")

    # The ghoul has claimed the run (QUEUED→RUNNING).
    await ledger.set_status("race", RunStatus.RUNNING)

    # Cancel WINS the race: writes CANCELLED, emits the terminal DONE, closes the channel.
    engine = RunEngine(
        ledger=ledger,
        bus=substrate.bus,
        workflows=substrate.workflows,
        queue_router=QueueRouter(),
        queues={"runs": _CancelQueue()},
    )
    await engine.cancel("race")

    # The ghoul's completion tail loses: the DONE write is caught as benign, and the
    # finally's terminal re-emit is dropped by the closed-guard.
    await _settle_terminal(ledger, "race", RunStatus.DONE)
    terminal = await ledger.get("race")
    assert terminal is not None
    ghoul_emitter.done(terminal.status.value)  # finally's re-emit → dropped by closed-guard

    run = await ledger.get("race")
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    dones = [e for e in list(channel._replay) if e.kind is RunEventKind.DONE]
    assert len(dones) == 1  # exactly one terminal event
    assert dones[0].data == "cancelled"


@pytest.mark.asyncio
async def test_perform_run_threads_run_priority_and_parks_ledger_around_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O5: perform_run threads float(run.priority) and writes RUNNING→AWAITING_HARDWARE→RUNNING.

    A GraphRunner spy captures the signal_priority + stasis callbacks and drives one
    park, observing the ledger flip AWAITING_HARDWARE while parked, then RUNNING again.
    """
    import lychd.ghouls.runs as runs_mod
    from lychd.domain.cortex.runs import RunStatus

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "prio")  # seeded with priority=70

    captured: dict[str, Any] = {}

    class _SpyRunner:
        def __init__(self, *, orchestrator: Any, persistence: Any, signal_priority: float = 100.0, **cbs: Any) -> None:
            _ = (orchestrator, persistence)
            captured["signal_priority"] = signal_priority
            captured["on_enter"] = cbs["on_stasis_enter"]
            captured["on_exit"] = cbs["on_stasis_exit"]

        async def run_graph(self, *_a: Any, **_k: Any) -> None:
            await captured["on_enter"]()
            parked = await ledger.get("prio")
            captured["parked_status"] = parked.status if parked else None
            await captured["on_exit"]()
            resumed = await ledger.get("prio")
            captured["resumed_status"] = resumed.status if resumed else None

    monkeypatch.setattr(runs_mod, "GraphRunner", _SpyRunner)

    result = await perform_run({"run_substrate": substrate}, run_id="prio")

    assert result["status"] == "done"
    assert captured["signal_priority"] == 70.0  # == float(run.priority)
    assert captured["parked_status"] is RunStatus.AWAITING_HARDWARE  # RUNNING → AWAITING_HARDWARE
    assert captured["resumed_status"] is RunStatus.RUNNING  # AWAITING_HARDWARE → RUNNING


@pytest.mark.asyncio
async def test_reconcile_runs_sweeps_aged_queued() -> None:
    """reconcile_runs fails a QUEUED row older than the sweep window (F3/F9/H2)."""
    from datetime import UTC, datetime, timedelta

    from lychd.ghouls.runs import RECONCILE_QUEUED_AFTER_S

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "fresh")  # young QUEUED — must survive
    await _seed_run(ledger, sessions, "stale")  # aged QUEUED — must be swept
    stale = await ledger.get("stale")
    assert stale is not None
    stale.created_at = datetime.now(UTC) - timedelta(seconds=RECONCILE_QUEUED_AFTER_S + 60)

    result = await reconcile_runs({"run_substrate": substrate})
    assert result["count"] == 1

    swept = await ledger.get("stale")
    assert swept is not None
    assert swept.status is RunStatus.FAILED
    assert swept.error == "enqueue lost"
    fresh = await ledger.get("fresh")
    assert fresh is not None
    assert fresh.status is RunStatus.QUEUED  # untouched


@pytest.mark.asyncio
async def test_reconcile_runs_fails_orphaned_running() -> None:
    """reconcile_runs marks orphaned RUNNING rows FAILED and emits their terminal DONE."""
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "orphan")
    await ledger.set_status("orphan", RunStatus.RUNNING)  # crash left it here
    # Hold the channel ref BEFORE the sweep: R2 now closes + drops the reconciled
    # channel (it used to leak), so a post-sweep `bus.open` would mint a fresh
    # unclosed one and hide the close.
    channel = substrate.bus.open("orphan")

    result = await reconcile_runs({"run_substrate": substrate})
    assert result["count"] == 1

    run = await ledger.get("orphan")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert run.error == "ghoul lost"
    assert channel.closed is True
    # R2: the reconciled channel was dropped, not leaked — reopening mints a fresh one.
    assert substrate.bus.open("orphan") is not channel
