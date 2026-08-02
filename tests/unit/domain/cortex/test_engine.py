"""RunEngine.submit routing + enqueue-key discipline + cancel; QueueRouter resolution."""
# White-box assertions read RunChannel._replay directly.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

from lychd.agents.router import Intent
from lychd.agents.workflows import builtin_workflow_registry
from lychd.domain.cortex.engine import QueueRouter, RunEngine, enqueue_run, run_job_key
from lychd.domain.cortex.events import InProcessEventBus, RunEventKind
from lychd.domain.cortex.ledger import InMemoryRunLedger, RunAdmissionConflictError
from lychd.domain.cortex.runs import RunDeliveryState, RunStatus


@dataclass
class _FakeJob:
    key: str


@dataclass
class _FakeQueue:
    """Records enqueue calls; hands back an abortable job by key."""

    enqueued: list[dict[str, Any]] = field(default_factory=list)
    aborted: list[str] = field(default_factory=list)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        self.enqueued.append({"func": job_or_func, **kwargs})
        return _FakeJob(key=str(kwargs.get("key", "")))

    async def job(self, job_key: str, /) -> Any:
        return _FakeJob(key=job_key)

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (error, ttl)
        self.aborted.append(job.key)


@dataclass
class _FailingQueue:
    """A queue whose enqueue always raises (broker down / unknown function)."""

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        _ = (job_or_func, kwargs)
        msg = "broker down"
        raise RuntimeError(msg)

    async def job(self, job_key: str, /) -> Any:
        _ = job_key
        return None

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)


@dataclass
class _CancellationQueue:
    """An enqueue that remains suspended until its caller is cancelled."""

    entered: asyncio.Event = field(default_factory=asyncio.Event)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        _ = (job_or_func, kwargs)
        self.entered.set()
        await asyncio.Event().wait()

    async def job(self, job_key: str, /) -> Any:
        _ = job_key
        return None

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)


@dataclass
class _ClaimThenRaiseQueue:
    """Simulate an accepted publication whose worker wins before the error returns."""

    ledger: InMemoryRunLedger

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        _ = job_or_func
        assert (
            await self.ledger.try_claim_run(
                str(kwargs["run_id"]),
                enqueue_seq=int(kwargs["enqueue_seq"]),
            )
            is True
        )
        message = "broker reply lost after claim"
        raise RuntimeError(message)

    async def job(self, job_key: str, /) -> Any:
        _ = job_key
        return None

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)


@dataclass
class _LatePublicationQueue:
    """Accept a job only after cancellation's first broker probe has passed."""

    entered: asyncio.Event = field(default_factory=asyncio.Event)
    release: asyncio.Event = field(default_factory=asyncio.Event)
    jobs: dict[str, _FakeJob] = field(default_factory=dict)
    aborted: list[str] = field(default_factory=list)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> _FakeJob:
        _ = job_or_func
        self.entered.set()
        await self.release.wait()
        job = _FakeJob(key=str(kwargs["key"]))
        self.jobs[job.key] = job
        return job

    async def job(self, job_key: str, /) -> _FakeJob | None:
        return self.jobs.get(job_key)

    async def abort(self, job: _FakeJob, error: str, /, ttl: float = 5) -> None:
        _ = (error, ttl)
        self.aborted.append(job.key)
        self.jobs.pop(job.key, None)


@dataclass
class _FlakyLatePublicationQueue(_LatePublicationQueue):
    """Lose the first late-job abort, then acknowledge its retry."""

    abort_attempts: int = 0

    async def abort(self, job: _FakeJob, error: str, /, ttl: float = 5) -> None:
        self.abort_attempts += 1
        if self.abort_attempts == 1:
            msg = "transient late-job abort failure"
            raise RuntimeError(msg)
        await super().abort(job, error, ttl)


@dataclass
class _CancellableFenceQueue(_LatePublicationQueue):
    """Block the post-cancellation job probe so its submit caller can disconnect."""

    fence_probe_entered: asyncio.Event = field(default_factory=asyncio.Event)
    fence_probe_release: asyncio.Event = field(default_factory=asyncio.Event)

    async def job(self, job_key: str, /) -> _FakeJob | None:
        if self.jobs:
            self.fence_probe_entered.set()
            await self.fence_probe_release.wait()
        return await super().job(job_key)


@dataclass
class _DelayedAbortQueue(_FakeQueue):
    """Hold an active abort so the request task can be cancelled mid-sequence."""

    abort_entered: asyncio.Event = field(default_factory=asyncio.Event)
    abort_release: asyncio.Event = field(default_factory=asyncio.Event)

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (error, ttl)
        self.abort_entered.set()
        await self.abort_release.wait()
        self.aborted.append(job.key)


@dataclass
class _FlakyAbortQueue(_FakeQueue):
    """Fail containment once so cancellation must remain retryable."""

    fail_abort: bool = True

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        if self.fail_abort:
            msg = "broker abort unavailable"
            raise RuntimeError(msg)
        await super().abort(job, error, ttl)


