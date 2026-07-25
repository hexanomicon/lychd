"""Immutable public models for reversible lifecycle operations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class LifecycleError(RuntimeError):
    """A lifecycle plan or ownership receipt is unsafe."""


class LifecycleDisposition(StrEnum):
    """One deterministic plan-line classification."""

    WOULD_CREATE = "WOULD CREATE"
    WOULD_REMOVE = "WOULD REMOVE"
    PRESERVE = "PRESERVE"
    BLOCKED = "BLOCKED"


class LifecycleResourceKind(StrEnum):
    """Physical resource types represented by lifecycle plans."""

    DIRECTORY = "directory"
    FILE = "file"
    MOUNT = "mount"
    RECEIPT = "receipt"
    UNIT = "unit"


@dataclass(frozen=True)
class LifecycleAction:
    """One human-readable, deterministic lifecycle plan line."""

    disposition: LifecycleDisposition
    kind: LifecycleResourceKind
    target: str
    detail: str


@dataclass(frozen=True)
class LifecyclePlan:
    """A complete immutable plan assembled before any host mutation."""

    actions: tuple[LifecycleAction, ...] = ()

    @classmethod
    def combine(cls, *plans: LifecyclePlan) -> LifecyclePlan:
        """Combine plans, removing identical lines and sorting deterministically."""
        unique = {
            (action.disposition, action.kind, action.target, action.detail): action
            for plan in plans
            for action in plan.actions
        }
        actions = tuple(
            sorted(
                unique.values(),
                key=lambda action: (
                    list(LifecycleDisposition).index(action.disposition),
                    action.target,
                    action.kind,
                    action.detail,
                ),
            )
        )
        return cls(actions=actions)

    @property
    def blockers(self) -> tuple[LifecycleAction, ...]:
        """Return every action that prevents safe execution."""
        return tuple(action for action in self.actions if action.disposition is LifecycleDisposition.BLOCKED)

    @property
    def mutates(self) -> bool:
        """Return whether the plan contains a create or removal effect."""
        return any(
            action.disposition in {LifecycleDisposition.WOULD_CREATE, LifecycleDisposition.WOULD_REMOVE}
            for action in self.actions
        )

    @property
    def removal_paths(self) -> frozenset[Path]:
        """Return absolute filesystem paths this plan will remove."""
        filesystem_kinds = {
            LifecycleResourceKind.DIRECTORY,
            LifecycleResourceKind.FILE,
            LifecycleResourceKind.RECEIPT,
        }
        return frozenset(
            Path(action.target)
            for action in self.actions
            if action.disposition is LifecycleDisposition.WOULD_REMOVE
            and action.kind in filesystem_kinds
            and Path(action.target).is_absolute()
        )

    def require_executable(self) -> None:
        """Fail with a stable summary when any blocker exists."""
        if not self.blockers:
            return
        detail = "; ".join(f"{action.target}: {action.detail}" for action in self.blockers)
        msg = f"Lifecycle plan is blocked: {detail}"
        raise LifecycleError(msg)


@dataclass(frozen=True)
class CreatedResources:
    """Exact resources one successful initialization call created."""

    directories: tuple[Path, ...] = ()
    files: tuple[Path, ...] = ()

    @classmethod
    def combine(cls, *resources: CreatedResources) -> CreatedResources:
        """Combine created-resource reports without losing deterministic order."""
        directories = tuple(sorted({path for resource in resources for path in resource.directories}))
        files = tuple(sorted({path for resource in resources for path in resource.files}))
        return cls(directories=directories, files=files)


@dataclass(frozen=True)
class DedicatedRootIdentity:
    """Initialization-attested identity of one recursively removable root."""

    path: Path
    device: int
    inode: int


def created_resources(*, directories: Iterable[Path] = (), files: Iterable[Path] = ()) -> CreatedResources:
    """Build one normalized created-resource report."""
    return CreatedResources(
        directories=tuple(sorted(set(directories))),
        files=tuple(sorted(set(files))),
    )
