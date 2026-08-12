"""The ghoul plane: perform_run drives the graph offline; reconcile heals orphans.

Offline floor: no real model request is permitted (`ALLOW_MODEL_REQUESTS = False`);
the graph runs on a `TestModel` handed through the fake dispatcher's grant.
"""
# White-box assertions + structural fakes for GrantPort/registry.
# pyright: reportPrivateUsage=false
# pyright: reportArgumentType=false

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pydantic_ai.models
import pytest
from pydantic_ai.models.test import TestModel

from lychd.agents.router import Intent
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import BRIDGE_CHAT, DELEGATED_RITE, BuiltinWorkflowRegistry, builtin_workflow_registry
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.events import InProcessEventBus, RunEventKind
from lychd.domain.cortex.ledger import ConsentAdmissionEvidence, InMemoryRunLedger
from lychd.domain.cortex.runs import RunDeliveryState, RunStatus
from lychd.domain.cortex.stasis import InMemoryStasisStore
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.ghouls.runs import (
    _DeliveryFlushOutcome,
    _flush_run_delivery_page,
    flush_run_deliveries,
    perform_run,
    reconcile_runs,
    relay_run_deliveries,
)
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


def _consent_evidence(run_id: str, consent_id: str) -> ConsentAdmissionEvidence:
    return ConsentAdmissionEvidence(
        consent_id=consent_id,
        run_id=run_id,
        status="granted",
        decided_by="test:operator",
        decided_at=datetime.now(UTC),
    )


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
    enqueued: list[dict[str, Any]] = field(default_factory=list, init=False)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        self.enqueued.append({"func": job_or_func, **kwargs})

    async def job(self, job_key: str, /) -> Any:
        self.probed.append(job_key)
        if self.probe_error is not None:
            raise self.probe_error
        return self.jobs.get(job_key)

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)


@dataclass
class _RecoveringQueue(_ProbeQueue):
    """Broker fake that becomes available while the lifespan relay is running."""

    available: bool = False
    published: asyncio.Event = field(default_factory=asyncio.Event)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        if not self.available:
            msg = "broker unavailable"
            raise ConnectionError(msg)
        await super().enqueue(job_or_func, **kwargs)
        self.published.set()


@dataclass
class _OrphanAwareQueue(_ProbeQueue):
    """Broker fake that can terminally fence a worker owned by a dead boot."""

    orphan_aborted: list[str] = field(default_factory=list)

    async def abort_orphan(self, job: Any, error: str, /) -> None:
        _ = error
        self.orphan_aborted.append(str(job.key))
        job.status = "aborted"


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
    from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT

    session = await sessions.create_session(title="t")
    intent = Intent(session_id=session.id, run_id=run_id, prompt="hello", source="bridge")
    await ledger.create(
        intent,
        workflow_name="bridge_chat",
        pattern_manifest=BRIDGE_CHAT.manifest.snapshot(),
        queue_name="runs",
        priority=70,
    )
    return intent


def _redigest_pattern(snapshot: dict[str, Any]) -> None:
    """Recompute a persisted Pattern digest after an intentional test mutation."""
    unsigned = {key: value for key, value in snapshot.items() if key != "digest"}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    snapshot["digest"] = hashlib.sha256(encoded).hexdigest()


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

    node_events = [event for event in channel._replay if event.kind is RunEventKind.NODE]
    assert [(event.data, event.meta["phase"]) for event in node_events] == [
        ("weave_context", "entered"),
        ("weave_context", "settled"),
        ("converse", "entered"),
        ("converse", "settled"),
        ("project_reply", "entered"),
        ("project_reply", "settled"),
    ]
    assert all(event.meta["pattern_revision"] == "1" for event in node_events)
    assert len({event.meta["occurrence_id"] for event in node_events}) == 3
    assert all(len(event.event_id) == 36 for event in node_events)
    # the settled agent turn landed on the session
    session_rec = await sessions.get_session(run.session_id)
    assert session_rec is not None
    settled = [t for t in session_rec.turns if t.state == "settled"]
    assert settled
    assert settled[0].content == "risen"


