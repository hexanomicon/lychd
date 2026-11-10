from __future__ import annotations

from contextlib import contextmanager, nullcontext
from dataclasses import replace
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
    OwnedUnitInventoryService,
    OwnedUnitRetirementService,
    ProcessResult,
    VesselAuthority,
)
from lychd.system.operator.inventory import OperatorInventoryService
from lychd.system.operator.process import ProcessInvocationError
from lychd.system.services.scribe import OwnedBindings, ScribeService

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from contextlib import AbstractContextManager

    from pytest_mock import MockerFixture


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


_COUNTERPART_SHOW = (
    "/usr/bin/systemctl",
    "--user",
    "show",
    "lychd-uncaged-vessel.service",
    "--property=Id",
    "--property=LoadState",
    "--property=ActiveState",
    "--property=SubState",
    "--property=MainPID",
    "--property=ControlPID",
    "--property=Job",
)


class _StartRunner(_Runner):
    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        result = super().run(argv, timeout_s=timeout_s)
        if argv == _COUNTERPART_SHOW:
            return ProcessResult(
                argv,
                0,
                "Id=lychd-uncaged-vessel.service\nLoadState=loaded\nActiveState=inactive\n"
                "SubState=dead\nMainPID=0\nControlPID=0\nJob=\n",
            )
        return result


class _TimedStartRunner(_StartRunner):
    def __init__(self, duration_s: float) -> None:
        super().__init__()
        self.duration_s = duration_s
        self.job_pending = False

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        result = super().run(argv, timeout_s=timeout_s)
        if argv[2] == "start":
            self.job_pending = True
            if self.duration_s > timeout_s:
                message = "Synthetic systemctl client observation timed out"
                raise ProcessInvocationError(message)
            self.job_pending = False
        return result


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
                replace(
                    unit,
                    state=ObservationState.INACTIVE if action == "stop" else unit.state,
                    unit_file_state="disabled" if action == "disable" else unit.unit_file_state,
                )
                if unit.name in argv[3:]
                else unit
                for unit in self._inventory.catalog.units
            ),
        )
        return result


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
                sources=(f"/units/{'lychd-vessel.container' if unit == 'lychd-vessel.service' else unit}",),
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
    lock_factory: Callable[[], AbstractContextManager[object]] = nullcontext,
) -> OperatorControlService:
    typed_inventory = cast("OperatorInventoryService", inventory)
    return OperatorControlService(
        inventory=typed_inventory,
        targets=OperatorTargetResolver(typed_inventory),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
        lock_factory=lock_factory,
    )


def test_start_down_system_uses_exact_owned_vessel_argv() -> None:
    runner = _StartRunner()
    control = _control(_Inventory(_catalog(ObservationState.INACTIVE)), runner)

    result = control.execute(OperatorAction.START)

    assert result.authority is VesselAuthority.DIRECT
    assert runner.calls == [
        (_COUNTERPART_SHOW, 3.0),
        (
            (
                "/usr/bin/systemctl",
                "--user",
                "start",
                "lychd-vessel.service",
            ),
            360.0,
        ),
    ]


def test_cold_start_can_complete_after_the_short_command_budget() -> None:
    runner = _TimedStartRunner(duration_s=75.0)
    control = _control(_Inventory(_catalog(ObservationState.INACTIVE)), runner)

    result = control.execute(OperatorAction.START)

    assert result.authority is VesselAuthority.DIRECT
    assert result.units == ("lychd-vessel.service",)
    assert not runner.job_pending
    assert runner.calls == [
        (_COUNTERPART_SHOW, 3.0),
        (("/usr/bin/systemctl", "--user", "start", "lychd-vessel.service"), 360.0),
    ]


def test_start_observation_timeout_preserves_uncertainty_without_second_action(mocker: MockerFixture) -> None:
    events: list[str] = []

    @contextmanager
    def lock() -> Generator[None]:
        events.append("locked")
        try:
            yield
        finally:
            events.append("unlocked")

    audit = mocker.patch("lychd.system.operator.control.logger")
    runner = _TimedStartRunner(duration_s=361.0)
    control = _control(_Inventory(_catalog(ObservationState.INACTIVE)), runner, lock_factory=lock)

    with pytest.raises(OperatorError, match="outcome is unconfirmed; the manager job may continue"):
        control.execute(OperatorAction.START)

    assert runner.job_pending
    assert events == ["locked", "unlocked"]
    assert runner.calls == [
        (_COUNTERPART_SHOW, 3.0),
        (("/usr/bin/systemctl", "--user", "start", "lychd-vessel.service"), 360.0),
    ]
    audit.info.assert_called_once_with(
        "operator_actuation_started",
        action="start",
        target="system",
        authority="direct",
        units=("lychd-vessel.service",),
    )


