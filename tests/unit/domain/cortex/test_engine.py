"""RunEngine.submit routing + enqueue-key discipline + cancel; QueueRouter resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from lychd.agents.router import Intent
from lychd.agents.workflows import builtin_workflow_registry
from lychd.domain.cortex.engine import QueueRouter, RunEngine, run_job_key
from lychd.domain.cortex.events import InProcessEventBus
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


def _engine() -> tuple[RunEngine, InMemoryRunLedger, dict[str, _FakeQueue]]:
    ledger = InMemoryRunLedger()
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
    assert job["priority"] == 70


@pytest.mark.asyncio
async def test_cancel_aborts_and_marks_cancelled() -> None:
    """cancel aborts the SAQ job by key, marks CANCELLED, and emits a terminal DONE."""
    engine, ledger, queues = _engine()
    await engine.submit(Intent(session_id="s", run_id="run_c", prompt="hi", source="bridge"))

    await engine.cancel("run_c")

    run = await ledger.get("run_c")
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    assert queues["runs"].aborted == [run_job_key("run_c", 1)]
    # a single terminal DONE landed on the channel (carrying the terminal status)
    channel = engine.bus.open("run_c")
    assert channel.closed is True


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