@pytest.mark.asyncio
async def test_perform_run_refreshes_saq_heartbeat_until_the_hop_settles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A live graph keeps SAQ's heartbeat fresh and leaves no updater after return."""
    import lychd.ghouls.runs as runs_mod

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "heartbeat")
    updated = asyncio.Event()

    class _HeartbeatJob:
        def __init__(self) -> None:
            self.updates = 0

        async def update(self) -> None:
            self.updates += 1
            updated.set()

    class _HeartbeatRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> None:
            await asyncio.wait_for(updated.wait(), timeout=1)

    job = _HeartbeatJob()
    monkeypatch.setattr(runs_mod, "RUN_JOB_HEARTBEAT_INTERVAL_S", 0.001)
    monkeypatch.setattr(runs_mod, "GraphRunner", _HeartbeatRunner)

    result = await perform_run(
        {"run_substrate": substrate, "job": job},
        run_id="heartbeat",
    )

    assert result == {"status": "done", "run_id": "heartbeat"}
    assert job.updates >= 1
    settled_updates = job.updates
    await asyncio.sleep(0.005)
    assert job.updates == settled_updates


@pytest.mark.parametrize("delivery_mode", ["fresh", "resume"])
@pytest.mark.asyncio
async def test_durable_delivery_mode_overrides_broker_payload(
    monkeypatch: pytest.MonkeyPatch,
    delivery_mode: str,
) -> None:
    """A stale broker argument cannot choose fresh execution versus checkpoint resume."""
    import lychd.ghouls.runs as runs_mod

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "mode-authority")
    durable_resume = delivery_mode == "resume"
    enqueue_seq = 0
    if durable_resume:
        assert await ledger.try_claim_run("mode-authority", enqueue_seq=0)
        await ledger.park_consent("mode-authority", "consent-mode-authority")
        admitted = await ledger.try_admit_consent(
            "mode-authority",
            consent_id="consent-mode-authority",
            evidence=_consent_evidence("mode-authority", "consent-mode-authority"),
        )
        assert admitted == 1
        enqueue_seq = admitted
        await substrate.stasis_store.replace("mode-authority", [])

    calls: list[str] = []

    class _ModeRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> None:
            calls.append("fresh")

        async def resume_graph(self, *_args: Any, **_kwargs: Any) -> None:
            calls.append("resume")

    monkeypatch.setattr(runs_mod, "GraphRunner", _ModeRunner)

    await perform_run(
        {"run_substrate": substrate},
        run_id="mode-authority",
        enqueue_seq=enqueue_seq,
        resume=not durable_resume,
    )

    assert calls == ["resume" if durable_resume else "fresh"]


