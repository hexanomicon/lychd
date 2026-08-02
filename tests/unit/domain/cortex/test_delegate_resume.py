# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock

import pytest

from lychd.agents.router import Intent
from lychd.agents.workflows import builtin_workflow_registry
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT
from lychd.domain.cortex.engine import QueueRouter, RunEngine, enqueue_run
from lychd.domain.cortex.events import InProcessEventBus, RunEventKind
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunDeliveryState, RunStatus
from lychd.domain.delegation import (
    DelegatedAgentCoordinator,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentParked,
    DelegatedAgentRequest,
    DelegatedAgentResult,
    InMemoryDelegatedAgentJobStore,
)
from lychd.ghouls.runs import (
    _commit_delegate_park,
    _reconcile_delegate_page,
    relay_delegated_runs,
)

if TYPE_CHECKING:
    from lychd.domain.cortex.substrate import RunSubstrate


@dataclass
class _Runtime:
    name: str = "fake"
    cancellations: list[str] = field(default_factory=list)
    poll_result: DelegatedAgentResult | None = None

    async def start(self, request: DelegatedAgentRequest, job: DelegatedAgentJobRef) -> None:
        assert request.request_id == job.request_id

    async def poll(self, job: DelegatedAgentJobRef) -> DelegatedAgentResult | None:
        _ = job
        return self.poll_result

    async def cancel(self, job: DelegatedAgentJobRef) -> None:
        self.cancellations.append(job.job_id)


@dataclass
class _Queue:
    fail: bool = False
    enqueued: list[dict[str, Any]] = field(default_factory=list)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> object:
        if self.fail:
            msg = "broker down"
            raise RuntimeError(msg)
        self.enqueued.append({"func": job_or_func, **kwargs})
        return object()

    async def job(self, job_key: str, /) -> None:
        _ = job_key

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)


async def _seed_running(ledger: InMemoryRunLedger, run_id: str) -> None:
    await ledger.create(
        Intent(session_id="session-1", run_id=run_id, prompt="delegate"),
        workflow_name=BRIDGE_CHAT.name,
        pattern_manifest=BRIDGE_CHAT.manifest.snapshot(),
        queue_name="runs",
        priority=50,
    )
    await ledger.set_status(run_id, RunStatus.RUNNING)


async def _delegated_job(
    coordinator: DelegatedAgentCoordinator,
    *,
    run_id: str,
    request_id: str | None = None,
    step_id: str = "step-1",
) -> DelegatedAgentJobRef:
    return await coordinator.submit(
        DelegatedAgentRequest(
            request_id=request_id or f"request-{run_id}",
            run_id=run_id,
            step_id=step_id,
            runtime="fake",
            prompt="inspect",
        )
    )


def _engine(
    *,
    ledger: InMemoryRunLedger,
    bus: InProcessEventBus,
    queue: _Queue,
    coordinator: DelegatedAgentCoordinator,
) -> RunEngine:
    return RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(),
        queues={"runs": queue},
        delegates=coordinator,
    )


@pytest.mark.asyncio
async def test_terminal_delegate_result_admits_exactly_one_resume_hop() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _Queue()
    runtime = _Runtime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={"fake": runtime},
        store=InMemoryDelegatedAgentJobStore(),
    )
    await _seed_running(ledger, "run-1")
    ref = await _delegated_job(coordinator, run_id="run-1")
    await ledger.park_delegate("run-1", ref.job_id)
    engine = _engine(ledger=ledger, bus=bus, queue=queue, coordinator=coordinator)
    result = DelegatedAgentResult(
        job_id=ref.job_id,
        status=DelegatedAgentJobStatus.SUCCEEDED,
        output="done",
    )

    assert await engine.adopt_delegate(ref.job_id, result) is True
    assert await engine.adopt_delegate(ref.job_id, result) is False

    run = await ledger.get("run-1")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert run.enqueue_seq == 1
    assert len(queue.enqueued) == 1
    assert "resume" not in queue.enqueued[0]
    assert queue.enqueued[0]["enqueue_seq"] == 1


