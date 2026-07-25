from __future__ import annotations

from pathlib import Path

from lychd.extensions.manager import ExtensionManager


def test_selected_crypt_extension_can_contribute_only_declarative_run_operation(
    tmp_path: Path,
) -> None:
    extension_dir = tmp_path / "cache-hunter"
    extension_dir.mkdir()
    (extension_dir / "register.py").write_text(
        """from lychd.domain.cortex.operations import (
    RunConsentMode,
    RunExecutionKind,
    RunExecutionTarget,
    RunInputSpec,
    RunMutationCharacteristic,
    RunOperationSpec,
    RunProgressProjection,
    RunResultProjection,
)

def register(context):
    context.run_operations.add(
        RunOperationSpec(
            name="hunt-cache",
            summary="Inspect cache reuse.",
            execution=RunExecutionTarget(
                kind=RunExecutionKind.SERVICE,
                name="cache-hunter.inspect",
            ),
            mutation=RunMutationCharacteristic.READ_ONLY,
            consent=RunConsentMode.NONE,
            progress=RunProgressProjection.RUN_EVENTS,
            result=RunResultProjection.DURABLE_RUN_RECORD,
            inputs=(RunInputSpec(name="target", help="Target run."),),
        )
    )
""",
        encoding="utf-8",
    )

    context = ExtensionManager(
        builtins=[],
        crypt=["cache-hunter"],
        crypt_root=tmp_path,
    ).assemble()

    registration = context.run_operations.get("hunt-cache")
    assert registration is not None
    assert registration.provider_id == "cache-hunter"
    assert registration.spec.execution.name == "cache-hunter.inspect"
    assert registration.spec.inputs[0].name == "target"
