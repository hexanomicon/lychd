"""Storage attestation and resumable privileged handoff for ``lychd del``."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol
from uuid import UUID

from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator.process import ProcessInvocationError, ProcessRunner
from lychd.system.operator.storage import MountObservation, MountTreeObservation
from lychd.system.services.lifecycle.deletion_checkpoint import (
    DeletionCheckpointStore,
)
from lychd.system.services.lifecycle.deletion_models import (
    BTRFS_FIRST_FREE_OBJECTID,
    BtrfsSubvolumeIdentity,
    DeletionAction,
    DeletionActionKind,
    DeletionDisposition,
    DeletionPaths,
    DeletionStage,
    PrivilegedHandoff,
)
from lychd.system.services.lifecycle.models import LifecycleError
from lychd.system.services.lifecycle.paths import (
    lexically_normal,
    path_has_symlink_component,
)

_BTRFS_PROBE_TIMEOUT_SECONDS = 5.0
_MAX_BTRFS_OUTPUT_BYTES = 64 * 1024
_AUTO_SUDO = ""
_SUDO_FALLBACKS = (
    Path("/usr/bin/sudo"),
    Path("/bin/sudo"),
    Path("/usr/local/bin/sudo"),
)


class StorageInventoryPort(Protocol):
    """Complete read-only mount inventory beneath dedicated roots."""

    def observe(self, target: Path) -> MountObservation:
        """Return the exact covering filesystem for one path."""
        ...

    def observe_under(self, roots: tuple[Path, ...]) -> MountTreeObservation:
        """Return every exact nested mount or one fail-closed warning."""
        ...


@dataclass(frozen=True)
class ObservedBtrfsSubvolume:
    """Identity returned by a bounded read-only Btrfs probe."""

    uuid: str
    subvolume_id: int


class BtrfsSubvolumeProbe(Protocol):
    """Attest a path as one exact Btrfs subvolume."""

    def inspect(self, path: Path) -> ObservedBtrfsSubvolume | None:
        """Return stable identity, or ``None`` when it cannot be proven."""
        ...


class CommandBtrfsSubvolumeProbe:
    """Attest subvolumes through an injected argv-only process boundary."""

    def __init__(self, runner: ProcessRunner, *, btrfs_bin: str | None) -> None:
        """Bind one already-resolved Btrfs executable."""
        self._runner = runner
        self._btrfs = btrfs_bin

    def inspect(self, path: Path) -> ObservedBtrfsSubvolume | None:  # noqa: PLR0911
        """Parse UUID and subvolume ID from ``btrfs subvolume show``."""
        if self._btrfs is None:
            return None
        try:
            result = self._runner.run(
                (self._btrfs, "subvolume", "show", str(path)),
                timeout_s=_BTRFS_PROBE_TIMEOUT_SECONDS,
            )
        except (OSError, ProcessInvocationError, TimeoutError):
            return None
        if result.returncode != 0 or len(result.stdout.encode(errors="replace")) > _MAX_BTRFS_OUTPUT_BYTES:
            return None
        fields = self._parse_fields(result.stdout)
        raw_uuid = fields.get("uuid")
        raw_subvolume_id = fields.get("subvolume id")
        if raw_uuid is None or raw_subvolume_id is None:
            return None
        try:
            normalized_uuid = str(UUID(raw_uuid))
            subvolume_id = int(raw_subvolume_id)
        except (ValueError, TypeError):
            return None
        if subvolume_id <= 0:
            return None
        return ObservedBtrfsSubvolume(
            uuid=normalized_uuid,
            subvolume_id=subvolume_id,
        )

    @staticmethod
    def _parse_fields(content: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for raw_line in content.splitlines():
            key, separator, value = raw_line.strip().partition(":")
            if separator:
                fields.setdefault(key.casefold(), value.strip())
        return fields


@dataclass(frozen=True)
class StorageDeletionEvidence:
    """Complete storage slice contributed to a deletion plan."""

    actions: tuple[DeletionAction, ...]
    identity: BtrfsSubvolumeIdentity | None = None
    handoffs: tuple[PrivilegedHandoff, ...] = ()


class DeletionStoragePlanner:
    """Classify nested mounts and the one allowed Btrfs handoff."""

    def __init__(
        self,
        *,
        paths: DeletionPaths,
        storage: StorageInventoryPort,
        subvolumes: BtrfsSubvolumeProbe,
        checkpoint: DeletionCheckpointStore,
        umount_bin: str | None,
        btrfs_bin: str | None,
        sudo_bin: str | None = _AUTO_SUDO,
    ) -> None:
        """Bind read-only storage evidence and exact handoff tools."""
        self._paths = paths
        self._storage = storage
        self._subvolumes = subvolumes
        self._checkpoint = checkpoint
        self._umount = umount_bin
        self._btrfs = btrfs_bin
        self._sudo = self._select_sudo(sudo_bin)

    def plan(self) -> StorageDeletionEvidence:
        """Build one zero-effect storage plan."""
        checkpoint, error = self._load_checkpoint()
        if error is not None:
            return StorageDeletionEvidence(actions=(error,))

        inventory = self._storage.observe_under(self._paths.dedicated_roots)
        if inventory.warning:
            return StorageDeletionEvidence(
                actions=(
                    self._action(
                        DeletionDisposition.BLOCKED,
                        DeletionActionKind.VERIFY,
                        "nested mount inventory",
                        inventory.warning,
                    ),
                ),
            )

        exact, unknown = self._partition_mounts(inventory)
        actions = [
            self._action(
                DeletionDisposition.BLOCKED,
                DeletionActionKind.VERIFY,
                str(mount.target),
                "unknown nested mount lies beneath a dedicated deletion root",
            )
            for mount in unknown
        ]
        if len(exact) > 1:
            actions.append(
                self._action(
                    DeletionDisposition.BLOCKED,
                    DeletionActionKind.VERIFY,
                    str(self._paths.postgres_data),
                    "multiple mount records claim the exact Phylactery target",
                )
            )
            return StorageDeletionEvidence(actions=tuple(actions))
        if exact:
            evidence = self._plan_exact_mount(exact[0], checkpoint)
            return StorageDeletionEvidence(
                actions=(*actions, *evidence.actions),
                identity=evidence.identity,
                handoffs=evidence.handoffs,
            )
        if checkpoint is not None:
            evidence = self._plan_pending_checkpoint(checkpoint)
            return StorageDeletionEvidence(
                actions=(*actions, *evidence.actions),
                identity=evidence.identity,
                handoffs=evidence.handoffs,
            )
        actions.append(
            self._action(
                DeletionDisposition.SATISFIED,
                DeletionActionKind.VERIFY,
                str(self._paths.postgres_data),
                "no nested mount or pending subvolume deletion exists",
            )
        )
        return StorageDeletionEvidence(actions=tuple(actions))

    def _load_checkpoint(
        self,
    ) -> tuple[BtrfsSubvolumeIdentity | None, DeletionAction | None]:
        try:
            checkpoint = self._checkpoint.load()
        except LifecycleError as exc:
            return None, self._action(
                DeletionDisposition.BLOCKED,
                DeletionActionKind.VERIFY,
                str(self._checkpoint.path),
                str(exc),
            )
        if checkpoint is not None and checkpoint.mount_target != self._paths.postgres_data:
            return None, self._action(
                DeletionDisposition.BLOCKED,
                DeletionActionKind.VERIFY,
                str(self._checkpoint.path),
                ("pending deletion checkpoint is not bound to the current Phylactery target"),
            )
        return checkpoint, None

    def _partition_mounts(
        self,
        inventory: MountTreeObservation,
    ) -> tuple[tuple[MountObservation, ...], tuple[MountObservation, ...]]:
        exact = tuple(mount for mount in inventory.mounts if mount.target == self._paths.postgres_data)
        unknown = tuple(mount for mount in inventory.mounts if mount.target != self._paths.postgres_data)
        return exact, unknown

    def _plan_exact_mount(
        self,
        mount: MountObservation,
        checkpoint: BtrfsSubvolumeIdentity | None,
    ) -> StorageDeletionEvidence:
        identity, detail = self._attest_exact_phylactery(mount)
        if identity is None:
            return StorageDeletionEvidence(
                actions=(
                    self._action(
                        DeletionDisposition.BLOCKED,
                        DeletionActionKind.VERIFY,
                        str(self._paths.postgres_data),
                        detail,
                    ),
                ),
            )
        if checkpoint is not None and checkpoint != identity:
            return StorageDeletionEvidence(
                actions=(
                    self._action(
                        DeletionDisposition.BLOCKED,
                        DeletionActionKind.VERIFY,
                        str(self._checkpoint.path),
                        "attested mount identity differs from the pending checkpoint",
                    ),
                ),
            )
        return self._root_handoff(identity)

    def _plan_pending_checkpoint(
        self,
        checkpoint: BtrfsSubvolumeIdentity,
    ) -> StorageDeletionEvidence:
        filesystem_error = self._checkpoint_filesystem_error(checkpoint)
        if filesystem_error is not None:
            return StorageDeletionEvidence(
                actions=(
                    self._action(
                        DeletionDisposition.BLOCKED,
                        DeletionActionKind.VERIFY,
                        str(checkpoint.top_level_mount),
                        filesystem_error,
                    ),
                ),
            )
        if not os.path.lexists(checkpoint.source_path):
            return StorageDeletionEvidence(
                actions=(
                    self._action(
                        DeletionDisposition.SATISFIED,
                        DeletionActionKind.DELETE_SUBVOLUME,
                        str(checkpoint.source_path),
                        "checkpointed subvolume is absent",
                    ),
                ),
                identity=checkpoint,
            )
        observed = self._subvolumes.inspect(checkpoint.source_path)
        observed_uuid = self._canonical_subvolume_uuid(observed)
        if observed is None or observed_uuid is None:
            return StorageDeletionEvidence(
                actions=(
                    self._action(
                        DeletionDisposition.BLOCKED,
                        DeletionActionKind.VERIFY,
                        str(checkpoint.source_path),
                        "cannot re-attest the checkpointed Btrfs subvolume identity",
                    ),
                ),
            )
        if observed.subvolume_id != checkpoint.subvolume_id or observed_uuid != checkpoint.subvolume_uuid:
            return StorageDeletionEvidence(
                actions=(
                    self._action(
                        DeletionDisposition.BLOCKED,
                        DeletionActionKind.VERIFY,
                        str(checkpoint.source_path),
                        ("Btrfs reports a different subvolume UUID or ID at the checkpointed path"),
                    ),
                ),
            )
        return self._root_handoff(checkpoint, include_unmount=False)

    def _attest_exact_phylactery(  # noqa: PLR0911 - fail closed on each incomplete identity component
        self,
        mount: MountObservation,
    ) -> tuple[BtrfsSubvolumeIdentity | None, str]:
        source_path = mount.btrfs_source_path
        top_level = mount.top_level_mount
        filesystem_uuid = mount.filesystem_uuid
        subvolume_id = mount.subvolume_id
        if (
            not mount.mounted
            or mount.mount_target != self._paths.postgres_data
            or mount.filesystem != "btrfs"
            or mount.source_device is None
            or filesystem_uuid is None
            or mount.fs_root is None
            or source_path is None
            or top_level is None
            or subvolume_id is None
        ):
            return None, "exact Phylactery mount lacks complete Btrfs identity"
        fs_root = PurePosixPath(mount.fs_root)
        if not fs_root.is_absolute() or fs_root == PurePosixPath("/") or ".." in fs_root.parts:
            return None, "exact Phylactery mount has an unsafe Btrfs fs-root"
        if subvolume_id < BTRFS_FIRST_FREE_OBJECTID:
            return None, "exact Phylactery mount reports a reserved Btrfs subvolume ID"
        try:
            filesystem_uuid = str(UUID(filesystem_uuid))
        except (TypeError, ValueError):
            return None, "exact Phylactery mount reports an invalid filesystem UUID"
        expected_source = f"{mount.source_device}[{mount.fs_root}]"
        subvolume_paths = [option.removeprefix("subvol=") for option in mount.options if option.startswith("subvol=")]
        if mount.source != expected_source or subvolume_paths != [mount.fs_root]:
            return None, "findmnt Btrfs source, fs-root, and subvolume option disagree"
        if (
            not lexically_normal(source_path)
            or source_path in {Path("/"), Path.home()}
            or not lexically_normal(top_level)
            or path_has_symlink_component(source_path) is not None
            or path_has_symlink_component(top_level) is not None
        ):
            return None, "derived Btrfs source path is not safe for an exact handoff"
        observed = self._subvolumes.inspect(self._paths.postgres_data)
        observed_uuid = self._canonical_subvolume_uuid(observed)
        if observed is None or observed_uuid is None:
            return None, "Btrfs could not attest the exact Phylactery subvolume"
        if observed.subvolume_id != subvolume_id:
            return None, "Btrfs and findmnt report different subvolume IDs"
        return (
            BtrfsSubvolumeIdentity(
                mount_target=self._paths.postgres_data,
                top_level_mount=top_level,
                source_device=mount.source_device,
                filesystem_uuid=filesystem_uuid,
                subvolume_uuid=observed_uuid,
                fs_root=mount.fs_root,
                source_path=source_path,
                subvolume_id=subvolume_id,
            ),
            "",
        )

    def _checkpoint_filesystem_error(
        self,
        checkpoint: BtrfsSubvolumeIdentity,
    ) -> str | None:
        """Re-attest the filesystem selector before reissuing an ID deletion."""
        observed = self._storage.observe(checkpoint.top_level_mount)
        if observed.warning is not None:
            return f"cannot re-attest checkpointed Btrfs filesystem: {observed.warning}"
        if (
            not observed.mounted
            or observed.mount_target != checkpoint.top_level_mount
            or observed.filesystem != "btrfs"
            or observed.fs_root != "/"
            or observed.source_device != checkpoint.source_device
            or observed.filesystem_uuid != checkpoint.filesystem_uuid
        ):
            return "top-level mount no longer matches the checkpointed Btrfs filesystem"
        return None

    def _root_handoff(
        self,
        identity: BtrfsSubvolumeIdentity,
        *,
        include_unmount: bool = True,
    ) -> StorageDeletionEvidence:
        if self._sudo is None or self._btrfs is None or (include_unmount and self._umount is None):
            return StorageDeletionEvidence(
                actions=(
                    self._action(
                        DeletionDisposition.BLOCKED,
                        DeletionActionKind.VERIFY,
                        str(identity.mount_target),
                        (
                            "cannot construct an exact privileged handoff "
                            "because trusted sudo or another host tool is unavailable"
                        ),
                    ),
                ),
            )
        actions: list[DeletionAction] = []
        handoffs: list[PrivilegedHandoff] = []
        if include_unmount:
            actions.append(
                self._action(
                    DeletionDisposition.REQUIRES_ROOT,
                    DeletionActionKind.UNMOUNT,
                    str(identity.mount_target),
                    "attested Phylactery mount must be unmounted outside LychD",
                )
            )
            handoffs.append(
                PrivilegedHandoff(
                    argv=(
                        self._sudo,
                        self._umount or "umount",
                        "--",
                        str(identity.mount_target),
                    ),
                    reason="unmount the exact checkpointed Phylactery",
                )
            )
        actions.append(
            self._action(
                DeletionDisposition.REQUIRES_ROOT,
                DeletionActionKind.DELETE_SUBVOLUME,
                str(identity.source_path),
                "attested Btrfs subvolume must be deleted outside LychD",
            )
        )
        handoffs.append(
            PrivilegedHandoff(
                argv=(
                    self._sudo,
                    self._btrfs,
                    "subvolume",
                    "delete",
                    "--subvolid",
                    str(identity.subvolume_id),
                    str(identity.top_level_mount),
                ),
                reason="delete the checkpointed subvolume ID on the exact Btrfs filesystem",
            )
        )
        return StorageDeletionEvidence(
            actions=tuple(actions),
            identity=identity,
            handoffs=tuple(handoffs),
        )

    @staticmethod
    def _canonical_subvolume_uuid(
        observed: ObservedBtrfsSubvolume | None,
    ) -> str | None:
        if observed is None:
            return None
        try:
            return str(UUID(observed.uuid))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _select_sudo(sudo_bin: str | None) -> str | None:
        """Resolve production sudo or accept one injected trusted absolute path."""
        if sudo_bin == _AUTO_SUDO:
            return trusted_host_tool("sudo", fallbacks=_SUDO_FALLBACKS)
        if sudo_bin is None or not Path(sudo_bin).is_absolute():
            return None
        return sudo_bin

    @staticmethod
    def _action(
        disposition: DeletionDisposition,
        kind: DeletionActionKind,
        target: str,
        detail: str,
    ) -> DeletionAction:
        return DeletionAction(
            stage=DeletionStage.STORAGE,
            disposition=disposition,
            kind=kind,
            target=target,
            detail=detail,
        )


__all__ = (
    "BtrfsSubvolumeProbe",
    "CommandBtrfsSubvolumeProbe",
    "DeletionStoragePlanner",
    "ObservedBtrfsSubvolume",
    "StorageDeletionEvidence",
    "StorageInventoryPort",
)
