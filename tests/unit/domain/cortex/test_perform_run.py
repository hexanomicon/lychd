"""The ghoul plane: perform_run drives the graph offline; reconcile heals orphans.

Offline floor: no real model request is permitted (`ALLOW_MODEL_REQUESTS = False`);
the graph runs on a `TestModel` handed through the fake dispatcher's grant.
"""
# White-box assertions + structural fakes for GrantPort/registry.
# pyright: reportPrivateUsage=false
# pyright: reportArgumentType=false

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
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
from lychd.domain.cortex.stasis import InMemoryStasisStore
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


@dataclass
class _ProbeQueue:
    """Minimal durable-queue fake for reconcile's exact-key probe."""

    jobs: dict[str, Any] = field(default_factory=dict)
    probe_error: Exception | None = None
    probed: list[str] = field(default_factory=list, init=False)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        _ = (job_or_func, kwargs)

    async def job(self, job_key: str, /) -> Any:
        self.probed.append(job_key)
        if self.probe_error is not None:
            raise self.probe_error
        return self.jobs.get(job_key)

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)


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
        turns=sessions,
        forge=default_forge(),
        queues={"runs": _ProbeQueue()},
        stasis_store=InMemoryStasisStore(),
    )
    return substrate, ledger, sessions


async def _seed_run(ledger: InMemoryRunLedger, sessions: BridgeSessionStore, run_id: str) -> Intent:
    session = await sessions.create_session(title="t")
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
    session_rec = await sessions.get_session(run.session_id)
    assert session_rec is not None
    settled = [t for t in session_rec.turns if t.state == "settled"]
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
async def test_concurrent_redelivery_executes_graph_exactly_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two deliveries may read the same job, but only the atomic claim winner runs."""
    import lychd.ghouls.runs as runs_mod

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "redelivery")
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    class _BlockingRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> None:
            nonlocal calls
            calls += 1
            entered.set()
            await release.wait()

    monkeypatch.setattr(runs_mod, "GraphRunner", _BlockingRunner)
    winner = asyncio.create_task(perform_run({"run_substrate": substrate}, run_id="redelivery"))
    await entered.wait()
    loser = await perform_run({"run_substrate": substrate}, run_id="redelivery")
    release.set()
    settled = await winner

    assert loser["status"] == "skipped"
    assert settled["status"] == "done"
    assert calls == 1


@pytest.mark.asyncio
async def test_cancellation_during_committed_claim_settles_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancellation cannot strand RUNNING after the claim CAS committed."""
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "claim-cancel")
    channel = substrate.bus.open("claim-cancel")
    original_claim = ledger.try_claim_run
    committed = asyncio.Event()
    release = asyncio.Event()

    async def delayed_claim(run_id: str, *, enqueue_seq: int) -> bool:
        claimed = await original_claim(run_id, enqueue_seq=enqueue_seq)
        committed.set()
        await release.wait()
        return claimed

    monkeypatch.setattr(ledger, "try_claim_run", delayed_claim)
    task = asyncio.create_task(perform_run({"run_substrate": substrate}, run_id="claim-cancel"))
    await committed.wait()

    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task

    run = await ledger.get("claim-cancel")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert channel.closed is True