def _engine() -> tuple[RunEngine, InMemoryRunLedger, dict[str, _FakeQueue]]:
    # honor_intent_run_id: test-only seam so these assertions can key off stable ids
    # (R4: production always mints; identity is the ledger's, not the advisory field).
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queues = {"runs": _FakeQueue(), "rites": _FakeQueue()}
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues=queues,
    )
    return engine, ledger, queues


def test_queue_router_resolves_source_and_priority_override() -> None:
    """Bridge routes to runs@70; an explicit Intent.priority overrides the default."""
    router = QueueRouter()
    assert router.resolve(Intent(session_id="s", run_id="r", prompt="p", source="bridge")) == ("runs", 70)
    assert router.resolve(Intent(session_id="s", run_id="r", prompt="p", source="rite")) == ("rites", 20)
    assert router.resolve(Intent(session_id="s", run_id="r", prompt="p", source="weird")) == ("runs", 50)
    override = Intent(session_id="s", run_id="r", prompt="p", source="bridge", priority=5)
    assert router.resolve(override) == ("runs", 5)


@pytest.mark.asyncio
async def test_submit_routes_persists_and_enqueues() -> None:
    """submit routes once, persists QUEUED, opens a channel, and enqueues perform_run."""
    engine, ledger, queues = _engine()
    handle = await engine.submit(Intent(session_id="s", run_id="run_1", prompt="hi", source="bridge"))

    assert handle.run_id == "run_1"
    assert handle.workflow_name == "bridge_chat"
    assert handle.channel.run_id == "run_1"

    run = await ledger.get("run_1")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert run.queue_name == "runs"
    assert run.priority == 70  # bridge default
    assert run.pattern_manifest["key"] == "bridge_chat"
    assert run.pattern_manifest["revision"] == "1"
    assert run.pattern_manifest["implementation_revision"] == "py.1"
    assert run.pattern_manifest["entry_node"] == "weave_context"
    assert len(str(run.pattern_manifest["digest"])) == 64

    assert len(queues["runs"].enqueued) == 1
    job = queues["runs"].enqueued[0]
    assert job["func"] == "perform_run"
    assert job["run_id"] == "run_1"
    assert job["key"] == run_job_key("run_1", 0)
    assert job["retries"] == 0
    assert job["timeout"] == 0  # SAQ's 10s default must never kill local inference
    assert job["heartbeat"] == 120  # stale ACTIVE work is swept after missed worker heartbeats
    # R9 wire inversion: doctrine bridge=70 → saq priority number 100-70=30 (saq
    # dequeues lowest-first, so a hotter run gets a LOWER number on the wire).
    assert job["priority"] == 30


@pytest.mark.asyncio
async def test_submit_retains_caller_context_before_broker_visibility() -> None:
    """Bridge's user turn is linked to the canonical run before a worker can claim it."""
    engine, ledger, queues = _engine()
    retained: list[str] = []

    async def retain(run_id: str) -> None:
        assert await ledger.get(run_id) is not None
        assert queues["runs"].enqueued == []
        retained.append(run_id)

    await engine.submit(
        Intent(session_id="s", run_id="ordered", prompt="hi", source="bridge"),
        retain_before_publish=retain,
    )

    assert retained == ["ordered"]
    assert [job["run_id"] for job in queues["runs"].enqueued] == ["ordered"]


@pytest.mark.asyncio
async def test_idempotent_submit_single_flights_retention_and_publication() -> None:
    engine, ledger, queues = _engine()
    retained: list[str] = []
    entered = asyncio.Event()
    release = asyncio.Event()

    async def retain(run_id: str) -> None:
        retained.append(run_id)
        entered.set()
        await release.wait()

    intent = Intent(session_id="s", prompt="one offering", source="bridge")
    first = asyncio.create_task(engine.submit(intent, retain_before_publish=retain, idempotency_key="bridge:s:req-1"))
    await entered.wait()
    replay = asyncio.create_task(engine.submit(intent, retain_before_publish=retain, idempotency_key="bridge:s:req-1"))
    await asyncio.sleep(0)
    release.set()
    first_handle, replay_handle = await asyncio.gather(first, replay)

    assert first_handle.run_id == replay_handle.run_id
    assert retained == [first_handle.run_id]
    assert [job["run_id"] for job in queues["runs"].enqueued] == [first_handle.run_id]
    assert len(await ledger.list_for_session("s")) == 1


