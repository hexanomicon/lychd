from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import pytest

from lychd.system.operator.control import OperatorControlService
from lychd.system.operator.inventory import OperatorInventoryService
from lychd.system.operator.models import (
    ObservationState,
    OperatorAction,
    OperatorAuthorityError,
    OperatorError,
    OperatorTarget,
    OwnedUnit,
    OwnedUnitCatalog,
    VesselAuthority,
)
from lychd.system.operator.process import ProcessInvocationError, ProcessResult
from lychd.system.operator.targets import OperatorTargetResolver

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

_VESSEL = "lychd-uncaged-vessel.service"
_DEPENDENCIES = ("lychd-qwen.service", "lychd-phylactery.service")
_UNITS = (_VESSEL, *_DEPENDENCIES)


class _World:
    def __init__(self) -> None:
        self.catalog = OwnedUnitCatalog(
            receipt_present=True,
            generation="a" * 64,
            units=tuple(
                OwnedUnit(name, (f"/owned/{name}",), ObservationState.ACTIVE, load_state="loaded") for name in _UNITS
            ),
        )
        self.calls: list[tuple[str, ...]] = []
        self.admissions: list[str] = []
        self.locked = False
        self.exit_fields = {
            "Id": _VESSEL,
            "LoadState": "loaded",
            "ActiveState": "inactive",
            "SubState": "dead",
            "MainPID": "0",
            "ControlPID": "0",
            "Result": "success",
            "ExecMainCode": "1",
            "ExecMainStatus": "0",
        }
        self.jobs: list[str] = []
        self.stop_error: BaseException | None = None
        self.stop_returncode = 0
        self.settle_stops = True
        self.reference_held = False
        self.reference_events: list[str] = []
        self.verify_calls = 0
        self.fail_on_verify: int | None = None
        self.fail_acquire = False
        self.fail_release = False

    @contextmanager
    def lock(self) -> Generator[None]:
        assert not self.locked
        self.locked = True
        try:
            yield
        finally:
            self.locked = False

    def owned_units(self) -> OwnedUnitCatalog:
        assert self.locked
        return self.catalog

    def admit(self, generation: str) -> None:
        assert self.locked
        assert not self.reference_held
        self.admissions.append(generation)

    @contextmanager
    def reference(self) -> Generator[_World]:
        assert self.locked
        assert self.admissions
        if self.fail_acquire:
            message = "reference acquisition refused"
            raise OperatorAuthorityError(message)
        self.reference_held = True
        self.reference_events.append("acquired")
        try:
            yield self
        finally:
            assert self.locked
            self.reference_held = False
            self.reference_events.append("released")
            if self.fail_release:
                message = "reference release is uncertain"
                raise OperatorAuthorityError(message)

    def verify(self) -> None:
        assert self.locked
        assert self.reference_held
        self.verify_calls += 1
        if self.verify_calls == self.fail_on_verify:
            message = "reference connection was lost"
            raise OperatorAuthorityError(message)

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        assert self.locked
        assert self.reference_held
        assert timeout_s == 30
        assert argv[:2] == ("/trusted/systemctl", "--user")
        self.calls.append(argv)
        if argv[2] == "list-jobs":
            return ProcessResult(argv, 0, self.jobs.pop(0) if self.jobs else "")
        if argv[2] == "show":
            assert argv[3] == _VESSEL
            return ProcessResult(argv, 0, "".join(f"{key}={value}\n" for key, value in self.exit_fields.items()))
        assert argv[2:4] == ("stop", "--job-mode=fail")
        if self.stop_error is not None:
            raise self.stop_error
        if self.settle_stops:
            self.catalog = replace(
                self.catalog,
                units=tuple(
                    replace(unit, state=ObservationState.INACTIVE) if unit.name in argv[4:] else unit
                    for unit in self.catalog.units
                ),
            )
        return ProcessResult(argv, self.stop_returncode)

    def control(self, admission: Callable[[str], None] | None = None) -> OperatorControlService:
        inventory = cast("OperatorInventoryService", self)
        return OperatorControlService(
            inventory=inventory,
            targets=OperatorTargetResolver(inventory),
            runner=self,
            systemctl_bin="/trusted/systemctl",
            lock_factory=self.lock,
            stop_admission=admission or self.admit,
            exit_reference_factory=self.reference,
        )

    @property
    def stops(self) -> list[tuple[str, ...]]:
        return [argv[4:] for argv in self.calls if argv[2] == "stop"]


def test_admitted_active_stop_settles_vessel_before_stopping_dependencies() -> None:
    world = _World()

    result = world.control().execute(OperatorAction.STOP)

    assert result.authority is VesselAuthority.VESSEL
    assert result.units == _UNITS
    assert world.admissions == ["a" * 64]
    assert world.stops == [(_VESSEL,), _DEPENDENCIES]
    assert [argv[2] for argv in world.calls] == ["list-jobs", "stop", "show", "list-jobs", "stop", "list-jobs"]
    assert world.reference_events == ["acquired", "released"]
    assert world.verify_calls == 4
    assert not world.reference_held
    assert not world.locked