@pytest.mark.asyncio
async def test_unexpected_worker_cancellation_settles_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A worker cancellation cannot strand durable truth in RUNNING."""
    import lychd.ghouls.runs as runs_mod

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "cancelled-worker")
    entered = asyncio.Event()

    class _BlockingRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> None:
            entered.set()
            await asyncio.Event().wait()

    monkeypatch.setattr(runs_mod, "GraphRunner", _BlockingRunner)
    task = asyncio.create_task(perform_run({"run_substrate": substrate}, run_id="cancelled-worker"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    run = await ledger.get("cancelled-worker")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert run.error == "run worker cancelled"


@pytest.mark.asyncio
async def test_stale_delivery_sequence_is_skipped_before_claim() -> None:
    """A broker job from a compensated consent hop cannot claim the retried row."""
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "stale-hop")

    result = await perform_run(
        {"run_substrate": substrate},
        run_id="stale-hop",
        enqueue_seq=1,
    )

    assert result == {"status": "skipped", "run_id": "stale-hop"}
    run = await ledger.get("stale-hop")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert run.enqueue_seq == 0


@pytest.mark.asyncio
async def test_cancellation_after_terminal_commit_still_emits_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cancelled await cannot orphan DONE after the status commit already won."""
    import lychd.ghouls.runs as runs_mod

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "terminal-cancel")
    channel = substrate.bus.open("terminal-cancel")
    committed = asyncio.Event()
    release = asyncio.Event()
    original_set_status = ledger.set_status

    class _ImmediateRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    async def delayed_terminal(
        run_id: str,
        status: RunStatus,
        *,
        error: str | None = None,
    ) -> None:
        await original_set_status(run_id, status, error=error)
        if status is RunStatus.DONE:
            committed.set()
            await release.wait()

    monkeypatch.setattr(runs_mod, "GraphRunner", _ImmediateRunner)
    monkeypatch.setattr(ledger, "set_status", delayed_terminal)
    task = asyncio.create_task(perform_run({"run_substrate": substrate}, run_id="terminal-cancel"))
    await committed.wait()

    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task

    run = await ledger.get("terminal-cancel")
    assert run is not None
    assert run.status is RunStatus.DONE
    assert not await substrate.stasis_store.exists("terminal-cancel")
    dones = [event for event in channel._replay if event.kind is RunEventKind.DONE]
    assert [event.data for event in dones] == [RunStatus.DONE.value]


@pytest.mark.asyncio
async def test_cancellation_during_terminal_cleanup_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Best-effort cleanup completes, then the worker still propagates cancellation."""
    import lychd.ghouls.runs as runs_mod

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "cleanup-cancel")
    channel = substrate.bus.open("cleanup-cancel")
    cleanup_entered = asyncio.Event()
    cleanup_release = asyncio.Event()
    original_delete = substrate.stasis_store.delete

    class _ImmediateRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    async def delayed_delete(run_id: str) -> None:
        cleanup_entered.set()
        await cleanup_release.wait()
        await original_delete(run_id)

    monkeypatch.setattr(runs_mod, "GraphRunner", _ImmediateRunner)
    monkeypatch.setattr(substrate.stasis_store, "delete", delayed_delete)
    task = asyncio.create_task(perform_run({"run_substrate": substrate}, run_id="cleanup-cancel"))
    await cleanup_entered.wait()

    task.cancel()
    cleanup_release.set()
    with pytest.raises(asyncio.CancelledError):
        await task

    run = await ledger.get("cleanup-cancel")
    assert run is not None
    assert run.status is RunStatus.DONE
    assert not await substrate.stasis_store.exists("cleanup-cancel")
    dones = [event for event in channel._replay if event.kind is RunEventKind.DONE]
    assert [event.data for event in dones] == [RunStatus.DONE.value]


@pytest.mark.asyncio
async def test_cleanup_failure_cannot_hide_committed_failed_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checkpoint cleanup is retryable bookkeeping, never a gate on terminal DONE."""
    import lychd.ghouls.runs as runs_mod

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "cleanup-fail")
    channel = substrate.bus.open("cleanup-fail")
    await substrate.stasis_store.replace("cleanup-fail", [])

    class _FailingRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> None:
            msg = "graph failed"
            raise RuntimeError(msg)

    async def fail_delete(_run_id: str) -> None:
        msg = "checkpoint store unavailable"
        raise RuntimeError(msg)

    monkeypatch.setattr(runs_mod, "GraphRunner", _FailingRunner)
    monkeypatch.setattr(substrate.stasis_store, "delete", fail_delete)

    with pytest.raises(RuntimeError, match="graph failed"):
        await perform_run({"run_substrate": substrate}, run_id="cleanup-fail")

    run = await ledger.get("cleanup-fail")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert await substrate.stasis_store.exists("cleanup-fail")  # retained for reconciliation to retry cleanup
    dones = [event for event in channel._replay if event.kind is RunEventKind.DONE]
    assert [event.data for event in dones] == [RunStatus.FAILED.value]