@pytest.mark.asyncio
async def test_idempotent_replay_repairs_held_custody_after_leader_compensation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A waiter must take the HELD gate, not receive a falsely successful handle."""
    engine, ledger, queues = _engine()
    entered = asyncio.Event()
    release = asyncio.Event()
    retain_calls = 0

    async def retain(_run_id: str) -> None:
        nonlocal retain_calls
        retain_calls += 1
        if retain_calls == 1:
            entered.set()
            await release.wait()

    async def fail_refusal(_run_id: str, *, enqueue_seq: int, error: str) -> bool:
        _ = (enqueue_seq, error)
        msg = "refusal database unavailable"
        raise RuntimeError(msg)

    monkeypatch.setattr(ledger, "try_fail_held", fail_refusal)
    intent = Intent(session_id="s", prompt="repair me", source="bridge")
    leader = asyncio.create_task(
        engine.submit(intent, retain_before_publish=retain, idempotency_key="bridge:s:req-repair")
    )
    await entered.wait()
    replay = asyncio.create_task(
        engine.submit(intent, retain_before_publish=retain, idempotency_key="bridge:s:req-repair")
    )
    leader.cancel()
    release.set()

    with pytest.raises(RuntimeError, match="could not be refused"):
        await leader
    handle = await replay

    delivery = await ledger.get_delivery(handle.run_id, enqueue_seq=0)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PUBLISHED
    assert retain_calls == 2
    assert [job["run_id"] for job in queues["runs"].enqueued] == [handle.run_id]


@pytest.mark.asyncio
async def test_idempotent_submit_rejects_payload_reuse() -> None:
    engine, _ledger, _queues = _engine()
    await engine.submit(
        Intent(session_id="s", prompt="first offering", source="bridge"),
        idempotency_key="bridge:s:req-conflict",
    )

    with pytest.raises(RunAdmissionConflictError):
        await engine.submit(
            Intent(session_id="s", prompt="different offering", source="bridge"),
            idempotency_key="bridge:s:req-conflict",
        )


@pytest.mark.asyncio
async def test_idempotent_submit_rejects_requested_priority_reuse() -> None:
    engine, _ledger, _queues = _engine()
    await engine.submit(
        Intent(session_id="s", prompt="same offering", source="bridge", priority=60),
        idempotency_key="bridge:s:req-priority-conflict",
    )

    with pytest.raises(RunAdmissionConflictError):
        await engine.submit(
            Intent(session_id="s", prompt="same offering", source="bridge", priority=61),
            idempotency_key="bridge:s:req-priority-conflict",
        )


@pytest.mark.asyncio
async def test_idempotent_replay_publishes_a_pending_admission() -> None:
    engine, ledger, queues = _engine()
    intent = Intent(session_id="s", prompt="publish stranded admission", source="bridge")
    admitted, created = await ledger.create_idempotent(
        intent,
        idempotency_key="bridge:s:req-pending",
        workflow_name="bridge_chat",
        pattern_manifest=builtin_workflow_registry().route(intent).manifest.snapshot(),
        queue_name="runs",
        priority=70,
    )
    assert created is True
    delivery = await ledger.get_delivery(admitted.run_id, enqueue_seq=0)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PENDING

    replay = await engine.submit(intent, idempotency_key="bridge:s:req-pending")

    assert replay.run_id == admitted.run_id
    assert [job["run_id"] for job in queues["runs"].enqueued] == [admitted.run_id]


@pytest.mark.asyncio
async def test_idempotent_replay_loads_durable_admission_before_routing() -> None:
    engine, _ledger, _queues = _engine()
    intent = Intent(session_id="s", prompt="accepted before registry change", source="bridge")
    first = await engine.submit(intent, idempotency_key="bridge:s:req-stable-route")

    class _RejectEveryRoute:
        def route(self, _intent: Intent) -> None:
            message = "durable replay must not route again"
            raise AssertionError(message)

    engine.workflows = _RejectEveryRoute()
    replay = await engine.submit(intent, idempotency_key="bridge:s:req-stable-route")

    assert replay.run_id == first.run_id
    assert replay.workflow_name == first.workflow_name


@pytest.mark.asyncio
async def test_submit_retention_failure_never_publishes_work() -> None:
    """A caller-record failure settles the invisible row before any broker publish."""
    engine, ledger, queues = _engine()

    async def fail_retention(_run_id: str) -> None:
        msg = "session write failed"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="session write failed"):
        await engine.submit(
            Intent(session_id="s", run_id="retain-fail", prompt="hi", source="bridge"),
            retain_before_publish=fail_retention,
        )

    run = await ledger.get("retain-fail")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert queues["runs"].enqueued == []


@pytest.mark.asyncio
async def test_retention_refusal_retries_transient_ledger_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, ledger, queues = _engine()
    original = ledger.try_fail_held
    attempts = 0

    async def flaky_refusal(run_id: str, *, enqueue_seq: int, error: str) -> bool:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            msg = "temporary database fault"
            raise RuntimeError(msg)
        return await original(run_id, enqueue_seq=enqueue_seq, error=error)

    monkeypatch.setattr(ledger, "try_fail_held", flaky_refusal)

    async def fail_retention(_run_id: str) -> None:
        msg = "session write failed"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="session write failed"):
        await engine.submit(
            Intent(session_id="s", run_id="retry-refusal", prompt="hi", source="bridge"),
            retain_before_publish=fail_retention,
        )

    run = await ledger.get("retry-refusal")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert attempts == 2
    assert queues["runs"].enqueued == []


@pytest.mark.asyncio
async def test_submit_cancellation_compensates_a_retention_task_that_then_fails() -> None:
    """Caller cancellation cannot skip refusal when the shielded retention also fails."""
    engine, ledger, queues = _engine()
    entered = asyncio.Event()
    release = asyncio.Event()

    async def fail_after_cancellation(_run_id: str) -> None:
        entered.set()
        await release.wait()
        message = "retention completed ambiguously"
        raise RuntimeError(message)

    task = asyncio.create_task(
        engine.submit(
            Intent(session_id="s", run_id="retain-cancel-fail", prompt="hi", source="bridge"),
            retain_before_publish=fail_after_cancellation,
        )
    )
    await entered.wait()
    task.cancel()
    release.set()

    with pytest.raises(asyncio.CancelledError):
        await task

    run = await ledger.get("retain-cancel-fail")
    assert run is not None
    assert run.status is RunStatus.FAILED
    delivery = await ledger.get_delivery(run.run_id, enqueue_seq=0)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.SETTLED
    assert queues["runs"].enqueued == []


@pytest.mark.asyncio
@pytest.mark.parametrize("held", [False, True], ids=["admitted", "caller-gated"])
async def test_submit_cancellation_after_create_refuses_only_caller_gated_delivery(
    monkeypatch: pytest.MonkeyPatch,
    *,
    held: bool,
) -> None:
    engine, ledger, queues = _engine()
    create = ledger.create
    created = asyncio.Event()
    release = asyncio.Event()
    retained = False

    async def create_then_wait(*args: Any, **kwargs: Any) -> Any:
        run = await create(*args, **kwargs)
        created.set()
        await release.wait()
        return run

    async def retain(_run_id: str) -> None:
        nonlocal retained
        retained = True

    monkeypatch.setattr(ledger, "create", create_then_wait)
    task = asyncio.create_task(
        engine.submit(
            Intent(session_id="s", run_id=f"create-cancel-{held}", prompt="hi", source="bridge"),
            retain_before_publish=retain if held else None,
        )
    )
    await created.wait()
    task.cancel()
    release.set()

    with pytest.raises(asyncio.CancelledError):
        await task

    run = await ledger.get(f"create-cancel-{held}")
    assert run is not None
    delivery = await ledger.get_delivery(run.run_id, enqueue_seq=0)
    assert delivery is not None
    assert run.status is (RunStatus.FAILED if held else RunStatus.QUEUED)
    assert delivery.state is (RunDeliveryState.SETTLED if held else RunDeliveryState.PENDING)
    assert retained is False
    assert queues["runs"].enqueued == []


@pytest.mark.asyncio
async def test_submit_release_failure_compensates_the_held_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, ledger, queues = _engine()

    async def fail_release(_run_id: str, *, enqueue_seq: int) -> bool:
        _ = enqueue_seq
        message = "release transaction failed"
        raise RuntimeError(message)

    monkeypatch.setattr(ledger, "release_delivery", fail_release)

    with pytest.raises(RuntimeError, match="release transaction failed"):
        await engine.submit(
            Intent(session_id="s", run_id="release-fail", prompt="hi", source="bridge"),
            retain_before_publish=lambda _run_id: asyncio.sleep(0),
        )

    run = await ledger.get("release-fail")
    assert run is not None
    assert run.status is RunStatus.FAILED
    delivery = await ledger.get_delivery(run.run_id, enqueue_seq=0)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.SETTLED
    assert queues["runs"].enqueued == []


@pytest.mark.asyncio
async def test_submit_release_error_after_commit_preserves_admitted_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutate-then-raise release cannot be mistaken for a retained admission."""
    engine, ledger, queues = _engine()
    release_delivery = ledger.release_delivery

    async def release_then_raise(run_id: str, *, enqueue_seq: int) -> bool:
        assert await release_delivery(run_id, enqueue_seq=enqueue_seq) is True
        message = "connection lost after commit"
        raise RuntimeError(message)

    monkeypatch.setattr(ledger, "release_delivery", release_then_raise)

    await engine.submit(
        Intent(session_id="s", run_id="release-committed", prompt="hi", source="bridge"),
        retain_before_publish=lambda _run_id: asyncio.sleep(0),
    )

    run = await ledger.get("release-committed")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    delivery = await ledger.get_delivery(run.run_id, enqueue_seq=0)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PUBLISHED
    assert [job["run_id"] for job in queues["runs"].enqueued] == ["release-committed"]


