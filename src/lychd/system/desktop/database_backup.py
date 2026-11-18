"""Capture the registered desktop database with its installation-owned credential."""

from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import click

from lychd.system.desktop.private import private_directory, publish_file, verify_private_directory
from lychd.system.pg_backup import capture

if TYPE_CHECKING:
    from lychd.config.settings import DatabaseSettings


def _field(value: str) -> str:
    if any(character in value for character in ("\x00", "\r", "\n")):
        msg = "Desktop database credentials must fit a single libpq password record."
        raise ValueError(msg)
    return value.replace("\\", "\\\\").replace(":", "\\:")


def capture_registered(pg_bin: Path, source: Path, destination: Path, db: DatabaseSettings) -> Path:
    """Stream and verify an inactive recovery copy of the running, registered cluster."""
    if db.password is None:
        msg = "An administrator credential is required to capture the desktop database."
        raise click.ClickException(msg)
    try:
        verify_private_directory(destination)
        with TemporaryDirectory(prefix=".backup-auth-", dir=source.parent) as directory:
            private_directory(Path(directory))
            passfile = Path(directory) / "pgpass"
            record = f"127.0.0.1:{db.port}:*:{_field(db.user)}:{_field(db.password.get_secret_value())}\n"
            publish_file(passfile, record.encode("utf-8"))
            return capture(pg_bin, source, destination, port=db.port, user=db.user, passfile=passfile)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise click.ClickException(str(exc)) from exc
