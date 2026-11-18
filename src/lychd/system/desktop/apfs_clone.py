"""Unprivileged macOS cold PostgreSQL copy using APFS copy-on-write for each regular file."""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from typing import TYPE_CHECKING

from lychd.system.desktop.private import publish_file, verify_private_directory
from lychd.system.desktop.volume_cluster import active_id, cold_control, inventory

if TYPE_CHECKING:
    from collections.abc import Callable

    from lychd.config.settings import DatabaseSettings


def clone_database(
    source: Path,
    destination: Path,
    db: DatabaseSettings,
    control: str,
    stop: Callable[[], None],
    start: Callable[[], None],
) -> Path:
    """Restart the original before hashing the inactive copy and publishing its receipt."""
    if sys.platform != "darwin":
        msg = "APFS cloning requires a native macOS host."
        raise ValueError(msg)
    verify_private_directory(destination)
    if (
        destination.is_relative_to(source)
        or source.is_relative_to(destination)
        or source.stat().st_dev != destination.stat().st_dev
    ):
        msg = "Choose a private sibling location on the same APFS volume as the dedicated cluster."
        raise ValueError(msg)
    ident = active_id(source, db)
    lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    lib.clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    lib.clonefile.restype = ctypes.c_int

    def clone_file(original: str, copy: str) -> str:
        if lib.clonefile(os.fsencode(original), os.fsencode(copy), 1):  # CLONE_NOFOLLOW
            errno = ctypes.get_errno()
            raise OSError(errno, os.strerror(errno), original)
        return copy

    beginning = monotonic()
    before = shutil.disk_usage(destination).free
    with TemporaryDirectory(prefix=".apfs-cut-", dir=destination) as stage:
        private = Path(stage)
        cluster = private / "cluster"
        stop()
        try:
            inventory(source, digest=False)
            cold_control(source, control, ident)
            shutil.copytree(source, cluster, symlinks=True, copy_function=clone_file)
            cold_control(cluster, control, ident)
        finally:
            start()
        pause = monotonic() - beginning
        files = inventory(cluster, digest=True)
        record = {
            "method": "apfs-file-clone-v1",
            "postgres_major": 18,
            "system_identifier": ident,
            "files": files,
            "pause_seconds": pause,
            "total_seconds": monotonic() - beginning,
            "free_bytes_before": before,
            "free_bytes_after": shutil.disk_usage(destination).free,
        }
        publish_file(private / "verified.json", json.dumps(record, sort_keys=True).encode("ascii"))
        output = destination / ("lychd-postgres-" + private.name.removeprefix(".apfs-cut-"))
        if output.exists():
            raise FileExistsError(output)
        private.rename(output)
    return output
