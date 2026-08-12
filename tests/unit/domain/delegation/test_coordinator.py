from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import cast

import pytest

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.delegation import (
    DelegatedAgentCoordinator,
    DelegatedAgentEventKind,
    DelegatedAgentJob,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentProfile,
    DelegatedAgentRequest,
    DelegatedAgentResult,
    DelegatedAgentRuntime,
    IllegalDelegatedAgentTransitionError,
    InMemoryDelegatedAgentJobStore,
)
from lychd.domain.delegation.services import DelegatedAgentIdempotencyConflictError
from lychd.extensions.builtin.delegation.reference import ReferenceDelegatedAgentRuntime


@dataclass
class FakeDelegatedAgentRuntime:
    """Deterministic adapter used to prove the structural runtime contract."""

    name: str = "fake"
    starts: list[DelegatedAgentRequest] = field(default_factory=list)
    polls: list[str] = field(default_factory=list)
    cancellations: list[str] = field(default_factory=list)
    next_result: DelegatedAgentResult | None = None

    async def start(self, request: DelegatedAgentRequest, job: DelegatedAgentJobRef) -> None:
        self.starts.append(request)
        await asyncio.sleep(0)
        assert job.request_id == request.request_id

    async def poll(self, job: DelegatedAgentJobRef) -> DelegatedAgentResult | None:
        self.polls.append(job.job_id)
        return self.next_result

    async def cancel(self, job: DelegatedAgentJobRef) -> None:
        self.cancellations.append(job.job_id)


def _request(*, request_id: str = "req-1", prompt: str = "inspect the repository") -> DelegatedAgentRequest:
    return DelegatedAgentRequest(
        request_id=request_id,
        run_id="run-1",
        step_id="step-1",
        runtime="fake",
        profile=DelegatedAgentProfile.READ,
        prompt=prompt,
        input_artifacts=(
            ArtifactRef(
                artifact_id="artifact-1",
                digest=f"sha256:{'a' * 64}",
                media_type="text/plain",
                size=12,
                classification="internal",
            ),
        ),
    )


def _coordinator() -> tuple[DelegatedAgentCoordinator, FakeDelegatedAgentRuntime]:
    runtime = FakeDelegatedAgentRuntime()
    return (
        DelegatedAgentCoordinator(
            runtimes={runtime.name: runtime},
            store=InMemoryDelegatedAgentJobStore(),
        ),
        runtime,
    )


def _coordinator_lock_count(coordinator: DelegatedAgentCoordinator) -> int:
    """Read the private lock registry only for lifecycle regression evidence."""
    return len(cast("dict[str, object]", vars(coordinator)["_locks"]))


def _reference_projection_count(runtime: ReferenceDelegatedAgentRuntime) -> int:
    """Read retained pure projections for lifecycle regression evidence."""
    return len(cast("dict[str, object]", vars(runtime)["_jobs"]))


def test_fake_adapter_conforms_to_runtime_port() -> None:
    assert isinstance(FakeDelegatedAgentRuntime(), DelegatedAgentRuntime)


def test_typed_contracts_round_trip_with_artifact_refs() -> None:
    request = _request()
    restored = DelegatedAgentRequest.model_validate_json(request.model_dump_json())

    assert restored == request
    assert restored.input_artifacts[0].modality == "binary"


@pytest.mark.asyncio
async def test_terminal_store_transition_requires_result_adoption() -> None:
    store = InMemoryDelegatedAgentJobStore()
    request = _request()
    ref = DelegatedAgentJobRef(
        job_id="job-terminal-evidence",
        request_id=request.request_id,
        run_id=request.run_id,
        runtime=request.runtime,
        profile=request.profile,
    )
    await store.create(request, ref)

    with pytest.raises(IllegalDelegatedAgentTransitionError, match="requires adopt"):
        await store.transition(ref.job_id, DelegatedAgentJobStatus.SUCCEEDED)


