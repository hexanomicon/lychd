"""Stable facade for one descriptor-pinned Scribe workspace."""

from __future__ import annotations

import os
import secrets
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from lychd.system.descriptor_settlement import DescriptorSet
from lychd.system.services.scribe.storage import PinnedPath
from lychd.system.services.scribe.workspace_creation import (
    allocate_workspace,
    raise_workspace_creation_failure,
)
from lychd.system.services.scribe.workspace_settlement import (
    WorkspaceParentIdentityError,
    WorkspaceSettlementError,
    WorkspaceSettlementMixin,
)
from lychd.system.services.scribe.workspace_staging import (
    WorkspaceStagingMixin,
)


@dataclass
class TransactionWorkspace(
    WorkspaceSettlementMixin,
    WorkspaceStagingMixin,
):
    """One flat, same-filesystem workspace pinned to its original directory."""

    path: Path
    parent_fd: int
    directory_fd: int
    parent_device: int
    parent_inode: int
    device: int
    inode: int
    reserved_names: set[str] = field(default_factory=set)
    owned_entries: dict[str, tuple[int, int]] = field(default_factory=dict)
    recovery_names: set[str] = field(default_factory=set)

    @classmethod
    def create(
        cls,
        parent: Path,
        *,
        expected_parent_identity: tuple[int, int] | None = None,
    ) -> Self:
        """Verify, then create a private workspace below the pinned site."""
        descriptors = DescriptorSet()
        parent_fd = descriptors.add(
            os.open(
                parent,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            )
        )
        path: Path | None = None
        outcome = "unchanged"
        verified = True
        try:
            parent_metadata = os.fstat(parent_fd)
            observed_parent_identity = (
                parent_metadata.st_dev,
                parent_metadata.st_ino,
            )
            if expected_parent_identity is not None and observed_parent_identity != expected_parent_identity:
                message = f"Pinned Scribe site does not match its approved identity: {parent}."
                raise WorkspaceParentIdentityError(  # noqa: TRY301 - transaction primary
                    message
                )
            outcome = "recovery"
            verified = False
            path = allocate_workspace(parent, parent_fd=parent_fd)
            outcome = "workspace_retained"
            verified = True
            directory_fd = descriptors.add(
                os.open(
                    path.name,
                    os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=parent_fd,
                )
            )
            metadata = os.fstat(directory_fd)
            workspace = cls(
                path=path,
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                parent_device=parent_metadata.st_dev,
                parent_inode=parent_metadata.st_ino,
                device=metadata.st_dev,
                inode=metadata.st_ino,
            )
            descriptors.transfer(parent_fd)
            descriptors.transfer(directory_fd)
        except BaseException as primary:  # noqa: BLE001 - settle every acquired peer
            raise_workspace_creation_failure(
                parent=parent,
                path=path,
                primary=primary,
                descriptors=descriptors,
                outcome=outcome,
                verified=verified,
            )
        return workspace

    def reserve(self, *, prefix: str) -> PinnedPath:
        """Return one unpredictable absent name within this workspace."""
        for _attempt in range(128):
            name = f"{prefix}{secrets.token_hex(12)}"
            if name in self.reserved_names:
                continue
            try:
                os.stat(
                    name,
                    dir_fd=self.directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                self.reserved_names.add(name)
                return self.workspace_entry(name)
        message = f"Could not reserve a unique Scribe quarantine below {self.path}."
        raise FileExistsError(message)

    def parent_entry(self, name: str) -> PinnedPath:
        """Address one binding filename through the pinned site descriptor."""
        return PinnedPath(
            directory_fd=self.parent_fd,
            name=name,
            display=self.path.parent / name,
        )

    def workspace_entry(self, name: str) -> PinnedPath:
        """Address one transaction filename through the pinned workspace."""
        return PinnedPath(
            directory_fd=self.directory_fd,
            name=name,
            display=self.path / name,
        )

    def claim(self, path: PinnedPath, *, device: int, inode: int) -> None:
        """Record the exact identity now held by one workspace entry."""
        known_names = self.reserved_names | self.owned_entries.keys()
        if path.directory_fd != self.directory_fd or path.name not in known_names:
            message = f"Cannot claim a path outside this Scribe workspace: {path}."
            raise ValueError(message)
        self.owned_entries[path.name] = (device, inode)

    def forget(self, path: PinnedPath) -> None:
        """Forget an entry proved absent after rollback."""
        if path.directory_fd != self.directory_fd:
            message = f"Cannot forget a path outside this Scribe workspace: {path}."
            raise ValueError(message)
        self.owned_entries.pop(path.name, None)

    def namespace_drift_paths(self) -> frozenset[Path]:
        """Return public names that no longer identify the pinned directories."""
        drifted: set[Path] = set()
        try:
            parent_metadata = self.path.parent.lstat()
        except OSError:
            drifted.add(self.path.parent)
        else:
            if (
                not stat.S_ISDIR(parent_metadata.st_mode)
                or parent_metadata.st_dev != self.parent_device
                or parent_metadata.st_ino != self.parent_inode
            ):
                drifted.add(self.path.parent)
        if not self._named_path_matches():
            drifted.add(self.path)
        return frozenset(drifted)

    def fsync_parent(self) -> None:
        """Persist binding-site namespace changes through the pinned descriptor."""
        os.fsync(self.parent_fd)

    def recovery_path(self, *, descriptor: int | None = None) -> Path:
        """Resolve the current Linux path of retained descriptor-pinned evidence."""
        directory_fd = self.directory_fd if descriptor is None else descriptor
        if directory_fd < 0:
            return self.path
        try:
            return Path(f"/proc/self/fd/{directory_fd}").readlink()
        except OSError:
            return self.path


# Stable exception provenance for callers importing the historical facade.
WorkspaceParentIdentityError.__module__ = __name__
WorkspaceSettlementError.__module__ = __name__

__all__ = (
    "TransactionWorkspace",
    "WorkspaceParentIdentityError",
    "WorkspaceSettlementError",
)