def test_missing_reference_factory_refuses_before_admission_or_host_calls() -> None:
    world = _World()
    inventory = cast("OperatorInventoryService", world)
    control = OperatorControlService(
        inventory=inventory,
        targets=OperatorTargetResolver(inventory),
        runner=world,
        systemctl_bin="/trusted/systemctl",
        lock_factory=world.lock,
        stop_admission=world.admit,
    )

    with pytest.raises(OperatorAuthorityError, match="exit evidence retention is unavailable"):
        control.execute(OperatorAction.STOP)

    assert world.admissions == []
    assert world.calls == []


def test_reference_acquisition_refusal_cannot_submit_a_stop() -> None:
    world = _World()
    world.fail_acquire = True

    with pytest.raises(OperatorAuthorityError, match=r"Vessel stop was not submitted.*reference acquisition"):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == []
    assert world.admissions == ["a" * 64]
    assert not world.reference_held
    assert not world.locked


@pytest.mark.parametrize("phase", [1, 2, 3])
def test_reference_loss_before_dependency_decision_preserves_dependencies(phase: int) -> None:
    world = _World()
    world.fail_on_verify = phase

    with pytest.raises(OperatorAuthorityError, match="reference connection was lost"):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == ([] if phase == 1 else [(_VESSEL,)])
    assert world.reference_events == ["acquired", "released"]
    assert not world.reference_held
    assert not world.locked


@pytest.mark.parametrize("failure", ["last-verification", "release"])
def test_late_reference_uncertainty_reports_dependency_submission(failure: str) -> None:
    world = _World()
    if failure == "release":
        world.fail_release = True
    else:
        world.fail_on_verify = 4

    with pytest.raises(OperatorAuthorityError, match=r"Vessel stop settled; dependency stop was attempted.*reference"):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == [(_VESSEL,), _DEPENDENCIES]
    assert world.reference_events == ["acquired", "released"]
    assert not world.reference_held
    assert not world.locked


def test_cancelled_host_stop_releases_reference_and_preserves_dependencies() -> None:
    world = _World()
    world.stop_error = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == [(_VESSEL,)]
    assert world.reference_events == ["acquired", "released"]
    assert not world.reference_held
    assert not world.locked


def test_caged_vessel_refuses_before_admission_or_host_calls() -> None:
    world = _World()
    world.catalog = replace(
        world.catalog,
        units=(replace(world.catalog.units[0], name="lychd-vessel.service"), *world.catalog.units[1:]),
    )

    with pytest.raises(OperatorAuthorityError, match="exact owned native Vessel"):
        world.control().execute(OperatorAction.STOP)

    assert world.admissions == []
    assert world.calls == []


def test_mixed_vessel_ownership_cannot_select_the_native_profile() -> None:
    world = _World()
    world.catalog = replace(
        world.catalog,
        units=(
            *world.catalog.units,
            OwnedUnit("lychd-vessel.service", ("/owned/caged",), ObservationState.INACTIVE, load_state="loaded"),
        ),
    )

    with pytest.raises(OperatorAuthorityError, match="Cannot prove"):
        world.control().execute(OperatorAction.STOP)

    assert world.admissions == []
    assert world.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Result", "exit-code"),
        ("Result", "timeout"),
        ("ExecMainCode", "2"),
        ("ExecMainStatus", "1"),
        ("ActiveState", "failed"),
        ("SubState", "failed"),
        ("MainPID", "123"),
        ("ControlPID", "123"),
        ("LoadState", "not-found"),
        ("Id", "foreign.service"),
    ],
)
def test_failed_or_uncertain_vessel_exit_preserves_dependencies(field: str, value: str) -> None:
    world = _World()
    world.exit_fields[field] = value

    with pytest.raises(OperatorAuthorityError, match="dependencies were preserved"):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == [(_VESSEL,)]
    assert world.admissions == ["a" * 64]


def test_missing_exit_field_does_not_infer_success_from_inactivity() -> None:
    world = _World()
    del world.exit_fields["ExecMainStatus"]

    with pytest.raises(OperatorAuthorityError, match="dependencies were preserved"):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == [(_VESSEL,)]


@pytest.mark.parametrize("failure", ["timeout", "nonzero"])
def test_uncertain_stop_never_repeats_or_falls_back(failure: str) -> None:
    world = _World()
    if failure == "timeout":
        world.stop_error = ProcessInvocationError("client timed out")
    else:
        world.stop_returncode = 1

    with pytest.raises(OperatorError, match="no further stop was attempted"):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == [(_VESSEL,)]
    assert world.admissions == ["a" * 64]