@pytest.mark.asyncio
async def test_concurrent_submit_starts_one_external_job() -> None:
    coordinator, runtime = _coordinator()
    request = _request()

    first, second = await asyncio.gather(coordinator.submit(request), coordinator.submit(request))

    assert first == second
    assert runtime.starts == [request]
    events = await coordinator.events(first.job_id)
    assert [event.status for event in events] == [
        DelegatedAgentJobStatus.QUEUED,
        DelegatedAgentJobStatus.ADMITTED,
        DelegatedAgentJobStatus.PREPARING,
        DelegatedAgentJobStatus.RUNNING,
    ]
    assert all(event.kind is DelegatedAgentEventKind.STATUS_CHANGED for event in events)
    correlated = await coordinator.jobs_for_run("run-1")
    assert [job.ref for job in correlated] == [first]
    assert _coordinator_lock_count(coordinator) == 0


@pytest.mark.asyncio
async def test_completed_unique_requests_and_jobs_do_not_accumulate_locks() -> None:
    coordinator, runtime = _coordinator()

    for index in range(32):
        ref = await coordinator.submit(_request(request_id=f"finite-lock-{index}"))
        runtime.next_result = DelegatedAgentResult(
            job_id=ref.job_id,
            status=DelegatedAgentJobStatus.SUCCEEDED,
            output="complete",
        )
        await coordinator.refresh(ref.job_id)

    assert _coordinator_lock_count(coordinator) == 0


@pytest.mark.asyncio
async def test_cancelled_same_request_waiter_releases_its_lock_reference() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()

    @dataclass
    class _BlockingRuntime(FakeDelegatedAgentRuntime):
        async def start(self, request: DelegatedAgentRequest, job: DelegatedAgentJobRef) -> None:
            self.starts.append(request)
            assert job.request_id == request.request_id
            entered.set()
            await release.wait()

    runtime = _BlockingRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=InMemoryDelegatedAgentJobStore(),
    )
    request = _request(request_id="cancelled-waiter")
    leader = asyncio.create_task(coordinator.submit(request))
    await asyncio.wait_for(entered.wait(), timeout=1)
    waiter = asyncio.create_task(coordinator.submit(request))
    await asyncio.sleep(0)

    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter
    assert _coordinator_lock_count(coordinator) == 1

    release.set()
    await leader

    assert runtime.starts == [request]
    assert _coordinator_lock_count(coordinator) == 0


@pytest.mark.asyncio
async def test_repeated_cancellation_cannot_interrupt_indeterminate_submission_settlement() -> None:
    class _DelayedLostStore(InMemoryDelegatedAgentJobStore):
        def __init__(self) -> None:
            super().__init__()
            self.lost_adoption_started = asyncio.Event()
            self.release_lost_adoption = asyncio.Event()

        async def adopt(
            self,
            job_id: str,
            result: DelegatedAgentResult,
        ) -> tuple[DelegatedAgentJob, bool]:
            if result.status is DelegatedAgentJobStatus.LOST:
                self.lost_adoption_started.set()
                await self.release_lost_adoption.wait()
            return await super().adopt(job_id, result)

    @dataclass
    class _BlockingStartRuntime(FakeDelegatedAgentRuntime):
        start_entered: asyncio.Event = field(default_factory=asyncio.Event)

        async def start(self, request: DelegatedAgentRequest, job: DelegatedAgentJobRef) -> None:
            self.starts.append(request)
            assert job.request_id == request.request_id
            self.start_entered.set()
            await asyncio.Event().wait()

    store = _DelayedLostStore()
    runtime = _BlockingStartRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=store,
    )
    request = _request(request_id="repeated-submit-cancel")
    submission = asyncio.create_task(coordinator.submit(request))
    await asyncio.wait_for(runtime.start_entered.wait(), timeout=1)

    submission.cancel()
    await asyncio.wait_for(store.lost_adoption_started.wait(), timeout=1)
    submission.cancel()
    await asyncio.sleep(0)
    store.release_lost_adoption.set()

    with pytest.raises(asyncio.CancelledError):
        await submission
    settled = await store.get_by_request(request.request_id)
    assert settled is not None
    assert settled.status is DelegatedAgentJobStatus.LOST
    assert _coordinator_lock_count(coordinator) == 0