@pytest.mark.asyncio
async def test_delegate_relay_closes_terminal_result_loop_without_callback() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _Queue()
    runtime = _Runtime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={"fake": runtime},
        store=InMemoryDelegatedAgentJobStore(),
    )
    await _seed_running(ledger, "run-relay")
    ref = await _delegated_job(coordinator, run_id="run-relay")
    await ledger.park_delegate("run-relay", ref.job_id)
    runtime.poll_result = DelegatedAgentResult(
        job_id=ref.job_id,
        status=DelegatedAgentJobStatus.SUCCEEDED,
        output="finished while no callback was connected",
    )
    engine = _engine(ledger=ledger, bus=bus, queue=queue, coordinator=coordinator)

    result, cursor = await _reconcile_delegate_page(engine, after=None)

    run = await ledger.get("run-relay")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0, "_revisit": False}
    assert cursor is None
    assert queue.enqueued[0]["enqueue_seq"] == 1


@pytest.mark.asyncio
async def test_delegate_page_revisits_a_clean_unfinished_job() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _Queue()
    coordinator = DelegatedAgentCoordinator(
        runtimes={"fake": _Runtime()},
        store=InMemoryDelegatedAgentJobStore(),
    )
    await _seed_running(ledger, "run-active-delegate")
    ref = await _delegated_job(coordinator, run_id="run-active-delegate")
    await ledger.park_delegate("run-active-delegate", ref.job_id)
    engine = _engine(ledger=ledger, bus=bus, queue=queue, coordinator=coordinator)

    result, _cursor = await _reconcile_delegate_page(engine, after=None)

    assert result == {"status": "reconciled", "count": 0, "probe_errors": 0, "_revisit": True}


@pytest.mark.asyncio
async def test_delegate_relay_fairly_retries_multiple_degraded_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    calls: list[tuple[datetime, str] | None] = []
    stop = asyncio.Event()
    first_page_end = (datetime.now(UTC), "delegate-page-1")
    second_page_end = (datetime.now(UTC), "delegate-page-2")

    async def fake_page(
        _engine: Any,
        *,
        after: tuple[datetime, str] | None,
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

    monkeypatch.setattr("lychd.ghouls.runs._reconcile_delegate_page", fake_page)

    await relay_delegated_runs(
        engine=object(),
        stop=stop,
        interval_s=0.001,
    )

    assert calls == [None, None, first_page_end, None, second_page_end, first_page_end]


@pytest.mark.asyncio
async def test_delegate_resume_enqueue_failure_retains_exact_durable_hop() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _Queue(fail=True)
    coordinator = DelegatedAgentCoordinator(
        runtimes={"fake": _Runtime()},
        store=InMemoryDelegatedAgentJobStore(),
    )
    await _seed_running(ledger, "run-2")
    ref = await _delegated_job(coordinator, run_id="run-2")
    await ledger.park_delegate("run-2", ref.job_id)
    engine = _engine(ledger=ledger, bus=bus, queue=queue, coordinator=coordinator)
    result = DelegatedAgentResult(
        job_id=ref.job_id,
        status=DelegatedAgentJobStatus.SUCCEEDED,
        output="done",
    )

    assert await engine.adopt_delegate(ref.job_id, result) is True
    admitted = await ledger.get("run-2")
    assert admitted is not None
    assert admitted.status is RunStatus.QUEUED
    assert admitted.enqueue_seq == 1
    delivery = await ledger.get_delivery("run-2", enqueue_seq=1)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PENDING
    assert delivery.resume is True
    assert delivery.last_error == "broker down"

    queue.fail = False
    await enqueue_run({"runs": queue}, ledger, admitted, enqueue_seq=1)
    assert queue.enqueued[0]["enqueue_seq"] == 1
    assert "resume" not in queue.enqueued[0]


@pytest.mark.asyncio
async def test_run_cancellation_cancels_correlated_delegate_once() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    runtime = _Runtime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={"fake": runtime},
        store=InMemoryDelegatedAgentJobStore(),
    )
    await _seed_running(ledger, "run-3")
    ref = await _delegated_job(coordinator, run_id="run-3")
    await ledger.park_delegate("run-3", ref.job_id)
    engine = _engine(ledger=ledger, bus=bus, queue=_Queue(), coordinator=coordinator)

    await engine.cancel("run-3")
    await engine.cancel("run-3")

    run = await ledger.get("run-3")
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    assert runtime.cancellations == [ref.job_id]
    job = await coordinator.get(ref.job_id)
    assert job is not None
    assert job.status is DelegatedAgentJobStatus.CANCELLED


