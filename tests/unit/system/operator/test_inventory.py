from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from lychd.system.operator import (
    DeclaredAnimator,
    MountObservation,
    ObservationState,
    OperatorInventoryService,
    OperatorPaths,
    OperatorTarget,
    OwnedUnit,
    OwnedUnitCatalog,
    SystemSummary,
)

if TYPE_CHECKING:
    from lychd.system.operator.inventory import AnimatorDeclarationProvider
    from lychd.system.operator.storage import StorageInventoryService
    from lychd.system.operator.units import OwnedUnitInventoryService
    from lychd.system.services.lifecycle import LifecycleReceiptStore


class _Receipt:
    def __init__(self, *, exists: bool, error: Exception | None = None) -> None:
        self.exists = exists
        self.error = error

    def load(self) -> object:
        if self.error is not None:
            raise self.error
        return object()


class _Units:
    def __init__(self, catalog: OwnedUnitCatalog) -> None:
        self.catalog = catalog

    def inspect(self) -> OwnedUnitCatalog:
        return self.catalog


class _Storage:
    def observe(self, target: Path) -> MountObservation:
        return MountObservation(target=target, exists=False, mounted=False)


class _Animators:
    def __init__(self, declarations: tuple[DeclaredAnimator, ...] = ()) -> None:
        self._declarations = declarations

    def declarations(self) -> tuple[DeclaredAnimator, ...]:
        return self._declarations


def _paths(tmp_path: Path) -> OperatorPaths:
    return OperatorPaths(
        codex_root=tmp_path / "config",
        config=tmp_path / "config" / "lychd.toml",
        receipt=tmp_path / "config" / ".receipt",
        runes=tmp_path / "config" / "runes",
        bindings=tmp_path / "quadlets",
        systemd_bindings=tmp_path / "systemd",
        storage_data=tmp_path / "data",
        snapshots=tmp_path / "snapshots",
    )


def _service(
    tmp_path: Path,
    *,
    receipt: _Receipt,
    catalog: OwnedUnitCatalog,
    animators: _Animators | None = None,
) -> OperatorInventoryService:
    return OperatorInventoryService(
        paths=_paths(tmp_path),
        receipt=cast("LifecycleReceiptStore", receipt),
        units=cast("OwnedUnitInventoryService", _Units(catalog)),
        storage=cast("StorageInventoryService", _Storage()),
        animators=cast("AnimatorDeclarationProvider", animators or _Animators()),
    )


def test_status_is_graceful_before_init(tmp_path: Path) -> None:
    report = _service(
        tmp_path,
        receipt=_Receipt(exists=False),
        catalog=OwnedUnitCatalog(receipt_present=False),
    ).inspect()

    assert report.summary is SystemSummary.NOT_INITIALIZED
    assert report.items[0].state is ObservationState.ABSENT
    assert report.warnings == ()


def test_corrupt_receipt_is_degraded_not_a_crash(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.config.parent.mkdir()
    paths.config.write_text("", encoding="utf-8")
    report = _service(
        tmp_path,
        receipt=_Receipt(exists=True, error=RuntimeError("bad receipt")),
        catalog=OwnedUnitCatalog(receipt_present=False),
    ).inspect()

    assert report.summary is SystemSummary.DEGRADED
    assert "bad receipt" in report.warnings[0]


def test_managed_config_without_lifecycle_receipt_is_degraded(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.config.parent.mkdir()
    paths.config.write_text("", encoding="utf-8")

    report = _service(
        tmp_path,
        receipt=_Receipt(exists=False),
        catalog=OwnedUnitCatalog(receipt_present=False),
    ).inspect()

    assert report.summary is SystemSummary.DEGRADED
    assert report.items[0].state is ObservationState.ABSENT


def test_scribe_ownership_without_lifecycle_receipt_is_degraded(tmp_path: Path) -> None:
    report = _service(
        tmp_path,
        receipt=_Receipt(exists=False),
        catalog=OwnedUnitCatalog(
            receipt_present=True,
            generation="orphaned",
            units=(
                OwnedUnit(
                    name="lychd-vessel.service",
                    sources=(),
                    state=ObservationState.INACTIVE,
                ),
            ),
        ),
    ).inspect()

    assert report.summary is SystemSummary.DEGRADED
    assert report.items[0].state is ObservationState.ABSENT
    assert report.items[1].state is ObservationState.PRESENT


def test_corrupt_scribe_ownership_is_unknown_in_system_summary(tmp_path: Path) -> None:
    report = _service(
        tmp_path,
        receipt=_Receipt(exists=True),
        catalog=OwnedUnitCatalog(
            receipt_present=True,
            warning="Cannot validate Scribe ownership",
        ),
    ).inspect()

    binding = report.items[1]
    assert report.summary is SystemSummary.DEGRADED
    assert binding.name == "bindings"
    assert binding.state is ObservationState.UNKNOWN
    assert binding.detail == "Cannot validate Scribe ownership"


def test_animator_selector_cross_checks_declaration_against_exact_owned_unit(tmp_path: Path) -> None:
    catalog = OwnedUnitCatalog(
        receipt_present=True,
        generation="g",
        units=(
            OwnedUnit(
                name="lychd-qwen.service",
                sources=("/units/lychd-qwen.container",),
                state=ObservationState.ACTIVE,
                unit_file_state="disabled",
            ),
        ),
    )
    report = _service(
        tmp_path,
        receipt=_Receipt(exists=True),
        catalog=catalog,
        animators=_Animators(
            (
                DeclaredAnimator(
                    name="qwen",
                    kind="soulstone",
                    runtime="vllm",
                    unit_name="lychd-qwen.service",
                ),
                DeclaredAnimator(
                    name="other",
                    kind="soulstone",
                    runtime="vllm",
                    unit_name="lychd-other.service",
                ),
            )
        ),
    ).inspect(OperatorTarget.ANIMATORS)

    assert [(item.name, item.state) for item in report.items] == [
        ("qwen", ObservationState.ACTIVE),
        ("other", ObservationState.ABSENT),
    ]
    assert "model-level warmth is not yet projected" in report.items[0].detail


def test_workers_never_infer_readiness_from_active_vessel(tmp_path: Path) -> None:
    report = _service(
        tmp_path,
        receipt=_Receipt(exists=True),
        catalog=OwnedUnitCatalog(
            receipt_present=True,
            units=(
                OwnedUnit(
                    name="lychd-vessel.service",
                    sources=(),
                    state=ObservationState.ACTIVE,
                    unit_file_state="enabled",
                ),
            ),
        ),
    ).inspect(OperatorTarget.WORKERS)

    assert all(item.state is ObservationState.UNKNOWN for item in report.items)
    assert report.as_dict()["selector"] == "workers"


def test_failed_owned_unit_degrades_whole_system_even_when_another_is_active(tmp_path: Path) -> None:
    report = _service(
        tmp_path,
        receipt=_Receipt(exists=True),
        catalog=OwnedUnitCatalog(
            receipt_present=True,
            units=(
                OwnedUnit(
                    name="lychd-vessel.service",
                    sources=(),
                    state=ObservationState.ACTIVE,
                    unit_file_state="enabled",
                ),
                OwnedUnit(
                    name="lychd-migrate.service",
                    sources=(),
                    state=ObservationState.FAILED,
                    unit_file_state="static",
                ),
            ),
        ),
    ).inspect()

    assert report.summary is SystemSummary.DEGRADED