@pytest.mark.asyncio
async def test_repeated_cancellation_finishes_running_transition_after_runtime_acceptance() -> None:
    class _DelayedRunningStore(InMemoryDelegatedAgentJobStore):
        def __init__(self) -> None:
            super().__init__()
            self.running_transition_started = asyncio.Event()
            self.release_running_transition = asyncio.Event()

        async def transition(
            self,
            job_id: str,
            status: DelegatedAgentJobStatus,
        ) -> tuple[DelegatedAgentJob, bool]:
            if status is DelegatedAgentJobStatus.RUNNING:
                self.running_transition_started.set()
                await self.release_running_transition.wait()
            return await super().transition(job_id, status)

    store = _DelayedRunningStore()
    runtime = FakeDelegatedAgentRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=store,
    )
    request = _request(request_id="cancel-after-runtime-acceptance")
    submission = asyncio.create_task(coordinator.submit(request))
    await asyncio.wait_for(store.running_transition_started.wait(), timeout=1)

    submission.cancel()
    await asyncio.sleep(0)
    submission.cancel()
    await asyncio.sleep(0)
    assert not submission.done()
    store.release_running_transition.set()

    with pytest.raises(asyncio.CancelledError):
        await submission
    settled = await store.get_by_request(request.request_id)
    assert settled is not None
    assert settled.status is DelegatedAgentJobStatus.RUNNING
    assert runtime.starts == [request]
    assert _coordinator_lock_count(coordinator) == 0


@pytest.mark.asyncio
async def test_jobs_for_run_limit_returns_newest_jobs_in_creation_order() -> None:
    coordinator, _runtime = _coordinator()
    refs = [await coordinator.submit(_request(request_id=f"bounded-{index}")) for index in range(3)]

    bounded = await coordinator.jobs_for_run("run-1", limit=2, event_limit=2)

    assert [job.ref for job in bounded] == refs[1:]
    assert [[event.seq for event in job.events] for job in bounded] == [[2, 3], [2, 3]]
    assert await coordinator.jobs_for_run("run-1", limit=0) == ()


@pytest.mark.asyncio
async def test_submit_loser_uses_durable_winner_identity_without_second_start() -> None:
    request = _request(request_id="cross-coordinator")
    store = InMemoryDelegatedAgentJobStore()
    winner = DelegatedAgentJobRef(
        job_id="winner-job",
        request_id=request.request_id,
        run_id=request.run_id,
        runtime=request.runtime,
        profile=request.profile,
    )
    await store.create(request, winner)

    class _RacingStore(InMemoryDelegatedAgentJobStore):
        async def get_by_request(self, request_id: str) -> DelegatedAgentJob | None:
            _ = request_id
            return None

        async def create(
            self,
            request: DelegatedAgentRequest,
            ref: DelegatedAgentJobRef,
        ) -> tuple[DelegatedAgentJob, bool]:
            _ = ref
            existing = await store.get_by_request(request.request_id)
            assert existing is not None
            return existing, False

    runtime = FakeDelegatedAgentRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=_RacingStore(),
    )

    assert await coordinator.submit(request) == winner
    assert runtime.starts == []


@pytest.mark.asyncio
async def test_unrelated_requests_can_start_in_parallel() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()

    @dataclass
    class _BlockingRuntime(FakeDelegatedAgentRuntime):
        async def start(self, request: DelegatedAgentRequest, job: DelegatedAgentJobRef) -> None:
            self.starts.append(request)
            assert job.request_id == request.request_id
            if len(self.starts) == 2:
                entered.set()
            await release.wait()

    runtime = _BlockingRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=InMemoryDelegatedAgentJobStore(),
    )
    first = asyncio.create_task(coordinator.submit(_request(request_id="parallel-1")))
    second = asyncio.create_task(coordinator.submit(_request(request_id="parallel-2")))

    await asyncio.wait_for(entered.wait(), timeout=1)
    release.set()
    refs = await asyncio.gather(first, second)

    assert len(runtime.starts) == 2
    assert refs[0] != refs[1]