@pytest.mark.parametrize("other_state", [ObservationState.ACTIVE, ObservationState.UNKNOWN])
def test_start_down_system_refuses_split_active_runtime(other_state: ObservationState) -> None:
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
                    state=other_state,
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


@pytest.mark.parametrize(
    ("action", "target"),
    [
        (OperatorAction.STOP, OperatorTarget.SYSTEM),
        (OperatorAction.START, OperatorTarget.STORAGE),
        (OperatorAction.STOP, OperatorTarget.STORAGE),
    ],
)
def test_direct_actuation_refuses_unknown_selected_unit(
    action: OperatorAction,
    target: OperatorTarget,
) -> None:
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
                    name="lychd-phylactery.service",
                    sources=(),
                    state=ObservationState.UNKNOWN,
                ),
            ),
        )
    )
    runner = _Runner()

    with pytest.raises(OperatorAuthorityError, match=r"Cannot prove runtime state.*lychd-phylactery"):
        _control(inventory, runner).execute(action, target)

    assert runner.calls == []


@pytest.mark.parametrize("action", [OperatorAction.START, OperatorAction.STOP])
@pytest.mark.parametrize(
    "storage_state",
    [ObservationState.INACTIVE, ObservationState.ACTIVE, ObservationState.FAILED],
)
def test_storage_actuation_ignores_unchanged_unknown_unselected_unit(
    action: OperatorAction,
    storage_state: ObservationState,
) -> None:
    inventory = _Inventory(
        OwnedUnitCatalog(
            receipt_present=True,
            generation="generation",
            units=(
                OwnedUnit(name="lychd-vessel.service", sources=(), state=ObservationState.INACTIVE),
                OwnedUnit(name="lychd-phylactery.service", sources=(), state=storage_state),
                OwnedUnit(name="lychd-qwen.service", sources=(), state=ObservationState.UNKNOWN),
            ),
        )
    )
    runner = _Runner()

    result = _control(inventory, runner).execute(action, OperatorTarget.STORAGE)

    assert result.authority is VesselAuthority.DIRECT
    assert result.units == ("lychd-phylactery.service",)
    assert runner.calls == [
        (
            ("/usr/bin/systemctl", "--user", action.value, "lychd-phylactery.service"),
            360.0 if action is OperatorAction.START else 30.0,
        ),
    ]


@pytest.mark.parametrize("action", [OperatorAction.START, OperatorAction.STOP])
@pytest.mark.parametrize("changed_unit", ["lychd-phylactery.service", "lychd-qwen.service"])
def test_storage_actuation_refuses_selected_or_unselected_state_drift_to_unknown(
    action: OperatorAction,
    changed_unit: str,
) -> None:
    planned = _catalog(
        ObservationState.INACTIVE,
        units=("lychd-vessel.service", "lychd-phylactery.service", "lychd-qwen.service"),
    )
    current = replace(
        planned,
        units=tuple(
            replace(unit, state=ObservationState.UNKNOWN) if unit.name == changed_unit else unit
            for unit in planned.units
        ),
    )
    runner = _Runner()

    with pytest.raises(OperatorAuthorityError, match="runtime authority changed"):
        _control(_SequencedInventory(planned, current), runner).execute(action, OperatorTarget.STORAGE)

    assert runner.calls == []


@pytest.mark.parametrize("action", [OperatorAction.START, OperatorAction.STOP])
@pytest.mark.parametrize("target", [OperatorTarget.SYSTEM, OperatorTarget.STORAGE])
def test_active_vessel_without_authenticated_port_refuses_direct_control(
    action: OperatorAction,
    target: OperatorTarget,
) -> None:
    runner = _Runner()
    control = _control(_Inventory(_catalog(ObservationState.ACTIVE)), runner)

    with pytest.raises(OperatorAuthorityError, match="authenticated lifecycle API"):
        control.execute(action, target)

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
    def lock() -> Generator[None]:
        events.append("lock-enter")
        yield
        events.append("lock-exit")

    class LockAwareRunner(_StartRunner):
        def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
            events.append("systemctl")
            expected = (
                ["lock-enter", "systemctl"] if argv == _COUNTERPART_SHOW else ["lock-enter", "systemctl", "systemctl"]
            )
            assert events == expected
            return super().run(argv, timeout_s=timeout_s)

    runner = LockAwareRunner()
    control = _control(
        _Inventory(_catalog(ObservationState.INACTIVE)),
        runner,
        lock_factory=lock,
    )

    control.execute(OperatorAction.START)

    assert events == ["lock-enter", "systemctl", "systemctl", "lock-exit"]


