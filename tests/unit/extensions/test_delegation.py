from __future__ import annotations

import pytest

from lychd.domain.artifacts import ArtifactRef
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
@pytest.mark.parametrize("maximum_prompt", [False, True])
async def test_reference_runtime_bounds_echo_for_valid_large_prompt(*, maximum_prompt: bool) -> None:
    prefix = "Reference delegate completed: "
    text_limit = 1_048_576
    prompt = "é" * (text_limit if maximum_prompt else text_limit - len(prefix))
    context = _assembled_delegation()
    coordinator = DelegatedAgentCoordinator(
        runtimes=context.delegated_runtimes.runtime_adapters,
        store=InMemoryDelegatedAgentJobStore(),
    )
    request = DelegatedAgentRequest(
        request_id="large-reference-request",
        run_id="reference-run",
        step_id="delegate",
        runtime="reference",
        prompt=prompt,
    )

    ref = await coordinator.submit(request)
    completed = await coordinator.refresh(ref.job_id)

    assert completed.status is DelegatedAgentJobStatus.SUCCEEDED
    assert completed.result is not None
    output = completed.result.output
    assert output is not None
    assert len(output) == text_limit
    if maximum_prompt:
        assert output.startswith(prefix + "é")
        assert output.endswith("\n...[truncated]")
    else:
        assert output == prefix + prompt
    assert completed.request.prompt == prompt
    assert await coordinator.submit(request) == ref


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


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["poll", "cancel"])
@pytest.mark.parametrize("substitution", ["prompt", "artifact"])
async def test_reference_runtime_rejects_request_substitution_without_mutating_projection(
    operation: str, substitution: str
) -> None:
    runtime = _assembled_delegation().delegated_runtimes.runtime_adapters["reference"]
    request = DelegatedAgentRequest(
        request_id="retained-request",
        run_id="run",
        step_id="delegate",
        runtime="reference",
        prompt="original",
        input_artifacts=(
            ArtifactRef(
                artifact_id="input",
                digest="sha256:" + "a" * 64,
                media_type="text/plain",
                size=12,
                classification="internal",
            ),
        ),
    )
    job = DelegatedAgentJobRef(job_id="job", request_id=request.request_id, run_id=request.run_id, runtime="reference")
    await runtime.start(request, job)
    changed = (
        request.model_copy(update={"prompt": "substituted"})
        if substitution == "prompt"
        else request.model_copy(
            update={"input_artifacts": (request.input_artifacts[0].model_copy(update={"classification": "public"}),)}
        )
    )

    runtime_operation = runtime.poll if operation == "poll" else runtime.cancel
    with pytest.raises(ValueError, match="does not match"):
        await runtime_operation(job, request=changed)
    result = await runtime.poll(job, request=request)
    assert result is not None
    assert result.status is DelegatedAgentJobStatus.SUCCEEDED
    assert result.output == "Reference delegate completed: original"
    await runtime.cancel(job, request=request)
    await runtime.cancel(job, request=request)
    cancelled = await runtime.poll(job, request=request)
    assert cancelled is not None
    assert cancelled.status is DelegatedAgentJobStatus.CANCELLED