@pytest.mark.asyncio
async def test_commit_delegate_park_sets_wait_status_without_terminal_event() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    await ledger.create(
        Intent(session_id="session-1", run_id="run-4", prompt="delegate"),
        workflow_name=BRIDGE_CHAT.name,
        pattern_manifest=BRIDGE_CHAT.manifest.snapshot(),
        queue_name="runs",
        priority=50,
    )
    await ledger.set_status("run-4", RunStatus.RUNNING)
    channel = bus.open("run-4")
    ref = DelegatedAgentJobRef(
        job_id="job-4",
        request_id="request-4",
        run_id="run-4",
        runtime="fake",
    )

    result = await _commit_delegate_park(
        cast("RunSubstrate", SimpleNamespace(delegates=None, queues={})),
        ledger,
        bus.emitter("run-4"),
        "run-4",
        DelegatedAgentParked(job=ref),
    )

    run = await ledger.get("run-4")
    assert run is not None
    assert run.status is RunStatus.AWAITING_DELEGATE
    assert run.delegated_job_id == "job-4"
    assert result == {"status": "awaiting_delegate", "run_id": "run-4", "job_id": "job-4"}
    assert any(
        event.kind is RunEventKind.STATUS and event.data == RunStatus.AWAITING_DELEGATE.value
        for event in channel._replay
    )
    assert not any(event.kind is RunEventKind.DONE for event in channel._replay)


@pytest.mark.asyncio
async def test_post_park_delegate_probe_failure_preserves_waiting_authority() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    await _seed_running(ledger, "run-probe-failure")
    ref = DelegatedAgentJobRef(
        job_id="job-probe-failure",
        request_id="request-probe-failure",
        run_id="run-probe-failure",
        runtime="fake",
    )
    refresh = AsyncMock(side_effect=RuntimeError("delegate store unavailable"))

    result = await _commit_delegate_park(
        cast(
            "RunSubstrate",
            SimpleNamespace(delegates=SimpleNamespace(refresh=refresh), queues={}),
        ),
        ledger,
        bus.emitter("run-probe-failure"),
        "run-probe-failure",
        DelegatedAgentParked(job=ref),
    )

    run = await ledger.get("run-probe-failure")
    assert run is not None
    assert run.status is RunStatus.AWAITING_DELEGATE
    assert run.delegated_job_id == ref.job_id
    assert result == {
        "status": "awaiting_delegate",
        "run_id": "run-probe-failure",
        "job_id": ref.job_id,
    }


@pytest.mark.asyncio
async def test_delegate_park_rejects_job_owned_by_another_run() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    await _seed_running(ledger, "run-owner")
    ref = DelegatedAgentJobRef(
        job_id="job-foreign",
        request_id="request-foreign",
        run_id="run-foreign",
        runtime="fake",
    )

    with pytest.raises(ValueError, match="belongs to Run 'run-foreign'"):
        await _commit_delegate_park(
            cast("RunSubstrate", SimpleNamespace(delegates=None, queues={})),
            ledger,
            bus.emitter("run-owner"),
            "run-owner",
            DelegatedAgentParked(job=ref),
        )

    run = await ledger.get("run-owner")
    assert run is not None
    assert run.status is RunStatus.RUNNING
    assert run.delegated_job_id is None


