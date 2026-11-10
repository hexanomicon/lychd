"""Absent-only native key custody with exact public Podman identity receipts.

The caller holds the host lifecycle transaction lock across each public method.
Private values exist only in bounded local variables, stdin, Podman's secret
store, and a short-lived owned SSH generation directory. Pending receipts carry
public identity before creation; uncertainty never authorizes replacement.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import stat
import struct
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from lychd.lib.json_objects import unique_json_object
from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator.process import SubprocessRunner
from lychd.system.secret_names import is_valid_podman_secret_name
from lychd.system.services.tether.models import TetherError

if TYPE_CHECKING:
    from lychd.system.operator.process import InputProcessRunner
    from lychd.system.services.tether.custody import TetherCustody

Purpose = Literal["wireguard", "ssh-host", "preshared"]
_MAX_KEY_BYTES = 8192
_RAW_KEY_BYTES = 32
_SSH_PRIVATE_BYTES = 64
_SSH_PUBLIC_BYTES = 51
_SSH_PUBLIC_FIELDS = 2
_UINT32_BYTES = 4
_SSH_ENVELOPE_LINES = 3
_MAX_OUTPUT = 65536
_MAX_REFERENCES = 512
_PRIVATE_MODE = 0o600
_DIRECTORY_MODE = 0o700
_SCHEMA = "lychd.tether.key"
_FIELDS = {
    "schema",
    "version",
    "installation_epoch",
    "reference",
    "purpose",
    "operation_id",
    "public_key",
    "fingerprint",
}
_LABEL_EPOCH = "io.lychd.tether.epoch"
_LABEL_PURPOSE = "io.lychd.tether.purpose"
_LABEL_OPERATION = "io.lychd.tether.operation"


def _refuse() -> TetherError:
    return TetherError("Tether key custody or operation refused")


def _require(condition: bool) -> None:  # noqa: FBT001 - assertion helper
    if not condition:
        raise _refuse()


def _reference(reference: str) -> None:
    _require(
        type(reference) is str and is_valid_podman_secret_name(reference) and reference.startswith("lychd-tether-")
    )


def _name(reference: str, *, pending: bool = False) -> str:
    suffix = "-pending" if pending else ""
    return f"key-{hashlib.sha256(reference.encode()).hexdigest()}{suffix}.json"


def _raw32(value: str) -> bytes:
    _require(type(value) is str)
    encoded = value.removesuffix("\n")
    decoded = base64.b64decode(encoded, validate=True)
    _require(len(decoded) == _RAW_KEY_BYTES and any(decoded) and base64.b64encode(decoded).decode() == encoded)
    return decoded


def _fingerprint(public: bytes) -> str:
    return "SHA256:" + base64.b64encode(hashlib.sha256(public).digest()).decode().rstrip("=")


def _ssh_public(value: str) -> tuple[str, bytes]:
    parts = value.strip().split(" ")
    _require(len(parts) == _SSH_PUBLIC_FIELDS and parts[0] == "ssh-ed25519")
    decoded = base64.b64decode(parts[1], validate=True)
    _require(len(decoded) == _SSH_PUBLIC_BYTES and decoded[:19] == b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20")
    _require(any(decoded[19:]) and base64.b64encode(decoded).decode() == parts[1])
    return " ".join(parts), decoded


class _SSHFields:
    """Bounded parser for the generated unencrypted one-key OpenSSH envelope."""

    def __init__(self, value: bytes) -> None:
        """Consume only already size-bounded bytes."""
        self.value = value
        self.offset = 0

    def number(self) -> int:
        _require(len(self.value) - self.offset >= _UINT32_BYTES)
        result = struct.unpack_from(">I", self.value, self.offset)[0]
        self.offset += 4
        return result

    def field(self) -> bytes:
        size = self.number()
        _require(size <= len(self.value) - self.offset)
        result = self.value[self.offset : self.offset + size]
        self.offset += size
        return result

    def remaining(self) -> bytes:
        return self.value[self.offset :]


def _ssh_seed(value: str) -> bytes:
    """Extract seed only for in-memory cross-purpose comparison, never a receipt."""
    lines = value.splitlines()
    _require(len(value.encode()) <= _MAX_KEY_BYTES and len(lines) >= _SSH_ENVELOPE_LINES)
    _require(lines[0] == "-----BEGIN OPENSSH PRIVATE KEY-----" and lines[-1] == "-----END OPENSSH PRIVATE KEY-----")
    raw = base64.b64decode("".join(lines[1:-1]), validate=True)
    magic = b"openssh-key-v1\x00"
    _require(raw.startswith(magic))
    outer = _SSHFields(raw[len(magic) :])
    _require(outer.field() == b"none" and outer.field() == b"none" and outer.field() == b"" and outer.number() == 1)
    public = outer.field()
    private = _SSHFields(outer.field())
    _require(not outer.remaining() and private.number() == private.number() and private.field() == b"ssh-ed25519")
    public_bytes, private_bytes = private.field(), private.field()
    _require(len(public_bytes) == _RAW_KEY_BYTES and len(private_bytes) == _SSH_PRIVATE_BYTES)
    _require(hmac.compare_digest(private_bytes[_RAW_KEY_BYTES:], public_bytes))
    _require(public == b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + public_bytes)
    _require(private.field() == b"")  # Factory admits no comments or foreign metadata.
    padding = private.remaining()
    _require(bool(padding) and padding == bytes(range(1, len(padding) + 1)))
    seed = private_bytes[:_RAW_KEY_BYTES]
    _require(any(seed))
    return seed


def _private_file(path: Path) -> str:
    """Open through non-symlink directories and validate the private inode."""
    _require(path.is_absolute() and ".." not in path.parts and bool(path.name))
    parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in path.parent.parts[1:]:
            following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            os.close(parent)
            parent = following
        directory = os.fstat(parent)
        _require(directory.st_uid == os.getuid() and stat.S_IMODE(directory.st_mode) == _DIRECTORY_MODE)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        try:
            before = os.fstat(fd)
            _require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid() and before.st_nlink == 1)
            _require(stat.S_IMODE(before.st_mode) == _PRIVATE_MODE and 0 < before.st_size <= _MAX_KEY_BYTES)
            raw = os.read(fd, _MAX_KEY_BYTES + 1)
            after = os.fstat(fd)
            _require(
                len(raw) == before.st_size
                and (before.st_mtime_ns, before.st_ctime_ns) == (after.st_mtime_ns, after.st_ctime_ns)
            )
            return raw.decode("ascii")
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def _default_driver_directory(graph_root: str, configured: str) -> None:
    """Prove the default local secret directory without following another storage owner."""
    root = Path(graph_root)
    _require(root.is_absolute() and root.anchor == "/" and str(root) == graph_root and ".." not in root.parts)
    _require(configured == str(root / "secrets" / "filedriver"))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    parent = os.open("/", flags)
    try:
        for component in root.parts[1:]:
            following = os.open(component, flags, dir_fd=parent)
            os.close(parent)
            parent = following
            metadata = os.fstat(parent)
            sticky_system = metadata.st_uid == 0 and bool(metadata.st_mode & stat.S_ISVTX)
            _require(metadata.st_uid in {0, os.getuid()} and (not metadata.st_mode & 0o022 or sticky_system))
        _require(os.fstat(parent).st_uid == os.getuid())
        for component in ("secrets", "filedriver"):
            following = os.open(component, flags, dir_fd=parent)
            os.close(parent)
            parent = following
            metadata = os.fstat(parent)
            _require(metadata.st_uid == os.getuid() and stat.S_IMODE(metadata.st_mode) == _DIRECTORY_MODE)
    finally:
        os.close(parent)


class TetherKeys:
    """Exact-reference factories and attestations; no replace, ignore, or deletion."""

    def __init__(self, custody: TetherCustody, epoch: str, runner: InputProcessRunner | None = None) -> None:
        """Bind existing host custody; callers serialize complete transactions."""
        _require(type(epoch) is str and re.fullmatch(r"[0-9a-f]{32}", epoch) is not None)
        self.custody, self.epoch, self.runner = custody, epoch, runner or SubprocessRunner()

    def _tool(self, name: str) -> str:
        result = trusted_host_tool(name, fallbacks=(Path("/usr/bin") / name, Path("/usr/sbin") / name))
        if result is None:
            raise _refuse()
        return result

    def _call(self, name: str, *arguments: str, value: str | None = None, absence: bool = False) -> str | None:
        try:
            local_engine = ("--remote=false",) if name == "podman" else ()
            argv = (self._tool(name), *local_engine, *arguments)
            result = (
                self.runner.run(argv, timeout_s=30)
                if value is None
                else self.runner.run_with_input(argv, timeout_s=30, input_text=value)
            )
            if absence and result.returncode == 1:
                return None
            _require(result.returncode == 0 and len(result.stdout.encode()) <= _MAX_OUTPUT)
        except Exception:  # noqa: BLE001 - suppress tool diagnostics and any secret-bearing exception chain
            raise _refuse() from None
        else:
            return result.stdout

    def _record(self, value: Any, reference: str, *, final: bool) -> dict[str, Any]:
        _require(type(value) is dict and set(value) == (_FIELDS | {"secret_id"} if final else _FIELDS))
        value = cast("dict[str, Any]", value)
        _require(value["schema"] == _SCHEMA and type(value["version"]) is int and value["version"] == 1)
        _require(value["installation_epoch"] == self.epoch and value["reference"] == reference)
        _require(value["purpose"] in {"wireguard", "ssh-host", "preshared"})
        _require(
            type(value["operation_id"]) is str and re.fullmatch(r"[0-9a-f]{32}", value["operation_id"]) is not None
        )
        _require(
            type(value["fingerprint"]) is str
            and re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}", value["fingerprint"]) is not None
        )
        if value["purpose"] == "preshared":
            _require(value["public_key"] is None)
        elif value["purpose"] == "wireguard":
            _raw32(value["public_key"])
        else:
            _ssh_public(value["public_key"])
        if final:
            _require(
                type(value["secret_id"]) is str and re.fullmatch(r"[a-zA-Z0-9]{12,128}", value["secret_id"]) is not None
            )
        return value

    def _labels(self, record: dict[str, Any]) -> dict[str, str]:
        return {_LABEL_EPOCH: self.epoch, _LABEL_PURPOSE: record["purpose"], _LABEL_OPERATION: record["operation_id"]}

    def _identity(self, value: str, purpose: Purpose) -> tuple[str | None, str, bytes]:
        if purpose == "ssh-host":
            material = _ssh_seed(value)
            output = self._call("ssh-keygen", "-y", "-P", "", "-f", "/dev/stdin", value=value)
            if output is None:
                raise _refuse()
            public, encoded = _ssh_public(output)
            return public, _fingerprint(encoded), material
        material = _raw32(value)
        if purpose == "preshared":
            return None, _fingerprint(material), material
        output = self._call("wg", "pubkey", value=base64.b64encode(material).decode() + "\n")
        if output is None:
            raise _refuse()
        encoded = _raw32(output)
        return base64.b64encode(encoded).decode(), _fingerprint(encoded), material

    def _file_driver(self, driver: Any) -> None:
        """Admit only the file backend's freshly proved default storage descriptor."""
        _require(type(driver) is dict and driver.get("Name") == "file")
        options = driver.get("Options")
        _require(type(options) is dict and set(options) == {"path"} and type(options["path"]) is str)
        graph_root = self._call("podman", "info", "--format", "{{.Store.GraphRoot}}")
        _require(graph_root is not None)
        _default_driver_directory(cast("str", graph_root).removesuffix("\n"), cast("dict[str, str]", options)["path"])

    def _inspect(self, record: dict[str, Any]) -> tuple[dict[str, Any], str, bytes]:
        reference = record["reference"]
        target = record.get("secret_id", reference)
        output = self._call("podman", "secret", "inspect", "--showsecret", target)
        if output is None:
            raise _refuse()
        rows = json.loads(output, object_pairs_hook=unique_json_object)
        _require(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict)
        row = cast("dict[str, Any]", rows[0])
        spec = row.get("Spec")
        _require(type(spec) is dict and spec.get("Name") == reference and spec.get("Labels") == self._labels(record))
        spec = cast("dict[str, Any]", spec)
        self._file_driver(spec.get("Driver"))
        secret_id = row.get("ID")
        _require(type(secret_id) is str and re.fullmatch(r"[a-zA-Z0-9]{12,128}", secret_id) is not None)
        _require("secret_id" not in record or record["secret_id"] == secret_id)
        value = row.get("SecretData")
        _require(type(value) is str and 0 < len(value.encode()) <= _MAX_KEY_BYTES)
        value = cast("str", value)
        public, fingerprint, material = self._identity(value, record["purpose"])
        _require(public == record["public_key"] and hmac.compare_digest(fingerprint, record["fingerprint"]))
        return {**record, "secret_id": secret_id}, value, material

    def owned_references(self) -> tuple[str, ...]:
        """Observe exact owned live secrets, including recoverable pending creations."""
        try:
            owned: list[str] = []
            materials: list[tuple[bytes, str | None, str]] = []
            for reference in self.known_references():
                phase = self.preparation_state(reference)
                pending = phase == "pending"
                record = self._record(
                    self.custody.read(_name(reference, pending=pending)), reference, final=not pending
                )
                if pending and self._call("podman", "secret", "exists", reference, absence=True) is None:
                    continue
                identity, _value, material = self._inspect(record)
                purpose, public = identity["purpose"], identity["public_key"]
                for previous, previous_public, previous_purpose in materials:
                    _require(not hmac.compare_digest(material, previous))
                    if purpose == "wireguard" or previous_purpose == "wireguard":
                        left, right = bytearray(material), bytearray(previous)
                        left[0] &= 248
                        right[0] &= 248
                        left[-1] = (left[-1] & 127) | 64
                        right[-1] = (right[-1] & 127) | 64
                        _require(not hmac.compare_digest(left, right))
                    if public is not None and purpose == previous_purpose:
                        _require(public != previous_public)
                materials.append((material, public, purpose))
                owned.append(reference)
        except Exception:  # noqa: BLE001 - secret observations never escape diagnostics
            raise _refuse() from None
        else:
            return tuple(owned)

    def preparation_state(self, reference: str) -> Literal["absent", "pending", "ready"]:
        """Classify receipted preparation only; readiness still requires attestation."""
        try:
            _reference(reference)
            self.known_references()  # Validate inventory names, epochs and schemas first.
            final = self.custody.read(_name(reference))
            pending = self.custody.read(_name(reference, pending=True))
            if final is None and pending is None:
                return "absent"
            pending = self._record(pending, reference, final=False)
            if final is None:
                return "pending"
            final = self._record(final, reference, final=True)
            _require({name: final[name] for name in _FIELDS} == pending)
        except Exception:  # noqa: BLE001 - metadata diagnostics remain content-free
            raise _refuse() from None
        else:
            return "ready"

    def known_references(self) -> tuple[str, ...]:
        """Discover only positively receipted key records, including pending work."""
        try:
            self.custody.attest()
            references: set[str] = set()
            for path in self.custody.known_paths():
                if re.fullmatch(r"key-[0-9a-f]{64}(?:-pending)?\.json", path.name) is None:
                    continue
                row = self.custody.read(path.name)
                if row is None:
                    raise _refuse()  # noqa: TRY301 - normalize the public gateway boundary
                reference = row.get("reference")
                if not isinstance(reference, str):
                    raise _refuse()  # noqa: TRY301 - retain type narrowing inside quarantine
                _reference(reference)
                pending = path.name.endswith("-pending.json")
                _require(path.name == _name(reference, pending=pending))
                self._record(row, reference, final=not pending)
                references.add(reference)
            _require(len(references) <= _MAX_REFERENCES)
            return tuple(sorted(references))
        except Exception:  # noqa: BLE001 - public gateway has content-free diagnostics
            raise _refuse() from None

    def _unique_material(self, reference: str, material: bytes, public: str | None, purpose: Purpose) -> None:
        """Compare existing owned material without coupling absent pending creations."""

        def scalar(value: bytes) -> bytes:
            copy = bytearray(value)
            copy[0] &= 248
            copy[-1] = (copy[-1] & 127) | 64
            return bytes(copy)

        for other in self.known_references():
            if other == reference:
                continue
            pending = self.preparation_state(other) == "pending"
            record = self._record(self.custody.read(_name(other, pending=pending)), other, final=not pending)
            if pending and self._call("podman", "secret", "exists", other, absence=True) is None:
                continue
            _identity, _value, previous = self._inspect(record)
            _require(not hmac.compare_digest(material, previous))
            if purpose == "wireguard" or record["purpose"] == "wireguard":
                _require(not hmac.compare_digest(scalar(material), scalar(previous)))
            if public is not None and purpose == record["purpose"]:
                _require(public != record["public_key"])

    def _existing(self, reference: str, purpose: Purpose, imported: str | None = None) -> dict[str, Any] | None:
        final = self.custody.read(_name(reference))
        pending = self.custody.read(_name(reference, pending=True))
        if final is None and pending is None:
            return None
        _require(pending is not None)
        pending = self._record(pending, reference, final=False)
        _require(pending["purpose"] == purpose)
        record = pending if final is None else self._record(final, reference, final=True)
        _require({name: record[name] for name in _FIELDS} == pending)
        identity, current, material = self._inspect(record)
        if imported is not None:
            _require(hmac.compare_digest(_raw32(current), _raw32(imported)))
        self._unique_material(reference, material, identity["public_key"], purpose)
        if final is None:
            self.custody.write(_name(reference), identity, immutable=True)
        return identity

    def _create(self, reference: str, purpose: Purpose, value: str) -> dict[str, Any]:
        public, fingerprint, material = self._identity(value, purpose)
        self._unique_material(reference, material, public, purpose)
        pending: dict[str, Any] = {
            "schema": _SCHEMA,
            "version": 1,
            "installation_epoch": self.epoch,
            "reference": reference,
            "purpose": purpose,
            "operation_id": uuid.uuid4().hex,
            "public_key": public,
            "fingerprint": fingerprint,
        }
        self.custody.write(_name(reference, pending=True), pending, immutable=True)
        labels = tuple(part for name, label in self._labels(pending).items() for part in ("--label", f"{name}={label}"))
        secret_id = self._call("podman", "secret", "create", "--driver", "file", *labels, reference, "-", value=value)
        if secret_id is None:
            raise _refuse()
        candidate = self._record({**pending, "secret_id": secret_id.strip()}, reference, final=True)
        identity, _value, _material = self._inspect(candidate)
        self.custody.write(_name(reference), identity, immutable=True)
        return identity

    def ensure(self, reference: str, purpose: Literal["wireguard", "ssh-host"]) -> dict[str, Any]:
        """Generate only for a proven absent name; resume exact labeled pending creation."""
        try:
            _reference(reference)
            _require(purpose in {"wireguard", "ssh-host"})
            self.custody.attest()
            existing = self._existing(reference, purpose)
            if existing is not None:
                return existing
            _require(self._call("podman", "secret", "exists", reference, absence=True) is None)
            if purpose == "wireguard":
                value = self._call("wg", "genkey")
                if value is None:
                    raise _refuse()  # noqa: TRY301 - retain type narrowing inside quarantine
                value = base64.b64encode(_raw32(value)).decode() + "\n"
            else:
                directory = self.custody.directory("key-staging")
                with tempfile.TemporaryDirectory(prefix="generation-", dir=directory) as scratch:
                    path = Path(scratch) / "host"
                    self._call("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "", "-f", str(path))
                    value = _private_file(path)
        except Exception:  # noqa: BLE001 - secret values and tool errors never cross this boundary
            raise _refuse() from None
        else:
            try:
                return self._create(reference, purpose, value)
            except Exception:  # noqa: BLE001 - preserve the same diagnostic quarantine during creation
                raise _refuse() from None

    def import_key(self, reference: str, path: Path, purpose: Literal["wireguard", "preshared"]) -> dict[str, Any]:
        """Import one private owned file without hooks, replacement, or name adoption."""
        try:
            _reference(reference)
            _require(purpose in {"wireguard", "preshared"})
            self.custody.attest()
            value = base64.b64encode(_raw32(_private_file(path))).decode() + "\n"
            existing = self._existing(reference, purpose, imported=value)
            if existing is not None:
                return existing
            _require(self._call("podman", "secret", "exists", reference, absence=True) is None)
            return self._create(reference, purpose, value)
        except Exception:  # noqa: BLE001 - import diagnostics are intentionally content-free
            raise _refuse() from None

    def attest(self, reference: str) -> dict[str, Any]:
        """Check exact receipt ID, labels, name and current cryptographic identity."""
        try:
            _reference(reference)
            self.custody.attest()
            final = self._record(self.custody.read(_name(reference)), reference, final=True)
            pending = self._record(self.custody.read(_name(reference, pending=True)), reference, final=False)
            _require({name: final[name] for name in _FIELDS} == pending)
            identity, _value, material = self._inspect(final)
            self._unique_material(reference, material, identity["public_key"], identity["purpose"])
        except Exception:  # noqa: BLE001 - no secret-bearing diagnostic escapes
            raise _refuse() from None
        else:
            return identity


__all__ = ("TetherKeys",)