@pytest.mark.asyncio
async def test_request_id_reuse_with_different_content_is_rejected() -> None:
    coordinator, runtime = _coordinator()
    await coordinator.submit(_request())

    with pytest.raises(DelegatedAgentIdempotencyConflictError):
        await coordinator.submit(_request(prompt="different work"))

    assert len(runtime.starts) == 1


@pytest.mark.asyncio
async def test_poll_adopts_result_once_without_repolling_terminal_job() -> None:
    coordinator, runtime = _coordinator()
    ref = await coordinator.submit(_request())
    runtime.next_result = DelegatedAgentResult(
        job_id=ref.job_id,
        status=DelegatedAgentJobStatus.SUCCEEDED,
        output="complete",
    )

    first = await coordinator.refresh(ref.job_id)
    second = await coordinator.refresh(ref.job_id)

    assert first == second
    assert first.status is DelegatedAgentJobStatus.SUCCEEDED
    assert len(runtime.starts) == 1
    assert runtime.polls == [ref.job_id]
    assert [event.kind for event in first.events] == [
        DelegatedAgentEventKind.STATUS_CHANGED,
        DelegatedAgentEventKind.STATUS_CHANGED,
        DelegatedAgentEventKind.STATUS_CHANGED,
        DelegatedAgentEventKind.STATUS_CHANGED,
        DelegatedAgentEventKind.RESULT_ADOPTED,
    ]


@pytest.mark.asyncio
async def test_direct_adopt_is_idempotent() -> None:
    coordinator, _runtime = _coordinator()
    ref = await coordinator.submit(_request())
    result = DelegatedAgentResult(
        job_id=ref.job_id,
        status=DelegatedAgentJobStatus.FAILED,
        error="adapter failed",
    )

    assert await coordinator.adopt(ref.job_id, result) is True
    assert await coordinator.adopt(ref.job_id, result) is False
    events = await coordinator.events(ref.job_id)
    assert [event.kind for event in events].count(DelegatedAgentEventKind.RESULT_ADOPTED) == 1


@pytest.mark.asyncio
async def test_cancel_is_idempotent_and_late_result_is_not_adopted() -> None:
    coordinator, runtime = _coordinator()
    ref = await coordinator.submit(_request())
    late = DelegatedAgentResult(
        job_id=ref.job_id,
        status=DelegatedAgentJobStatus.SUCCEEDED,
        output="too late",
    )

    assert await coordinator.cancel(ref.job_id) is True
    assert await coordinator.cancel(ref.job_id) is False
    assert await coordinator.adopt(ref.job_id, late) is False

    job = await coordinator.get(ref.job_id)
    assert job is not None
    assert job.status is DelegatedAgentJobStatus.CANCELLED
    assert runtime.cancellations == [ref.job_id]
    assert [event.kind for event in job.events] == [
        DelegatedAgentEventKind.STATUS_CHANGED,
        DelegatedAgentEventKind.STATUS_CHANGED,
        DelegatedAgentEventKind.STATUS_CHANGED,
        DelegatedAgentEventKind.STATUS_CHANGED,
        DelegatedAgentEventKind.STATUS_CHANGED,
    ]