@pytest.mark.asyncio
async def test_perform_run_executes_pinned_old_revision_after_active_revision_changes() -> None:
    model = TestModel(custom_output_args={"answer": "risen", "fragments": []}, call_tools=[])
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=model))
    bridge_v2 = replace(BRIDGE_CHAT, manifest=replace(BRIDGE_CHAT.manifest, revision="2"))
    substrate.workflows = BuiltinWorkflowRegistry(
        workflows=(BRIDGE_CHAT, bridge_v2, DELEGATED_RITE),
        active_revisions=((BRIDGE_CHAT.name, "2"), (DELEGATED_RITE.name, "1")),
        route_precedence=(DELEGATED_RITE.name,),
        default_name=BRIDGE_CHAT.name,
    )
    await _seed_run(ledger, sessions, "run-pinned-v1")

    result = await perform_run({"run_substrate": substrate}, run_id="run-pinned-v1")

    assert result == {"status": "done", "run_id": "run-pinned-v1"}
    run = await ledger.get("run-pinned-v1")
    assert run is not None
    assert run.status is RunStatus.DONE
    assert run.pattern_manifest["revision"] == "1"


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
    original_try_settle_claim = ledger.try_settle_claim

    class _ImmediateRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    async def delayed_terminal(
        run_id: str,
        *,
        enqueue_seq: int,
        status: RunStatus,
        error: str | None = None,
    ) -> bool:
        settled = await original_try_settle_claim(
            run_id,
            enqueue_seq=enqueue_seq,
            status=status,
            error=error,
        )
        if settled and status is RunStatus.DONE:
            committed.set()
            await release.wait()
        return settled

    monkeypatch.setattr(runs_mod, "GraphRunner", _ImmediateRunner)
    monkeypatch.setattr(ledger, "try_settle_claim", delayed_terminal)
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

        async def get(self, consent_id: str) -> Any:
            return SimpleNamespace(
                id=consent_id,
                run_id="resume-owner",
                status="granted",
                decided_by="test:operator",
                decided_at=datetime.now(UTC),
            )

        async def cancel_pending_for_run(self, run_id: str, *, decided_by: str) -> int:
            _ = (run_id, decided_by)
            return 0

    class _ParkingRunner:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_graph(self, *_args: Any, **_kwargs: Any) -> RunParked:
            return RunParked(consent_id="consent-owner", tool_name="probe")

    class _ClaimThenRaiseQueue:
        async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
            assert job_or_func == "perform_run"
            assert "resume" not in kwargs
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

    result = await perform_run({"run_substrate": substrate}, run_id="resume-owner")
    assert result == {"status": "queued", "run_id": "resume-owner"}

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
async def test_perform_run_retries_transient_failure_containment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import lychd.ghouls.runs as runs_mod

    class _FlakyConsents:
        calls = 0

        async def cancel_pending_for_run(self, run_id: str, *, decided_by: str) -> int:
            _ = (run_id, decided_by)
            self.calls += 1
            if self.calls == 1:
                msg = "consent ledger briefly unavailable"
                raise RuntimeError(msg)
            return 0

    substrate, ledger, sessions = _substrate(dispatcher=_RaisingDispatcher())
    consents = _FlakyConsents()
    substrate.consents = consents
    await _seed_run(ledger, sessions, "run_containment_retry")
    monkeypatch.setattr(runs_mod, "FAILURE_CONTAINMENT_RETRY_S", 0)

    with pytest.raises(RuntimeError):
        await perform_run({"run_substrate": substrate}, run_id="run_containment_retry")

    run = await ledger.get("run_containment_retry")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert consents.calls == 2


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
    assert "pinned Pattern unavailable" in (run.error or "")
    dones = [e for e in list(channel._replay) if e.kind is RunEventKind.DONE]
    assert len(dones) == 1
    assert dones[0].data == "failed"
    assert channel.closed is True  # F2: the stream ends instead of tailing keepalives


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "invalid_checksum",
        "drifted_snapshot",
        "implementation_drift",
        "unavailable_revision",
        "mismatched_identity",
    ],
)
async def test_perform_run_fails_honestly_when_pinned_pattern_is_unavailable(
    case: str,
) -> None:
    """A worker never executes against corrupt, drifted, or unavailable Pattern law."""
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, f"pattern-{case}")
    # Deliberately corrupt canonical storage through the adapter's private seam;
    # public reads are detached snapshots, as they are with PostgreSQL.
    run = ledger._require(f"pattern-{case}")

    if case == "invalid_checksum":
        run.pattern_manifest["digest"] = "0" * 64
    elif case == "drifted_snapshot":
        run.pattern_manifest["nodes"][0]["label"] = "Drifted station"
        _redigest_pattern(run.pattern_manifest)
    elif case == "implementation_drift":
        run.pattern_manifest["implementation_revision"] = "py.0"
        _redigest_pattern(run.pattern_manifest)
    elif case == "unavailable_revision":
        run.pattern_manifest["revision"] = "unavailable"
        _redigest_pattern(run.pattern_manifest)
    else:
        run.pattern_manifest = DELEGATED_RITE.manifest.snapshot()

    channel = substrate.bus.open(run.run_id)
    result = await perform_run({"run_substrate": substrate}, run_id=run.run_id)

    assert result == {"status": "failed", "run_id": run.run_id}
    assert run.status is RunStatus.FAILED
    assert "pinned Pattern unavailable" in (run.error or "")
    assert [event.data for event in channel._replay if event.kind is RunEventKind.DONE] == ["failed"]
    assert channel.closed is True


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
    await _settle_terminal(ledger, "race", 0, RunStatus.DONE)
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
async def test_reconcile_runs_publishes_pending_deliveries_without_age_guess() -> None:
    """Every accepted delivery is republished from truth, regardless of row age."""
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "fresh")
    await _seed_run(ledger, sessions, "old")

    result = await reconcile_runs({"run_substrate": substrate})
    assert result == {"status": "reconciled", "count": 0, "probe_errors": 0}

    for run_id in ("fresh", "old"):
        run = await ledger.get(run_id)
        delivery = await ledger.get_delivery(run_id, enqueue_seq=0)
        assert run is not None
        assert run.status is RunStatus.QUEUED
        assert delivery is not None
        assert delivery.state is RunDeliveryState.PUBLISHED


