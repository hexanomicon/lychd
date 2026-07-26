"""Immutable models for the staged, resumable ``lychd del`` lifecycle."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from lychd.system.btrfs_identity import BTRFS_FIRST_FREE_OBJECTID
from lychd.system.services.lifecycle.models import DedicatedRootIdentity

if TYPE_CHECKING:
    from lychd.system.operator.retirement import UnitRetirementPlan


class DeletionStage(StrEnum):
    """Ordered safety barriers in one destructive lifecycle."""

    QUIESCE = "quiesce"
    RUNTIME = "runtime"
    STORAGE = "storage"
    UNBIND = "unbind"
    SECRETS = "secrets"
    FILESYSTEM = "filesystem"
    PACKAGE = "package"
    VERIFY = "verify"


DELETION_STAGE_ORDER: tuple[DeletionStage, ...] = (
    DeletionStage.QUIESCE,
    DeletionStage.RUNTIME,
    DeletionStage.STORAGE,
    DeletionStage.UNBIND,
    DeletionStage.SECRETS,
    DeletionStage.FILESYSTEM,
    DeletionStage.PACKAGE,
    DeletionStage.VERIFY,
)


class DeletionDisposition(StrEnum):
    """One deletion action's current, read-only verdict."""

    WOULD_APPLY = "would-apply"
    SATISFIED = "satisfied"
    PRESERVE = "preserve"
    BLOCKED = "blocked"
    REQUIRES_ROOT = "requires-root"


class DeletionActionKind(StrEnum):
    """Physical or evidentiary operation represented by a deletion action."""

    STOP_UNIT = "stop-unit"
    DISABLE_UNIT = "disable-unit"
    VERIFY_UNIT = "verify-unit"
    PRESERVE_RUNTIME = "preserve-runtime"
    UNMOUNT = "unmount"
    DELETE_SUBVOLUME = "delete-subvolume"
    REMOVE_BINDING = "remove-binding"
    RELOAD_MANAGER = "reload-manager"
    PRESERVE_SECRET = "preserve-secret"  # noqa: S105 - resource-kind label, never a credential
    VERIFY_ROOT_AUTHORITY = "verify-root-authority"
    REMOVE_TREE = "remove-tree"
    PRESERVE_PACKAGE = "preserve-package"
    VERIFY = "verify"


