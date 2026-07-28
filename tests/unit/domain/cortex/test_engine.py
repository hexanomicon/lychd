"""RunEngine.submit routing + enqueue-key discipline + cancel; QueueRouter resolution."""
# White-box assertions read RunChannel._replay directly.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest

from lychd.agents.router import Intent
from lychd.agents.workflows import builtin_workflow_registry
from lychd.domain.cortex.engine import QueueRouter, RunEngine, run_job_key
from lychd.domain.cortex.events import InProcessEventBus, RunEventKind
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus


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
class _DelayedAbortQueue(_FakeQueue):
    """Hold an active abort so the request task can be cancelled mid-sequence."""

    abort_entered: asyncio.Event = field(default_factory=asyncio.Event)
    abort_release: asyncio.Event = field(default_factory=asyncio.Event)

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (error, ttl)
        self.abort_entered.set()
        await self.abort_release.wait()
        self.aborted.append(job.key)


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
    assert len(str(run.pattern_manifest["digest"])) == 64

    assert len(queues["runs"].enqueued) == 1
    job = queues["runs"].enqueued[0]
    assert job["func"] == "perform_run"
    assert job["run_id"] == "run_1"
    assert job["key"] == run_job_key("run_1", 1)  # enqueue_seq bumped to 1
    assert job["retries"] == 0
    assert job["timeout"] == 0  # SAQ's 10s default must never kill local inference
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
async def test_submit_compensates_enqueue_failure() -> None:
    """A failed `_enqueue` fails the QUEUED row, emits ONE terminal DONE, and re-raises (F3/H2).

    Without compensation the run would rot QUEUED forever and its stream keepalive
    into eternity. With it: FAILED row + a single terminal DONE(failed) so any open
    stream ends, and the original broker error surfaces to the caller.
    """
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
    channel = bus.open("efail")  # hold the ref before compensation closes + drops it

    with pytest.raises(RuntimeError, match="broker down"):
        await engine.submit(Intent(session_id="s", run_id="efail", prompt="hi", source="bridge"))

    run = await ledger.get("efail")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert "enqueue failed" in (run.error or "")
    dones = [e for e in list(channel._replay) if e.kind is RunEventKind.DONE]
    assert len(dones) == 1
    assert dones[0].data == "failed"
    assert channel.closed is True


@pytest.mark.asyncio
async def test_submit_cancellation_during_enqueue_settles_failed() -> None:
    """Request cancellation cannot strand a persisted initial run QUEUED."""
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
    assert run.status is RunStatus.FAILED
    assert channel.closed is True


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

    with pytest.raises(RuntimeError, match="reply lost"):
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
    assert queues["runs"].aborted == [run_job_key("run_c", 1)]
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
    assert queues["runs"].aborted == [run_job_key("cancel-once", 1)]
    dones = [event for event in channel._replay if event.kind is RunEventKind.DONE]
    assert [event.data for event in dones] == [RunStatus.CANCELLED.value]


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
    assert keys == [run_job_key("run_p", 1), run_job_key("run_p", 2)]
    assert queues["runs"].enqueued[-1]["resume"] is True


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
    resume_keys = [e["key"] for e in queues["runs"].enqueued if e.get("resume")]
    assert resume_keys == [run_job_key("run_d", 2)]  # exactly one resume enqueue
    assert run.enqueue_seq == 2  # bumped once past the submit, not twice


@pytest.mark.asyncio
async def test_approve_enqueue_failure_restores_retryable_consent_wait() -> None:
    """A broker failure after admission restores AWAITING_CONSENT for a later retry."""
    engine, ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="run_r", prompt="hi", source="bridge"))
    await ledger.set_status("run_r", RunStatus.RUNNING)
    await ledger.set_status("run_r", RunStatus.AWAITING_CONSENT)
    await ledger.set_consent("run_r", "consent_r")

    queues["runs"] = _FailingQueue()  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="broker down"):
        await engine.approve("consent_r", approved=True)

    restored = await ledger.get("run_r")
    assert restored is not None
    assert restored.status is RunStatus.AWAITING_CONSENT
    assert restored.enqueue_seq == 2  # the possibly-published key is never reused

    retry_queue = _FakeQueue()
    queues["runs"] = retry_queue
    await engine.approve("consent_r", approved=True)

    admitted = await ledger.get("run_r")
    assert admitted is not None
    assert admitted.status is RunStatus.QUEUED
    assert [job["key"] for job in retry_queue.enqueued] == [run_job_key("run_r", 3)]


@pytest.mark.asyncio
async def test_approve_cancellation_restores_retryable_consent_wait() -> None:
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

    restored = await ledger.get("run_cancel")
    assert restored is not None
    assert restored.status is RunStatus.AWAITING_CONSENT
    assert restored.enqueue_seq == 2

    retry_queue = _FakeQueue()
    queues["runs"] = retry_queue
    await engine.approve("consent_cancel", approved=True)
    assert [job["key"] for job in retry_queue.enqueued] == [run_job_key("run_cancel", 3)]