@pytest.mark.asyncio
async def test_repeated_cancellation_cannot_interrupt_post_containment_settlement() -> None:
    class _DelayedCancelStore(InMemoryDelegatedAgentJobStore):
        def __init__(self) -> None:
            super().__init__()
            self.cancellation_started = asyncio.Event()
            self.release_cancellation = asyncio.Event()

        async def cancel(self, job_id: str) -> tuple[DelegatedAgentJob, bool]:
            self.cancellation_started.set()
            await self.release_cancellation.wait()
            return await super().cancel(job_id)

    store = _DelayedCancelStore()
    runtime = FakeDelegatedAgentRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=store,
    )
    ref = await coordinator.submit(_request(request_id="repeated-post-containment-cancel"))
    cancellation = asyncio.create_task(coordinator.cancel(ref.job_id))
    await asyncio.wait_for(store.cancellation_started.wait(), timeout=1)

    cancellation.cancel()
    await asyncio.sleep(0)
    cancellation.cancel()
    await asyncio.sleep(0)
    assert not cancellation.done()
    store.release_cancellation.set()

    with pytest.raises(asyncio.CancelledError):
        await cancellation
    settled = await store.get(ref.job_id)
    assert settled is not None
    assert settled.status is DelegatedAgentJobStatus.CANCELLED
    assert runtime.cancellations == [ref.job_id]
    assert _coordinator_lock_count(coordinator) == 0


@pytest.mark.asyncio
async def test_cancel_rehydrates_effect_free_reference_job_after_restart() -> None:
    store = InMemoryDelegatedAgentJobStore()
    first_runtime = ReferenceDelegatedAgentRuntime()
    first_coordinator = DelegatedAgentCoordinator(
        runtimes={first_runtime.name: first_runtime},
        store=store,
    )
    request = DelegatedAgentRequest(
        request_id="reference-cancel-restart",
        run_id="run-reference-cancel-restart",
        step_id="step-reference-cancel-restart",
        runtime=first_runtime.name,
        prompt="cancel after restart",
    )
    ref = await first_coordinator.submit(request)

    restarted_runtime = ReferenceDelegatedAgentRuntime()
    restarted_coordinator = DelegatedAgentCoordinator(
        runtimes={restarted_runtime.name: restarted_runtime},
        store=store,
    )

    assert await restarted_coordinator.cancel(ref.job_id) is True
    settled = await restarted_coordinator.get(ref.job_id)
    assert settled is not None
    assert settled.status is DelegatedAgentJobStatus.CANCELLED
    assert settled.result is not None
    assert settled.result.status is DelegatedAgentJobStatus.CANCELLED
    assert _reference_projection_count(restarted_runtime) == 0


@pytest.mark.asyncio
async def test_reference_runtime_retires_high_cardinality_terminal_projections() -> None:
    runtime = ReferenceDelegatedAgentRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=InMemoryDelegatedAgentJobStore(),
    )

    for index in range(128):
        request = DelegatedAgentRequest(
            request_id=f"reference-retirement-{index}",
            run_id="run-reference-retirement",
            step_id="delegate",
            runtime=runtime.name,
            prompt=f"bounded projection {index}",
        )
        ref = await coordinator.submit(request)
        if index % 3 == 0:
            assert await coordinator.adopt(
                ref.job_id,
                DelegatedAgentResult(
                    job_id=ref.job_id,
                    status=DelegatedAgentJobStatus.SUCCEEDED,
                    output=f"direct adoption {index}",
                ),
            )
        elif index % 3 == 1:
            settled = await coordinator.refresh(ref.job_id)
            assert settled.status is DelegatedAgentJobStatus.SUCCEEDED
        else:
            assert await coordinator.cancel(ref.job_id) is True
        assert _reference_projection_count(runtime) == 0


