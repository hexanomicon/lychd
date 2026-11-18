# ruff: noqa: INP001 -- standalone provisioning program in the image
"""Provision independent role credentials into the project's engine-managed volumes."""

from __future__ import annotations

import fcntl
import hmac
import os
import secrets
import tempfile
from pathlib import Path

SEED_BYTES = 32
ROLES = ("admin", "runtime", "phoenix", "app", "access")


def publish(path: Path, value: bytes, mode: int) -> None:
    """Publish a durable complete file under the exclusive provisioning lock."""
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(value)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
            temporary.replace(path)
            directory = os.open(path.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)


def provision(root: Path) -> None:
    """Restore missing projections from their seed and refuse mismatched existing values."""
    seed_dir = root / "seed"
    lock = os.open(seed_dir, os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        seed_path = seed_dir / "key"
        targets = {role: root / role / "value" for role in ROLES}
        if not seed_path.exists():
            if any(target.exists() for target in targets.values()):
                message = "Existing credentials need their original seed. Restore matching volumes."
                raise ValueError(message)
            publish(seed_path, secrets.token_bytes(SEED_BYTES), 0o400)
        key = seed_path.read_bytes()
        if len(key) != SEED_BYTES:
            message = "Invalid portable credential seed. Restore its original volume."
            raise ValueError(message)
        values = {
            role: hmac.digest(key, f"lychd-portable/v1/{role}".encode("ascii"), "sha256").hex().encode("ascii")
            for role in ROLES
        }
        for role, target in targets.items():
            if target.exists() and not hmac.compare_digest(target.read_bytes(), values[role]):
                message = f"Existing {role} credential differs. Restore matching volumes."
                raise ValueError(message)
        for role, target in targets.items():
            if not target.exists():
                # Each consumer sees only its role directories, mounted read-only.
                publish(target, values[role], 0o444)
    finally:
        os.close(lock)


if __name__ == "__main__":
    provision(Path("/run/lychd"))
