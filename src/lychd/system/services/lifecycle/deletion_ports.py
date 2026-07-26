"""Effect and evidence ports for the staged deletion lifecycle."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from lychd.system.btrfs_identity import BtrfsSubvolumeObservation
from lychd.system.operator.retirement import UnitRetirementPlan
from lychd.system.operator.storage import MountObservation, MountTreeObservation
from lychd.system.services.lifecycle.models import (
    CreatedBtrfsSubvolume,
    DedicatedRootIdentity,
    LifecyclePlan,
)
from lychd.system.services.scribe.models import OwnedBindings

ObservedBtrfsSubvolume = BtrfsSubvolumeObservation


class UnitRetirementPort(Protocol):
    """Exact Scribe-owned unit retirement supplied by the operator layer."""

    def plan(self) -> UnitRetirementPlan:
        """Return one immutable stop/disable plan."""
        ...

    def execute(self, plan: UnitRetirementPlan) -> None:
        """Apply one unchanged retirement plan."""
        ...


class ScribeOwnershipPort(Protocol):
    """Read-only Scribe authority needed by the deletion planner."""

    @property
    def ownership_path(self) -> Path:
        """Return the exact ownership receipt path."""
        ...

    def inspect_owned_bindings(self) -> OwnedBindings:
        """Return exact generated binding and runtime-unit ownership."""
        ...


class BindingCleanupPort(Protocol):
    """Existing exact Scribe binding cleanup transaction."""

    def plan_destroy(self) -> LifecyclePlan:
        """Verify exact units are inert and bindings remain unchanged."""
        ...

    def destroy(self) -> None:
        """Remove exact bindings and reload the user manager."""
        ...


class DedicatedRootAuthorityPort(Protocol):
    """Initialization-issued authority for recursive dedicated-root removal."""

    path: Path

    def require_dedicated_root_identities(
        self,
        expected_roots: tuple[Path, ...],
    ) -> tuple[DedicatedRootIdentity, ...]:
        """Return exact live identities or fail closed."""
        ...

    def created_subvolume(
        self,
        path: Path,
    ) -> CreatedBtrfsSubvolume | None:
        """Return exact init-created storage authority without adopting it."""
        ...


class StorageInventoryPort(Protocol):
    """Complete read-only mount inventory beneath dedicated roots."""

    def observe(self, target: Path) -> MountObservation:
        """Return the exact covering filesystem for one path."""
        ...

    def observe_under(self, roots: tuple[Path, ...]) -> MountTreeObservation:
        """Return every exact nested mount or one fail-closed warning."""
        ...


class BtrfsSubvolumeProbe(Protocol):
    """Attest a path as one exact Btrfs subvolume."""

    def inspect(self, path: Path) -> ObservedBtrfsSubvolume | None:
        """Return stable identity, or ``None`` when it cannot be proven."""
        ...


class InitializedSubvolumeAuthorityPort(Protocol):
    """Initialization-issued identity for an unmounted Phylactery subvolume."""

    def created_subvolume(
        self,
        path: Path,
    ) -> CreatedBtrfsSubvolume | None:
        """Return exact creation authority or ``None`` without adopting state."""
        ...


__all__ = (
    "BindingCleanupPort",
    "BtrfsSubvolumeProbe",
    "DedicatedRootAuthorityPort",
    "InitializedSubvolumeAuthorityPort",
    "ObservedBtrfsSubvolume",
    "ScribeOwnershipPort",
    "StorageInventoryPort",
    "UnitRetirementPort",
)
