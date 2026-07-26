"""Identity-pinned flat storage for one Scribe filesystem transaction."""

from __future__ import annotations

import os
import secrets
import stat
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.services.scribe.storage import (
    AttestedPath,
    PinnedPath,
    capture_pinned_path_state,
)


class WorkspaceParentIdentityError(RuntimeError):
    """A pinned site descriptor does not match its approved identity."""


@dataclass
class TransactionWorkspace:
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

    @classmethod
    def create(
        cls,
        parent: Path,
        *,
        expected_parent_identity: tuple[int, int] | None = None,
    ) -> TransactionWorkspace:
        """Verify, then create a private workspace below the pinned site."""
        parent_fd = os.open(
            parent,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            parent_metadata = os.fstat(parent_fd)
        except BaseException:
            os.close(parent_fd)
            raise
        observed_parent_identity = (
            parent_metadata.st_dev,
            parent_metadata.st_ino,
        )
        if expected_parent_identity is not None and observed_parent_identity != expected_parent_identity:
            os.close(parent_fd)
            message = f"Pinned Scribe site does not match its approved identity: {parent}."
            raise WorkspaceParentIdentityError(message)
        path: Path | None = None
        directory_fd = -1
        try:
            path = _allocate_workspace(parent, parent_fd=parent_fd)
            directory_fd = os.open(
                path.name,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
            metadata = os.fstat(directory_fd)
            return cls(
                path=path,
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                parent_device=parent_metadata.st_dev,
                parent_inode=parent_metadata.st_ino,
                device=metadata.st_dev,
                inode=metadata.st_ino,
            )
        except BaseException:
            if directory_fd >= 0:
                os.close(directory_fd)
            # No deletion authority exists until the child descriptor has
            # yielded an identity token. Preserve any unattested residue.
            os.close(parent_fd)
            raise

    def prepare_file(self, content: bytes, *, mode: int, prefix: str) -> AttestedPath:
        """Create, fsync, and attest one exact staged file."""
        for _attempt in range(128):
            name = f"{prefix}{secrets.token_hex(12)}.tmp"
            try:
                descriptor = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    mode,
                    dir_fd=self.directory_fd,
                )
            except FileExistsError:
                continue
            path = self.path / name
            try:
                os.fchmod(descriptor, mode)
                with os.fdopen(descriptor, "wb") as handle:
                    descriptor = -1
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                    metadata = os.fstat(handle.fileno())
                    self.owned_entries[name] = (metadata.st_dev, metadata.st_ino)
            except BaseException:
                if descriptor >= 0:
                    os.close(descriptor)
                with suppress(OSError):
                    os.unlink(name, dir_fd=self.directory_fd)
                raise
            pinned = self.workspace_entry(name)
            state = capture_pinned_path_state(pinned)
            if state is None or state.content != content:
                message = f"Could not attest staged Scribe bytes at {path}."
                raise RuntimeError(message)
            return AttestedPath(path=pinned, state=state)
        message = f"Could not allocate a unique Scribe transaction entry below {self.path}."
        raise FileExistsError(message)

    def reserve(self, *, prefix: str) -> PinnedPath:
        """Return one unpredictable absent name within this workspace."""
        for _attempt in range(128):
            name = f"{prefix}{secrets.token_hex(12)}"
            if name in self.reserved_names:
                continue
            try:
                os.stat(name, dir_fd=self.directory_fd, follow_symlinks=False)
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
        if path.directory_fd != self.directory_fd or path.name not in self.reserved_names | self.owned_entries.keys():
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

    def recovery_path(self) -> Path:
        """Resolve the current Linux path of retained descriptor-pinned evidence."""
        if self.directory_fd < 0:
            return self.path
        try:
            return Path(f"/proc/self/fd/{self.directory_fd}").readlink()
        except OSError:
            return self.path

    def cleanup(self) -> bool:
        """Remove only the pinned flat workspace; preserve any pathname replacement."""
        try:
            if not self._unlink_pinned_entries():
                return False
            if not self._named_path_matches():
                return False
            cleanup_name = f".lychd-cleanup-{secrets.token_hex(12)}"
            rename_noreplace_at(
                self.path.name,
                cleanup_name,
                source_dir_fd=self.parent_fd,
                destination_dir_fd=self.parent_fd,
            )
            if not self._relative_path_matches(cleanup_name):
                self._restore_foreign_cleanup_name(cleanup_name)
                return False
            os.rmdir(cleanup_name, dir_fd=self.parent_fd)
            os.fsync(self.parent_fd)
        except FileNotFoundError:
            return False
        else:
            return True
        finally:
            self.close()

    def close(self) -> None:
        """Close pinned descriptors without mutating recovery evidence."""
        if self.directory_fd >= 0:
            os.close(self.directory_fd)
            self.directory_fd = -1
        if self.parent_fd >= 0:
            os.close(self.parent_fd)
            self.parent_fd = -1

    def _unlink_pinned_entries(self) -> bool:
        """Delete only exact claimed children through the pinned descriptor."""
        os.lseek(self.directory_fd, 0, os.SEEK_SET)
        names = os.listdir(self.directory_fd)  # noqa: PTH208 - descriptor-pinned enumeration
        for name in names:
            expected = self.owned_entries.get(name)
            if expected is None or self._entry_identity(name) != expected:
                return False
        for name in names:
            expected = self.owned_entries[name]
            if not self._quarantine_and_unlink_entry(name, expected=expected):
                return False
        os.fsync(self.directory_fd)
        return True

    def _quarantine_and_unlink_entry(
        self,
        name: str,
        *,
        expected: tuple[int, int],
    ) -> bool:
        """Move one exact child to an unpredictable name before unlinking it."""
        cleanup_name = f".entry-cleanup-{secrets.token_hex(12)}"
        try:
            rename_noreplace_at(
                name,
                cleanup_name,
                source_dir_fd=self.directory_fd,
                destination_dir_fd=self.directory_fd,
            )
        except FileNotFoundError:
            return True
        if self._entry_identity(cleanup_name) != expected:
            self._restore_foreign_entry(cleanup_name, name)
            return False
        os.unlink(cleanup_name, dir_fd=self.directory_fd)
        return True

    def _entry_identity(self, name: str) -> tuple[int, int] | None:
        try:
            metadata = os.stat(name, dir_fd=self.directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if stat.S_ISDIR(metadata.st_mode):
            return None
        return metadata.st_dev, metadata.st_ino

    def _restore_foreign_entry(self, cleanup_name: str, original_name: str) -> None:
        """Restore an entry moved after its claimed identity drifted."""
        try:
            rename_noreplace_at(
                cleanup_name,
                original_name,
                source_dir_fd=self.directory_fd,
                destination_dir_fd=self.directory_fd,
            )
        except OSError:
            return

    def _named_path_matches(self) -> bool:
        """Return whether the public workspace name still identifies the pinned inode."""
        return self._relative_path_matches(self.path.name)

    def _relative_path_matches(self, name: str) -> bool:
        try:
            metadata = os.stat(name, dir_fd=self.parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return stat.S_ISDIR(metadata.st_mode) and metadata.st_dev == self.device and metadata.st_ino == self.inode

    def _restore_foreign_cleanup_name(self, cleanup_name: str) -> None:
        """Put a mistakenly moved replacement back without overwriting another path."""
        try:
            rename_noreplace_at(
                cleanup_name,
                self.path.name,
                source_dir_fd=self.parent_fd,
                destination_dir_fd=self.parent_fd,
            )
        except OSError:
            return


def _allocate_workspace(parent: Path, *, parent_fd: int) -> Path:
    """Allocate one unpredictable directory through the pinned site."""
    for _attempt in range(128):
        path = parent / f".lychd-transaction-{secrets.token_hex(12)}"
        try:
            os.mkdir(path.name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            continue
        return path
    message = f"Could not allocate a unique Scribe workspace below {parent}."
    raise FileExistsError(message)


__all__ = ("TransactionWorkspace", "WorkspaceParentIdentityError")