@pytest.mark.asyncio
async def test_api_abort_cancellation_wins_over_worker_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """An abort-triggered CancelledError waits for durable CANCELLED, never writes FAILED."""
    import lychd.ghouls.runs as runs_mod
    from lychd.domain.cortex.engine import QueueRouter, RunEngine

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "api-cancel")
    channel = substrate.bus.open("api-cancel")
    entered = asyncio.Event()

    class _BlockingRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> None:
            entered.set()
            await asyncio.Event().wait()

    class _AbortQueue:
        worker: asyncio.Task[dict[str, Any]] | None = None

        async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
            _ = (job_or_func, kwargs)

        async def job(self, job_key: str, /) -> Any:
            return {"key": job_key}

        async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
            _ = (job, error, ttl)
            assert self.worker is not None
            self.worker.cancel()
            # Reproduce the dangerous window: the worker handles CancelledError
            # before RunEngine can return from abort and commit CANCELLED.
            await asyncio.sleep(0)

    monkeypatch.setattr(runs_mod, "GraphRunner", _BlockingRunner)
    queue = _AbortQueue()
    substrate.queues = {"runs": queue}
    engine = RunEngine(
        ledger=ledger,
        bus=substrate.bus,
        workflows=substrate.workflows,
        queue_router=QueueRouter(),
        queues=substrate.queues,
        cancellations=substrate.cancellations,
        stasis_store=substrate.stasis_store,
    )
    worker = asyncio.create_task(perform_run({"run_substrate": substrate}, run_id="api-cancel"))
    queue.worker = worker
    await entered.wait()

    await engine.cancel("api-cancel")
    with pytest.raises(asyncio.CancelledError):
        await worker

    run = await ledger.get("api-cancel")
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    assert run.error is None
    assert not await substrate.stasis_store.exists("api-cancel")
    dones = [event for event in channel._replay if event.kind is RunEventKind.DONE]
    assert [event.data for event in dones] == [RunStatus.CANCELLED.value]


