"""RunEngine.submit routing + enqueue-key discipline + cancel; QueueRouter resolution."""
# White-box assertions read RunChannel._replay directly.
# pyright: reportPrivateUsage=false

from __future__ import annotations

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

    assert len(queues["runs"].enqueued) == 1
    job = queues["runs"].enqueued[0]
    assert job["func"] == "perform_run"
    assert job["run_id"] == "run_1"
    assert job["key"] == run_job_key("run_1", 1)  # enqueue_seq bumped to 1
    assert job["retries"] == 0
    # R9 wire inversion: doctrine bridge=70 → saq priority number 100-70=30 (saq
    # dequeues lowest-first, so a hotter run gets a LOWER number on the wire).
    assert job["priority"] == 30


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
async def test_cancel_aborts_and_marks_cancelled() -> None:
    """cancel aborts the SAQ job by key, marks CANCELLED, and emits a terminal DONE."""
    engine, ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="run_c", prompt="hi", source="bridge"))
    # Hold the channel ref BEFORE cancel: R2 closes + drops it, so a post-cancel
    # `bus.open` would mint a fresh unclosed channel and hide the close.
    channel = engine.bus.open("run_c")

    await engine.cancel("run_c")

    run = await ledger.get("run_c")
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    assert queues["runs"].aborted == [run_job_key("run_c", 1)]
    # a single terminal DONE landed on the channel (carrying the terminal status)
    assert channel.closed is True
    # R2: cancel closed AND dropped the channel — reopening mints a fresh one.
    assert engine.bus.open("run_c") is not channel


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
