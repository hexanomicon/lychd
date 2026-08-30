from __future__ import annotations

import pytest

from lychd.domain.delegation import (
    DelegatedAgentCoordinator,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentProfile,
    DelegatedAgentRequest,
    InMemoryDelegatedAgentJobStore,
)
from lychd.extensions.context import ExtensionContext
from lychd.extensions.manager import ExtensionManager


def _assembled_delegation() -> ExtensionContext:
    return ExtensionManager(builtins=["delegation"], crypt=[]).assemble()


@pytest.mark.asyncio
async def test_reference_runtime_completes_through_real_coordinator_without_network() -> None:
    context = _assembled_delegation()
    coordinator = DelegatedAgentCoordinator(
        runtimes=context.delegated_runtimes.runtime_adapters,
        store=InMemoryDelegatedAgentJobStore(),
    )
    request = DelegatedAgentRequest(
        request_id="reference-request",
        run_id="reference-run",
        step_id="delegate",
        runtime="reference",
        profile=DelegatedAgentProfile.READ,
        prompt="weave the graph",
    )

    ref = await coordinator.submit(request)
    running = await coordinator.get(ref.job_id)
    completed = await coordinator.refresh(ref.job_id)

    assert running is not None
    assert running.status is DelegatedAgentJobStatus.RUNNING
    assert completed.status is DelegatedAgentJobStatus.SUCCEEDED
    assert completed.result is not None
    assert completed.result.output == "Reference delegate completed: weave the graph"


@pytest.mark.asyncio
async def test_reference_runtime_cancellation_is_terminal_and_idempotent() -> None:
    context = _assembled_delegation()
    coordinator = DelegatedAgentCoordinator(
        runtimes=context.delegated_runtimes.runtime_adapters,
        store=InMemoryDelegatedAgentJobStore(),
    )
    request = DelegatedAgentRequest(
        request_id="cancel-reference",
        run_id="reference-run",
        step_id="delegate",
        runtime="reference",
        prompt="cancel me",
    )
    ref = await coordinator.submit(request)

    assert await coordinator.cancel(ref.job_id) is True
    assert await coordinator.cancel(ref.job_id) is False
    cancelled = await coordinator.get(ref.job_id)
    assert cancelled is not None
    assert cancelled.status is DelegatedAgentJobStatus.CANCELLED


@pytest.mark.asyncio
async def test_reference_runtime_rejects_uncorrelated_job_identity() -> None:
    context = _assembled_delegation()
    runtime = context.delegated_runtimes.runtime_adapters["reference"]
    request = DelegatedAgentRequest(
        request_id="request-1",
        run_id="run-1",
        step_id="delegate",
        runtime="reference",
        prompt="work",
    )
    mismatched = DelegatedAgentJobRef(
        job_id="job-1",
        request_id="different",
        run_id="run-1",
        runtime="reference",
    )

    with pytest.raises(ValueError, match="does not match"):
        await runtime.start(request, mismatched)