@pytest.mark.asyncio
async def test_old_park_hop_cannot_fail_resume_that_already_claimed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lost resume-publish reply cannot let the parked hop fail its successor."""
    import lychd.ghouls.runs as runs_mod
    from lychd.domain.cortex.runs import RunParked

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "resume-owner")
    await substrate.stasis_store.replace("resume-owner", [])
    substrate.context._cache["resume-owner"] = object()

    class _DecidedConsents:
        async def verdict(self, consent_id: str) -> bool:
            _ = consent_id
            return True

    class _ParkingRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> RunParked:
            return RunParked(consent_id="consent-owner", tool_name="probe")

    class _ClaimThenRaiseQueue:
        async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
            assert job_or_func == "perform_run"
            assert kwargs["resume"] is True
            assert (
                await ledger.try_claim_run(
                    str(kwargs["run_id"]),
                    enqueue_seq=int(kwargs["enqueue_seq"]),
                )
                is True
            )
            msg = "broker reply lost after resume claim"
            raise RuntimeError(msg)

        async def job(self, job_key: str, /) -> Any:
            _ = job_key
            return None

        async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
            _ = (job, error, ttl)

    substrate.consents = _DecidedConsents()
    substrate.queues = {"runs": _ClaimThenRaiseQueue()}
    monkeypatch.setattr(runs_mod, "GraphRunner", _ParkingRunner)

    with pytest.raises(RuntimeError, match="broker reply lost after resume claim"):
        await perform_run({"run_substrate": substrate}, run_id="resume-owner")

    run = await ledger.get("resume-owner")
    assert run is not None
    assert run.status is RunStatus.RUNNING
    assert run.enqueue_seq == 1
    assert run.error is None
    assert await substrate.stasis_store.exists("resume-owner")
    assert "resume-owner" in substrate.context._cache
    session = await sessions.get_session(run.session_id)
    assert session is not None
    assert not any(turn.state == "failed" for turn in session.turns)


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
    assert not await substrate.stasis_store.exists("run_3")

    dones = [e for e in list(channel._replay) if e.kind is RunEventKind.DONE]
    assert len(dones) == 1
    assert dones[0].data == "failed"
    # H6: the context floor was released on the failure path (no per-run leak).
    assert "run_3" not in substrate.context._cache


@pytest.mark.asyncio
async def test_perform_run_unknown_workflow_emits_terminal_and_closes() -> None:
    """An unknown workflow settles FAILED, emits ONE terminal DONE, and CLOSES the channel (F2).

    The early-fail branch used to `return` before the try/finally — it emitted no
    terminal on some paths and never closed the channel, so a subscriber tailed
    keepalives forever. Now it routes through the single terminal-emit-and-close.
    """
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    session = await sessions.create_session(title="t")
    intent = Intent(session_id=session.id, run_id="run_uw", prompt="hi", source="bridge")
    await ledger.create(intent, workflow_name="does_not_exist", queue_name="runs", priority=70)
    channel = substrate.bus.open("run_uw")  # hold the ref before the finally drops it

    result = await perform_run({"run_substrate": substrate}, run_id="run_uw")
    assert result["status"] == "failed"

    run = await ledger.get("run_uw")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert "unknown workflow" in (run.error or "")
    dones = [e for e in list(channel._replay) if e.kind is RunEventKind.DONE]
    assert len(dones) == 1
    assert dones[0].data == "failed"
    assert channel.closed is True  # F2: the stream ends instead of tailing keepalives


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
async def test_reconcile_runs_preserves_aged_queued_with_durable_job() -> None:
    """An old QUEUED row survives when its exact monotonic-hop SAQ job exists."""
    from datetime import UTC, datetime, timedelta

    from lychd.domain.cortex.engine import run_job_key
    from lychd.ghouls.runs import RECONCILE_QUEUED_AFTER_S

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "durable")
    enqueue_seq = await ledger.bump_enqueue_seq("durable")
    durable = await ledger.get("durable")
    assert durable is not None
    durable.created_at = datetime.now(UTC) - timedelta(seconds=RECONCILE_QUEUED_AFTER_S + 60)

    queue = substrate.queues["runs"]
    assert isinstance(queue, _ProbeQueue)
    key = run_job_key("durable", enqueue_seq)
    queue.jobs[key] = object()

    result = await reconcile_runs({"run_substrate": substrate})

    kept = await ledger.get("durable")
    assert kept is not None
    assert kept.status is RunStatus.QUEUED
    assert queue.probed == [key]
    assert result == {"status": "reconciled", "count": 0, "probe_errors": 0}


@pytest.mark.asyncio
async def test_reconcile_runs_preserves_queued_when_broker_probe_fails() -> None:
    """A broker error is uncertainty, not evidence of an absent durable job."""
    from datetime import UTC, datetime, timedelta

    from lychd.domain.cortex.engine import run_job_key
    from lychd.ghouls.runs import RECONCILE_QUEUED_AFTER_S

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "uncertain")
    enqueue_seq = await ledger.bump_enqueue_seq("uncertain")
    uncertain = await ledger.get("uncertain")
    assert uncertain is not None
    uncertain.created_at = datetime.now(UTC) - timedelta(seconds=RECONCILE_QUEUED_AFTER_S + 60)

    queue = substrate.queues["runs"]
    assert isinstance(queue, _ProbeQueue)
    queue.probe_error = ConnectionError("broker unavailable")

    result = await reconcile_runs({"run_substrate": substrate})

    kept = await ledger.get("uncertain")
    assert kept is not None
    assert kept.status is RunStatus.QUEUED
    assert queue.probed == [run_job_key("uncertain", enqueue_seq)]
    assert result == {"status": "degraded", "count": 0, "probe_errors": 1}


@pytest.mark.asyncio
async def test_reconcile_respects_boot_cutoff_and_deletes_checkpoint() -> None:
    """Boot-gate: a run started AFTER the cutoff survives; a pre-boot orphan is swept and its checkpoint deleted."""
    from datetime import UTC, datetime, timedelta

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "old")
    await _seed_run(ledger, sessions, "new")
    await ledger.set_status("old", RunStatus.RUNNING)
    await ledger.set_status("new", RunStatus.RUNNING)  # started_at = now (this boot)

    # Give "old" an orphaned durable checkpoint (as an AWAITING_HARDWARE crash would).
    await substrate.stasis_store.replace("old", [])
    old = await ledger.get("old")
    assert old is not None
    assert old.started_at is not None
    old.started_at = datetime.now(UTC) - timedelta(seconds=30)  # predates the boot cutoff

    boot_cutoff = datetime.now(UTC) - timedelta(seconds=10)  # sits between the two starts
    result = await reconcile_runs({"run_substrate": substrate}, boot_cutoff=boot_cutoff)
    assert result["count"] == 1

    swept = await ledger.get("old")
    assert swept is not None
    assert swept.status is RunStatus.FAILED
    assert not await substrate.stasis_store.exists("old")
    kept = await ledger.get("new")
    assert kept is not None
    assert kept.status is RunStatus.RUNNING  # F3: a run this boot claimed is never swept


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
