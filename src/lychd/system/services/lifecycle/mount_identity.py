"""Linux mount-identity proofs shared by lifecycle authority boundaries."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from lychd.system.services.lifecycle.models import LifecycleError

_FDINFO_ROOT = Path("/proc/self/fdinfo")
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)


def mount_id_for_fd(descriptor: int) -> int:
    """Return the Linux mount ID for one already-open descriptor."""
    if not getattr(os, "O_PATH", 0):
        msg = "Linux mount identity support is unavailable."
        raise LifecycleError(msg)
    try:
        content = (_FDINFO_ROOT / str(descriptor)).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        msg = f"Cannot read Linux mount identity for descriptor {descriptor}."
        raise LifecycleError(msg) from exc
    values = [
        value.strip()
        for line in content.splitlines()
        for key, separator, value in (line.partition(":"),)
        if separator and key == "mnt_id"
    ]
    if len(values) != 1 or not values[0].isascii() or not values[0].isdecimal() or int(values[0]) <= 0:
        msg = f"Linux mount identity is unavailable for descriptor {descriptor}."
        raise LifecycleError(msg)
    return int(values[0])


def directory_identity_on_parent_mount(path: Path) -> os.stat_result:
    """Return a stable directory identity only when it shares its parent's mount."""
    parent_descriptor = -1
    descriptor = -1
    try:
        parent_descriptor = os.open(path.parent, _DIRECTORY_FLAGS)
        before_open = os.stat(
            path.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISDIR(before_open.st_mode):
            msg = f"Lifecycle authority target is not a directory: {path}"
            raise LifecycleError(msg)
        descriptor = os.open(
            path.name,
            _DIRECTORY_FLAGS,
            dir_fd=parent_descriptor,
        )
        observed = os.fstat(descriptor)
        if (
            before_open.st_dev != observed.st_dev
            or before_open.st_ino != observed.st_ino
            or before_open.st_uid != observed.st_uid
            or stat.S_IFMT(before_open.st_mode) != stat.S_IFMT(observed.st_mode)
        ):
            msg = f"Lifecycle authority target changed during inspection: {path}"
            raise LifecycleError(msg)
        parent_mount_id = mount_id_for_fd(parent_descriptor)
        if mount_id_for_fd(descriptor) != parent_mount_id:
            msg = f"Lifecycle authority target is a mount boundary: {path}"
            raise LifecycleError(msg)
    except OSError as exc:
        msg = f"Cannot inspect lifecycle mount identity safely: {path}"
        raise LifecycleError(msg) from exc
    else:
        return observed
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if parent_descriptor >= 0:
            os.close(parent_descriptor)


__all__ = ("directory_identity_on_parent_mount", "mount_id_for_fd")
