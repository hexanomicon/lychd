"""Exact target resolution shared by status-adjacent operator services."""

from __future__ import annotations

from lychd.system.operator.inventory import OperatorInventoryService
from lychd.system.operator.models import (
    ObservationState,
    OperatorTarget,
    OperatorTargetError,
    OwnedUnitCatalog,
)

_VESSEL_UNITS = frozenset({"lychd-vessel.service", "lychd-uncaged-vessel.service"})
_STORAGE_UNITS = frozenset({"lychd-phylactery.service"})


class OperatorTargetResolver:
    """Resolve public selectors only through validated Scribe/config truth."""

    def __init__(self, inventory: OperatorInventoryService) -> None:
        """Bind the shared inventory source."""
        self._inventory = inventory

    def observation_units(
        self,
        target: OperatorTarget,
        *,
        catalog: OwnedUnitCatalog | None = None,
    ) -> tuple[str, ...]:
        """Return exact owned units meaningful for log observation."""
        owned = catalog or self._inventory.owned_units()
        if owned.warning:
            raise OperatorTargetError(owned.warning)
        if target in {OperatorTarget.SYSTEM, OperatorTarget.SERVICES}:
            return tuple(unit.name for unit in owned.units)
        if target in {OperatorTarget.WORKERS, OperatorTarget.RUNS}:
            vessel = owned.select(_VESSEL_UNITS)
            if len(vessel) > 1:
                message = "Both caged and uncaged Vessel units are owned; target is ambiguous."
                raise OperatorTargetError(message)
            return tuple(unit.name for unit in vessel)
        if target is OperatorTarget.STORAGE:
            return tuple(unit.name for unit in owned.select(_STORAGE_UNITS))
        if target is OperatorTarget.ANIMATORS:
            try:
                declared = self._inventory.declared_animators()
            except Exception as exc:
                message = f"Cannot resolve Animator targets: {exc}"
                raise OperatorTargetError(message) from exc
            declared_units = {animator.unit_name for animator in declared if animator.unit_name is not None}
            return tuple(unit.name for unit in owned.units if unit.name in declared_units)
        message = f"Target '{target.value}' has no journal-backed runtime."
        raise OperatorTargetError(message)

    def direct_actuation_units(
        self,
        action: str,
        target: OperatorTarget,
        *,
        catalog: OwnedUnitCatalog,
    ) -> tuple[str, ...]:
        """Return an exact dead-Vessel unit set without narrowing system intent."""
        if catalog.warning:
            raise OperatorTargetError(catalog.warning)
        if target is OperatorTarget.SYSTEM:
            vessels = catalog.select(_VESSEL_UNITS)
            if len(vessels) != 1:
                detail = "not bound" if not vessels else "both caged and uncaged units are owned"
                message = f"System target is {detail}; cannot choose a Vessel unit."
                raise OperatorTargetError(message)
            if action == "start":
                other_non_inactive = tuple(
                    unit
                    for unit in catalog.units
                    if unit.name != vessels[0].name and unit.state is not ObservationState.INACTIVE
                )
                if other_non_inactive:
                    detail = ", ".join(f"{unit.name}={unit.state.value}" for unit in other_non_inactive)
                    message = (
                        "Direct system start can bootstrap the Vessel only when "
                        "every other exact owned unit is inactive; "
                        f"found {detail}."
                    )
                    raise OperatorTargetError(message)
                return (vessels[0].name,)
            if action == "stop":
                return tuple(unit.name for unit in catalog.units)
            message = f"Unsupported direct system action: {action!r}."
            raise OperatorTargetError(message)
        if target is OperatorTarget.STORAGE:
            storage = catalog.select(_STORAGE_UNITS)
            if len(storage) != 1:
                message = "Storage target has no exact owned Phylactery unit."
                raise OperatorTargetError(message)
            return (storage[0].name,)
        if target is OperatorTarget.ANIMATORS:
            message = f"Cannot {action} Animators directly; their lifecycle must pass through the live Orchestrator."
            raise OperatorTargetError(message)
        message = f"Target '{target.value}' is observational or aggregate and cannot be {action}ed directly."
        raise OperatorTargetError(message)

    @staticmethod
    def vessel_units(catalog: OwnedUnitCatalog) -> tuple[str, ...]:
        """Return exact caged/uncaged Vessel candidates."""
        return tuple(unit.name for unit in catalog.select(_VESSEL_UNITS))