@pytest.mark.asyncio
async def test_reconcile_runs_reports_queued_run_with_missing_delivery_truth() -> None:
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "missing-delivery")
    del ledger._deliveries[("missing-delivery", 0)]

    result = await reconcile_runs({"run_substrate": substrate})

    run = await ledger.get("missing-delivery")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert result == {"status": "degraded", "count": 0, "probe_errors": 1}


@pytest.mark.asyncio
async def test_reconcile_runs_preserves_queued_with_durable_job() -> None:
    """A QUEUED row survives when its exact monotonic-hop SAQ job exists."""
    from lychd.domain.cortex.engine import run_job_key

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "durable")
    enqueue_seq = await ledger.bump_enqueue_seq("durable")
    durable = await ledger.get("durable")
    assert durable is not None

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
async def test_reconcile_rotates_preboot_active_job_with_heartbeats_disabled() -> None:
    """A dead worker's pre-claim ACTIVE record cannot strand its QUEUED Run."""
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    from lychd.domain.cortex.engine import run_job_key

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "preclaim-crash")
    queue = _OrphanAwareQueue()
    substrate.queues = {"runs": queue}
    boot_cutoff = datetime.now(UTC)
    key = run_job_key("preclaim-crash", 0)
    queue.jobs[key] = SimpleNamespace(
        key=key,
        status="active",
        started=int((boot_cutoff - timedelta(seconds=1)).timestamp() * 1000),
        timeout=0,
        heartbeat=0,
    )

    result = await reconcile_runs(
        {"run_substrate": substrate},
        boot_cutoff=boot_cutoff,
    )

    run = await ledger.get("preclaim-crash")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert run.enqueue_seq == 1
    assert queue.orphan_aborted == [key]
    assert queue.enqueued[-1]["key"] == run_job_key("preclaim-crash", 1)
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0}


@pytest.mark.asyncio
async def test_reconcile_preserves_current_boot_active_preclaim_job() -> None:
    """The boot fence never aborts a worker generation started by this process."""
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    from lychd.domain.cortex.engine import run_job_key

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "current-preclaim")
    queue = _OrphanAwareQueue()
    substrate.queues = {"runs": queue}
    boot_cutoff = datetime.now(UTC)
    key = run_job_key("current-preclaim", 0)
    queue.jobs[key] = SimpleNamespace(
        key=key,
        status="active",
        started=int((boot_cutoff + timedelta(seconds=1)).timestamp() * 1000),
        timeout=0,
        heartbeat=0,
    )

    result = await reconcile_runs(
        {"run_substrate": substrate},
        boot_cutoff=boot_cutoff,
    )

    run = await ledger.get("current-preclaim")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert run.enqueue_seq == 0
    assert queue.orphan_aborted == []
    assert queue.enqueued == []
    assert result == {"status": "reconciled", "count": 0, "probe_errors": 0}


@pytest.mark.asyncio
async def test_reconcile_runs_preserves_queued_when_broker_probe_fails() -> None:
    """A broker error is uncertainty, not evidence of an absent durable job."""
    from lychd.domain.cortex.engine import run_job_key

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "uncertain")
    enqueue_seq = await ledger.bump_enqueue_seq("uncertain")
    uncertain = await ledger.get("uncertain")
    assert uncertain is not None

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
@pytest.mark.parametrize("delivery_mode", ["fresh", "resume"])
async def test_delivery_flush_rotates_terminal_broker_record_without_changing_mode(
    delivery_mode: str,
) -> None:
    """A dead SAQ key gets a fresh sequence while fresh/resume truth stays exact."""
    from types import SimpleNamespace

    from lychd.domain.cortex.engine import run_job_key

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "terminal-job")
    resume = delivery_mode == "resume"
    enqueue_seq = 0
    if resume:
        assert await ledger.try_claim_run("terminal-job", enqueue_seq=0)
        await ledger.park_consent("terminal-job", "consent-terminal-job")
        admitted = await ledger.try_admit_consent(
            "terminal-job",
            consent_id="consent-terminal-job",
            evidence=_consent_evidence("terminal-job", "consent-terminal-job"),
        )
        assert admitted == 1
        enqueue_seq = admitted

    queue = substrate.queues["runs"]
    assert isinstance(queue, _ProbeQueue)
    queue.jobs[run_job_key("terminal-job", enqueue_seq)] = SimpleNamespace(status="failed")

    result = await flush_run_deliveries({"run_substrate": substrate})

    run = await ledger.get("terminal-job")
    assert run is not None
    assert run.enqueue_seq == enqueue_seq + 1
    old = await ledger.get_delivery("terminal-job", enqueue_seq=enqueue_seq)
    current = await ledger.get_delivery("terminal-job", enqueue_seq=enqueue_seq + 1)
    assert old is not None
    assert old.state is RunDeliveryState.SETTLED
    assert current is not None
    assert current.state is RunDeliveryState.PUBLISHED
    assert current.resume is resume
    assert queue.enqueued[-1]["key"] == run_job_key("terminal-job", enqueue_seq + 1)
    assert "resume" not in queue.enqueued[-1]
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0}


