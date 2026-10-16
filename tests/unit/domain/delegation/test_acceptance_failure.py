"""Acceptance persistence faults preserve identity, disposition, and cancellation."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio

import pytest

from lychd.domain.delegation import (
    DelegatedAgentCoordinator,
    DelegatedAgentJob,
    DelegatedAgentJobRef,
    DelegatedAgentRequest,
    DelegatedAgentResult,
    InMemoryDelegatedAgentJobStore,
)
from lychd.domain.delegation import (
    DelegatedAgentJobStatus as Status,
)
from lychd.domain.delegation.models import TERMINAL_DELEGATED_AGENT_STATUSES, DelegatedAgentEventKind, DelegatedRequest
from lychd.domain.delegation.services import IllegalDelegatedAgentTransitionError, UnknownDelegatedAgentJobError
from lychd.extensions.builtin.delegation.reference import ReferenceDelegatedAgentRuntime


class AcceptanceRuntime(ReferenceDelegatedAgentRuntime):
    """Count the real, effect-free reference runtime's calls and exact identities."""

    def __init__(self, timeline: list[str] | None = None) -> None:
        super().__init__()
        self.starts: list[DelegatedAgentJobRef] = []
        self.cancels: list[DelegatedAgentJobRef] = []
        self.timeline = timeline if timeline is not None else []

    async def start(self, request: DelegatedRequest, job: DelegatedAgentJobRef) -> None:
        self.starts.append(job)
        await super().start(request, job)
        self.timeline.append("start returned")

    async def cancel(self, job: DelegatedAgentJobRef, *, request: DelegatedRequest) -> None:
        self.cancels.append(job)
        await super().cancel(job, request=request)
        self.timeline.append("containment returned")


class AcceptanceStore(InMemoryDelegatedAgentJobStore):
    """Inject persistence acknowledgements; keep all lifecycle mutation real."""

    def __init__(self, mode: str, *, block: str = "", settlement_fault: str = "") -> None:
        super().__init__()
        self.mode = mode
        self.settlement_fault = settlement_fault
        self.write_error = OSError("RUNNING write acknowledgement unavailable")
        self.settlement_error = LookupError("conditional disposition unavailable")
        self.running_entered = asyncio.Event()
        self.release_running = asyncio.Event()
        self.settlement_entered = asyncio.Event()
        self.release_settlement = asyncio.Event()
        if block != "write":
            self.release_running.set()
        if block != "settlement":
            self.release_settlement.set()
        self.running_calls = 0
        self.settlement_calls = 0
        self.ordinary_adoptions = 0

    async def transition(self, job_id: str, status: Status) -> tuple[DelegatedAgentJob, bool]:
        if status is not Status.RUNNING:
            return await super().transition(job_id, status)
        self.running_calls += 1
        if self.mode == "after":
            await super().transition(job_id, status)
        self.running_entered.set()
        await self.release_running.wait()
        if self.mode in {"before", "after"}:
            raise self.write_error
        return await super().transition(job_id, status)

    async def settle_acceptance_failure(
        self, job_id: str, result: DelegatedAgentResult
    ) -> tuple[DelegatedAgentJob, bool]:
        self.settlement_calls += 1
        self.settlement_entered.set()
        await self.release_settlement.wait()
        if self.settlement_fault == "before":
            raise self.settlement_error
        outcome = await super().settle_acceptance_failure(job_id, result)
        if self.settlement_fault == "after":
            raise self.settlement_error
        return outcome

    async def adopt(self, job_id: str, result: DelegatedAgentResult) -> tuple[DelegatedAgentJob, bool]:
        self.ordinary_adoptions += 1
        return await super().adopt(job_id, result)


def request() -> DelegatedAgentRequest:
    return DelegatedAgentRequest(
        request_id="acceptance-request",
        run_id="acceptance-run",
        step_id="dispatch_delegate",
        runtime="reference",
        prompt="Return an inert bounded reply.",
    )


def lost(job_id: str) -> DelegatedAgentResult:
    return DelegatedAgentResult(job_id=job_id, status=Status.LOST, error="acceptance outcome unknown")


def exception_chain(error: BaseException) -> list[BaseException]:
    found: list[BaseException] = []
    pending = [error]
    while pending:
        item = pending.pop()
        if any(item is prior for prior in found):
            continue
        found.append(item)
        pending.extend(x for x in (item.__cause__, item.__context__) if x is not None)
    return found


