"""Verify the PostgreSQL cold cut and compare every file when exporting a fresh copy."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lychd.config.settings import DatabaseSettings


def active_id(source: Path, db: DatabaseSettings) -> str:
    import psycopg

    if db.password is None:
        msg = "Desktop administrator credential required."
        raise ValueError(msg)
    with psycopg.connect(
        hostaddr="127.0.0.1",
        host="127.0.0.1",
        dbname="postgres",
        port=db.port,
        user=db.user,
        password=db.password.get_secret_value(),
        connect_timeout=5,
    ) as conn:
        row = conn.execute(
            "SELECT current_setting('data_directory'), system_identifier::text, "
            "EXISTS (SELECT FROM pg_tablespace WHERE pg_tablespace_location(oid) <> '') FROM pg_control_system()"
        ).fetchone()
    if not row or not source.samefile(row[0]) or row[2]:
        msg = "The live cluster path must match and all tablespaces must be built in."
        raise ValueError(msg)
    return str(row[1])


def cold_control(source: Path, tool: str, expected: str) -> None:
    if (source / "postmaster.pid").exists() or (source / "PG_VERSION").read_text(encoding="ascii").strip() != "18":
        msg = "Expected an inactive PostgreSQL 18 data directory."
        raise ValueError(msg)
    if any((source / "pg_tblspc").iterdir()) or not (source / "pg_wal").is_dir():
        msg = "This cold capture requires in-cluster WAL and built-in tablespaces."
        raise ValueError(msg)
    output = subprocess.check_output([tool, str(source)], env={**os.environ, "LC_ALL": "C", "LANG": "C"}, text=True)  # noqa: S603
    fields = dict(line.split(":", 1) for line in output.splitlines() if ":" in line)
    if (
        fields["Database system identifier"].strip() != expected
        or fields["Database cluster state"].strip() != "shut down"
    ):
        msg = "The physical cluster identifier or its clean shutdown state differs from the cold cut."
        raise ValueError(msg)


def inventory(source: Path, *, digest: bool) -> dict[str, str]:
    """Reject redirects, special files and nested volumes before traversal or copying."""
    device = source.stat().st_dev
    found = {}
    stack = [source]
    while stack:
        path = stack.pop()
        info = path.lstat()
        if info.st_dev != device or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            msg = f"PostgreSQL storage crosses a mounted volume or reparse point at {path}."
            raise ValueError(msg)
        relative = path.relative_to(source).as_posix()
        if stat.S_ISDIR(info.st_mode):
            found[relative] = "directory"
            stack.extend(path.iterdir())
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            if digest:
                with path.open("rb") as stream:
                    found[relative] = hashlib.file_digest(stream, "sha256").hexdigest()
        else:
            msg = f"Refusing linked or special PostgreSQL file {path}."
            raise ValueError(msg)
    return found


def bind_installation(default: Path, db: DatabaseSettings, *, initialize: bool) -> None:
    """Pin the selected installation's live PG identity independently of its snapshot grants."""
    from lychd.system.desktop.volume_storage import STORAGE, authority, read_record, selected, write_record

    directory = authority(default)
    if not (directory / "storage.json").exists():
        return
    root, volume = selected(default)
    identifier = active_id(root / STORAGE / default.name, db)
    expected = {"volume": volume, "system_identifier": identifier}
    binding = directory / "database.json"
    if initialize and not binding.exists():
        write_record(binding, **expected)
    elif read_record(binding) != expected:
        msg = "The running database differs from this registered installation volume or system identifier."
        raise ValueError(msg)
