"""Arbitrated start/stop over exact Scribe-owned units."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

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
from lychd.system.operator.process import ProcessInvocationError, ProcessRunner
from lychd.system.operator.targets import OperatorTargetResolver

_SYSTEMCTL_TIMEOUT_SECONDS = 30.0
# Cold starts include the 60s database readiness gate and prerequisite units.
# Match the controller convergence window without changing manager completion semantics.
_SYSTEMCTL_START_TIMEOUT_SECONDS = 360.0
_COUNTERPART_TIMEOUT_SECONDS = 3.0
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
    ) -> None:
        """Bind typed discovery and process ports."""
        self._inventory = inventory
        self._targets = targets
        self._runner = runner
        self._systemctl = systemctl_bin
        self._lock_factory = lock_factory

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
        if planned.has_retired_native_vessel():
            message = "Retired native Vessel bindings are observational only; no action was taken."
            raise OperatorAuthorityError(message)
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
        if action is OperatorAction.START and target is OperatorTarget.SYSTEM:
            self._require_quiescent_counterpart(units[0])
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
        timeout_s = _SYSTEMCTL_START_TIMEOUT_SECONDS if action is OperatorAction.START else _SYSTEMCTL_TIMEOUT_SECONDS
        try:
            result = self._runner.run(argv, timeout_s=timeout_s)
        except ProcessInvocationError as exc:
            message = (
                f"systemctl start outcome is unconfirmed; the manager job may continue: {exc}"
                if action is OperatorAction.START
                else f"systemctl {action.value} failed: {exc}"
            )
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

    def _require_quiescent_counterpart(self, vessel: str) -> None:
        """Observe the fixed opposite Vessel without granting ownership or actuation.

        This bounded check follows owned revalidation under the lifecycle lock;
        it cannot reserve the manager namespace against other clients.
        """
        counterpart = "lychd-uncaged-vessel.service" if vessel == "lychd-vessel.service" else None
        if counterpart is None or self._systemctl is None:
            msg = "Cannot observe the exact Vessel counterpart; system start refused."
            raise OperatorAuthorityError(msg)
        expected = {
            "Id": counterpart,
            "LoadState": "loaded",
            "ActiveState": "inactive",
            "SubState": "dead",
            "MainPID": "0",
            "ControlPID": "0",
            "Job": "",
        }
        argv = (self._systemctl, "--user", "show", counterpart, *(f"--property={field}" for field in expected))
        try:
            result = self._runner.run(argv, timeout_s=_COUNTERPART_TIMEOUT_SECONDS)
        except ProcessInvocationError:
            msg = f"Cannot prove counterpart {counterpart} quiescent: observation failed or timed out; system start refused."
            raise OperatorAuthorityError(msg) from None
        if result.returncode != 0:
            msg = (
                f"Cannot prove counterpart {counterpart} quiescent: observation was unsuccessful; system start refused."
            )
            raise OperatorAuthorityError(msg)
        fields: dict[str, str] = {}
        for line in result.stdout.splitlines():
            key, separator, value = line.partition("=")
            if not separator or key not in expected or key in fields:
                msg = f"Counterpart {counterpart} observation is malformed; system start refused."
                raise OperatorAuthorityError(msg)
            fields[key] = value
        if fields.get("LoadState") == "not-found":
            expected["LoadState"] = "not-found"
        if fields != expected:
            msg = f"Counterpart {counterpart} is not proven inactive/dead without processes or a pending job; system start refused."
            raise OperatorAuthorityError(msg)

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
