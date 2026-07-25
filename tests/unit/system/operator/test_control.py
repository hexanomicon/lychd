from __future__ import annotations

from contextlib import contextmanager, nullcontext
from typing import TYPE_CHECKING, cast

import pytest

from lychd.system.operator import (
    ObservationState,
    OperatorAction,
    OperatorAuthorityError,
    OperatorControlService,
    OperatorError,
    OperatorTarget,
    OperatorTargetResolver,
    OwnedUnit,
    OwnedUnitCatalog,
    OwnedUnitRetirementService,
    ProcessResult,
    VesselAuthority,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

    from pytest_mock import MockerFixture

    from lychd.system.operator.inventory import OperatorInventoryService


class _Inventory:
    def __init__(self, catalog: OwnedUnitCatalog) -> None:
        self.catalog = catalog

    def owned_units(self) -> OwnedUnitCatalog:
        return self.catalog

    def declared_animators(self) -> tuple[object, ...]:
        return ()


class _SequencedInventory(_Inventory):
    def __init__(self, *catalogs: OwnedUnitCatalog) -> None:
        super().__init__(catalogs[-1])
        self._catalogs = iter(catalogs)

    def owned_units(self) -> OwnedUnitCatalog:
        return next(self._catalogs)


class _Runner:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], float]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        self.calls.append((argv, timeout_s))
        return ProcessResult(argv=argv, returncode=0)


class _RetiringRunner(_Runner):
    def __init__(self, inventory: _Inventory) -> None:
        super().__init__()
        self._inventory = inventory

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        result = super().run(argv, timeout_s=timeout_s)
        action = argv[2]
        self._inventory.catalog = OwnedUnitCatalog(
            receipt_present=True,
            generation=self._inventory.catalog.generation,
            units=tuple(
                OwnedUnit(
                    name=unit.name,
                    sources=unit.sources,
                    state=ObservationState.INACTIVE if action == "stop" else unit.state,
                    unit_file_state="disabled" if action == "disable" else unit.unit_file_state,
                )
                for unit in self._inventory.catalog.units
            ),
        )
        return result


class _Vessel:
    def __init__(self) -> None:
        self.calls: list[tuple[OperatorAction, OperatorTarget]] = []

    def actuate(self, action: OperatorAction, target: OperatorTarget) -> str:
        self.calls.append((action, target))
        return "accepted"


def _catalog(
    state: ObservationState,
    *,
    units: tuple[str, ...] = ("lychd-vessel.service",),
    unit_file_state: str = "enabled",
) -> OwnedUnitCatalog:
    return OwnedUnitCatalog(
        receipt_present=True,
        generation="generation",
        units=tuple(
            OwnedUnit(
                name=unit,
                sources=(f"/units/{unit}",),
                state=state,
                unit_file_state=unit_file_state,
            )
            for unit in units
        ),
    )


def _control(
    inventory: _Inventory,
    runner: _Runner,
    *,
    vessel: _Vessel | None = None,
    lock_factory: Callable[[], AbstractContextManager[object]] = nullcontext,
) -> OperatorControlService:
    typed_inventory = cast("OperatorInventoryService", inventory)
    return OperatorControlService(
        inventory=typed_inventory,
        targets=OperatorTargetResolver(typed_inventory),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
        vessel=vessel,
        lock_factory=lock_factory,
    )


def test_start_down_system_uses_exact_owned_vessel_argv() -> None:
    runner = _Runner()
    control = _control(_Inventory(_catalog(ObservationState.INACTIVE)), runner)

    result = control.execute(OperatorAction.START)

    assert result.authority is VesselAuthority.DIRECT
    assert runner.calls == [
        (
            (
                "/usr/bin/systemctl",
                "--user",
                "start",
                "lychd-vessel.service",
            ),
            30.0,
        )
    ]


def test_start_down_system_refuses_split_active_runtime() -> None:
    inventory = _Inventory(
        OwnedUnitCatalog(
            receipt_present=True,
            generation="generation",
            units=(
                OwnedUnit(
                    name="lychd-vessel.service",
                    sources=(),
                    state=ObservationState.INACTIVE,
                ),
                OwnedUnit(
                    name="lychd-qwen.service",
                    sources=(),
                    state=ObservationState.ACTIVE,
                ),
            ),
        )
    )
    runner = _Runner()

    with pytest.raises(
        OperatorError,
        match="every other exact owned unit is inactive",
    ):
        _control(inventory, runner).execute(OperatorAction.START)

    assert runner.calls == []


def test_start_down_system_rejects_runtime_state_drift_before_effect() -> None:
    def catalog(qwen_state: ObservationState) -> OwnedUnitCatalog:
        return OwnedUnitCatalog(
            receipt_present=True,
            generation="generation",
            units=(
                OwnedUnit(
                    name="lychd-vessel.service",
                    sources=(),
                    state=ObservationState.INACTIVE,
                ),
                OwnedUnit(
                    name="lychd-qwen.service",
                    sources=(),
                    state=qwen_state,
                ),
            ),
        )

    inventory = _SequencedInventory(
        catalog(ObservationState.INACTIVE),
        catalog(ObservationState.ACTIVE),
    )
    runner = _Runner()

    with pytest.raises(OperatorAuthorityError, match="runtime authority changed"):
        _control(inventory, runner).execute(OperatorAction.START)

    assert runner.calls == []