async def prepared(store: InMemoryDelegatedAgentJobStore) -> DelegatedAgentJobRef:
    req = request()
    ref = DelegatedAgentJobRef(
        job_id="acceptance-job",
        request_id=req.request_id,
        run_id=req.run_id,
        runtime=req.runtime,
        profile=req.profile,
    )
    await store.create(req, ref)
    await store.transition(ref.job_id, Status.ADMITTED)
    await store.transition(ref.job_id, Status.PREPARING)
    return ref


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["none", "before", "after"])
async def test_acceptance_fault_disposition_and_fresh_reference_recovery(mode: str) -> None:
    store = AcceptanceStore(mode)
    runtime = AcceptanceRuntime()
    coordinator = DelegatedAgentCoordinator(runtimes={runtime.name: runtime}, store=store)
    req = request()
    if mode == "before":
        with pytest.raises(OSError, match="RUNNING write acknowledgement unavailable") as caught:
            await coordinator.submit(req)
        assert caught.value is store.write_error
    else:
        ref = await coordinator.submit(req)
        assert ref == runtime.starts[0]
    job = await store.get_by_request(req.request_id)
    assert job is not None
    expected = Status.LOST if mode == "before" else Status.RUNNING
    assert job.status is expected
    assert [e.status for e in job.events] == [Status.QUEUED, Status.ADMITTED, Status.PREPARING, expected]
    assert job.events[-1].kind is (
        DelegatedAgentEventKind.RESULT_ADOPTED if mode == "before" else DelegatedAgentEventKind.STATUS_CHANGED
    )
    assert [e.seq for e in job.events] == [0, 1, 2, 3]
    assert store.running_calls == 1
    assert store.settlement_calls == (0 if mode == "none" else 1)
    assert store.ordinary_adoptions == 0
    assert runtime.starts == [job.ref]

    fresh_runtime = AcceptanceRuntime()
    fresh = DelegatedAgentCoordinator(runtimes={fresh_runtime.name: fresh_runtime}, store=store)
    assert await fresh.submit(req) == job.ref
    refreshed = await fresh.refresh(job.ref.job_id)
    assert fresh_runtime.starts == []
    if mode == "before":
        assert refreshed == job
        assert not await fresh.adopt(
            job.ref.job_id, DelegatedAgentResult(job_id=job.ref.job_id, status=Status.SUCCEEDED)
        )
        assert await fresh.cancel(job.ref.job_id)
        assert not await fresh.cancel(job.ref.job_id)
        assert fresh_runtime.cancels == [job.ref]
        settled = await store.get(job.ref.job_id)
        assert settled is not None
        assert settled.status is Status.CANCELLED
    else:
        assert refreshed.status is Status.SUCCEEDED
        assert not await fresh.cancel(job.ref.job_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["before", "after"])
@pytest.mark.parametrize("phase", ["write", "settlement"])
async def test_repeated_cancellation_waits_for_known_disposition(mode: str, phase: str) -> None:
    store = AcceptanceStore(mode, block=phase)
    runtime = AcceptanceRuntime()
    coordinator = DelegatedAgentCoordinator(runtimes={runtime.name: runtime}, store=store)
    req = request()
    task = asyncio.create_task(coordinator.submit(req))
    entered = store.running_entered if phase == "write" else store.settlement_entered
    release = store.release_running if phase == "write" else store.release_settlement
    try:
        await asyncio.wait_for(entered.wait(), 1)
        replay = asyncio.create_task(coordinator.submit(req))
        task.cancel("first caller interruption")
        await asyncio.sleep(0)
        task.cancel("second caller interruption")
        await asyncio.sleep(0)
        assert not task.done()
        assert not replay.done()
        release.set()
        with pytest.raises(asyncio.CancelledError, match="first caller interruption") as caught:
            await task
        assert store.write_error in exception_chain(caught.value)
        ref = await replay
        job = await store.get(ref.job_id)
        assert job is not None
        assert job.status is (Status.LOST if mode == "before" else Status.RUNNING)
        assert len(job.events) == 4
        assert runtime.starts == [ref]
        assert store.running_calls == store.settlement_calls == 1
    finally:
        store.release_running.set()
        store.release_settlement.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["before", "after"])
@pytest.mark.parametrize("cancelled", [False, True])
async def test_unresolved_settlement_retains_write_and_interruption_provenance(fault: str, *, cancelled: bool) -> None:
    store = AcceptanceStore("before", block="settlement", settlement_fault=fault)
    runtime = AcceptanceRuntime()
    coordinator = DelegatedAgentCoordinator(runtimes={runtime.name: runtime}, store=store)
    task = asyncio.create_task(coordinator.submit(request()))
    try:
        await asyncio.wait_for(store.settlement_entered.wait(), 1)
        if cancelled:
            task.cancel("first caller interruption")
            await asyncio.sleep(0)
            task.cancel("second caller interruption")
            await asyncio.sleep(0)
            assert not task.done()
        store.release_settlement.set()
        with pytest.raises(LookupError) as caught:
            await task
        assert caught.value is store.settlement_error
        chain = exception_chain(caught.value)
        assert store.write_error in chain
        if cancelled:
            assert any(isinstance(e, asyncio.CancelledError) and str(e) == "first caller interruption" for e in chain)
        row = await store.get_by_request(request().request_id)
        assert row is not None
        assert row.status is (Status.PREPARING if fault == "before" else Status.LOST)
        assert len(row.events) == (3 if fault == "before" else 4)
        assert await coordinator.submit(request()) == row.ref
        assert runtime.starts == [row.ref]
        assert store.running_calls == store.settlement_calls == 1
    finally:
        store.release_settlement.set()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("winner", [Status.RUNNING, *sorted(TERMINAL_DELEGATED_AGENT_STATUSES)])
