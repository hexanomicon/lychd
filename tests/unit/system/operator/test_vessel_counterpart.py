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
    OperatorTarget,
    OwnedUnit,
    OwnedUnitCatalog,
    VesselAuthority,
)
from lychd.system.operator.process import ProcessInvocationError, ProcessResult
from lychd.system.operator.targets import OperatorTargetResolver

if TYPE_CHECKING:
    from collections.abc import Generator

_PAIRS = (("lychd-vessel.service", "lychd-uncaged-vessel.service"),)
_FIELDS = ("Id", "LoadState", "ActiveState", "SubState", "MainPID", "ControlPID", "Job")


class _World:
    def __init__(self, vessel: str, counterpart: str) -> None:
        self.vessel = vessel
        self.counterpart = counterpart
        self.catalog = OwnedUnitCatalog(
            receipt_present=True,
            generation="fixed-generation",
            units=(
                OwnedUnit(vessel, ("/owned/lychd-vessel.container",), ObservationState.INACTIVE),
                OwnedUnit("lychd-phylactery.service", ("/owned/storage",), ObservationState.INACTIVE),
            ),
        )
        self.fields: dict[str, str] = dict(
            zip(_FIELDS, (counterpart, "loaded", "inactive", "dead", "0", "0", ""), strict=True)
        )
        self.stdout: str | None = None
        self.returncode = 0
        self.failure: ProcessInvocationError | None = None
        self.events: list[str] = []
        self.calls: list[tuple[tuple[str, ...], float]] = []
        self.locked = False
        self.observations = 0
        self.drift = False

    @contextmanager
    def lock(self) -> Generator[None]:
        assert not self.locked
        self.locked = True
        self.events.append("lock")
        try:
            yield
        finally:
            self.events.append("unlock")
            self.locked = False

    def owned_units(self) -> OwnedUnitCatalog:
        assert self.locked
        self.observations += 1
        self.events.append(f"owned-{self.observations}")
        if self.drift and self.observations == 2:
            return replace(self.catalog, generation="changed-generation")
        return self.catalog

    def show_argv(self) -> tuple[str, ...]:
        return (
            "/trusted/systemctl",
            "--user",
            "show",
            self.counterpart,
            *(f"--property={field}" for field in _FIELDS),
        )

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        assert self.locked
        self.calls.append((argv, timeout_s))
        self.events.append(argv[2])
        if argv[2] == "show":
            assert self.observations == 2
            assert argv == self.show_argv()
            assert timeout_s == 3.0
            if self.failure is not None:
                raise self.failure
            stdout = self.stdout
            if stdout is None:
                stdout = "".join(f"{key}={value}\n" for key, value in self.fields.items())
            return ProcessResult(argv, self.returncode, stdout, "private untrusted stderr" * 1000)
        assert argv == ("/trusted/systemctl", "--user", "start", self.vessel)
        assert timeout_s == 360.0
        return ProcessResult(argv, 0)

    def control(self, *, systemctl_bin: str | None = "/trusted/systemctl") -> OperatorControlService:
        inventory = cast("OperatorInventoryService", self)
        return OperatorControlService(
            inventory=inventory,
            targets=OperatorTargetResolver(inventory),
            runner=self,
            systemctl_bin=systemctl_bin,
            lock_factory=self.lock,
        )


@pytest.mark.parametrize(("vessel", "counterpart"), _PAIRS)
@pytest.mark.parametrize("load_state", ["loaded", "not-found"])
def test_cold_counterpart_allows_only_exact_owned_start(vessel: str, counterpart: str, load_state: str) -> None:
    world = _World(vessel, counterpart)
    catalog = world.catalog
    world.fields["LoadState"] = load_state

    result = world.control().execute(OperatorAction.START)

    assert result.authority is VesselAuthority.DIRECT
    assert result.units == (vessel,)
    assert world.catalog is catalog
    assert tuple(unit.name for unit in world.catalog.units) == (vessel, "lychd-phylactery.service")
    assert world.calls == [
        (world.show_argv(), 3.0),
        (("/trusted/systemctl", "--user", "start", vessel), 360.0),
    ]
    assert world.events == ["lock", "owned-1", "owned-2", "show", "start", "unlock"]