def test_stop_down_system_covers_every_exact_owned_unit_in_one_transaction() -> None:
    inventory = _Inventory(
        OwnedUnitCatalog(
            receipt_present=True,
            generation="generation",
            units=(
                OwnedUnit(
                    name="lychd-vessel.service",
                    sources=(),
                    state=ObservationState.INACTIVE,
                ),
                OwnedUnit(
                    name="lychd-qwen.service",
                    sources=(),
                    state=ObservationState.ACTIVE,
                ),
                OwnedUnit(
                    name="lychd-phylactery.service",
                    sources=(),
                    state=ObservationState.FAILED,
                ),
            ),
        )
    )
    runner = _Runner()

    result = _control(inventory, runner).execute(OperatorAction.STOP)

    assert result.units == (
        "lychd-vessel.service",
        "lychd-qwen.service",
        "lychd-phylactery.service",
    )
    assert runner.calls == [
        (
            (
                "/usr/bin/systemctl",
                "--user",
                "stop",
                "lychd-vessel.service",
                "lychd-qwen.service",
                "lychd-phylactery.service",
            ),
            30.0,
        )
    ]


def test_active_vessel_without_authenticated_port_refuses_direct_stop() -> None:
    runner = _Runner()
    control = _control(_Inventory(_catalog(ObservationState.ACTIVE)), runner)

    with pytest.raises(OperatorAuthorityError, match="authenticated lifecycle API"):
        control.execute(OperatorAction.STOP)

    assert runner.calls == []


def test_active_vessel_routes_to_injected_port_without_systemctl() -> None:
    runner = _Runner()
    vessel = _Vessel()
    control = _control(_Inventory(_catalog(ObservationState.ACTIVE)), runner, vessel=vessel)

    result = control.execute(OperatorAction.STOP)

    assert result.authority is VesselAuthority.VESSEL
    assert vessel.calls == [(OperatorAction.STOP, OperatorTarget.SYSTEM)]
    assert runner.calls == []


def test_unknown_vessel_state_never_mutates() -> None:
    runner = _Runner()
    control = _control(_Inventory(_catalog(ObservationState.UNKNOWN)), runner)

    with pytest.raises(OperatorAuthorityError, match="Cannot prove"):
        control.execute(OperatorAction.START)

    assert runner.calls == []


def test_direct_actuation_holds_lifecycle_lock_through_effect() -> None:
    events: list[str] = []

    @contextmanager
    def lock() -> Iterator[None]:
        events.append("lock-enter")
        yield
        events.append("lock-exit")

    class LockAwareRunner(_Runner):
        def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
            events.append("systemctl")
            assert events == ["lock-enter", "systemctl"]
            return super().run(argv, timeout_s=timeout_s)

    runner = LockAwareRunner()
    control = _control(
        _Inventory(_catalog(ObservationState.INACTIVE)),
        runner,
        lock_factory=lock,
    )

    control.execute(OperatorAction.START)

    assert events == ["lock-enter", "systemctl", "lock-exit"]


def test_direct_actuation_emits_semantic_audit_events(
    mocker: MockerFixture,
) -> None:
    audit = mocker.patch("lychd.system.operator.control.logger")
    runner = _Runner()
    control = _control(_Inventory(_catalog(ObservationState.INACTIVE)), runner)

    control.execute(OperatorAction.START)

    audit.info.assert_any_call(
        "operator_actuation_started",
        action="start",
        target="system",
        authority="direct",
        units=("lychd-vessel.service",),
    )
    audit.info.assert_any_call(
        "operator_actuation_completed",
        action="start",
        target="system",
        authority="direct",
        units=("lychd-vessel.service",),
    )


def test_retirement_stops_then_disables_only_exact_owned_units() -> None:
    inventory = _Inventory(
        _catalog(
            ObservationState.ACTIVE,
            units=("lychd-vessel.service", "lychd-qwen.service"),
        )
    )
    runner = _RetiringRunner(inventory)
    service = OwnedUnitRetirementService(
        inventory=cast("OperatorInventoryService", inventory),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    plan = service.plan()
    service.execute(plan)

    assert runner.calls == [
        (
            (
                "/usr/bin/systemctl",
                "--user",
                "stop",
                "lychd-vessel.service",
                "lychd-qwen.service",
            ),
            30.0,
        ),
        (
            (
                "/usr/bin/systemctl",
                "--user",
                "disable",
                "lychd-vessel.service",
                "lychd-qwen.service",
            ),
            30.0,
        ),
    ]


def test_retirement_blocks_when_systemctl_success_did_not_change_state() -> None:
    inventory = _Inventory(_catalog(ObservationState.ACTIVE))
    service = OwnedUnitRetirementService(
        inventory=cast("OperatorInventoryService", inventory),
        runner=_Runner(),
        systemctl_bin="/usr/bin/systemctl",
    )

    with pytest.raises(OperatorError, match="remain active or enabled"):
        service.execute(service.plan())


def test_retirement_blocks_unknown_enablement() -> None:
    service = OwnedUnitRetirementService(
        inventory=cast(
            "OperatorInventoryService",
            _Inventory(_catalog(ObservationState.INACTIVE, unit_file_state="unknown")),
        ),
        runner=_Runner(),
        systemctl_bin="/usr/bin/systemctl",
    )

    with pytest.raises(OperatorError, match="enablement state"):
        service.plan()
