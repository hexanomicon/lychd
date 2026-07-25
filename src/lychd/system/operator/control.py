"""Arbitrated start/stop over exact Scribe-owned units."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

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
logger = structlog.get_logger(__name__)


class VesselControlPort(Protocol):
    """Future authenticated Vessel actuation seam."""

    def actuate(self, action: OperatorAction, target: OperatorTarget) -> str:
        """Request one typed lifecycle operation through the living Vessel."""
        ...


@dataclass(frozen=True)
class ControlResult:
    """One completed actuation with its authority visible."""

    action: OperatorAction
    target: OperatorTarget
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
        vessel: VesselControlPort | None = None,
    ) -> None:
        """Bind typed discovery, process, and optional Vessel control ports."""
        self._inventory = inventory
        self._targets = targets
        self._runner = runner
        self._systemctl = systemctl_bin
        self._vessel = vessel
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
        """Hold the lifecycle lock across authority selection and physical effect."""
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
            if self._vessel is None:
                message = (
                    "The Vessel is active, but an authenticated lifecycle API is not available; no action was taken."
                )
                logger.warning(
                    "operator_actuation_refused",
                    action=action.value,
                    target=target.value,
                    authority=authority.value,
                    reason=message,
                )
                raise OperatorAuthorityError(message)
            logger.info(
                "operator_actuation_started",
                action=action.value,
                target=target.value,
                authority=authority.value,
                units=(),
            )
            try:
                detail = self._vessel.actuate(action, target)
            except Exception:
                logger.exception(
                    "operator_actuation_failed",
                    action=action.value,
                    target=target.value,
                    authority=authority.value,
                    units=(),
                )
                raise
            logger.info(
                "operator_actuation_completed",
                action=action.value,
                target=target.value,
                authority=authority.value,
                units=(),
            )
            return ControlResult(
                action=action,
                target=target,
                authority=authority,
                detail=detail,
            )

        units = self._targets.direct_actuation_units(action.value, target, catalog=planned)
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
            action=action,
            target=target,
            authority=authority,
            units=units,
            detail=result.stdout.strip(),
        )

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
