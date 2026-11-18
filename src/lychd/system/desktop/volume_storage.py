"""Bind a new desktop cluster to an explicitly selected, non-system volume."""

from __future__ import annotations

import ctypes
import json
import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from lychd.system.desktop.private import (
    check_path,
    private_directory,
    publish_file,
    verify_private_directory,
    verify_private_file,
)

STORAGE = "LychD-Postgres"
_DRIVE_FIXED = 3


def diskutil(*arguments: str) -> dict[str, Any]:
    result = subprocess.check_output(["/usr/sbin/diskutil", *arguments])  # noqa: S603
    return plistlib.loads(result)


def powershell(script: str, **parameters: str) -> str:
    executable = Path(os.environ["SYSTEMROOT"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.check_output(  # noqa: S603
        [executable, "-NoProfile", "-NonInteractive", "-Command", "$ErrorActionPreference='Stop';" + script],
        env={**{key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"}, **parameters},
        text=True,
    )
    return result.strip()


def volume_id(root: Path) -> str:
    """Identify the actual mount, failing closed on a startup, profile or redirected volume."""
    check_path(root)
    if root.stat().st_dev == Path.home().stat().st_dev:
        msg = "The desktop account and the database must occupy different volumes."
        raise ValueError(msg)
    if sys.platform == "darwin":
        info = diskutil("info", "-plist", str(root))
        if (
            info.get("FilesystemType") != "apfs"
            or info.get("MountPoint") != str(root)
            or not root.is_mount()
            or root.stat().st_dev in {Path("/").stat().st_dev, Path("/System/Volumes/Data").stat().st_dev}
            or os.statvfs(root).f_flag & os.ST_RDONLY
        ):
            msg = "Select the writable mount point of a dedicated APFS volume."
            raise ValueError(msg)
        return str(UUID(info["VolumeUUID"]))
    if sys.platform != "win32" or not re.fullmatch(r"[a-zA-Z]:\\", str(root)):
        msg = "Select the drive root of a dedicated local NTFS volume."
        raise ValueError(msg)
    if root.drive.casefold() == Path(os.environ["SYSTEMROOT"]).drive.casefold():
        msg = "The Windows startup volume cannot be selected."
        raise ValueError(msg)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    name = ctypes.create_unicode_buffer(64)
    filesystem = ctypes.create_unicode_buffer(32)
    drive = str(root)
    if (
        kernel.GetDriveTypeW(drive) != _DRIVE_FIXED
        or not kernel.GetVolumeNameForVolumeMountPointW(drive, name, len(name))
        or not kernel.GetVolumeInformationW(drive, None, 0, None, None, None, filesystem, len(filesystem))
        or filesystem.value != "NTFS"
    ):
        msg = "Expected a fixed NTFS drive with a stable volume GUID."
        raise ValueError(msg)
    match = re.fullmatch(r"\\\\\?\\Volume\{([0-9a-f-]+)\}\\", name.value, re.IGNORECASE)
    if not match:
        msg = "Windows did not return an exact volume GUID."
        raise ValueError(msg)
    return str(UUID(match[1]))


def authority(default: Path) -> Path:
    return default.parent / "volume-authority"


def read_record(path: Path) -> dict[str, str]:
    from pydantic import TypeAdapter

    verify_private_directory(path.parent)
    verify_private_file(path)
    return TypeAdapter(dict[str, str]).validate_json(path.read_bytes(), strict=True)


def write_record(path: Path, **values: str) -> None:
    publish_file(path, json.dumps(values, sort_keys=True).encode("utf-8"))


def dedicated_contents(root: Path) -> None:
    system_entries = {
        "$RECYCLE.BIN",
        "System Volume Information",
        ".Spotlight-V100",
        ".fseventsd",
        ".Trashes",
        ".TemporaryItems",
        ".DocumentRevisions-V100",
        ".metadata_never_index",
        ".DS_Store",
        STORAGE,
    }
    if any(entry.name not in system_entries for entry in root.iterdir()):
        msg = "The volume contains files outside the dedicated database storage directory."
        raise ValueError(msg)


def selected(default: Path) -> tuple[Path, str]:
    record = read_record(authority(default) / "storage.json")
    root = Path(record["root"])
    if volume_id(root) != record["volume"] or root.stat().st_dev == default.parent.stat().st_dev:
        msg = "The registered database volume is absent or has been replaced."
        raise ValueError(msg)
    directory = root / STORAGE
    verify_private_directory(directory)
    if read_record(directory / ".storage-id") != {"storage": record["storage"]}:
        msg = "The dedicated database storage marker differs from registration."
        raise ValueError(msg)
    return root, record["volume"]


def cluster_path(default: Path) -> Path:
    """Resolve the recorded storage binding on each native command requiring PGDATA."""
    selection = authority(default) / "storage.json"
    check_path(selection)
    if not selection.parent.exists():
        return default
    root, _ = selected(default)
    return root / STORAGE / default.name


def select_storage(default: Path, root: Path) -> Path:
    selection = authority(default) / "storage.json"
    check_path(default)
    if default.exists() or selection.exists():
        msg = "Select storage before desktop install. Existing clusters require a separate migration."
        raise ValueError(msg)
    identity = volume_id(root)
    dedicated_contents(root)
    if root.stat().st_dev == default.parent.stat().st_dev:
        msg = "Storage selection and snapshot authority must occupy different volumes."
        raise ValueError(msg)
    directory = root / STORAGE
    check_path(directory)
    directory.mkdir(mode=0o700)
    private_directory(directory)
    private_directory(selection.parent)
    identifier = str(uuid4())
    write_record(directory / ".storage-id", storage=identifier)
    write_record(selection, root=str(root), volume=identity, storage=identifier)
    return directory / default.name
