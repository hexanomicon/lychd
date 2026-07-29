from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

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
    InMemoryDelegatedAgentJobStore,
)
from lychd.domain.delegation.services import DelegatedAgentIdempotencyConflictError


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


def test_fake_adapter_conforms_to_runtime_port() -> None:
    assert isinstance(FakeDelegatedAgentRuntime(), DelegatedAgentRuntime)


def test_typed_contracts_round_trip_with_artifact_refs() -> None:
    request = _request()
    restored = DelegatedAgentRequest.model_validate_json(request.model_dump_json())

    assert restored == request
    assert restored.input_artifacts[0].modality == "binary"


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