@pytest.mark.parametrize("drift", ["generation", "sources", "unknown"])
def test_binding_drift_after_admission_refuses_all_host_effects(drift: str) -> None:
    world = _World()

    def admit(generation: str) -> None:
        world.admit(generation)
        if drift == "generation":
            world.catalog = replace(world.catalog, generation="b" * 64)
        else:
            vessel = world.catalog.units[0]
            changed = (
                replace(vessel, sources=("/other/vessel.service",))
                if drift == "sources"
                else replace(vessel, state=ObservationState.UNKNOWN)
            )
            world.catalog = replace(world.catalog, units=(changed, *world.catalog.units[1:]))

    with pytest.raises(OperatorAuthorityError, match="stop refused"):
        world.control(admit).execute(OperatorAction.STOP)

    assert world.stops == []


def test_installation_stop_accepts_runtime_succession_under_unchanged_binding() -> None:
    world = _World()

    def admit(generation: str) -> None:
        world.admit(generation)
        world.catalog = replace(
            world.catalog,
            units=tuple(replace(unit, detail="successor process start") for unit in world.catalog.units),
        )

    world.control(admit).execute(OperatorAction.STOP)

    assert world.stops == [(_VESSEL,), _DEPENDENCIES]


@pytest.mark.parametrize("after_vessel", [False, True])
def test_pending_jobs_preserve_unstopped_units(*, after_vessel: bool) -> None:
    world = _World()
    world.jobs = [""] if after_vessel else []
    world.jobs.append(f"123 {_VESSEL} start waiting\n")

    with pytest.raises(OperatorAuthorityError, match="jobs remain pending"):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == ([(_VESSEL,)] if after_vessel else [])


def test_unclassified_jobs_refuse_all_host_effects() -> None:
    world = _World()
    world.jobs = ["unclassified manager reply\n"]

    with pytest.raises(OperatorAuthorityError, match="jobs remain pending or uncertain"):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == []


def test_inactive_exit_snapshot_cannot_override_still_active_owned_inventory() -> None:
    world = _World()
    world.settle_stops = False

    with pytest.raises(OperatorAuthorityError, match="did not settle inactive"):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == [(_VESSEL,)]


def test_binding_change_during_vessel_stop_preserves_dependencies() -> None:
    class ChangingWorld(_World):
        def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
            result = super().run(argv, timeout_s=timeout_s)
            if argv[2] == "show":
                self.catalog = replace(self.catalog, generation="b" * 64)
            return result

    world = ChangingWorld()

    with pytest.raises(
        OperatorAuthorityError,
        match=r"Vessel stop was attempted; dependency stop was not submitted.*stop refused",
    ) as caught:
        world.control().execute(OperatorAction.STOP)

    assert isinstance(caught.value.__cause__, OperatorAuthorityError)
    assert world.stops == [(_VESSEL,)]


def test_successful_dependency_command_does_not_attest_inactive_units() -> None:
    class UnsettledDependencies(_World):
        def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
            if argv[2:4] == ("stop", "--job-mode=fail") and argv[4:] == _DEPENDENCIES:
                self.settle_stops = False
            return super().run(argv, timeout_s=timeout_s)

    world = UnsettledDependencies()

    with pytest.raises(
        OperatorAuthorityError,
        match=r"Vessel stop settled; dependency stop was attempted.*did not settle inactive",
    ) as caught:
        world.control().execute(OperatorAction.STOP)

    assert isinstance(caught.value.__cause__, OperatorAuthorityError)
    assert "dependencies were preserved" not in str(caught.value)
    assert world.stops == [(_VESSEL,), _DEPENDENCIES]


def test_jobs_after_dependency_stop_refuse_success_without_repeating_stop() -> None:
    world = _World()
    world.jobs = ["", "", f"456 {_DEPENDENCIES[0]} start waiting\n"]

    with pytest.raises(OperatorAuthorityError, match="jobs remain pending"):
        world.control().execute(OperatorAction.STOP)

    assert world.stops == [(_VESSEL,), _DEPENDENCIES]


def test_admission_failure_never_uses_direct_stop_fallback() -> None:
    world = _World()

    def refuse(generation: str) -> None:
        world.admit(generation)
        msg = "Admission refused"
        raise OperatorAuthorityError(msg)

    with pytest.raises(OperatorAuthorityError, match="Admission refused"):
        world.control(refuse).execute(OperatorAction.STOP)

    assert world.calls == []


@pytest.mark.parametrize(
    ("action", "target"),
    [
        (OperatorAction.START, OperatorTarget.SYSTEM),
        (OperatorAction.STOP, OperatorTarget.STORAGE),
        (OperatorAction.START, OperatorTarget.STORAGE),
    ],
)
def test_admission_callback_does_not_expand_other_active_control(
    action: OperatorAction, target: OperatorTarget
) -> None:
    world = _World()

    with pytest.raises(OperatorAuthorityError, match="authenticated lifecycle API"):
        world.control().execute(action, target)

    assert world.admissions == []
    assert world.calls == []