def test_direct_actuation_emits_semantic_audit_events(
    mocker: MockerFixture,
) -> None:
    audit = mocker.patch("lychd.system.operator.control.logger")
    runner = _StartRunner()
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


@pytest.mark.parametrize("unit_file_state", ["disabled", "enabled"])
def test_retirement_refuses_failed_units_before_any_command(unit_file_state: str) -> None:
    runner = _Runner()
    names = ("lychd-vessel.service", "lychd-qwen.service")
    service = OwnedUnitRetirementService(
        inventory=cast(
            "OperatorInventoryService",
            _Inventory(_catalog(ObservationState.FAILED, units=names, unit_file_state=unit_file_state)),
        ),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    with pytest.raises(OperatorError, match="failed state") as caught:
        service.plan()

    assert all(name in str(caught.value) for name in names)
    assert runner.calls == []


def test_retirement_refuses_each_exact_masked_file_state() -> None:
    runner = _Runner()
    catalog = OwnedUnitCatalog(
        receipt_present=True,
        generation="generation",
        units=(
            OwnedUnit("lychd-vessel.service", (), ObservationState.INACTIVE, "masked"),
            OwnedUnit("lychd-qwen.service", (), ObservationState.INACTIVE, "masked-runtime"),
        ),
    )
    service = OwnedUnitRetirementService(
        inventory=cast("OperatorInventoryService", _Inventory(catalog)),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    with pytest.raises(OperatorError, match="unsupported unit-file state") as caught:
        service.plan()

    assert "lychd-vessel.service (masked)" in str(caught.value)
    assert "lychd-qwen.service (masked-runtime)" in str(caught.value)
    assert runner.calls == []


@pytest.mark.parametrize(
    ("state", "unit_file_state", "reason"),
    [
        (ObservationState.FAILED, "disabled", "failed state: lychd-qwen.service"),
        (ObservationState.INACTIVE, "indirect", r"unsupported unit-file state: lychd-qwen.service \(indirect\)"),
    ],
)
def test_retirement_unsupported_peer_prevents_partial_retirement(
    state: ObservationState,
    unit_file_state: str,
    reason: str,
) -> None:
    runner = _Runner()
    catalog = OwnedUnitCatalog(
        receipt_present=True,
        generation="generation",
        units=(
            OwnedUnit("lychd-vessel.service", (), ObservationState.ACTIVE, "enabled"),
            OwnedUnit("lychd-qwen.service", (), state, unit_file_state),
        ),
    )
    service = OwnedUnitRetirementService(
        inventory=cast("OperatorInventoryService", _Inventory(catalog)),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    with pytest.raises(OperatorError, match=reason):
        service.execute(service.plan())

    assert runner.calls == []


@pytest.mark.parametrize(
    ("state", "unit_file_state", "reason"),
    [
        (ObservationState.FAILED, "disabled", "failed state"),
        (ObservationState.INACTIVE, "masked-runtime", "unsupported unit-file state"),
    ],
)
def test_retirement_revalidation_refuses_failed_or_masked_drift_before_effect(
    state: ObservationState,
    unit_file_state: str,
    reason: str,
) -> None:
    inventory = _SequencedInventory(
        _catalog(ObservationState.ACTIVE),
        _catalog(state, unit_file_state=unit_file_state),
    )
    runner = _Runner()
    service = OwnedUnitRetirementService(
        inventory=cast("OperatorInventoryService", inventory),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )
    plan = service.plan()

    with pytest.raises(OperatorError, match=reason):
        service.execute(plan)

    assert runner.calls == []


def test_retirement_keeps_unknown_runtime_refusal() -> None:
    runner = _Runner()
    service = OwnedUnitRetirementService(
        inventory=cast(
            "OperatorInventoryService",
            _Inventory(_catalog(ObservationState.UNKNOWN, unit_file_state="disabled")),
        ),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    with pytest.raises(OperatorError, match=r"Cannot prove runtime state.*lychd-vessel.service"):
        service.plan()

    assert runner.calls == []


@pytest.mark.parametrize("unit_file_state", ["disabled", "generated", "static", ""])
def test_retirement_inactive_unenabled_states_need_no_command(unit_file_state: str) -> None:
    runner = _Runner()
    service = OwnedUnitRetirementService(
        inventory=cast(
            "OperatorInventoryService",
            _Inventory(_catalog(ObservationState.INACTIVE, unit_file_state=unit_file_state)),
        ),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    plan = service.plan()
    service.execute(plan)

    assert plan.owned_units == ("lychd-vessel.service",)
    assert plan.stop_units == plan.disable_units == ()
    assert runner.calls == []


@pytest.mark.parametrize("state", [ObservationState.ACTIVE, ObservationState.INACTIVE])
@pytest.mark.parametrize("unit_file_state", ["enabled", "enabled-runtime", "linked", "linked-runtime"])
def test_retirement_keeps_exact_stop_and_disable_planning(state: ObservationState, unit_file_state: str) -> None:
    runner = _Runner()
    service = OwnedUnitRetirementService(
        inventory=cast(
            "OperatorInventoryService",
            _Inventory(_catalog(state, unit_file_state=unit_file_state)),
        ),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )

    plan = service.plan()

    assert plan.disable_units == ("lychd-vessel.service",)
    assert plan.stop_units == (("lychd-vessel.service",) if state is ObservationState.ACTIVE else ())
    assert runner.calls == []


def test_retirement_revalidation_refuses_indirect_drift_before_retiring_active_peer() -> None:
    inventory = _Inventory(
        OwnedUnitCatalog(
            receipt_present=True,
            generation="generation",
            units=(
                OwnedUnit("lychd-vessel.service", (), ObservationState.ACTIVE, "enabled"),
                OwnedUnit("lychd-qwen.service", (), ObservationState.INACTIVE, "disabled"),
            ),
        )
    )
    runner = _RetiringRunner(inventory)
    service = OwnedUnitRetirementService(
        inventory=cast("OperatorInventoryService", inventory),
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )
    plan = service.plan()
    assert plan.stop_units == plan.disable_units == ("lychd-vessel.service",)
    inventory.catalog = replace(
        inventory.catalog,
        units=(inventory.catalog.units[0], replace(inventory.catalog.units[1], unit_file_state="indirect")),
    )

    with pytest.raises(OperatorError, match=r"unsupported unit-file state: lychd-qwen.service \(indirect\)"):
        service.execute(plan)

    assert runner.calls == []


def test_retirement_revalidation_observes_bad_setting_before_retiring_active_peer(mocker: MockerFixture) -> None:
    class ObservingRunner(_Runner):
        load_state = "loaded"

        def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
            result = super().run(argv, timeout_s=timeout_s)
            if argv[2] == "show":
                load, active, unit_file = (
                    ("loaded", "active", "enabled")
                    if argv[3] == "lychd-peer.service"
                    else (self.load_state, "inactive", "disabled")
                )
                return ProcessResult(argv, 0, f"LoadState={load}\nActiveState={active}\nUnitFileState={unit_file}\n")
            return result

    scribe = mocker.MagicMock(spec=ScribeService)
    scribe.inspect_owned_bindings.return_value = OwnedBindings(
        receipt_present=True,
        generation="unchanged-generation",
        runtime_units=("lychd-peer.service", "lychd-test.service"),
    )
    runner = ObservingRunner()
    observer = OwnedUnitInventoryService(scribe, runner, systemctl_bin="/usr/bin/systemctl")
    inventory = mocker.MagicMock(spec=OperatorInventoryService)
    inventory.owned_units.side_effect = observer.inspect
    service = OwnedUnitRetirementService(inventory=inventory, runner=runner, systemctl_bin="/usr/bin/systemctl")
    plan = service.plan()
    assert plan.stop_units == plan.disable_units == ("lychd-peer.service",)
    runner.load_state = "bad-setting"

    with pytest.raises(OperatorError, match=r"load state: lychd-test.service \(bad-setting\)"):
        service.execute(plan)

    assert [argv for argv, _ in runner.calls if argv[2] != "show"] == []


@pytest.mark.parametrize("action", [OperatorAction.START, OperatorAction.STOP])
@pytest.mark.parametrize("state", [ObservationState.INACTIVE, ObservationState.ACTIVE])
def test_direct_selected_control_keeps_bad_setting_activity_policy(
    action: OperatorAction, state: ObservationState
) -> None:
    catalog = OwnedUnitCatalog(
        receipt_present=True,
        generation="generation",
        units=(
            OwnedUnit("lychd-vessel.service", (), ObservationState.INACTIVE),
            OwnedUnit("lychd-phylactery.service", (), state, "disabled", load_state="bad-setting"),
        ),
    )
    runner = _Runner()

    result = _control(_Inventory(catalog), runner).execute(action, OperatorTarget.STORAGE)

    assert result.authority is VesselAuthority.DIRECT
    assert result.units == ("lychd-phylactery.service",)
    assert runner.calls == [
        (
            ("/usr/bin/systemctl", "--user", action.value, "lychd-phylactery.service"),
            360.0 if action is OperatorAction.START else 30.0,
        )
    ]


def test_retiring_runner_preserves_observed_load_state_and_detail() -> None:
    unit = OwnedUnit(
        "lychd-peer.service", (), ObservationState.ACTIVE, "enabled", "fixture detail", load_state="loaded"
    )
    inventory = _Inventory(OwnedUnitCatalog(receipt_present=True, units=(unit,), generation="generation"))
    runner = _RetiringRunner(inventory)

    runner.run(("/usr/bin/systemctl", "--user", "stop", unit.name), timeout_s=30.0)
    runner.run(("/usr/bin/systemctl", "--user", "disable", unit.name), timeout_s=30.0)

    assert inventory.catalog.units == (replace(unit, state=ObservationState.INACTIVE, unit_file_state="disabled"),)


@pytest.mark.parametrize("action", [OperatorAction.START, OperatorAction.STOP])
@pytest.mark.parametrize("target", [OperatorTarget.SYSTEM, OperatorTarget.STORAGE])
@pytest.mark.parametrize("state", [ObservationState.ACTIVE, ObservationState.INACTIVE, ObservationState.FAILED])
@pytest.mark.parametrize("vessel_name", ["lychd-uncaged-vessel.service", "lychd-vessel.service"])
def test_retired_native_binding_never_grants_control(
    action: OperatorAction, target: OperatorTarget, state: ObservationState, vessel_name: str
) -> None:
    runner = _Runner()
    catalog = _catalog(state, units=(vessel_name, "lychd-phylactery.service"))
    catalog = replace(
        catalog,
        units=(replace(catalog.units[0], sources=(f"/units/{vessel_name}",)), catalog.units[1]),
    )
    with pytest.raises(OperatorAuthorityError, match="Retired native Vessel bindings are observational only"):
        _control(_Inventory(catalog), runner).execute(action, target)
    assert runner.calls == []


@pytest.mark.parametrize("state", [ObservationState.ACTIVE, ObservationState.INACTIVE, ObservationState.FAILED])
@pytest.mark.parametrize("vessel_name", ["lychd-uncaged-vessel.service", "lychd-vessel.service"])
def test_retired_native_binding_blocks_retirement_before_any_effect(state: ObservationState, vessel_name: str) -> None:
    runner = _Runner()
    catalog = _catalog(state, units=(vessel_name, "lychd-phylactery.service"))
    inventory = _Inventory(
        replace(
            catalog,
            units=(replace(catalog.units[0], sources=(f"/units/{vessel_name}",)), catalog.units[1]),
        )
    )
    service = OwnedUnitRetirementService(
        inventory=cast("OperatorInventoryService", inventory), runner=runner, systemctl_bin="/usr/bin/systemctl"
    )
    with pytest.raises(OperatorError, match="Retired native Vessel bindings require manual reconciliation"):
        service.plan()
    assert runner.calls == []


@pytest.mark.parametrize("action", [OperatorAction.START, OperatorAction.STOP])
@pytest.mark.parametrize("target", [OperatorTarget.SYSTEM, OperatorTarget.STORAGE])
@pytest.mark.parametrize("vessel_name", ["lychd-uncaged-vessel.service", "lychd-vessel.service"])
def test_retired_native_binding_never_resolves_direct_actuation(
    action: OperatorAction, target: OperatorTarget, vessel_name: str
) -> None:
    catalog = _catalog(ObservationState.INACTIVE, units=(vessel_name, "lychd-phylactery.service"))
    catalog = replace(
        catalog,
        units=(replace(catalog.units[0], sources=(f"/units/{vessel_name}",)), catalog.units[1]),
    )
    resolver = OperatorTargetResolver(cast("OperatorInventoryService", _Inventory(catalog)))

    with pytest.raises(OperatorError, match="Retired native Vessel bindings are observational only"):
        resolver.direct_actuation_units(action.value, target, catalog=catalog)


@pytest.mark.parametrize("vessel_name", ["lychd-uncaged-vessel.service", "lychd-vessel.service"])
def test_retired_native_binding_remains_observable(vessel_name: str) -> None:
    catalog = _catalog(ObservationState.ACTIVE, units=(vessel_name,))
    catalog = replace(catalog, units=(replace(catalog.units[0], sources=(f"/units/{vessel_name}",)),))
    resolver = OperatorTargetResolver(cast("OperatorInventoryService", _Inventory(catalog)))

    assert resolver.observation_units(OperatorTarget.WORKERS) == (vessel_name,)
    assert resolver.observation_units(OperatorTarget.SYSTEM) == (vessel_name,)