@pytest.mark.asyncio
async def test_enqueue_inverts_priority_on_the_wire() -> None:
    """R9: a hotter doctrine priority (bridge 70) enqueues at a LOWER saq number than cli (50)."""
    engine, _ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="hot", prompt="hi", source="bridge"))  # doctrine 70
    await engine.submit(Intent(session_id="s", run_id="warm", prompt="hi", source="cli"))  # doctrine 50

    by_run = {e["run_id"]: e["priority"] for e in queues["runs"].enqueued}
    assert by_run["hot"] == 30  # 100 - 70
    assert by_run["warm"] == 50  # 100 - 50
    assert by_run["hot"] < by_run["warm"]  # bridge dequeues before cli


@pytest.mark.asyncio
async def test_submit_retains_delivery_when_broker_is_down() -> None:
    """A broker outage leaves accepted work queued under its original durable key."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queues: dict[str, Any] = {"runs": _FailingQueue(), "rites": _FakeQueue()}
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues=queues,
    )
    channel = bus.open("efail")

    handle = await engine.submit(Intent(session_id="s", run_id="efail", prompt="hi", source="bridge"))

    run = await ledger.get("efail")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    delivery = await ledger.get_delivery("efail", enqueue_seq=0)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PENDING
    assert delivery.publish_attempts == 1
    assert delivery.last_error == "broker down"
    assert handle.channel is channel
    assert [e for e in channel._replay if e.kind is RunEventKind.DONE] == []
    assert channel.closed is False


@pytest.mark.asyncio
async def test_submit_cancellation_during_enqueue_preserves_delivery() -> None:
    """Caller cancellation cannot retract an already accepted initial delivery."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _CancellationQueue()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": queue, "rites": _FakeQueue()},
    )
    channel = bus.open("cancelled-publish")
    task = asyncio.create_task(
        engine.submit(
            Intent(
                session_id="s",
                run_id="cancelled-publish",
                prompt="hi",
                source="bridge",
            )
        )
    )
    await queue.entered.wait()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    run = await ledger.get("cancelled-publish")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    delivery = await ledger.get_delivery("cancelled-publish", enqueue_seq=0)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PENDING
    assert delivery.publish_attempts == 1
    assert channel.closed is False