class DeletionOutcome(StrEnum):
    """Terminal status of one executor invocation."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class DeletionPaths:
    """Exact dedicated roots and storage target governed by deletion."""

    codex_root: Path
    crypt_root: Path
    cache_root: Path
    postgres_data: Path
    lifecycle_receipt: Path
    source_checkout: Path | None = None

    @classmethod
    def current(cls, *, source_checkout: Path | None = None) -> DeletionPaths:
        """Read one canonical lifecycle-authority snapshot."""
        from lychd.system.services.lifecycle._authority import current_authority

        authority = current_authority()
        return cls(
            codex_root=authority.codex_root,
            crypt_root=authority.crypt_root,
            cache_root=authority.cache_root,
            postgres_data=authority.postgres_data,
            lifecycle_receipt=authority.lifecycle_receipt,
            source_checkout=source_checkout,
        )

    @property
    def dedicated_roots(self) -> tuple[Path, Path, Path]:
        """Return roots in final-removal order, retaining the Codex last."""
        return (self.crypt_root, self.cache_root, self.codex_root)


@dataclass(frozen=True)
class BtrfsSubvolumeIdentity:
    """Attested identity required to resume deletion after unmount."""

    mount_target: Path
    top_level_mount: Path
    source_device: str
    filesystem_uuid: str
    subvolume_uuid: str
    fs_root: str
    source_path: Path
    subvolume_id: int

    def __post_init__(self) -> None:
        """Retain UUID selectors only in their canonical immutable form."""
        object.__setattr__(
            self,
            "filesystem_uuid",
            str(UUID(self.filesystem_uuid)),
        )
        object.__setattr__(
            self,
            "subvolume_uuid",
            str(UUID(self.subvolume_uuid)),
        )

    def fingerprint_payload(self) -> dict[str, object]:
        """Return one deterministic JSON-compatible representation."""
        return {
            "mount_target": str(self.mount_target),
            "top_level_mount": str(self.top_level_mount),
            "source_device": self.source_device,
            "filesystem_uuid": self.filesystem_uuid,
            "subvolume_uuid": self.subvolume_uuid,
            "fs_root": self.fs_root,
            "source_path": str(self.source_path),
            "subvolume_id": self.subvolume_id,
        }


@dataclass(frozen=True)
class PrivilegedHandoff:
    """One exact command LychD may display but must never execute."""

    argv: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class DeletionAction:
    """One deterministic line in a staged deletion plan."""

    stage: DeletionStage
    disposition: DeletionDisposition
    kind: DeletionActionKind
    target: str
    detail: str


@dataclass(frozen=True)
class DeletionPlan:
    """Complete immutable evidence consumed by confirmation and execution."""

    actions: tuple[DeletionAction, ...]
    unit_plan: UnitRetirementPlan | None = None
    storage_identity: BtrfsSubvolumeIdentity | None = None
    root_identities: tuple[DedicatedRootIdentity, ...] = ()
    handoffs: tuple[PrivilegedHandoff, ...] = ()

    def actions_for(self, stage: DeletionStage) -> tuple[DeletionAction, ...]:
        """Return actions belonging to one ordered safety stage."""
        return tuple(action for action in self.actions if action.stage is stage)

    @property
    def first_blocked_stage(self) -> DeletionStage | None:
        """Return the earliest stage containing an unsafe blocker."""
        blocked = {action.stage for action in self.actions if action.disposition is DeletionDisposition.BLOCKED}
        return next((stage for stage in DELETION_STAGE_ORDER if stage in blocked), None)

    @property
    def requires_root(self) -> bool:
        """Return whether a privileged operator handoff is required."""
        return any(action.disposition is DeletionDisposition.REQUIRES_ROOT for action in self.actions)

    @property
    def complete(self) -> bool:
        """Return whether only satisfied or deliberately preserved state remains."""
        pending = {
            DeletionDisposition.WOULD_APPLY,
            DeletionDisposition.BLOCKED,
            DeletionDisposition.REQUIRES_ROOT,
        }
        return all(action.disposition not in pending for action in self.actions)

    @property
    def fingerprint(self) -> str:
        """Hash every approved target and identity for plan/apply drift checks."""
        unit_payload: dict[str, Any] | None = None
        if self.unit_plan is not None:
            unit_payload = {
                "generation": self.unit_plan.generation,
                "owned_units": list(self.unit_plan.owned_units),
                "stop_units": list(self.unit_plan.stop_units),
                "disable_units": list(self.unit_plan.disable_units),
            }
        payload = {
            "actions": [
                {
                    "stage": action.stage.value,
                    "disposition": action.disposition.value,
                    "kind": action.kind.value,
                    "target": action.target,
                    "detail": action.detail,
                }
                for action in self.actions
            ],
            "unit_plan": unit_payload,
            "storage_identity": (
                self.storage_identity.fingerprint_payload() if self.storage_identity is not None else None
            ),
            "root_identities": [
                {
                    "path": str(identity.path),
                    "device": identity.device,
                    "inode": identity.inode,
                }
                for identity in self.root_identities
            ],
            "handoffs": [{"argv": list(handoff.argv), "reason": handoff.reason} for handoff in self.handoffs],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DeletionResult:
    """Explicit result of one possibly partial deletion invocation."""

    outcome: DeletionOutcome
    plan: DeletionPlan
    applied_stages: tuple[DeletionStage, ...] = ()
    detail: str = ""


__all__ = (
    "BTRFS_FIRST_FREE_OBJECTID",
    "DELETION_STAGE_ORDER",
    "BtrfsSubvolumeIdentity",
    "DeletionAction",
    "DeletionActionKind",
    "DeletionDisposition",
    "DeletionOutcome",
    "DeletionPaths",
    "DeletionPlan",
    "DeletionResult",
    "DeletionStage",
    "PrivilegedHandoff",
)