@pytest.mark.asyncio
async def test_reference_projection_survives_adoption_failure_until_retry_succeeds() -> None:
    class _FailFirstTerminalAdoptionStore(InMemoryDelegatedAgentJobStore):
        def __init__(self) -> None:
            super().__init__()
            self.failed = False

        async def adopt(
            self,
            job_id: str,
            result: DelegatedAgentResult,
        ) -> tuple[DelegatedAgentJob, bool]:
            if result.status is DelegatedAgentJobStatus.SUCCEEDED and not self.failed:
                self.failed = True
                msg = "terminal adoption unavailable"
                raise RuntimeError(msg)
            return await super().adopt(job_id, result)

    store = _FailFirstTerminalAdoptionStore()
    runtime = ReferenceDelegatedAgentRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=store,
    )
    request = DelegatedAgentRequest(
        request_id="reference-adoption-retry",
        run_id="run-reference-adoption-retry",
        step_id="delegate",
        runtime=runtime.name,
        prompt="retain until the ledger acknowledges",
    )
    ref = await coordinator.submit(request)

    with pytest.raises(RuntimeError, match="terminal adoption unavailable"):
        await coordinator.refresh(ref.job_id)
    unsettled = await store.get(ref.job_id)
    assert unsettled is not None
    assert unsettled.status is DelegatedAgentJobStatus.RUNNING
    assert _reference_projection_count(runtime) == 1

    settled = await coordinator.refresh(ref.job_id)
    assert settled.status is DelegatedAgentJobStatus.SUCCEEDED
    assert settled.result is not None
    assert settled.result.output == "Reference delegate completed: retain until the ledger acknowledges"
    assert _reference_projection_count(runtime) == 0


@pytest.mark.asyncio
async def test_reference_retirement_finishes_before_refresh_cancellation_propagates() -> None:
    class _DelayedRetirementRuntime(ReferenceDelegatedAgentRuntime):
        def __init__(self) -> None:
            super().__init__()
            self.retirement_started = asyncio.Event()
            self.release_retirement = asyncio.Event()

        async def retire_effect_free(self, job: DelegatedAgentJobRef) -> None:
            self.retirement_started.set()
            await self.release_retirement.wait()
            await super().retire_effect_free(job)

    store = InMemoryDelegatedAgentJobStore()
    runtime = _DelayedRetirementRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=store,
    )
    request = DelegatedAgentRequest(
        request_id="reference-retirement-cancel",
        run_id="run-reference-retirement-cancel",
        step_id="delegate",
        runtime=runtime.name,
        prompt="retire after durable adoption",
    )
    ref = await coordinator.submit(request)
    refresh = asyncio.create_task(coordinator.refresh(ref.job_id))
    await asyncio.wait_for(runtime.retirement_started.wait(), timeout=1)
    settled = await store.get(ref.job_id)
    assert settled is not None
    assert settled.status is DelegatedAgentJobStatus.SUCCEEDED
    assert _reference_projection_count(runtime) == 1

    refresh.cancel()
    await asyncio.sleep(0)
    refresh.cancel()
    await asyncio.sleep(0)
    assert not refresh.done()
    runtime.release_retirement.set()

    with pytest.raises(asyncio.CancelledError):
        await refresh
    assert _reference_projection_count(runtime) == 0


@pytest.mark.asyncio
async def test_lost_is_terminal_and_never_polled_or_retried() -> None:
    coordinator, runtime = _coordinator()
    ref = await coordinator.submit(_request())
    lost = DelegatedAgentResult(
        job_id=ref.job_id,
        status=DelegatedAgentJobStatus.LOST,
        error="runtime no longer recognizes the job",
    )

    assert await coordinator.adopt(ref.job_id, lost) is True
    settled = await coordinator.refresh(ref.job_id)

    assert settled.status is DelegatedAgentJobStatus.LOST
    assert runtime.polls == []
    assert await coordinator.adopt(ref.job_id, lost) is False


@pytest.mark.asyncio
async def test_cancel_contains_lost_job_before_recording_cancellation() -> None:
    coordinator, runtime = _coordinator()
    ref = await coordinator.submit(_request())
    lost = DelegatedAgentResult(
        job_id=ref.job_id,
        status=DelegatedAgentJobStatus.LOST,
        error="submission outcome was indeterminate",
    )
    assert await coordinator.adopt(ref.job_id, lost) is True

    assert await coordinator.cancel(ref.job_id) is True
    assert await coordinator.cancel(ref.job_id) is False

    settled = await coordinator.get(ref.job_id)
    assert settled is not None
    assert settled.status is DelegatedAgentJobStatus.CANCELLED
    assert settled.result is not None
    assert settled.result.status is DelegatedAgentJobStatus.CANCELLED
    assert runtime.cancellations == [ref.job_id]
