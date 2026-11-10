"""No-follow, descriptor-bound, durable custody for fixed Tether leaves.

Creation records are written only after absent-only creation. An interrupted
creation without its receipt refuses subsequent adoption.
"""

from __future__ import annotations

import json
import os
import stat
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from lychd.system.services.tether.models import TetherError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pydantic import BaseModel

_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_MAX_BYTES = 131072
_DIRS = ("public", "wireguard", "forwarder", "private", "operations", "revocations", "generations")


class TetherCustody:
    """Use only compiler-fixed roles beneath init-attested dedicated roots."""

    def __init__(self, codex_root: Path, crypt_root: Path) -> None:
        """Bind fixed native roles to trusted custody and process dependencies."""
        self.codex_root = codex_root
        self.crypt_root = crypt_root
        self.directories = {
            "public": codex_root / "tether",
            "wireguard": codex_root / "tether/wireguard",
            "forwarder": codex_root / "tether/forwarder",
            "private": crypt_root / "tether",
            "operations": crypt_root / "tether/operations",
            "revocations": crypt_root / "tether/revocations",
            "generations": crypt_root / "tether/generations",
        }

    @contextmanager
    def _directory(self, path: Path) -> Iterator[int]:
        if not path.is_absolute() or ".." in path.parts:
            msg = "Tether custody requires canonical absolute roots"
            raise TetherError(msg)
        descriptor = os.open("/", _FLAGS)
        try:
            for part in path.parts[1:]:
                child = os.open(part, _FLAGS, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            metadata = os.fstat(descriptor)
            if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != (
                0o755 if path in (self.directories["wireguard"], self.directories["forwarder"]) else 0o700
            ):
                msg = "Tether custody directory must be operator-owned mode 0700"
                raise TetherError(msg)
            yield descriptor
        finally:
            os.close(descriptor)

    @staticmethod
    def _identity(descriptor: int) -> list[int]:
        metadata = os.fstat(descriptor)
        return [metadata.st_dev, metadata.st_ino]

    def initialize(self) -> None:
        """Create absent leaves once; existing leaves require exact creation receipt."""
        if os.path.lexists(self.directories["private"]):
            self.attest()
            return
        if os.path.lexists(self.directories["public"]):
            msg = "Unreceipted Tether public custody exists; refusing adoption"
            raise TetherError(msg)
        identities: dict[str, list[int]] = {}
        for role in _DIRS:
            path = self.directories[role]
            with self._directory(path.parent) as parent:
                mode = 0o755 if role in {"wireguard", "forwarder"} else 0o700
                os.mkdir(path.name, mode, dir_fd=parent)
                child = os.open(path.name, _FLAGS, dir_fd=parent)
                try:
                    os.fchmod(child, mode)
                    os.fsync(child)
                finally:
                    os.close(child)
                os.fsync(parent)
            with self._directory(path) as descriptor:
                os.fchmod(descriptor, 0o755 if role in {"wireguard", "forwarder"} else 0o700)
                identities[role] = self._identity(descriptor)
        for role, path in (("codex", self.codex_root), ("crypt", self.crypt_root)):
            with self._directory(path) as descriptor:
                os.fchmod(descriptor, 0o755 if role in {"wireguard", "forwarder"} else 0o700)
                identities[role] = self._identity(descriptor)
        self._write("private", ".custody.json", json.dumps(identities).encode(), immutable=True)
        self.attest()

    def attest(self) -> None:
        """Refuse replaced directories even when their names and modes match."""
        raw = self._read("private", ".custody.json")
        if raw is None:
            msg = "Tether creation receipt is absent; preserve uncertain custody"
            raise TetherError(msg)
        expected = cast("dict[str, list[int]]", json.loads(raw))
        paths = {**self.directories, "codex": self.codex_root, "crypt": self.crypt_root}
        if set(expected) != set(paths):
            msg = "Tether custody receipt has an unknown or missing role"
            raise TetherError(msg)
        for role, path in paths.items():
            with self._directory(path) as descriptor:
                if expected[role] != self._identity(descriptor):
                    msg = "Tether custody identity changed"
                    raise TetherError(msg)

    @staticmethod
    def _name(name: str) -> None:
        if not name or name in {".", ".."} or "/" in name or "\x00" in name:
            msg = "Invalid internal Tether record name"
            raise TetherError(msg)

    def _read(self, role: str, name: str) -> bytes | None:
        self._name(name)
        with self._directory(self.directories[role]) as parent:
            try:
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            except FileNotFoundError:
                return None
            try:
                metadata = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) != (0o644 if role in {"wireguard", "forwarder"} else 0o600)
                    or metadata.st_nlink != 1
                ):
                    msg = "Unsafe Tether record metadata"
                    raise TetherError(msg)
                content = os.read(descriptor, _MAX_BYTES + 1)
                if len(content) > _MAX_BYTES:
                    msg = "Oversized Tether record"
                    raise TetherError(msg)
                return content
            finally:
                os.close(descriptor)

    def read(self, role: str, name: str) -> bytes | None:
        """Read bounded bytes after full custody revalidation."""
        self.attest()
        return self._read(role, name)

    def write(self, role: str, name: str, value: BaseModel, *, immutable: bool = False) -> None:
        """Publish one typed record, durably and atomically."""
        self.publish(role, name, value.model_dump_json().encode(), immutable=immutable)

    def publish(self, role: str, name: str, content: bytes, *, immutable: bool = False) -> None:
        """Publish a compiler-owned public projection or typed journal record."""
        self.attest()
        self._write(role, name, content, immutable=immutable)

    def _write(self, role: str, name: str, content: bytes, *, immutable: bool) -> None:
        self._name(name)
        if len(content) > _MAX_BYTES:
            msg = "Oversized Tether publication"
            raise TetherError(msg)
        previous = self._read(role, name)
        if previous is not None and immutable:
            if previous != content:
                msg = "Immutable Tether evidence disagrees with retry"
                raise TetherError(msg)
            return
        temporary = f".staging-{uuid4()}"
        with self._directory(self.directories[role]) as parent:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o644 if role in {"wireguard", "forwarder"} else 0o600,
                dir_fd=parent,
            )
            try:
                os.fchmod(descriptor, 0o644 if role in {"wireguard", "forwarder"} else 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                if immutable:
                    os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                    os.unlink(temporary, dir_fd=parent)
                else:
                    os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                with suppress(FileNotFoundError):
                    os.unlink(temporary, dir_fd=parent)

    def clear_latch(self, expected: bytes) -> None:
        """Remove only the active latch after exact cold reenrollment validation."""
        self.attest()
        if self._read("private", "closed.json") != expected:
            msg = "Closure latch changed before cold reenrollment"
            raise TetherError(msg)
        with self._directory(self.directories["private"]) as parent:
            os.unlink("closed.json", dir_fd=parent)
            os.fsync(parent)