@pytest.mark.asyncio
async def test_cancel_fences_job_accepted_after_its_broker_probe() -> None:
    """A late broker accept cannot resurrect work after canonical cancellation."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _FlakyLatePublicationQueue()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": queue, "rites": _FakeQueue()},
    )
    submit = asyncio.create_task(
        engine.submit(Intent(session_id="s", run_id="late-publication", prompt="hi", source="bridge"))
    )
    await queue.entered.wait()

    await engine.cancel("late-publication")
    queue.release.set()
    await submit

    run = await ledger.get("late-publication")
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    assert queue.abort_attempts == 2
    assert queue.aborted == [run_job_key("late-publication", 0)]
    assert queue.jobs == {}


@pytest.mark.asyncio
async def test_submit_cancellation_cannot_interrupt_late_publication_fence() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _CancellableFenceQueue()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": queue, "rites": _FakeQueue()},
    )
    submit = asyncio.create_task(
        engine.submit(Intent(session_id="s", run_id="cancel-fence-probe", prompt="hi", source="bridge"))
    )
    await queue.entered.wait()
    await engine.cancel("cancel-fence-probe")
    queue.release.set()
    await queue.fence_probe_entered.wait()

    submit.cancel()
    await asyncio.sleep(0)
    queue.fence_probe_release.set()
    with pytest.raises(asyncio.CancelledError):
        await submit

    run = await ledger.get("cancel-fence-probe")
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    assert queue.aborted == [run_job_key("cancel-fence-probe", 0)]
    assert queue.jobs == {}


@pytest.mark.asyncio
async def test_ambiguous_publish_error_cannot_fail_already_claimed_run() -> None:
    """Conditional compensation preserves a worker that won the publish race."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _ClaimThenRaiseQueue(ledger)
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": queue, "rites": _FakeQueue()},
    )
    channel = bus.open("ambiguous")

    await engine.submit(Intent(session_id="s", run_id="ambiguous", prompt="hi", source="bridge"))

    run = await ledger.get("ambiguous")
    assert run is not None
    assert run.status is RunStatus.RUNNING
    assert channel.closed is False
    assert [event for event in channel._replay if event.kind is RunEventKind.DONE] == []


@pytest.mark.asyncio
async def test_cancel_aborts_marks_cancelled_and_cleans_checkpoint() -> None:
    """cancel commits CANCELLED, closes the stream, then removes stale checkpoint state."""
    engine, ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="run_c", prompt="hi", source="bridge"))
    await engine.stasis_store.replace("run_c", [])
    # Hold the channel ref BEFORE cancel: R2 closes + drops it, so a post-cancel
    # `bus.open` would mint a fresh unclosed channel and hide the close.
    channel = engine.bus.open("run_c")

    await engine.cancel("run_c")

    run = await ledger.get("run_c")
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    assert queues["runs"].aborted == [run_job_key("run_c", 0)]
    assert not await engine.stasis_store.exists("run_c")
    # a single terminal DONE landed on the channel (carrying the terminal status)
    assert channel.closed is True
    # R2: cancel closed AND dropped the channel — reopening mints a fresh one.
    assert engine.bus.open("run_c") is not channel


