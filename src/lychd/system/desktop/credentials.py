"""Private per-user credential files for native desktop installation."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import click

from lychd.system.constants import PATH_POSTGRES_ROOT_DIR
from lychd.system.desktop.private import (
    check_path,
    private_directory,
    private_file,
    publish_file,
    verify_private_directory,
    verify_private_file,
)

_RUNTIME = ("LYCHD_RUNTIME_DB_PASSWORD", "LYCHD_APP_SECRET_KEY", "LYCHD_LOCAL_ACCESS_PASSWORD")
_ADMIN = ("LYCHD_DB_PASSWORD", "LYCHD_PHOENIX_DB_PASSWORD")


def load_credentials(*, administrative: bool = False, provision: bool = False, required: bool = False) -> None:
    """Set standard file references without replacing explicit credentials or disclosing values."""
    directory = PATH_POSTGRES_ROOT_DIR / "desktop-credentials"
    if provision:
        private_directory(directory)
    for name in (*_RUNTIME, *_ADMIN) if administrative else _RUNTIME:
        file_key = f"{name}_FILE"
        if os.environ.get(name) or os.environ.get(file_key):
            continue
        path = directory / name.lower()
        check_path(path)
        if provision and not path.exists():
            publish_file(path, secrets.token_urlsafe(48).encode("ascii"))
        if required and not path.is_file():
            msg = f"Missing desktop credential {name}. Restore its original file or supply its explicit override."
            raise click.ClickException(msg)
        if path.is_file():
            private_file(path)
            os.environ[file_key] = str(path)


def verify_credential_copy(directory: Path) -> None:
    """Compare an independent, private copy of every generated credential to this installation."""
    source = PATH_POSTGRES_ROOT_DIR / "desktop-credentials"
    verify_private_directory(source)
    verify_private_directory(directory)
    if directory.samefile(source):
        msg = "Select an independent credential backup directory."
        raise click.ClickException(msg)
    for name in (*_RUNTIME, *_ADMIN):
        original = source / name.lower()
        reference = os.environ.get(f"{name}_FILE")
        if os.environ.get(name) or (reference and Path(reference) != original):
            msg = f"{name} has an explicit override. Verify it through the external credential owner."
            raise click.ClickException(msg)
        copy = directory / name.lower()
        for path in (original, copy):
            verify_private_file(path)
        value = original.read_bytes()
        if not value or not secrets.compare_digest(value, copy.read_bytes()):
            msg = f"Credential backup does not match {name}."
            raise click.ClickException(msg)
