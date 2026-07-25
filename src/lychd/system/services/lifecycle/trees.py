"""No-follow, no-cross-mount removal of exact dedicated LychD roots."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from lychd.system.services.lifecycle.models import (
    DedicatedRootIdentity,
    LifecycleError,
)
from lychd.system.services.lifecycle.mount_identity import mount_id_for_fd
from lychd.system.services.lifecycle.paths import (
    lexically_normal,
    path_has_symlink_component,
)

_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
_PATH_FLAGS = getattr(os, "O_PATH", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)

_mount_id_for_fd = mount_id_for_fd


def _same_identity(expected: os.stat_result, observed: os.stat_result) -> bool:
    """Compare every stable entry attribute required before deletion."""
    return (
        expected.st_dev == observed.st_dev
        and expected.st_ino == observed.st_ino
        and expected.st_uid == observed.st_uid
        and stat.S_IFMT(expected.st_mode) == stat.S_IFMT(observed.st_mode)
    )


def _order_final_entry(
    names: tuple[str, ...],
    *,
    final_name: str | None,
    display_path: Path,
) -> tuple[str, ...]:
    """Move one protected authority entry behind every other child."""
    if final_name is None:
        return names
    if final_name not in names:
        msg = f"Protected final entry disappeared before deletion: {display_path / final_name}"
        raise LifecycleError(msg)
    return (*(name for name in names if name != final_name), final_name)


def _open_root_descriptor(
    root: Path,
    *,
    parent_descriptor: int,
    parent_mount_id: int,
    expected_identity: DedicatedRootIdentity,
) -> tuple[int, os.stat_result, int]:
    """Open and revalidate one root relative to its anchored parent."""
    before_open = os.stat(
        root.name,
        dir_fd=parent_descriptor,
        follow_symlinks=False,
    )
    if not stat.S_ISDIR(before_open.st_mode) or before_open.st_uid != os.getuid():
        msg = f"Dedicated root became unsafe before descriptor open: {root}"
        raise LifecycleError(msg)
    descriptor = os.open(
        root.name,
        _DIRECTORY_FLAGS,
        dir_fd=parent_descriptor,
    )
    try:
        metadata = os.fstat(descriptor)
    except BaseException:
        os.close(descriptor)
        raise
    if not _same_identity(before_open, metadata):
        os.close(descriptor)
        msg = f"Dedicated root identity changed before deletion: {root}"
        raise LifecycleError(msg)
    if metadata.st_dev != expected_identity.device or metadata.st_ino != expected_identity.inode:
        os.close(descriptor)
        msg = f"Dedicated root no longer matches attested identity: {root}"
        raise LifecycleError(msg)
    try:
        mount_id = _mount_id_for_fd(descriptor)
    except BaseException:
        os.close(descriptor)
        raise
    if mount_id != parent_mount_id:
        os.close(descriptor)
        msg = f"Dedicated root became a mount boundary before deletion: {root}"
        raise LifecycleError(msg)
    return descriptor, metadata, mount_id


def _verify_root_before_rmdir(
    root: Path,
    *,
    parent_descriptor: int,
    expected: os.stat_result,
    expected_mount_id: int,
) -> None:
    """Reopen the root name and verify it still names the traversed mount."""
    descriptor = os.open(
        root.name,
        _DIRECTORY_FLAGS,
        dir_fd=parent_descriptor,
    )
    try:
        current = os.fstat(descriptor)
        if not _same_identity(expected, current):
            msg = f"Dedicated root identity changed before final removal: {root}"
            raise LifecycleError(msg)
        if _mount_id_for_fd(descriptor) != expected_mount_id:
            msg = f"Dedicated root mount identity changed before final removal: {root}"
            raise LifecycleError(msg)
    finally:
        os.close(descriptor)


@dataclass(frozen=True)
class ManagedTreeInspection:
    """Read-only verdict for one exact dedicated root."""

    root: Path
    exists: bool
    removable: bool
    detail: str


class ManagedTreeService:
    """Inspect and remove only constructor-authorized dedicated roots."""

    def __init__(self, allowed_roots: tuple[Path, ...]) -> None:
        """Bind an exact root allowlist; geography is never inferred later."""
        if len(set(allowed_roots)) != len(allowed_roots):
            msg = "Dedicated deletion roots must be unique."
            raise LifecycleError(msg)
        self._allowed_roots = frozenset(allowed_roots)

    def inspect(  # noqa: PLR0911 - every unsafe filesystem shape has a distinct verdict
        self,
        root: Path,
        *,
        deferred_mounts: frozenset[Path] = frozenset(),
    ) -> ManagedTreeInspection:
        """Prove one root can be traversed without links or mount crossings."""
        unsafe = self._unsafe_root(root)
        if unsafe is not None:
            return ManagedTreeInspection(
                root=root,
                exists=os.path.lexists(root),
                removable=False,
                detail=unsafe,
            )
        if not os.path.lexists(root):
            return ManagedTreeInspection(
                root=root,
                exists=False,
                removable=True,
                detail="dedicated root is already absent",
            )

        try:
            metadata = root.lstat()
        except OSError as exc:
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail=f"cannot inspect root: {exc}",
            )
        if not stat.S_ISDIR(metadata.st_mode):
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail="dedicated root is not a directory",
            )
        if metadata.st_uid != os.getuid():
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail=f"dedicated root is owned by uid {metadata.st_uid}, expected {os.getuid()}",
            )
        try:
            if root.is_mount():
                return ManagedTreeInspection(
                    root=root,
                    exists=True,
                    removable=False,
                    detail="dedicated root is itself a mountpoint",
                )
            blocker, deferred_count = self._scan(
                root,
                expected_device=metadata.st_dev,
                deferred_mounts=deferred_mounts,
            )
        except OSError as exc:
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail=f"cannot inspect tree safely: {exc}",
            )
        if blocker is not None:
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail=blocker,
            )
        return ManagedTreeInspection(
            root=root,
            exists=True,
            removable=True,
            detail=(
                f"safe after {deferred_count} attested mount handoff(s)"
                if deferred_count
                else "dedicated root contains no symlink traversal or mount boundary"
            ),
        )

    def remove(
        self,
        root: Path,
        *,
        expected_identity: DedicatedRootIdentity,
        final_entry: Path | None = None,
    ) -> None:
        """Remove one revalidated root through directory-relative descriptors."""
        if expected_identity.path != root:
            msg = f"Attested dedicated-root identity targets a different path: {expected_identity.path}"
            raise LifecycleError(msg)
        final_name: str | None = None
        if final_entry is not None:
            if final_entry.parent != root or final_entry.name in {"", ".", ".."}:
                msg = f"Final protected entry is not a direct child of {root}: {final_entry}"
                raise LifecycleError(msg)
            final_name = final_entry.name
        inspection = self.inspect(root)
        if not inspection.removable:
            msg = f"Refusing to remove unsafe dedicated root {root}: {inspection.detail}"
            raise LifecycleError(msg)
        if not inspection.exists:
            return

        descriptor = -1
        parent_descriptor = -1
        try:
            parent_descriptor = os.open(root.parent, _DIRECTORY_FLAGS)
            parent_mount_id = _mount_id_for_fd(parent_descriptor)
            descriptor, metadata, mount_id = _open_root_descriptor(
                root,
                parent_descriptor=parent_descriptor,
                parent_mount_id=parent_mount_id,
                expected_identity=expected_identity,
            )
            self._remove_contents(
                descriptor,
                display_path=root,
                expected_device=metadata.st_dev,
                expected_mount_id=mount_id,
                final_name=final_name,
            )
            _verify_root_before_rmdir(
                root,
                parent_descriptor=parent_descriptor,
                expected=metadata,
                expected_mount_id=mount_id,
            )
            os.rmdir(root.name, dir_fd=parent_descriptor)
        except OSError as exc:
            msg = f"Could not remove dedicated root safely: {root}: {exc}"
            raise LifecycleError(msg) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if parent_descriptor >= 0:
                os.close(parent_descriptor)

    def _unsafe_root(self, root: Path) -> str | None:
        if root not in self._allowed_roots:
            return "root is outside the exact deletion allowlist"
        if not lexically_normal(root):
            return "root is not an absolute canonical lexical path"
        if root in {Path("/"), Path.home()}:
            return "root is too broad for recursive deletion"
        if symlink := path_has_symlink_component(root):
            return f"root traverses an untrusted symlink component: {symlink}"
        for other in self._allowed_roots:
            if other == root:
                continue
            if root in other.parents or other in root.parents:
                return f"dedicated roots unexpectedly overlap: {root} and {other}"
        return None

    def _scan(
        self,
        directory: Path,
        *,
        expected_device: int,
        deferred_mounts: frozenset[Path],
    ) -> tuple[str | None, int]:
        deferred_count = 0
        with os.scandir(directory) as entries:
            for entry in entries:
                child = directory / entry.name
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode):
                    if child in deferred_mounts and child.is_mount():
                        deferred_count += 1
                        continue
                    if metadata.st_dev != expected_device:
                        return (
                            f"filesystem boundary exists beneath dedicated root: {child}",
                            deferred_count,
                        )
                    if child.is_mount():
                        return (
                            f"nested mount exists beneath dedicated root: {child}",
                            deferred_count,
                        )
                    blocker, nested_deferred = self._scan(
                        child,
                        expected_device=expected_device,
                        deferred_mounts=deferred_mounts,
                    )
                    deferred_count += nested_deferred
                    if blocker is not None:
                        return blocker, deferred_count
        return None, deferred_count

    def _remove_contents(
        self,
        descriptor: int,
        *,
        display_path: Path,
        expected_device: int,
        expected_mount_id: int,
        final_name: str | None = None,
    ) -> None:
        with os.scandir(descriptor) as entries:
            names = tuple(entry.name for entry in entries)
        names = _order_final_entry(
            names,
            final_name=final_name,
            display_path=display_path,
        )

        for name in names:
            metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            child = display_path / name
            if stat.S_ISDIR(metadata.st_mode):
                if metadata.st_dev != expected_device:
                    msg = f"Mount boundary appeared during dedicated-root deletion: {child}"
                    raise LifecycleError(msg)
                child_descriptor = os.open(
                    name,
                    _DIRECTORY_FLAGS,
                    dir_fd=descriptor,
                )
                try:
                    child_metadata = os.fstat(child_descriptor)
                    if not _same_identity(metadata, child_metadata) or child_metadata.st_dev != expected_device:
                        msg = f"Filesystem identity changed during deletion: {child}"
                        raise LifecycleError(msg)
                    if _mount_id_for_fd(child_descriptor) != expected_mount_id:
                        msg = f"Mount boundary appeared during dedicated-root deletion: {child}"
                        raise LifecycleError(msg)
                    self._remove_contents(
                        child_descriptor,
                        display_path=child,
                        expected_device=expected_device,
                        expected_mount_id=expected_mount_id,
                    )
                    current = os.stat(
                        name,
                        dir_fd=descriptor,
                        follow_symlinks=False,
                    )
                    if not _same_identity(child_metadata, current) or not stat.S_ISDIR(current.st_mode):
                        msg = f"Directory identity changed before final removal: {child}"
                        raise LifecycleError(msg)
                    os.rmdir(name, dir_fd=descriptor)
                finally:
                    os.close(child_descriptor)
            else:
                entry_descriptor = os.open(
                    name,
                    _PATH_FLAGS,
                    dir_fd=descriptor,
                )
                try:
                    opened = os.fstat(entry_descriptor)
                    if not _same_identity(metadata, opened) or opened.st_dev != expected_device:
                        msg = f"Entry identity changed during deletion: {child}"
                        raise LifecycleError(msg)
                    if _mount_id_for_fd(entry_descriptor) != expected_mount_id:
                        msg = f"Mount boundary appeared during dedicated-root deletion: {child}"
                        raise LifecycleError(msg)
                    current = os.stat(
                        name,
                        dir_fd=descriptor,
                        follow_symlinks=False,
                    )
                    if not _same_identity(opened, current):
                        msg = f"Entry identity changed before final removal: {child}"
                        raise LifecycleError(msg)
                    os.unlink(name, dir_fd=descriptor)
                finally:
                    os.close(entry_descriptor)


__all__ = ("ManagedTreeInspection", "ManagedTreeService")