async def test_late_committed_or_terminal_winner_is_preserved_at_conditional_lock(winner: Status) -> None:
    store = AcceptanceStore("before", block="settlement")
    runtime = AcceptanceRuntime()
    coordinator = DelegatedAgentCoordinator(runtimes={runtime.name: runtime}, store=store)
    task = asyncio.create_task(coordinator.submit(request()))
    try:
        await asyncio.wait_for(store.settlement_entered.wait(), 1)
        row = await store.get_by_request(request().request_id)
        assert row is not None
        await InMemoryDelegatedAgentJobStore.transition(store, row.ref.job_id, Status.RUNNING)
        if winner is not Status.RUNNING:
            await store.adopt(
                row.ref.job_id,
                DelegatedAgentResult.model_validate(
                    {
                        "job_id": row.ref.job_id,
                        "status": winner,
                        "error": "terminal winner"
                        if winner in {Status.FAILED, Status.TIMED_OUT, Status.LOST}
                        else None,
                    }
                ),
            )
        preserved = await store.get(row.ref.job_id)
        store.release_settlement.set()
        assert await task == row.ref
        assert await store.get(row.ref.job_id) == preserved
        assert store.settlement_calls == 1
        assert runtime.starts == [row.ref]
    finally:
        store.release_settlement.set()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_conditional_lost_wins_before_late_running_and_adopts_only_once() -> None:
    store = InMemoryDelegatedAgentJobStore()
    ref = await prepared(store)
    settled, adopted = await store.settle_acceptance_failure(ref.job_id, lost(ref.job_id))
    assert adopted
    assert settled.status is Status.LOST
    assert settled.events[-1].kind is DelegatedAgentEventKind.RESULT_ADOPTED
    assert len(settled.events) == 4
    duplicate, adopted = await store.settle_acceptance_failure(ref.job_id, lost(ref.job_id))
    assert not adopted
    assert duplicate == settled
    with pytest.raises(IllegalDelegatedAgentTransitionError):
        await store.transition(ref.job_id, Status.RUNNING)
    assert await store.get(ref.job_id) == settled


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["identity", "status", "shape"])
@pytest.mark.parametrize("state", [Status.PREPARING, Status.RUNNING, Status.SUCCEEDED])
async def test_conditional_settlement_rejects_invalid_result_without_mutation(invalid: str, state: Status) -> None:
    store = InMemoryDelegatedAgentJobStore()
    ref = await prepared(store)
    if state is not Status.PREPARING:
        await store.transition(ref.job_id, Status.RUNNING)
    if state is Status.SUCCEEDED:
        await store.adopt(ref.job_id, DelegatedAgentResult(job_id=ref.job_id, status=state))
    before = await store.get(ref.job_id)
    result = (
        lost("other-job")
        if invalid == "identity"
        else DelegatedAgentResult(job_id=ref.job_id, status=Status.SUCCEEDED)
        if invalid == "status"
        else DelegatedAgentResult.model_construct(job_id=ref.job_id, status=Status.LOST, error=None)
    )
    with pytest.raises(ValueError, match=r"Result for job|LOST|error"):
        await store.settle_acceptance_failure(ref.job_id, result)
    assert await store.get(ref.job_id) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("state", [None, Status.QUEUED, Status.ADMITTED])
async def test_conditional_settlement_refuses_missing_or_unexpected_state(state: Status | None) -> None:
    store = InMemoryDelegatedAgentJobStore()
    req = request()
    ref = DelegatedAgentJobRef(job_id="job", request_id=req.request_id, run_id=req.run_id, runtime=req.runtime)
    if state is not None:
        await store.create(req, ref)
        if state is Status.ADMITTED:
            await store.transition(ref.job_id, state)
    before = await store.get(ref.job_id)
    error = UnknownDelegatedAgentJobError if state is None else IllegalDelegatedAgentTransitionError
    with pytest.raises(error):
        await store.settle_acceptance_failure(ref.job_id, lost(ref.job_id))
    assert await store.get(ref.job_id) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("message", ["", "x" * 20_000], ids=["empty", "oversized"])
async def test_acceptance_failure_diagnostic_cannot_prevent_lost_settlement(message: str) -> None:
    store = AcceptanceStore("before")
    store.write_error = OSError(message)
    runtime = AcceptanceRuntime()
    coordinator = DelegatedAgentCoordinator(runtimes={runtime.name: runtime}, store=store)
    with pytest.raises(OSError, match=message or r"^$") as caught:
        await coordinator.submit(request())
    assert caught.value is store.write_error
    job = await store.get_by_request(request().request_id)
    assert job is not None
    assert job.status is Status.LOST
    assert job.result is not None
    assert job.result.error
    assert len(job.result.error) <= 16_384
    assert job.result.error == "OSError" if not message else job.result.error.endswith("\n...[truncated]")
