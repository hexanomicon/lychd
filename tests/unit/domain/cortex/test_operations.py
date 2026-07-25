from __future__ import annotations

import pytest

from lychd.domain.cortex.operations import (
    AGENT_RUN_OPERATION,
    RunConsentMode,
    RunExecutionKind,
    RunExecutionTarget,
    RunInputKind,
    RunInputSpec,
    RunMutationCharacteristic,
    RunOperationSpec,
    RunProgressProjection,
    RunResultProjection,
)
from lychd.extensions.context import ExtensionContext


def _service_operation(
    *,
    name: str,
    summary: str,
    inputs: tuple[RunInputSpec, ...] = (),
    required_scopes: frozenset[str] = frozenset(),
) -> RunOperationSpec:
    return RunOperationSpec(
        name=name,
        summary=summary,
        execution=RunExecutionTarget(
            kind=RunExecutionKind.SERVICE,
            name=f"cache.{name.replace('-', '_')}",
        ),
        mutation=RunMutationCharacteristic.READ_ONLY,
        consent=RunConsentMode.NONE,
        progress=RunProgressProjection.RUN_EVENTS,
        result=RunResultProjection.DURABLE_RUN_RECORD,
        inputs=inputs,
        required_scopes=required_scopes,
    )


def test_context_registers_core_agent_operation_with_submit_scope() -> None:
    context = ExtensionContext()

    registration = context.run_operations.get("agent")

    assert registration is not None
    assert registration.provider_id == "core"
    assert registration.spec is AGENT_RUN_OPERATION
    assert registration.required_scopes == frozenset({"runs:submit"})
    assert registration.spec.execution == RunExecutionTarget(
        kind=RunExecutionKind.WORKFLOW,
        name="bridge_chat",
    )
    assert registration.spec.mutation is RunMutationCharacteristic.MAY_MUTATE
    assert registration.spec.consent is RunConsentMode.POLICY
    assert registration.spec.progress is RunProgressProjection.RUN_EVENTS
    assert registration.spec.result is RunResultProjection.DURABLE_RUN_RECORD


def test_extension_operation_receives_provenance_and_cannot_replace_core() -> None:
    context = ExtensionContext()
    inspect = _service_operation(
        name="inspect-cache",
        summary="Inspect one extension-owned cache.",
        inputs=(
            RunInputSpec(
                name="verbose",
                help="Include detailed cache records.",
                kind=RunInputKind.FLAG,
                positional=False,
                required=False,
            ),
        ),
        required_scopes=frozenset({"cache:read"}),
    )

    with context.provenance("cache-hunter"):
        context.run_operations.add(inspect)

    registration = context.run_operations.get("inspect-cache")
    assert registration is not None
    assert registration.provider_id == "cache-hunter"
    assert registration.required_scopes == frozenset({"runs:submit", "cache:read"})

    with (
        context.provenance("hostile-replacement"),
        pytest.raises(ValueError, match="conflicts.*core"),
    ):
        context.run_operations.add(AGENT_RUN_OPERATION)


def test_extension_operation_requires_manager_provenance() -> None:
    context = ExtensionContext()

    with pytest.raises(RuntimeError, match="only defined inside"):
        context.run_operations.add(
            _service_operation(
                name="outside",
                summary="Cannot register outside extension assembly.",
            )
        )


def test_flag_shape_is_rejected_when_positional() -> None:
    with pytest.raises(ValueError, match="flags must be options"):
        RunInputSpec(
            name="verbose",
            help="Invalid positional flag.",
            kind=RunInputKind.FLAG,
        )


def test_flag_shape_is_rejected_when_required() -> None:
    with pytest.raises(ValueError, match="flags cannot be required or repeated"):
        RunInputSpec(
            name="verbose",
            help="Invalid required flag.",
            kind=RunInputKind.FLAG,
            positional=False,
        )


def test_operation_rejects_reserved_or_duplicate_inputs() -> None:
    prompt = RunInputSpec(name="prompt", help="Prompt.")

    with pytest.raises(ValueError, match="duplicate input"):
        _service_operation(
            name="duplicate",
            summary="Invalid duplicate inputs.",
            inputs=(prompt, prompt),
        )

    with pytest.raises(ValueError, match="host-owned 'follow'"):
        _service_operation(
            name="reserved",
            summary="Invalid reserved input.",
            inputs=(RunInputSpec(name="follow", help="Reserved."),),
        )

    with pytest.raises(ValueError, match="host-owned 'help'"):
        _service_operation(
            name="help-collision",
            summary="Cannot shadow generated command help.",
            inputs=(
                RunInputSpec(
                    name="help",
                    help="Reserved.",
                    positional=False,
                ),
            ),
        )


@pytest.mark.parametrize("target", ["", "   ", "bridge/chat", "BridgeChat", "bridge..chat"])
def test_execution_target_rejects_blank_or_invalid_identity(target: str) -> None:
    with pytest.raises(ValueError, match="target"):
        RunExecutionTarget(
            kind=RunExecutionKind.WORKFLOW,
            name=target,
        )