@pytest.mark.asyncio
async def test_delivery_relay_recovers_transient_broker_outage() -> None:
    """Accepted work publishes without requiring a restart after broker recovery."""
    from lychd.domain.cortex.engine import run_job_key

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "relay")
    queue = _RecoveringQueue()
    substrate.queues = {"runs": queue}
    stop = asyncio.Event()
    relay = asyncio.create_task(
        relay_run_deliveries(
            {"run_substrate": substrate},
            stop=stop,
            interval_s=0.001,
        )
    )
    await asyncio.sleep(0.01)
    queue.available = True
    await asyncio.wait_for(queue.published.wait(), timeout=1)
    stop.set()
    await relay

    delivery = await ledger.get_delivery("relay", enqueue_seq=0)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PUBLISHED
    assert delivery.publish_attempts >= 2
    assert queue.enqueued[-1]["key"] == run_job_key("relay", 0)


@pytest.mark.asyncio
async def test_delivery_page_revisits_a_clean_active_broker_job() -> None:
    from lychd.domain.cortex.engine import run_job_key

    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "active-job")
    queue = substrate.queues["runs"]
    assert isinstance(queue, _ProbeQueue)
    queue.jobs[run_job_key("active-job", 0)] = SimpleNamespace(status="active")

    result, _cursor = await _flush_run_delivery_page(
        substrate,
        after=None,
        refuse_held=False,
    )

    assert result["status"] == "reconciled"
    assert result["_revisit"] is True
    delivery = await ledger.get_delivery("active-job", enqueue_seq=0)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PUBLISHED


@pytest.mark.asyncio
async def test_delivery_page_isolates_one_exception_and_advances_later_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "row-failure-a")
    await _seed_run(ledger, sessions, "row-failure-b")
    seen: list[str] = []

    async def fake_target(
        _substrate: RunSubstrate,
        run: Any,
        *,
        refuse_held: bool,
    ) -> _DeliveryFlushOutcome:
        _ = refuse_held
        seen.append(run.run_id)
        if run.run_id == "row-failure-a":
            message = "corrupt delivery row"
            raise RuntimeError(message)
        return _DeliveryFlushOutcome(repaired=1)

    monkeypatch.setattr("lychd.ghouls.runs._delivery_target", fake_target)

    result = await flush_run_deliveries({"run_substrate": substrate})

    assert seen == ["row-failure-a", "row-failure-b"]
    assert result == {"status": "degraded", "count": 1, "probe_errors": 1}


@pytest.mark.asyncio
async def test_delivery_relay_retries_a_degraded_page_without_stalling_the_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    calls: list[tuple[datetime, str] | None] = []
    stop = asyncio.Event()
    first_page_end = (datetime.now(UTC), "page-1-end")

    async def fake_page(
        *_args: Any,
        after: tuple[datetime, str] | None,
        **_kwargs: Any,
    ) -> tuple[dict[str, int | str], tuple[datetime, str]]:
        calls.append(after)
        if len(calls) == 3:
            stop.set()
        return (
            {"status": "degraded", "count": 0, "probe_errors": 1},
            first_page_end,
        )

    monkeypatch.setattr("lychd.ghouls.runs._flush_run_delivery_page", fake_page)
    substrate, _, _ = _substrate(dispatcher=FakeDispatcher(model=TestModel()))

    await relay_run_deliveries(
        {"run_substrate": substrate},
        stop=stop,
        interval_s=0.001,
    )

    assert calls == [None, None, first_page_end]


