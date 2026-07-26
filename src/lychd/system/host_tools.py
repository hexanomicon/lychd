"""Trusted resolution of fixed host executables used at authority boundaries."""

from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from lychd.system.path_safety import filesystem_is_read_only

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
    "systemctl": (Path("/usr/bin/systemctl"), Path("/bin/systemctl")),
    "umount": (Path("/usr/bin/umount"), Path("/bin/umount")),
}

_SYSTEMD_USER_GENERATOR_PATHS: Final[tuple[Path, ...]] = (
    Path("/run/systemd/user-generators"),
    Path("/etc/systemd/user-generators"),
    Path("/usr/local/lib/systemd/user-generators"),
    Path("/usr/lib/systemd/user-generators"),
)
_PODMAN_USER_GENERATOR_NAMES: Final[tuple[str, ...]] = ("podman-user-generator",)


@dataclass(frozen=True, slots=True)
class TrustedExecutable:
    """Resolved host executable plus the kernel identity that was attested."""

    path: str
    device: int
    inode: int

    def __post_init__(self) -> None:
        """Reject relative paths and incomplete identity evidence."""
        if not Path(self.path).is_absolute() or self.device < 0 or self.inode <= 0:
            message = f"Trusted executable identity is incomplete: {self.path}"
            raise ValueError(message)


def trusted_executable(
    name: str,
    *,
    fallbacks: tuple[Path, ...] | None = None,
) -> TrustedExecutable | None:
    """Resolve and attest an executable whose complete path is root-controlled."""
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
        return TrustedExecutable(
            path=str(resolved),
            device=metadata.st_dev,
            inode=metadata.st_ino,
        )
    return None


def trusted_host_tool(
    name: str,
    *,
    fallbacks: tuple[Path, ...] | None = None,
) -> str | None:
    """Return the path projection of one freshly attested host executable."""
    executable = trusted_executable(name, fallbacks=fallbacks)
    return executable.path if executable is not None else None


def trusted_podman_user_generator_executable(
    *,
    search_paths: tuple[Path, ...] = _SYSTEMD_USER_GENERATOR_PATHS,
    names: tuple[str, ...] = _PODMAN_USER_GENERATOR_NAMES,
) -> TrustedExecutable | None:
    """Resolve and attest the effective root-controlled Podman user generator.

    Systemd searches generator directories in priority order. The first entry
    with a given filename wins; an empty file, a non-executable entry, or a
    symlink to ``/dev/null`` masks lower-priority copies.
    """
    for name in names:
        for directory in search_paths:
            candidate = directory / name
            if os.path.lexists(candidate):
                return _trusted_generator_target(candidate)
    return None


def trusted_podman_user_generator(
    *,
    search_paths: tuple[Path, ...] = _SYSTEMD_USER_GENERATOR_PATHS,
    names: tuple[str, ...] = _PODMAN_USER_GENERATOR_NAMES,
) -> str | None:
    """Return the path projection of the effective attested user generator."""
    executable = trusted_podman_user_generator_executable(
        search_paths=search_paths,
        names=names,
    )
    return executable.path if executable is not None else None


def _trusted_generator_target(candidate: Path) -> TrustedExecutable | None:
    """Validate the first effective generator entry without falling through."""
    try:
        metadata = candidate.lstat()
    except OSError:
        return None
    unsafe_entry = any(not _root_controlled(parent) for parent in candidate.parents) or (
        stat.S_ISREG(metadata.st_mode) and metadata.st_size == 0
    )
    if unsafe_entry:
        return None
    try:
        resolved = candidate.resolve(strict=True)
        resolved_metadata = resolved.stat()
    except OSError:
        return None
    valid = (
        resolved != Path("/dev/null")
        and stat.S_ISREG(resolved_metadata.st_mode)
        and os.access(resolved, os.X_OK)
        and _root_controlled(resolved, metadata=resolved_metadata)
        and all(_root_controlled(parent) for parent in resolved.parents)
    )
    if not valid:
        return None
    return TrustedExecutable(
        path=str(resolved),
        device=resolved_metadata.st_dev,
        inode=resolved_metadata.st_ino,
    )


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
        (observed.st_uid == 0 or filesystem_is_read_only(path))
        and observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH) == 0
        and not os.access(path, os.W_OK)
    )


__all__ = (
    "TrustedExecutable",
    "trusted_executable",
    "trusted_host_tool",
    "trusted_podman_user_generator",
    "trusted_podman_user_generator_executable",
)