@pytest.mark.asyncio
async def test_worker_cancellation_during_delegate_probe_preserves_waiting_authority() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    await _seed_running(ledger, "run-probe-cancel")
    ref = DelegatedAgentJobRef(
        job_id="job-probe-cancel",
        request_id="request-probe-cancel",
        run_id="run-probe-cancel",
        runtime="fake",
    )
    entered = asyncio.Event()

    async def blocked_refresh(_job_id: str) -> None:
        entered.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(
        _commit_delegate_park(
            cast(
                "RunSubstrate",
                SimpleNamespace(
                    delegates=SimpleNamespace(refresh=blocked_refresh),
                    queues={},
                ),
            ),
            ledger,
            bus.emitter("run-probe-cancel"),
            "run-probe-cancel",
            DelegatedAgentParked(job=ref),
        )
    )
    await entered.wait()

    task.cancel()
    result = await task

    run = await ledger.get("run-probe-cancel")
    assert run is not None
    assert run.status is RunStatus.AWAITING_DELEGATE
    assert run.delegated_job_id == ref.job_id
    assert result == {
        "status": "awaiting_delegate",
        "run_id": "run-probe-cancel",
        "job_id": ref.job_id,
    }


@pytest.mark.asyncio
async def test_terminal_result_before_park_status_is_rechecked_and_resumed() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _Queue()
    coordinator = DelegatedAgentCoordinator(
        runtimes={"fake": _Runtime()},
        store=InMemoryDelegatedAgentJobStore(),
    )
    await ledger.create(
        Intent(session_id="session-1", run_id="run-5", prompt="delegate"),
        workflow_name=BRIDGE_CHAT.name,
        pattern_manifest=BRIDGE_CHAT.manifest.snapshot(),
        queue_name="runs",
        priority=50,
    )
    await ledger.set_status("run-5", RunStatus.RUNNING)
    ref = await _delegated_job(coordinator, run_id="run-5")
    await coordinator.adopt(
        ref.job_id,
        DelegatedAgentResult(
            job_id=ref.job_id,
            status=DelegatedAgentJobStatus.SUCCEEDED,
            output="already done",
        ),
    )

    result = await _commit_delegate_park(
        cast(
            "RunSubstrate",
            SimpleNamespace(delegates=coordinator, queues={"runs": queue}),
        ),
        ledger,
        bus.emitter("run-5"),
        "run-5",
        DelegatedAgentParked(job=ref),
    )

    run = await ledger.get("run-5")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert result == {"status": "queued", "run_id": "run-5", "job_id": ref.job_id}
    assert len(queue.enqueued) == 1


@pytest.mark.asyncio
async def test_old_terminal_job_cannot_resume_a_newer_delegate_wait_for_same_run() -> None:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    queue = _Queue()
    coordinator = DelegatedAgentCoordinator(
        runtimes={"fake": _Runtime()},
        store=InMemoryDelegatedAgentJobStore(),
    )
    await _seed_running(ledger, "run-6")
    first = await _delegated_job(
        coordinator,
        run_id="run-6",
        request_id="request-run-6-first",
        step_id="first",
    )
    await ledger.park_delegate("run-6", first.job_id)
    engine = _engine(ledger=ledger, bus=bus, queue=queue, coordinator=coordinator)
    settled = DelegatedAgentResult(
        job_id=first.job_id,
        status=DelegatedAgentJobStatus.SUCCEEDED,
        output="first done",
    )
    assert await engine.adopt_delegate(first.job_id, settled) is True
    assert await ledger.try_claim_run("run-6", enqueue_seq=1) is True

    second = await _delegated_job(
        coordinator,
        run_id="run-6",
        request_id="request-run-6-second",
        step_id="second",
    )
    await ledger.park_delegate("run-6", second.job_id)

    assert await engine.resume_delegate(first.job_id) is False
    run = await ledger.get("run-6")
    assert run is not None
    assert run.status is RunStatus.AWAITING_DELEGATE
    assert run.delegated_job_id == second.job_id
    assert len(queue.enqueued) == 1
