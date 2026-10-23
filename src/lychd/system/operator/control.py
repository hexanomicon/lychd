"""Arbitrated start/stop over exact Scribe-owned units."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from lychd.system.operator.inventory import OperatorInventoryService
from lychd.system.operator.models import (
    ObservationState,
    OperatorAction,
    OperatorAuthorityError,
    OperatorError,
    OperatorTarget,
    OwnedUnitCatalog,
    VesselAuthority,
)
from lychd.system.operator.process import ProcessInvocationError, ProcessResult, ProcessRunner
from lychd.system.operator.targets import OperatorTargetResolver

if TYPE_CHECKING:
    from lychd.system.operator.stop_evidence import ExitReference

_SYSTEMCTL_TIMEOUT_SECONDS = 30.0
_JOB_COLUMN_COUNT = 4
_NATIVE_VESSEL_UNIT = "lychd-uncaged-vessel.service"
logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ControlResult:
    """One completed actuation with its authority visible."""

    authority: VesselAuthority
    units: tuple[str, ...] = ()
    detail: str = ""


class OperatorControlService:
    """Choose Vessel or direct host authority before any lifecycle effect."""

    def __init__(
        self,
        *,
        inventory: OperatorInventoryService,
        targets: OperatorTargetResolver,
        runner: ProcessRunner,
        systemctl_bin: str | None,
        lock_factory: Callable[[], AbstractContextManager[object]],
        stop_admission: Callable[[str], None] | None = None,
        exit_reference_factory: Callable[[], AbstractContextManager[ExitReference]] | None = None,
    ) -> None:
        """Bind typed discovery and process ports."""
        self._inventory = inventory
        self._targets = targets
        self._runner = runner
        self._systemctl = systemctl_bin
        self._lock_factory = lock_factory
        self._stop_admission = stop_admission
        self._exit_reference_factory = exit_reference_factory

    def execute(self, action: OperatorAction, target: OperatorTarget = OperatorTarget.SYSTEM) -> ControlResult:
        """Serialize and apply one operation only after proving current authority."""
        try:
            with self._lock_factory():
                return self._execute_locked(action, target)
        except OperatorError:
            raise
        except RuntimeError as exc:
            raise OperatorError(str(exc)) from exc

    def _execute_locked(
        self,
        action: OperatorAction,
        target: OperatorTarget,
    ) -> ControlResult:
        """Refuse unknown selected-unit state and hold the lock through physical effect."""
        planned = self._inventory.owned_units()
        authority = self.authority(planned)
        if authority is VesselAuthority.UNKNOWN:
            message = "Cannot prove whether the Vessel owns lifecycle mutation; no action was taken."
            logger.warning(
                "operator_actuation_refused",
                action=action.value,
                target=target.value,
                authority=authority.value,
                reason=message,
            )
            raise OperatorAuthorityError(message)

        if authority is VesselAuthority.VESSEL:
            if action is OperatorAction.STOP and target is OperatorTarget.SYSTEM and self._stop_admission is not None:
                return self._stop_active_system(planned)
            message = (
                "The Vessel is active, but authenticated lifecycle API completion is unavailable; no action was taken."
            )
            logger.warning(
                "operator_actuation_refused",
                action=action.value,
                target=target.value,
                authority=authority.value,
                reason=message,
            )
            raise OperatorAuthorityError(message)

        units = self._targets.direct_actuation_units(action.value, target, catalog=planned)
        unknown_units = tuple(
            unit.name for unit in planned.units if unit.name in units and unit.state is ObservationState.UNKNOWN
        )
        if unknown_units:
            message = f"Cannot prove runtime state for selected units: {', '.join(unknown_units)}; no action was taken."
            logger.warning(
                "operator_actuation_refused",
                action=action.value,
                target=target.value,
                authority=authority.value,
                units=units,
                reason=message,
            )
            raise OperatorAuthorityError(message)
        current = self._inventory.owned_units()
        if (
            current.warning
            or current.generation != planned.generation
            or tuple(unit.name for unit in current.units) != tuple(unit.name for unit in planned.units)
            or tuple(unit.state for unit in current.units) != tuple(unit.state for unit in planned.units)
            or self.authority(current) is not VesselAuthority.DIRECT
        ):
            message = "Binding ownership or runtime authority changed during planning; rerun the command."
            logger.warning(
                "operator_actuation_refused",
                action=action.value,
                target=target.value,
                authority=authority.value,
                units=units,
                reason=message,
            )
            raise OperatorAuthorityError(message)
        if self._systemctl is None:
            message = "systemctl is unavailable; no action was taken."
            logger.warning(
                "operator_actuation_refused",
                action=action.value,
                target=target.value,
                authority=authority.value,
                units=units,
                reason=message,
            )
            raise OperatorError(message)
        argv = (self._systemctl, "--user", action.value, *units)
        logger.info(
            "operator_actuation_started",
            action=action.value,
            target=target.value,
            authority=authority.value,
            units=units,
        )
        try:
            result = self._runner.run(argv, timeout_s=_SYSTEMCTL_TIMEOUT_SECONDS)
        except ProcessInvocationError as exc:
            message = f"systemctl {action.value} failed: {exc}"
            logger.exception(
                "operator_actuation_failed",
                action=action.value,
                target=target.value,
                authority=authority.value,
                units=units,
            )
            raise OperatorError(message) from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit {result.returncode}"
            message = f"systemctl {action.value} failed: {detail}"
            logger.error(
                "operator_actuation_failed",
                action=action.value,
                target=target.value,
                authority=authority.value,
                units=units,
                error=detail,
            )
            raise OperatorError(message)
        logger.info(
            "operator_actuation_completed",
            action=action.value,
            target=target.value,
            authority=authority.value,
            units=units,
        )
        return ControlResult(
            authority=authority,
            units=units,
            detail=result.stdout.strip(),
        )

    def _stop_active_system(self, planned: OwnedUnitCatalog) -> ControlResult:
        """Admit installation intent, stop the Vessel, then settle its dependencies.

        The existing lifecycle lock excludes Reactor effects throughout this
        sequence. Admission authenticates intent only; a clean process exit and
        settled host observations under the held manager reference are required
        before stopping dependencies.
        """
        if self._targets.vessel_units(planned) != (_NATIVE_VESSEL_UNIT,):
            msg = "Active system stop requires the exact owned native Vessel; no admission or host action was taken."
            raise OperatorAuthorityError(msg)
        self._revalidate_active_binding(planned, planned)
        if self._systemctl is None:
            msg = "systemctl is unavailable; no action was taken."
            raise OperatorError(msg)
        admission = self._stop_admission
        reference_factory = self._exit_reference_factory
        generation = planned.generation
        if admission is None or generation is None:
            msg = "Authenticated stop admission is unavailable; no action was taken."
            raise OperatorAuthorityError(msg)
        if reference_factory is None:
            msg = "Native exit evidence retention is unavailable; no admission or host action was taken."
            raise OperatorAuthorityError(msg)
        admission(generation)
        self._revalidate_active_binding(planned, self._inventory.owned_units())
        units = tuple(unit.name for unit in planned.units)
        vessel = self._targets.vessel_units(planned)[0]
        progress = "Vessel stop was not submitted; dependency stop was not submitted."
        try:
            with reference_factory() as reference:
                reference.verify()
                self._revalidate_active_binding(planned, self._inventory.owned_units())
                self._require_no_owned_jobs(units)
                progress = "Vessel stop was attempted; dependency stop was not submitted."
                self._stop_exact_units((vessel,))
                reference.verify()
                self._require_clean_vessel_exit(vessel)
                current = self._inventory.owned_units()
                self._revalidate_active_binding(planned, current)
                observed_vessel = current.unit(vessel)
                if observed_vessel is None or observed_vessel.state is not ObservationState.INACTIVE:
                    msg = "Vessel stop did not settle inactive; dependencies were preserved."
                    raise OperatorAuthorityError(msg)
                self._require_no_owned_jobs(units)
                dependencies = tuple(unit for unit in units if unit != vessel)
                reference.verify()
                if dependencies:
                    progress = "Vessel stop settled; dependency stop was attempted."
                    self._stop_exact_units(dependencies)
                self._require_inactive_system(planned, units)
                reference.verify()
        except OperatorError as exc:
            msg = f"{progress} {exc}"
            raise type(exc)(msg) from exc
        logger.info(
            "operator_actuation_completed",
            action=OperatorAction.STOP.value,
            target=OperatorTarget.SYSTEM.value,
            authority=VesselAuthority.VESSEL.value,
            units=units,
        )
        return ControlResult(authority=VesselAuthority.VESSEL, units=units)

    def _require_inactive_system(self, planned: OwnedUnitCatalog, units: tuple[str, ...]) -> None:
        """Verify the final owned system state before releasing exit evidence."""
        settled = self._inventory.owned_units()
        self._revalidate_active_binding(planned, settled)
        self._require_no_owned_jobs(units)
        if any(unit.state is not ObservationState.INACTIVE for unit in settled.units):
            msg = "Owned system units did not settle inactive; inspect status before retrying."
            raise OperatorAuthorityError(msg)

    @staticmethod
    def _revalidate_active_binding(planned: OwnedUnitCatalog, current: OwnedUnitCatalog) -> None:
        """Accept runtime succession only under the unchanged exact owned binding."""
        if (
            current.warning
            or not current.receipt_present
            or not planned.generation
            or current.generation != planned.generation
            or tuple((unit.name, unit.sources) for unit in current.units)
            != tuple((unit.name, unit.sources) for unit in planned.units)
            or any(unit.state is ObservationState.UNKNOWN or unit.load_state != "loaded" for unit in current.units)
        ):
            msg = "Binding ownership or runtime evidence changed or is uncertain; stop refused."
            raise OperatorAuthorityError(msg)

    def _stop_exact_units(self, units: tuple[str, ...]) -> None:
        """Submit one normal stop without replacing conflicting systemd jobs."""
        result = self._systemctl_result("stop", "--job-mode=fail", *units)
        if result.returncode != 0:
            msg = "System stop failed; no further stop was attempted. Inspect status before retrying."
            raise OperatorError(msg)

    def _require_clean_vessel_exit(self, vessel: str) -> None:
        """Require normal successful exit, with no retained main or control process."""
        expected = {
            "Id": vessel,
            "LoadState": "loaded",
            "ActiveState": "inactive",
            "SubState": "dead",
            "MainPID": "0",
            "ControlPID": "0",
            "Result": "success",
            "ExecMainCode": "1",
            "ExecMainStatus": "0",
        }
        result = self._systemctl_result("show", vessel, *(f"--property={field}" for field in expected))
        fields: dict[str, str] = {}
        for line in result.stdout.splitlines():
            key, separator, value = line.partition("=")
            if not separator or key in fields:
                msg = "Vessel exit evidence is malformed; dependencies were preserved."
                raise OperatorAuthorityError(msg)
            fields[key] = value
        if result.returncode != 0 or fields != expected:
            msg = "A clean Vessel exit is unproved; dependencies were preserved."
            raise OperatorAuthorityError(msg)

    def _require_no_owned_jobs(self, units: tuple[str, ...]) -> None:
        """Refuse unclassified or pending jobs before accepting a settled stop."""
        result = self._systemctl_result("list-jobs", "--no-legend", "--plain", "--no-pager")
        if result.returncode != 0:
            msg = "Systemd job settlement is unproved; no further stop was attempted."
            raise OperatorAuthorityError(msg)
        for line in result.stdout.splitlines():
            columns = line.split()
            if len(columns) != _JOB_COLUMN_COUNT or not columns[0].isdigit() or columns[1] in units:
                msg = "Systemd jobs remain pending or uncertain; no further stop was attempted."
                raise OperatorAuthorityError(msg)

    def _systemctl_result(self, *arguments: str) -> ProcessResult:
        """Keep every active-stop host call bounded and never retry uncertain effects."""
        if self._systemctl is None:
            msg = "systemctl is unavailable; no action was taken."
            raise OperatorError(msg)
        try:
            return self._runner.run((self._systemctl, "--user", *arguments), timeout_s=_SYSTEMCTL_TIMEOUT_SECONDS)
        except ProcessInvocationError:
            msg = "System stop is uncertain; no further stop was attempted. Inspect status."
            raise OperatorError(msg) from None

    def authority(self, catalog: OwnedUnitCatalog | None = None) -> VesselAuthority:
        """Project the current arbitration owner from exact Vessel unit state."""
        owned = catalog or self._inventory.owned_units()
        if owned.warning:
            return VesselAuthority.UNKNOWN
        vessel_names = self._targets.vessel_units(owned)
        result = VesselAuthority.UNKNOWN
        if not vessel_names:
            result = VesselAuthority.DIRECT
        elif len(vessel_names) == 1 and (vessel := owned.unit(vessel_names[0])) is not None:
            if vessel.state is ObservationState.ACTIVE:
                result = VesselAuthority.VESSEL
            elif vessel.state in {ObservationState.INACTIVE, ObservationState.FAILED}:
                result = VesselAuthority.DIRECT
        return result
