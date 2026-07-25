"""Exact stop/disable planning for the separately confirmed ``del`` ritual."""

from __future__ import annotations

from dataclasses import dataclass

from lychd.system.operator.inventory import OperatorInventoryService
from lychd.system.operator.models import ObservationState, OperatorError
from lychd.system.operator.process import ProcessInvocationError, ProcessRunner

_SYSTEMCTL_TIMEOUT_SECONDS = 30.0
_ENABLED_STATES = frozenset({"enabled", "enabled-runtime", "linked", "linked-runtime"})


@dataclass(frozen=True)
class UnitRetirementPlan:
    """Exact owned runtime units to stop and disable before deletion."""

    generation: str | None
    owned_units: tuple[str, ...]
    stop_units: tuple[str, ...]
    disable_units: tuple[str, ...]


class OwnedUnitRetirementService:
    """Retire every exact Scribe-owned unit after an outer destructive consent gate.

    This deliberately does not implement confirmation or deletion. It is the
    narrow physical helper that ``del`` may call only after presenting its full
    plan and obtaining destructive confirmation.
    """

    def __init__(
        self,
        *,
        inventory: OperatorInventoryService,
        runner: ProcessRunner,
        systemctl_bin: str | None,
    ) -> None:
        """Bind exact unit discovery and one argv-only process port."""
        self._inventory = inventory
        self._runner = runner
        self._systemctl = systemctl_bin

    def plan(self) -> UnitRetirementPlan:
        """Plan from validated receipt ownership and fail on unknown unit state."""
        catalog = self._inventory.owned_units()
        if catalog.warning:
            raise OperatorError(catalog.warning)
        unknown = tuple(unit.name for unit in catalog.units if unit.state is ObservationState.UNKNOWN)
        if unknown:
            message = f"Cannot prove runtime state for exact owned unit(s): {', '.join(unknown)}"
            raise OperatorError(message)
        unknown_enablement = tuple(unit.name for unit in catalog.units if unit.unit_file_state == "unknown")
        if unknown_enablement:
            message = f"Cannot prove enablement state for exact owned unit(s): {', '.join(unknown_enablement)}"
            raise OperatorError(message)
        return UnitRetirementPlan(
            generation=catalog.generation,
            owned_units=tuple(unit.name for unit in catalog.units),
            stop_units=tuple(unit.name for unit in catalog.units if unit.state is ObservationState.ACTIVE),
            disable_units=tuple(unit.name for unit in catalog.units if unit.unit_file_state in _ENABLED_STATES),
        )

    def execute(self, plan: UnitRetirementPlan) -> None:
        """Execute an unchanged plan, stopping before disabling."""
        current = self.plan()
        if current != plan:
            message = "Owned unit state changed after retirement planning; rerun del."
            raise OperatorError(message)
        if (plan.stop_units or plan.disable_units) and self._systemctl is None:
            message = "systemctl is unavailable; owned units were not retired."
            raise OperatorError(message)
        if plan.stop_units:
            self._run("stop", plan.stop_units)
        if plan.disable_units:
            self._require_unchanged_ownership(plan)
            self._run("disable", plan.disable_units)
        final = self.plan()
        if (
            final.generation != plan.generation
            or final.owned_units != plan.owned_units
            or final.stop_units
            or final.disable_units
        ):
            message = "Owned units remain active or enabled after retirement; deletion must remain blocked."
            raise OperatorError(message)

    def _require_unchanged_ownership(self, plan: UnitRetirementPlan) -> None:
        catalog = self._inventory.owned_units()
        if (
            catalog.warning
            or catalog.generation != plan.generation
            or tuple(unit.name for unit in catalog.units) != plan.owned_units
        ):
            message = "Binding ownership changed while retiring units; deletion must remain blocked."
            raise OperatorError(message)

    def _run(self, action: str, units: tuple[str, ...]) -> None:
        argv = (self._systemctl or "systemctl", "--user", action, *units)
        try:
            result = self._runner.run(argv, timeout_s=_SYSTEMCTL_TIMEOUT_SECONDS)
        except ProcessInvocationError as exc:
            message = f"systemctl {action} failed: {exc}"
            raise OperatorError(message) from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit {result.returncode}"
            message = f"systemctl {action} failed: {detail}"
            raise OperatorError(message)
