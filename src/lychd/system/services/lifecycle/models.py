"""Immutable public models for reversible lifecycle operations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from lychd.system.btrfs_identity import BTRFS_FIRST_FREE_OBJECTID


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
class CreatedDirectory:
    """Immutable identity of one directory creation won by initialization."""

    path: Path
    device: int
    inode: int

    def __post_init__(self) -> None:
        """Reject an identity that cannot safely authorize later cleanup."""
        if self.device < 0 or self.inode <= 0:
            message = "Created directory identity is incomplete."
            raise ValueError(message)


@dataclass(frozen=True)
class CreatedBtrfsSubvolume:
    """Exact init-created subvolume identity eligible for later deletion."""

    path: Path
    device: int
    inode: int
    subvolume_uuid: str
    subvolume_id: int

    def __post_init__(self) -> None:
        """Canonicalize the UUID and reject incomplete filesystem identity."""
        object.__setattr__(
            self,
            "subvolume_uuid",
            str(UUID(self.subvolume_uuid)),
        )
        if self.device < 0 or self.inode <= 0 or self.subvolume_id < BTRFS_FIRST_FREE_OBJECTID:
            message = "Created Btrfs subvolume identity is incomplete."
            raise ValueError(message)


@dataclass(frozen=True)
class CreatedResources:
    """Exact resources one successful initialization call created."""

    directories: tuple[Path, ...] = ()
    directory_identities: tuple[CreatedDirectory, ...] = ()
    files: tuple[Path, ...] = ()
    subvolumes: tuple[CreatedBtrfsSubvolume, ...] = ()

    def __post_init__(self) -> None:
        """Require every immutable directory identity to name a reported path."""
        identity_paths = [identity.path for identity in self.directory_identities]
        if len(set(identity_paths)) != len(identity_paths):
            message = "Created-resource report contains duplicate directory identities."
            raise LifecycleError(message)
        unreported = set(identity_paths) - set(self.directories)
        if unreported:
            message = f"Created directory identity has no matching reported path: {min(unreported)}"
            raise LifecycleError(message)

    @classmethod
    def combine(cls, *resources: CreatedResources) -> CreatedResources:
        """Combine created-resource reports without losing deterministic order."""
        directories = tuple(sorted({path for resource in resources for path in resource.directories}))
        directory_identity_by_path: dict[Path, CreatedDirectory] = {}
        for resource in resources:
            for identity in resource.directory_identities:
                previous = directory_identity_by_path.setdefault(
                    identity.path,
                    identity,
                )
                if previous != identity:
                    message = f"Created-resource reports disagree about directory identity: {identity.path}"
                    raise LifecycleError(message)
        files = tuple(sorted({path for resource in resources for path in resource.files}))
        subvolume_by_path: dict[Path, CreatedBtrfsSubvolume] = {}
        for resource in resources:
            for subvolume in resource.subvolumes:
                previous = subvolume_by_path.setdefault(
                    subvolume.path,
                    subvolume,
                )
                if previous != subvolume:
                    message = f"Created-resource reports disagree about Btrfs subvolume identity: {subvolume.path}"
                    raise LifecycleError(message)
        overlap = set(directories).intersection(subvolume_by_path)
        if overlap:
            message = f"Created resource is both a directory and Btrfs subvolume: {min(overlap)}"
            raise LifecycleError(message)
        return cls(
            directories=directories,
            directory_identities=tuple(directory_identity_by_path[path] for path in sorted(directory_identity_by_path)),
            files=files,
            subvolumes=tuple(subvolume_by_path[path] for path in sorted(subvolume_by_path)),
        )


@dataclass(frozen=True)
class DedicatedRootIdentity:
    """Initialization-attested identity of one recursively removable root."""

    path: Path
    device: int
    inode: int


def created_resources(
    *,
    directories: Iterable[Path] = (),
    directory_identities: Iterable[CreatedDirectory] = (),
    files: Iterable[Path] = (),
    subvolumes: Iterable[CreatedBtrfsSubvolume] = (),
) -> CreatedResources:
    """Build one normalized created-resource report."""
    return CreatedResources(
        directories=tuple(sorted(set(directories))),
        directory_identities=tuple(
            sorted(
                set(directory_identities),
                key=lambda item: item.path,
            )
        ),
        files=tuple(sorted(set(files))),
        subvolumes=tuple(
            sorted(
                set(subvolumes),
                key=lambda item: item.path,
            )
        ),
    )
