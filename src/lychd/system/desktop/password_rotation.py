"""Offline rotation of the dedicated desktop runtime role with recoverable file/database cutover."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

import psycopg

from lychd.db.authority import RUNTIME_AUTHORITY_QUERY, require_runtime_authority
from lychd.db.bootstrap import set_existing_runtime_password
from lychd.system.constants import PATH_POSTGRES_ROOT_DIR
from lychd.system.desktop.credentials import (
    GENERATED,
    generated_value,
    recovery_value,
    verify_credential_copy,
    verify_recovery_directory,
)
from lychd.system.desktop.private import overlaps, publish_file, verify_private_directory, verify_private_file
from lychd.system.desktop.vault import PREFIX, open_credential, seal_credential

if TYPE_CHECKING:
    from lychd.config.settings import DatabaseSettings

_ROLE = "LYCHD_RUNTIME_DB_PASSWORD"


class _RotationRecord(TypedDict):
    binding: dict[str, str]
    previous: str
    replacement: str


def _login(db: DatabaseSettings, value: str) -> bool:
    """Require a fresh TCP connection as the configured low-authority role."""
    try:
        with psycopg.connect(
            host="127.0.0.1",
            hostaddr="127.0.0.1",
            port=db.port,
            user=db.runtime_user,
            password=value,
            dbname=db.database,
            connect_timeout=5,
        ) as client:
            row = client.execute(RUNTIME_AUTHORITY_QUERY).fetchone()
            require_runtime_authority(row[0] if row else None)
    except psycopg.OperationalError:
        return False
    return True


def _active(db: DatabaseSettings, directory: Path) -> tuple[Path, bytes]:
    for name in GENERATED:
        path = directory / name.lower()
        if os.environ.get(name) or (os.environ.get(f"{name}_FILE") or str(path)) != str(path):
            msg = f"{name} has an externally supplied credential; use its owner for rotation."
            raise ValueError(msg)
    active = directory / _ROLE.lower()
    current = generated_value(active, _ROLE)
    if db.runtime_password is None or not secrets.compare_digest(
        current, db.runtime_password.get_secret_value().encode()
    ):
        msg = "The running configuration does not select the generated runtime credential."
        raise ValueError(msg)
    return active, current


def _prepare(
    db: DatabaseSettings, destination: Path, binding: dict[str, str], active: Path, current: bytes, pending: Path
) -> tuple[str, str]:
    if pending.exists():
        verify_private_file(pending)
        record: _RotationRecord = json.loads(pending.read_bytes())
        if record["binding"] != binding:
            msg = "Pending rotation belongs to another cluster, runtime role or recovery directory."
            raise ValueError(msg)
    else:
        if any(destination.iterdir()) or not _login(db, current.decode("ascii")):
            msg = "A new rotation requires an empty recovery directory and a working managed runtime credential."
            raise ValueError(msg)
        new = secrets.token_urlsafe(48).encode("ascii")
        sealed = seal_credential(active, new) if active.read_bytes().startswith(PREFIX.encode()) else new
        record = {
            "binding": binding,
            "previous": hashlib.sha256(current).hexdigest(),
            "replacement": sealed.decode("ascii"),
        }
        publish_file(pending, json.dumps(record).encode("ascii"))

    replacement: str = record["replacement"]
    password = open_credential(active, replacement) if replacement.startswith(PREFIX) else replacement
    if hashlib.sha256(current).hexdigest() != record["previous"] and not secrets.compare_digest(
        current, password.encode()
    ):
        msg = "The active credential has changed since this rotation began."
        raise ValueError(msg)
    return replacement, password


def _write_recovery(directory: Path, destination: Path, password: str) -> None:
    for name in GENERATED:
        target = destination / name.lower()
        value = password.encode("ascii") if name == _ROLE else generated_value(directory / name.lower(), name)
        if not target.exists():
            publish_file(target, value)
        if not secrets.compare_digest(recovery_value(target), value):
            msg = f"Unexpected recovery file for {name}; existing contents preserved."
            raise ValueError(msg)


def rotate(db: DatabaseSettings, owner: psycopg.Connection[Any], destination: Path) -> None:
    """Hold the caller's verified Vessel fence throughout preparation, change and readback."""
    directory = PATH_POSTGRES_ROOT_DIR / "desktop-credentials"
    verify_private_directory(directory)
    verify_recovery_directory(destination)
    active, current = _active(db, directory)
    ident = owner.execute(
        "SELECT system_identifier::text, current_setting('data_directory') FROM pg_control_system()"
    ).fetchone()
    if not ident:
        msg = "Unable to identify the running database."
        raise ValueError(msg)
    if overlaps(destination, Path(ident[1])):
        msg = "The recovery set must be stored outside the live PostgreSQL cluster."
        raise ValueError(msg)
    binding = {"cluster": str(ident[0]), "role": db.runtime_user, "database": db.database, "backup": str(destination)}
    pending = directory / "pending-runtime-rotation.json"
    replacement, password = _prepare(db, destination, binding, active, current, pending)
    _write_recovery(directory, destination, password)
    # Repeating this commit with the same pending secret is safe across a lost acknowledgment.
    if not _login(db, password) and not _login(db, current.decode("ascii")):
        msg = "Neither recorded credential authenticates to this cluster."
        raise ValueError(msg)
    set_existing_runtime_password(owner, db, password)
    closed = owner.execute(
        "SELECT pg_terminate_backend(pid, 5000) FROM pg_stat_activity WHERE usename = %s", (db.runtime_user,)
    ).fetchall()
    if not all(row[0] for row in closed) or not _login(db, password):
        msg = "The new credential or closure of prior sessions is unconfirmed. Repeat the pending rotation."
        raise ValueError(msg)
    if not secrets.compare_digest(current, password.encode("ascii")) and _login(db, current.decode("ascii")):
        msg = "The previous runtime credential still authenticates; rotation remains fenced."
        raise ValueError(msg)
    publish_file(active, replacement.encode("ascii"), replace=True)
    verify_credential_copy(destination)
    pending.unlink()
