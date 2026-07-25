"""Typed public models for the compact operator surface."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class OperatorTarget(StrEnum):
    """Stable selectors shared by status, logs, and lifecycle commands."""

    SYSTEM = "system"
    SERVICES = "services"
    WORKERS = "workers"
    ANIMATORS = "animators"
    STORAGE = "storage"
    CONFIG = "config"
    BINDINGS = "bindings"
    RUNS = "runs"


class ObservationState(StrEnum):
    """One deliberately small vocabulary for observed operator truth."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class SystemSummary(StrEnum):
    """Whole-installation projection without pretending activity is readiness."""

    NOT_INITIALIZED = "not-initialized"
    UNBOUND = "unbound"
    STOPPED = "stopped"
    RUNNING = "running"
    DEGRADED = "degraded"


class OperatorAction(StrEnum):
    """Physical lifecycle operations exposed by the Phase-1 surface."""

    START = "start"
    STOP = "stop"


class VesselAuthority(StrEnum):
    """Which control plane may currently mutate owned runtime units."""

    VESSEL = "vessel"
    DIRECT = "direct"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InventoryItem:
    """One human- and machine-readable observation."""

    category: OperatorTarget
    name: str
    state: ObservationState
    detail: str = ""
    attributes: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible projection."""
        return {
            "category": self.category.value,
            "name": self.name,
            "state": self.state.value,
            "detail": self.detail,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class InventoryReport:
    """One complete, immutable status response."""

    selector: OperatorTarget
    summary: SystemSummary
    items: tuple[InventoryItem, ...] = ()
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible projection."""
        return {
            "selector": self.selector.value,
            "summary": self.summary.value,
            "items": [item.as_dict() for item in self.items],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class OwnedUnit:
    """One exact runtime unit derived from the Scribe authority receipt."""

    name: str
    sources: tuple[str, ...]
    state: ObservationState = ObservationState.UNKNOWN
    unit_file_state: str = "unknown"
    detail: str = ""


@dataclass(frozen=True)
class OwnedUnitCatalog:
    """Exact binding ownership and the observed state of its runtime units."""

    receipt_present: bool
    units: tuple[OwnedUnit, ...] = ()
    generation: str | None = None
    warning: str | None = None

    def unit(self, name: str) -> OwnedUnit | None:
        """Return an exact owned unit without fuzzy matching."""
        return next((unit for unit in self.units if unit.name == name), None)

    def select(self, names: set[str] | frozenset[str]) -> tuple[OwnedUnit, ...]:
        """Return only exact owned unit names from a caller-owned allowlist."""
        return tuple(unit for unit in self.units if unit.name in names)


@dataclass(frozen=True)
class DeclaredAnimator:
    """One typed Animator declaration projected for operator inspection."""

    name: str
    kind: str
    runtime: str
    unit_name: str | None = None


class OperatorError(RuntimeError):
    """Base failure for operator discovery or actuation."""


class OperatorAuthorityError(OperatorError):
    """An operation cannot prove which control plane currently owns mutation."""


class OperatorTargetError(OperatorError):
    """A selector has no safe or meaningful operation for this command."""