@pytest.mark.asyncio
async def test_delivery_relay_revisits_a_held_page_after_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    calls: list[tuple[datetime, str] | None] = []
    stop = asyncio.Event()
    first_page_end = (datetime.now(UTC), "held-page-end")

    async def fake_page(
        *_args: Any,
        after: tuple[datetime, str] | None,
        **_kwargs: Any,
    ) -> tuple[dict[str, Any], tuple[datetime, str] | None]:
        calls.append(after)
        if len(calls) == 1:
            return (
                {
                    "status": "reconciled",
                    "count": 0,
                    "probe_errors": 0,
                    "_revisit": True,
                },
                first_page_end,
            )
        if len(calls) == 2:
            return (
                {
                    "status": "reconciled",
                    "count": 0,
                    "probe_errors": 0,
                    "_revisit": False,
                },
                first_page_end,
            )
        stop.set()
        return ({"status": "reconciled", "count": 0, "probe_errors": 0}, None)

    monkeypatch.setattr("lychd.ghouls.runs._flush_run_delivery_page", fake_page)
    substrate, _, _ = _substrate(dispatcher=FakeDispatcher(model=TestModel()))

    await relay_run_deliveries(
        {"run_substrate": substrate},
        stop=stop,
        interval_s=0.001,
    )

    assert calls == [None, None, first_page_end]


@pytest.mark.asyncio
async def test_delivery_relay_retry_exception_does_not_stall_the_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    calls: list[tuple[datetime, str] | None] = []
    stop = asyncio.Event()
    first_page_end = (datetime.now(UTC), "page-1-end")

    async def fake_page(
        *_args: Any,
        after: tuple[datetime, str] | None,
        **_kwargs: Any,
    ) -> tuple[dict[str, int | str], tuple[datetime, str] | None]:
        calls.append(after)
        if len(calls) == 2:
            message = "retry page unavailable"
            raise RuntimeError(message)
        if len(calls) == 3:
            stop.set()
            return ({"status": "reconciled", "count": 0, "probe_errors": 0}, None)
        return (
            {"status": "degraded", "count": 0, "probe_errors": 1},
            first_page_end,
        )

    monkeypatch.setattr("lychd.ghouls.runs._flush_run_delivery_page", fake_page)
    substrate, _, _ = _substrate(dispatcher=FakeDispatcher(model=TestModel()))

    await relay_run_deliveries(
        {"run_substrate": substrate},
        stop=stop,
        interval_s=0.001,
    )

    assert calls == [None, None, first_page_end]


@pytest.mark.asyncio
async def test_delivery_relay_fairly_retries_multiple_blocked_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    calls: list[tuple[datetime, str] | None] = []
    stop = asyncio.Event()
    first_page_end = (datetime.now(UTC), "page-1-end")
    second_page_end = (datetime.now(UTC), "page-2-end")

    async def fake_page(
        *_args: Any,
        after: tuple[datetime, str] | None,
        **_kwargs: Any,
    ) -> tuple[dict[str, int | str], tuple[datetime, str] | None]:
        calls.append(after)
        call = len(calls)
        if call == 1:
            return ({"status": "degraded", "count": 0, "probe_errors": 1}, first_page_end)
        if call == 2:
            return ({"status": "degraded", "count": 0, "probe_errors": 1}, first_page_end)
        if call == 3:
            return ({"status": "degraded", "count": 0, "probe_errors": 1}, second_page_end)
        if call == 4:
            return ({"status": "degraded", "count": 0, "probe_errors": 1}, first_page_end)
        if call == 5:
            return ({"status": "reconciled", "count": 0, "probe_errors": 0}, None)
        stop.set()
        return ({"status": "reconciled", "count": 1, "probe_errors": 0}, second_page_end)

    monkeypatch.setattr("lychd.ghouls.runs._flush_run_delivery_page", fake_page)
    substrate, _, _ = _substrate(dispatcher=FakeDispatcher(model=TestModel()))

    await relay_run_deliveries(
        {"run_substrate": substrate},
        stop=stop,
        interval_s=0.001,
    )

    assert calls == [None, None, first_page_end, None, second_page_end, first_page_end]


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
    # Backdate canonical storage to model a run claimed by the prior process.
    old = ledger._require("old")
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
