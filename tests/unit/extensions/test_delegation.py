from __future__ import annotations

from dataclasses import replace

import pytest

from lychd.domain.delegation import (
    DelegatedAgentCoordinator,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentProfile,
    DelegatedAgentRequest,
    DelegatedAgentRuntime,
    InMemoryDelegatedAgentJobStore,
)
from lychd.extensions.context import ExtensionContext
from lychd.extensions.delegation import DelegatedRuntimeDelivery, DelegatedRuntimeTransport
from lychd.extensions.manager import ExtensionManager


def _assembled_delegation() -> ExtensionContext:
    return ExtensionManager(builtins=["delegation"], crypt=[]).assemble()


def test_delegation_builtin_registers_full_catalog_but_only_reference_is_runnable() -> None:
    context = _assembled_delegation()

    assert [registration.definition.runtime_id for registration in context.delegated_runtimes.registrations] == [
        "reference",
        "codex-cli",
        "claude-code",
        "opencode-go",
        "openrouter",
    ]
    assert set(context.delegated_runtimes.runtime_adapters) == {"reference"}
    assert isinstance(context.delegated_runtimes.runtime_adapters["reference"], DelegatedAgentRuntime)
    assert all(registration.provider_id == "delegation" for registration in context.delegated_runtimes.registrations)


def test_cli_catalogue_records_only_locally_verified_command_semantics() -> None:
    context = _assembled_delegation()
    codex = context.delegated_runtimes.get("codex-cli")
    claude = context.delegated_runtimes.get("claude-code")
    opencode = context.delegated_runtimes.get("opencode-go")
    openrouter = context.delegated_runtimes.get("openrouter")

    assert codex is not None
    assert codex.definition.command is not None
    assert codex.definition.command.fixed_arguments == (
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--sandbox",
        "read-only",
        "-",
    )
    assert claude is not None
    assert claude.definition.command is not None
    assert claude.definition.command.fixed_arguments == (
        "--bare",
        "--print",
        "--output-format",
        "stream-json",
        "--no-session-persistence",
    )
    assert opencode is not None
    assert opencode.definition.command is not None
    assert opencode.definition.command.fixed_arguments == ()
    assert openrouter is not None
    assert openrouter.definition.transport is DelegatedRuntimeTransport.PROVIDER_API
    assert openrouter.definition.command is None


def test_every_effectful_catalogue_entry_is_fail_closed() -> None:
    context = _assembled_delegation()
    declared = [
        registration.definition
        for registration in context.delegated_runtimes.registrations
        if registration.definition.transport is not DelegatedRuntimeTransport.REFERENCE
    ]

    assert declared
    for definition in declared:
        assert definition.delivery is DelegatedRuntimeDelivery.DECLARED_ONLY
        assert definition.runtime_adapter is None
        assert definition.security.isolated_process is True
        assert definition.security.requires_nono is True
        assert definition.security.requires_provider_gate is True
        assert definition.security.permits_direct_provider_credentials is False


def test_declarative_registration_cannot_make_cli_adapter_runnable() -> None:
    context = _assembled_delegation()
    reference = context.delegated_runtimes.runtime_adapters["reference"]
    codex = context.delegated_runtimes.get("codex-cli")

    assert codex is not None
    with pytest.raises(ValueError, match="attested supervisor binding"):
        replace(
            codex.definition,
            delivery=DelegatedRuntimeDelivery.AVAILABLE,
            runtime_adapter=reference,
        )


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