@pytest.mark.asyncio
async def test_cancel_request_disconnect_cannot_interrupt_settlement() -> None:
    """Caller cancellation is propagated only after abort + durable CANCELLED finish."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _DelayedAbortQueue()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": queue, "rites": _FakeQueue()},
    )
    await engine.submit(Intent(session_id="s", run_id="cancel-shield", prompt="hi", source="bridge"))
    channel = bus.open("cancel-shield")
    task = asyncio.create_task(engine.cancel("cancel-shield"))
    await queue.abort_entered.wait()

    task.cancel()
    queue.abort_release.set()
    with pytest.raises(asyncio.CancelledError):
        await task

    run = await ledger.get("cancel-shield")
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    assert channel.closed is True
    assert engine.cancellations.active("cancel-shield") is False


@pytest.mark.asyncio
async def test_concurrent_cancel_calls_have_one_abort_and_terminal_writer() -> None:
    """Two stale API reads converge through one elected cancellation writer."""
    engine, ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="cancel-once", prompt="hi", source="bridge"))
    channel = engine.bus.open("cancel-once")

    await asyncio.gather(engine.cancel("cancel-once"), engine.cancel("cancel-once"))

    run = await ledger.get("cancel-once")
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    assert queues["runs"].aborted == [run_job_key("cancel-once", 0)]
    dones = [event for event in channel._replay if event.kind is RunEventKind.DONE]
    assert [event.data for event in dones] == [RunStatus.CANCELLED.value]


@pytest.mark.asyncio
async def test_cancel_failure_leaves_honest_cancelling_truth_for_retry() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _FlakyAbortQueue()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": queue, "rites": _FakeQueue()},
    )
    await engine.submit(Intent(session_id="s", run_id="cancel-retry", prompt="hi", source="bridge"))
    channel = bus.open("cancel-retry")

    with pytest.raises(RuntimeError, match="containment failed"):
        await engine.cancel("cancel-retry")

    pending = await ledger.get("cancel-retry")
    assert pending is not None
    assert pending.status is RunStatus.CANCELLING
    delivery = await ledger.get_delivery("cancel-retry", enqueue_seq=0)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PUBLISHED
    assert channel.closed is False

    queue.fail_abort = False
    await engine.cancel("cancel-retry")

    settled = await ledger.get("cancel-retry")
    assert settled is not None
    assert settled.status is RunStatus.CANCELLED
    assert queue.aborted == [run_job_key("cancel-retry", 0)]


@pytest.mark.asyncio
async def test_cancel_settles_the_runs_pending_consent_card() -> None:
    from lychd.domain.codex.ledger import InMemoryConsentLedger
    from lychd.domain.codex.sigil import Sigil

    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _FakeQueue()
    consents = InMemoryConsentLedger()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": queue, "rites": _FakeQueue()},
        consents=consents,
    )
    await engine.submit(Intent(session_id="s", run_id="cancel-consent", prompt="hi", source="bridge"))
    assert await ledger.try_claim_run("cancel-consent", enqueue_seq=0)
    consent = await consents.park(
        run_id="cancel-consent",
        tool_name="request_coven_swap",
        tool_call_id="call-1",
        call_ids=("call-1",),
        args={"target": "chat:local"},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    await ledger.park_consent("cancel-consent", consent.consent_id)

    await engine.cancel("cancel-consent")

    view = await consents.get(consent.consent_id)
    assert view is not None
    assert view.status == "cancelled"
    assert view.decided_by == "cortex:run-cancelled"
    assert await consents.pending_count() == 0


@pytest.mark.asyncio
async def test_cancel_sweeps_consent_created_while_parent_abort_settles() -> None:
    from lychd.domain.codex.ledger import InMemoryConsentLedger
    from lychd.domain.codex.sigil import Sigil

    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    consents = InMemoryConsentLedger()
    created: list[str] = []

    class EffectRaceQueue(_FakeQueue):
        async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
            decision = await consents.park(
                run_id="cancel-effect-race",
                tool_name="late_effect",
                tool_call_id="late-call",
                call_ids=("late-call",),
                args={},
                sigil=Sigil(name="magus", scopes=frozenset({"*"})),
            )
            created.append(decision.consent_id)
            await super().abort(job, error, ttl)

    queue = EffectRaceQueue()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": queue, "rites": _FakeQueue()},
        consents=consents,
    )
    await engine.submit(Intent(session_id="s", run_id="cancel-effect-race", prompt="hi", source="bridge"))

    await engine.cancel("cancel-effect-race")

    assert len(created) == 1
    view = await consents.get(created[0])
    assert view is not None
    assert view.status == "cancelled"
    run = await ledger.get("cancel-effect-race")
    assert run is not None
    assert run.status is RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancelled_retry_repairs_an_escaped_pending_consent() -> None:
    from lychd.domain.codex.ledger import InMemoryConsentLedger
    from lychd.domain.codex.sigil import Sigil

    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    consents = InMemoryConsentLedger()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": _FakeQueue(), "rites": _FakeQueue()},
        consents=consents,
    )
    await engine.submit(Intent(session_id="s", run_id="cancel-repair", prompt="hi", source="bridge"))
    await engine.cancel("cancel-repair")
    escaped = await consents.park(
        run_id="cancel-repair",
        tool_name="escaped_effect",
        tool_call_id="escaped-call",
        call_ids=("escaped-call",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )

    await engine.cancel("cancel-repair")

    view = await consents.get(escaped.consent_id)
    assert view is not None
    assert view.status == "cancelled"


@pytest.mark.asyncio
async def test_delegate_cancelled_error_keeps_run_honestly_cancelling() -> None:
    class CancelledDelegate:
        async def jobs_for_run(self, run_id: str) -> tuple[Any, ...]:
            _ = run_id
            return (SimpleNamespace(ref=SimpleNamespace(job_id="job-cancelled")),)

        async def cancel(self, job_id: str) -> bool:
            _ = job_id
            raise asyncio.CancelledError

    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    engine = RunEngine(
        ledger=ledger,
        bus=InProcessEventBus(ledger=ledger),
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": _FakeQueue(), "rites": _FakeQueue()},
        delegates=CancelledDelegate(),  # type: ignore[arg-type]
    )
    await engine.submit(Intent(session_id="s", run_id="cancel-uncertain", prompt="hi", source="bridge"))

    with pytest.raises(RuntimeError, match="containment failed"):
        await engine.cancel("cancel-uncertain")

    run = await ledger.get("cancel-uncertain")
    assert run is not None
    assert run.status is RunStatus.CANCELLING


@pytest.mark.asyncio
async def test_broker_abort_timeout_keeps_run_honestly_cancelling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HangingQueue(_FakeQueue):
        async def job(self, job_key: str, /) -> Any:
            _ = job_key
            await asyncio.Event().wait()

    monkeypatch.setattr("lychd.domain.cortex.engine.RUN_CONTAINMENT_TIMEOUT_S", 0.001)
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    engine = RunEngine(
        ledger=ledger,
        bus=InProcessEventBus(ledger=ledger),
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": HangingQueue(), "rites": _FakeQueue()},
    )
    await engine.submit(Intent(session_id="s", run_id="cancel-timeout", prompt="hi", source="bridge"))

    with pytest.raises(RuntimeError, match="containment failed"):
        await engine.cancel("cancel-timeout")

    run = await ledger.get("cancel-timeout")
    assert run is not None
    assert run.status is RunStatus.CANCELLING


@pytest.mark.asyncio
async def test_cancel_targets_delivery_generation_after_rotation() -> None:
    engine, ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="cancel-generation", prompt="hi", source="bridge"))
    assert await ledger.rotate_delivery("cancel-generation", enqueue_seq=0) == 1

    await engine.cancel("cancel-generation")

    assert queues["runs"].aborted == [run_job_key("cancel-generation", 1)]
    old = await ledger.get_delivery("cancel-generation", enqueue_seq=0)
    current = await ledger.get_delivery("cancel-generation", enqueue_seq=1)
    assert old is not None
    assert old.state is RunDeliveryState.SETTLED
    assert current is not None
    assert current.state is RunDeliveryState.SETTLED


@pytest.mark.asyncio
async def test_cancel_on_fresh_bus_continues_persisted_event_sequence() -> None:
    from lychd.domain.cortex.events import RunEvent

    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(
        Intent(session_id="s", run_id="cancel-restart", prompt="hi", source="bridge"),
        workflow_name="bridge_chat",
        queue_name="runs",
        priority=70,
    )
    await ledger.append_event(
        RunEvent(
            run_id="cancel-restart",
            seq=0,
            kind=RunEventKind.STATUS,
            data=RunStatus.QUEUED.value,
        )
    )
    bus = InProcessEventBus(ledger=ledger)
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": _FakeQueue(), "rites": _FakeQueue()},
    )

    await engine.cancel("cancel-restart", orphaned=True)

    events = await ledger.list_events("cancel-restart")
    assert [(event.seq, event.kind, event.data) for event in events] == [
        (0, RunEventKind.STATUS, RunStatus.QUEUED.value),
        (1, RunEventKind.DONE, RunStatus.CANCELLED.value),
    ]


@pytest.mark.asyncio
async def test_startup_cancel_reconciliation_fences_a_late_cancelled_broker_job() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    await ledger.create(
        Intent(session_id="s", run_id="cancelled-late-job", prompt="hi", source="bridge"),
        workflow_name="bridge_chat",
        queue_name="runs",
        priority=70,
    )
    elected = await ledger.begin_cancel("cancelled-late-job")
    assert elected is not None
    assert await ledger.finish_cancel("cancelled-late-job", enqueue_seq=elected.enqueue_seq)
    queue = _LatePublicationQueue()
    key = run_job_key("cancelled-late-job", elected.enqueue_seq)
    queue.jobs[key] = _FakeJob(key=key)
    engine = RunEngine(
        ledger=ledger,
        bus=InProcessEventBus(ledger=ledger),
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": queue, "rites": _FakeQueue()},
    )

    await engine.cancel("cancelled-late-job", orphaned=True)

    assert queue.aborted == [key]
    assert key not in queue.jobs
    terminal = await ledger.latest_event("cancelled-late-job", RunEventKind.DONE)
    assert terminal is not None
    assert terminal.data == RunStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_approve_seam_reenqueues_parked_run() -> None:
    """approve (consent seam) re-enqueues an AWAITING_CONSENT run with a resume hop."""
    engine, ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="run_p", prompt="hi", source="bridge"))
    await ledger.set_status("run_p", RunStatus.RUNNING)
    await ledger.set_status("run_p", RunStatus.AWAITING_CONSENT)
    await ledger.set_consent("run_p", "consent_1")

    await engine.approve("consent_1", approved=True)

    run = await ledger.get("run_p")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    # two enqueues total: the initial submit + the resume hop (fresh key)
    keys = [e["key"] for e in queues["runs"].enqueued]
    assert keys == [run_job_key("run_p", 0), run_job_key("run_p", 1)]
    assert all("resume" not in job for job in queues["runs"].enqueued)
    delivery = await ledger.get_delivery("run_p", enqueue_seq=1)
    assert delivery is not None
    assert delivery.resume is True


@pytest.mark.asyncio
async def test_double_approve_enqueues_the_resume_once() -> None:
    """Concurrent approves resolve to a SINGLE resume enqueue via the CAS admission gate (F4).

    Both callers pass the parked guard, but only one wins the atomic
    AWAITING_CONSENT → QUEUED transition (`try_admit_consent`), so `enqueue_seq`
    advances exactly once — a later cancel still targets the live job instead of a
    stale key.
    """
    import asyncio

    engine, ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="run_d", prompt="hi", source="bridge"))
    await ledger.set_status("run_d", RunStatus.RUNNING)
    await ledger.set_status("run_d", RunStatus.AWAITING_CONSENT)
    await ledger.set_consent("run_d", "consent_d")

    await asyncio.gather(
        engine.approve("consent_d", approved=True),
        engine.approve("consent_d", approved=True),
    )

    run = await ledger.get("run_d")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    keys = [e["key"] for e in queues["runs"].enqueued]
    assert keys.count(run_job_key("run_d", 1)) == 1
    assert all("resume" not in job for job in queues["runs"].enqueued)
    assert run.enqueue_seq == 1  # bumped once past the initial delivery, not twice


@pytest.mark.asyncio
async def test_approve_enqueue_failure_retains_exact_resume_delivery() -> None:
    """A broker failure after consent admission leaves one relayable resume hop."""
    engine, ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="run_r", prompt="hi", source="bridge"))
    await ledger.set_status("run_r", RunStatus.RUNNING)
    await ledger.set_status("run_r", RunStatus.AWAITING_CONSENT)
    await ledger.set_consent("run_r", "consent_r")

    queues["runs"] = _FailingQueue()  # type: ignore[assignment]
    await engine.approve("consent_r", approved=True)

    admitted = await ledger.get("run_r")
    assert admitted is not None
    assert admitted.status is RunStatus.QUEUED
    assert admitted.enqueue_seq == 1
    delivery = await ledger.get_delivery("run_r", enqueue_seq=1)
    assert delivery is not None
    assert delivery.resume is True
    assert delivery.state is RunDeliveryState.PENDING
    assert delivery.last_error == "broker down"

    retry_queue = _FakeQueue()
    queues["runs"] = retry_queue
    await enqueue_run(queues, ledger, admitted, enqueue_seq=1)

    assert [job["key"] for job in retry_queue.enqueued] == [run_job_key("run_r", 1)]


@pytest.mark.asyncio
async def test_approve_cancellation_preserves_exact_resume_delivery() -> None:
    """Cancellation after consent admission cannot lose the durable resume hop."""
    engine, ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="run_cancel", prompt="hi", source="bridge"))
    await ledger.set_status("run_cancel", RunStatus.RUNNING)
    await ledger.set_status("run_cancel", RunStatus.AWAITING_CONSENT)
    await ledger.set_consent("run_cancel", "consent_cancel")
    queue = _CancellationQueue()
    queues["runs"] = queue  # type: ignore[assignment]
    task = asyncio.create_task(engine.approve("consent_cancel", approved=True))
    await queue.entered.wait()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    admitted = await ledger.get("run_cancel")
    assert admitted is not None
    assert admitted.status is RunStatus.QUEUED
    assert admitted.enqueue_seq == 1
    delivery = await ledger.get_delivery("run_cancel", enqueue_seq=1)
    assert delivery is not None
    assert delivery.resume is True
    assert delivery.state is RunDeliveryState.PENDING

    retry_queue = _FakeQueue()
    queues["runs"] = retry_queue
    await enqueue_run(queues, ledger, admitted, enqueue_seq=1)
    assert [job["key"] for job in retry_queue.enqueued] == [run_job_key("run_cancel", 1)]
