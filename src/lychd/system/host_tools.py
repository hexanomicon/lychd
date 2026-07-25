"""Trusted resolution of fixed host executables used at authority boundaries."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

_SYSTEM_FALLBACKS: dict[str, tuple[Path, ...]] = {
    "btrfs": (
        Path("/usr/sbin/btrfs"),
        Path("/usr/bin/btrfs"),
        Path("/sbin/btrfs"),
        Path("/bin/btrfs"),
    ),
    "chattr": (
        Path("/usr/bin/chattr"),
        Path("/bin/chattr"),
        Path("/usr/sbin/chattr"),
        Path("/sbin/chattr"),
    ),
    "findmnt": (Path("/usr/bin/findmnt"), Path("/bin/findmnt")),
    "getenforce": (
        Path("/usr/sbin/getenforce"),
        Path("/usr/bin/getenforce"),
        Path("/sbin/getenforce"),
        Path("/bin/getenforce"),
    ),
    "journalctl": (Path("/usr/bin/journalctl"), Path("/bin/journalctl")),
    "lsattr": (
        Path("/usr/bin/lsattr"),
        Path("/bin/lsattr"),
        Path("/usr/sbin/lsattr"),
        Path("/sbin/lsattr"),
    ),
    "podman": (Path("/usr/bin/podman"), Path("/bin/podman")),
    "podman-user-generator": (
        Path("/usr/lib/systemd/user-generators/podman-user-generator"),
        Path("/usr/lib/systemd/user-generators/podman-system-generator"),
        Path("/usr/local/lib/systemd/user-generators/podman-user-generator"),
        Path("/usr/local/lib/systemd/user-generators/podman-system-generator"),
    ),
    "systemctl": (Path("/usr/bin/systemctl"), Path("/bin/systemctl")),
    "umount": (Path("/usr/bin/umount"), Path("/bin/umount")),
}


def trusted_host_tool(
    name: str,
    *,
    fallbacks: tuple[Path, ...] | None = None,
) -> str | None:
    """Resolve an executable whose complete path remains root-controlled."""
    discovered = shutil.which(name)
    candidates = (
        *((Path(discovered),) if discovered is not None else ()),
        *(fallbacks if fallbacks is not None else _SYSTEM_FALLBACKS.get(name, ())),
    )
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
            metadata = resolved.stat()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if not stat.S_ISREG(metadata.st_mode) or not os.access(resolved, os.X_OK):
            continue
        if not _root_controlled(resolved, metadata=metadata):
            continue
        if any(not _root_controlled(parent) for parent in resolved.parents):
            continue
        return str(resolved)
    return None


def _root_controlled(
    path: Path,
    *,
    metadata: os.stat_result | None = None,
) -> bool:
    """Reject owner, mode, or ACL authority available to the invoking user."""
    try:
        observed = path.stat() if metadata is None else metadata
    except OSError:
        return False
    return (
        observed.st_uid == 0 and observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH) == 0 and not os.access(path, os.W_OK)
    )


__all__ = ("trusted_host_tool",)