@pytest.mark.parametrize(("vessel", "counterpart"), _PAIRS)
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Id", "unrelated.service"),
        ("Id", ""),
        ("LoadState", "error"),
        ("LoadState", "masked"),
        ("LoadState", "bad-setting"),
        ("ActiveState", "active"),
        ("ActiveState", "failed"),
        ("ActiveState", "activating"),
        ("ActiveState", "deactivating"),
        ("ActiveState", "reloading"),
        ("ActiveState", "unknown"),
        ("SubState", "running"),
        ("SubState", "failed"),
        ("SubState", "auto-restart"),
        ("MainPID", "42"),
        ("ControlPID", "42"),
        ("MainPID", "00"),
        ("MainPID", "invalid"),
        ("Job", "27"),
        ("Job", "27 /org/freedesktop/systemd1/job/27"),
        ("Job", " "),
    ],
)
def test_uncertain_counterpart_refuses_without_foreign_or_owned_actuation(
    vessel: str, counterpart: str, field: str, value: str
) -> None:
    world = _World(vessel, counterpart)
    original = world.catalog
    world.fields[field] = value

    with pytest.raises(OperatorAuthorityError, match=r"[Cc]ounterpart.*system start refused") as caught:
        world.control().execute(OperatorAction.START)

    assert len(str(caught.value)) < 300
    assert "private untrusted stderr" not in str(caught.value)
    assert world.catalog is original
    assert world.calls == [(world.show_argv(), 3.0)]
    assert world.events == ["lock", "owned-1", "owned-2", "show", "unlock"]


@pytest.mark.parametrize("returncode", [1, 3, 4, -9])
def test_nonzero_counterpart_reply_refuses_even_with_exact_cold_fields(returncode: int) -> None:
    world = _World(*_PAIRS[0])
    world.returncode = returncode

    with pytest.raises(OperatorAuthorityError, match="observation was unsuccessful") as caught:
        world.control().execute(OperatorAction.START)

    assert "private untrusted stderr" not in str(caught.value)
    assert world.calls == [(world.show_argv(), 3.0)]


@pytest.mark.parametrize("field", _FIELDS)
def test_missing_or_duplicate_counterpart_field_refuses(field: str) -> None:
    world = _World(*_PAIRS[0])
    del world.fields[field]
    with pytest.raises(OperatorAuthorityError):
        world.control().execute(OperatorAction.START)
    assert world.calls == [(world.show_argv(), 3.0)]

    duplicate = _World(*_PAIRS[0])
    duplicate.stdout = "".join(f"{key}={value}\n" for key, value in duplicate.fields.items())
    duplicate.stdout += f"{field}={duplicate.fields[field]}\n"
    with pytest.raises(OperatorAuthorityError, match="malformed"):
        duplicate.control().execute(OperatorAction.START)
    assert duplicate.calls == [(duplicate.show_argv(), 3.0)]


@pytest.mark.parametrize("suffix", ["Unknown=ignored\n", "malformed\n", "\n", "=value\n"])
def test_extra_or_malformed_counterpart_output_refuses(suffix: str) -> None:
    world = _World(*_PAIRS[0])
    world.stdout = "".join(f"{key}={value}\n" for key, value in world.fields.items()) + suffix

    with pytest.raises(OperatorAuthorityError, match="malformed"):
        world.control().execute(OperatorAction.START)

    assert world.calls == [(world.show_argv(), 3.0)]


def test_counterpart_timeout_refuses_once_without_exposing_runner_error() -> None:
    world = _World(*_PAIRS[0])
    world.failure = ProcessInvocationError("private timeout diagnostic" * 1000)

    with pytest.raises(OperatorAuthorityError, match="failed or timed out") as caught:
        world.control().execute(OperatorAction.START)

    assert len(str(caught.value)) < 300
    assert "private timeout diagnostic" not in str(caught.value)
    assert world.calls == [(world.show_argv(), 3.0)]


def test_owned_revalidation_precedes_counterpart_observation() -> None:
    world = _World(*_PAIRS[0])
    world.drift = True

    with pytest.raises(OperatorAuthorityError, match="runtime authority changed"):
        world.control().execute(OperatorAction.START)

    assert world.calls == []
    assert world.events == ["lock", "owned-1", "owned-2", "unlock"]


def test_unavailable_systemctl_refuses_counterpart_authority() -> None:
    world = _World(*_PAIRS[0])

    with pytest.raises(OperatorAuthorityError, match="exact Vessel counterpart"):
        world.control(systemctl_bin=None).execute(OperatorAction.START, OperatorTarget.SYSTEM)

    assert world.calls == []
