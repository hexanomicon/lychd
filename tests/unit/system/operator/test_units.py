from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from lychd.system.operator import (
    ObservationState,
    OwnedUnitInventoryService,
    ProcessResult,
)
from lychd.system.services.scribe import OwnedBindings

if TYPE_CHECKING:
    from lychd.system.services.scribe import ScribeService


class _Scribe:
    def __init__(self, bindings: OwnedBindings | Exception) -> None:
        self.bindings = bindings

    def inspect_owned_bindings(self) -> OwnedBindings:
        if isinstance(self.bindings, Exception):
            raise self.bindings
        return self.bindings


class _Runner:
    def __init__(self, results: list[ProcessResult]) -> None:
        self.results = results
        self.calls: list[tuple[tuple[str, ...], float]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        self.calls.append((argv, timeout_s))
        return self.results.pop(0)


def test_unit_inventory_observes_only_receipted_runtime_units(tmp_path: Path) -> None:
    source = tmp_path / "lychd-vessel.container"
    bindings = OwnedBindings(
        receipt_present=True,
        generation="generation",
        quadlet_sources=(source,),
        runtime_units=("lychd-vessel.service",),
    )
    runner = _Runner(
        [
            ProcessResult(
                argv=(),
                returncode=0,
                stdout="LoadState=loaded\nActiveState=active\nUnitFileState=enabled\n",
            )
        ]
    )
    service = OwnedUnitInventoryService(
        cast("ScribeService", _Scribe(bindings)),
        runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    catalog = service.inspect()

    assert catalog.generation == "generation"
    assert catalog.units[0].state is ObservationState.ACTIVE
    assert catalog.units[0].sources == (str(source),)
    assert runner.calls == [
        (
            (
                "/usr/bin/systemctl",
                "--user",
                "show",
                "lychd-vessel.service",
                "--property=LoadState",
                "--property=ActiveState",
                "--property=UnitFileState",
            ),
            3.0,
        )
    ]


def test_absent_scribe_receipt_does_not_scan_systemd() -> None:
    runner = _Runner([])
    service = OwnedUnitInventoryService(
        cast("ScribeService", _Scribe(OwnedBindings(receipt_present=False))),
        runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    assert service.inspect().units == ()
    assert runner.calls == []


def test_invalid_scribe_authority_degrades_without_scanning() -> None:
    runner = _Runner([])
    service = OwnedUnitInventoryService(
        cast("ScribeService", _Scribe(RuntimeError("corrupt receipt"))),
        runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    catalog = service.inspect()

    assert catalog.warning == "Cannot validate Scribe ownership: corrupt receipt"
    assert runner.calls == []


def test_deactivating_vessel_remains_active_for_authority_arbitration(
    tmp_path: Path,
) -> None:
    """Shutdown work must finish before direct lifecycle authority can return."""
    source = tmp_path / "lychd-vessel.container"
    runner = _Runner(
        [
            ProcessResult(
                argv=(),
                returncode=0,
                stdout=("LoadState=loaded\nActiveState=deactivating\nUnitFileState=enabled\n"),
            )
        ]
    )
    service = OwnedUnitInventoryService(
        cast(
            "ScribeService",
            _Scribe(
                OwnedBindings(
                    receipt_present=True,
                    generation="generation",
                    quadlet_sources=(source,),
                    runtime_units=("lychd-vessel.service",),
                )
            ),
        ),
        runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    assert service.inspect().units[0].state is ObservationState.ACTIVE


def test_missing_owned_unit_is_reported_with_its_load_state(tmp_path: Path) -> None:
    source = tmp_path / "lychd-vessel.container"
    runner = _Runner(
        [
            ProcessResult(
                argv=(),
                returncode=0,
                stdout="LoadState=not-found\nActiveState=inactive\nUnitFileState=\n",
            )
        ]
    )
    service = OwnedUnitInventoryService(
        cast(
            "ScribeService",
            _Scribe(
                OwnedBindings(
                    receipt_present=True,
                    generation="generation",
                    quadlet_sources=(source,),
                    runtime_units=("lychd-vessel.service",),
                )
            ),
        ),
        runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    unit = service.inspect().units[0]

    assert unit.state is ObservationState.INACTIVE
    assert unit.detail == "load state: not-found"
    assert runner.calls


def test_unavailable_systemctl_keeps_owned_unit_state_unknown(tmp_path: Path) -> None:
    source = tmp_path / "lychd-vessel.container"
    runner = _Runner([])
    service = OwnedUnitInventoryService(
        cast(
            "ScribeService",
            _Scribe(
                OwnedBindings(
                    receipt_present=True,
                    generation="generation",
                    quadlet_sources=(source,),
                    runtime_units=("lychd-vessel.service",),
                )
            ),
        ),
        runner,
        systemctl_bin=None,
    )

    catalog = service.inspect()

    assert len(catalog.units) == 1
    assert catalog.units[0].state is ObservationState.UNKNOWN
    assert catalog.units[0].detail == "systemctl is unavailable"
    assert runner.calls == []
