"""Lost start acknowledgements retain exact job and containment ownership."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

from lychd.domain.delegation import (
    DelegatedAgentCoordinator,
    DelegatedAgentJob,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentRequest,
    DelegatedAgentResult,
    InMemoryDelegatedAgentJobStore,
)
from lychd.domain.delegation.services import UnknownDelegatedAgentRuntimeError


@dataclass
class _LostAcknowledgementRuntime:
    """Simulate acceptance in memory; never launch a process or contact a service."""

    name: str = "lost-acknowledgement"
    accepted: list[DelegatedAgentJobRef] = field(default_factory=list)
    cancelled: list[DelegatedAgentJobRef] = field(default_factory=list)

    async def start(self, request: DelegatedAgentRequest, job: DelegatedAgentJobRef) -> None:
        assert request.request_id == job.request_id
        self.accepted.append(job)
        msg = "acknowledgement lost after simulated acceptance"
        raise OSError(msg)

    async def poll(self, job: DelegatedAgentJobRef) -> DelegatedAgentResult | None:
        msg = f"Lost job {job.job_id} must not be polled as active."
        raise AssertionError(msg)

    async def cancel(self, job: DelegatedAgentJobRef) -> None:
        self.cancelled.append(job)


def _request() -> DelegatedAgentRequest:
    return DelegatedAgentRequest(
        request_id="lost-ack-request",
        run_id="lost-ack-run",
        step_id="lost-ack-step",
        runtime="lost-acknowledgement",
        prompt="Exercise only an inert adapter.",
    )


@pytest.mark.asyncio
async def test_lost_start_acknowledgement_preserves_replay_and_containment_identity() -> None:
    runtime = _LostAcknowledgementRuntime()
    store = InMemoryDelegatedAgentJobStore()
    coordinator = DelegatedAgentCoordinator(runtimes={runtime.name: runtime}, store=store)
    request = _request()

    with pytest.raises(OSError, match="acknowledgement lost"):
        await coordinator.submit(request)

    lost = await store.get_by_request(request.request_id)
    assert lost is not None
    assert lost.status is DelegatedAgentJobStatus.LOST
    assert lost.result is not None
    assert lost.result.status is DelegatedAgentJobStatus.LOST
    assert runtime.accepted == [lost.ref]

    assert await coordinator.submit(request) == lost.ref
    assert await coordinator.refresh(lost.ref.job_id) == lost
    assert runtime.accepted == [lost.ref]
    assert (
        await coordinator.adopt(
            lost.ref.job_id,
            DelegatedAgentResult(
                job_id=lost.ref.job_id,
                status=DelegatedAgentJobStatus.SUCCEEDED,
                output="A late provider claim cannot replace terminal truth.",
            ),
        )
        is False
    )
    assert await coordinator.get(lost.ref.job_id) == lost

    assert await coordinator.cancel(lost.ref.job_id) is True
    assert await coordinator.cancel(lost.ref.job_id) is False
    assert runtime.cancelled == [lost.ref]
    cancelled = await coordinator.get(lost.ref.job_id)
    assert cancelled is not None
    assert cancelled.status is DelegatedAgentJobStatus.CANCELLED
    assert cancelled.ref == lost.ref


@pytest.mark.asyncio
async def test_unknown_runtime_is_definitely_failed_before_start() -> None:
    store = InMemoryDelegatedAgentJobStore()
    coordinator = DelegatedAgentCoordinator(runtimes={}, store=store)
    request = _request()

    with pytest.raises(UnknownDelegatedAgentRuntimeError):
        await coordinator.submit(request)

    failed = await store.get_by_request(request.request_id)
    assert failed is not None
    assert failed.status is DelegatedAgentJobStatus.FAILED
    assert failed.result is not None
    assert failed.result.status is DelegatedAgentJobStatus.FAILED
    assert await coordinator.submit(request) == failed.ref
    assert await coordinator.cancel(failed.ref.job_id) is False


@pytest.mark.asyncio
async def test_cancellation_after_lost_acknowledgement_finishes_indeterminate_settlement() -> None:
    class _DelayedStore(InMemoryDelegatedAgentJobStore):
        def __init__(self) -> None:
            super().__init__()
            self.adoption_started = asyncio.Event()
            self.release_adoption = asyncio.Event()

        async def adopt(
            self,
            job_id: str,
            result: DelegatedAgentResult,
        ) -> tuple[DelegatedAgentJob, bool]:
            self.adoption_started.set()
            await self.release_adoption.wait()
            return await super().adopt(job_id, result)

    runtime = _LostAcknowledgementRuntime()
    store = _DelayedStore()
    coordinator = DelegatedAgentCoordinator(runtimes={runtime.name: runtime}, store=store)
    request = _request()
    submission = asyncio.create_task(coordinator.submit(request))
    await asyncio.wait_for(store.adoption_started.wait(), timeout=1)

    submission.cancel()
    await asyncio.sleep(0)
    submission.cancel()
    await asyncio.sleep(0)
    assert not submission.done()
    store.release_adoption.set()

    with pytest.raises(asyncio.CancelledError):
        await submission
    lost = await store.get_by_request(request.request_id)
    assert lost is not None
    assert lost.status is DelegatedAgentJobStatus.LOST
    assert await coordinator.submit(request) == lost.ref
    assert await coordinator.cancel(lost.ref.job_id) is True
    assert runtime.accepted == runtime.cancelled == [lost.ref]
