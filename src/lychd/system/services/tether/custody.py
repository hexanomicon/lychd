"""Descriptor-bound custody for persistent host Tether records and projections.

The root receipt records strong persistent identities. Directory locks serialize
writers; an interrupted file/receipt transaction is refused on the next access.
No operation adopts an existing unreceipted path or changes inherited permissions.
Runtime sockets under /run are deliberately outside this persistent store.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lychd.lib.json_objects import unique_json_object
from lychd.system.constants import PATH_TETHER_STATE_DIR
from lychd.system.path_identity import PathIdentityError, PersistentPathIdentity, observe_identity_fd
from lychd.system.services.tether.models import MAX_DOCUMENT_BYTES, TetherError, TetherIntent, canonical_bytes, digest

_RECEIPT = ".custody.json"
_MAX_PATHS = 4096
_MAX_SNAPSHOT_BYTES = 4 * MAX_DOCUMENT_BYTES
_MAX_RELATIVE_BYTES = 1024
_RECEIPT_ENTRY_RESERVE = 4096
_PRIVATE_FILE = 0o600
_PUBLIC_FILE = 0o444
_PRIVATE_DIRECTORY = 0o700
_PUBLIC_DIRECTORY = 0o755
_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}\Z")
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK


class _Directory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    identity: PersistentPathIdentity
    mode: Literal[0o700, 0o755]


class _File(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    identity: PersistentPathIdentity
    mode: Literal[0o600, 0o444]
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    immutable: bool


class _Receipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_name: Literal["lychd.tether.custody"] = Field(alias="schema")
    version: Literal[1]
    revision: int = Field(ge=1)
    root: PersistentPathIdentity
    directories: dict[str, _Directory]
    files: dict[str, _File]


class CustodyRecords(Protocol):
    """Read-only record access valid only inside the custody lock interval."""

    @property
    def names(self) -> tuple[str, ...]: ...

    def read(self, name: str) -> dict[str, object] | None: ...


class _RecordView:
    def __init__(self, names: tuple[str, ...], reader: Callable[[str], bytes | None]) -> None:
        self._names = names
        self._reader: Callable[[str], bytes | None] | None = reader
        self._reads = 0
        self._bytes = 0

    @property
    def names(self) -> tuple[str, ...]:
        if self._reader is None:
            raise _refuse()
        return self._names

    def read(self, name: str) -> dict[str, object] | None:
        if self._reader is None or self._reads >= _MAX_PATHS:
            raise _refuse()
        self._reads += 1
        raw = self._reader(_relative(name))
        if raw is None:
            return None
        self._bytes += len(raw)
        if self._bytes > _MAX_SNAPSHOT_BYTES:
            raise _refuse()
        return _object(raw)

    def close(self) -> None:
        self._reader = None


def _refuse() -> TetherError:
    return TetherError("Tether custody cannot establish current ownership")


def _relative(value: str | Path) -> str:
    path = Path(value)
    if (
        path.is_absolute()
        or not path.parts
        or str(path) != str(value)
        or any(_NAME.fullmatch(part) is None or part in {".", ".."} for part in path.parts)
    ):
        raise _refuse()
    result = path.as_posix()
    if result == _RECEIPT or len(result.encode()) > _MAX_RELATIVE_BYTES:
        raise _refuse()
    return result


def _directory_metadata(descriptor: int, *, owned: bool, mode: int | None = None) -> os.stat_result:
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_mode & 0o022:
        raise _refuse()
    if owned and metadata.st_uid != os.getuid():
        raise _refuse()
    if mode is not None and stat.S_IMODE(metadata.st_mode) != mode:
        raise _refuse()
    if owned and metadata.st_mode & _PRIVATE_DIRECTORY != _PRIVATE_DIRECTORY:
        raise _refuse()
    return metadata


@contextmanager
def _open_directory(path: Path) -> Generator[int]:
    """Pin every absolute path component without following symlinks."""
    if not path.is_absolute() or ".." in path.parts:
        raise _refuse()
    descriptor = os.open("/", _DIRECTORY_FLAGS)
    try:
        for part in path.parts[1:]:
            child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            metadata = os.fstat(descriptor)
            sticky_system = metadata.st_uid == 0 and bool(metadata.st_mode & stat.S_ISVTX)
            if metadata.st_uid not in {0, os.getuid()} or (metadata.st_mode & 0o022 and not sticky_system):
                raise _refuse()
        yield descriptor
    finally:
        os.close(descriptor)


def _same_path(path: Path, descriptor: int) -> None:
    """Rewalk the path to reject renaming/replacement of the pinned directory."""
    with _open_directory(path) as observed:
        old, new = os.fstat(descriptor), os.fstat(observed)
        if (old.st_dev, old.st_ino) != (new.st_dev, new.st_ino):
            raise _refuse()


def _read_file(
    parent: int, name: str, *, mode: int, persistent: bool = True
) -> tuple[bytes, PersistentPathIdentity | None]:
    descriptor = os.open(name, _FILE_FLAGS, dir_fd=parent)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid != os.getuid()
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_size > MAX_DOCUMENT_BYTES
        ):
            raise _refuse()
        identity = observe_identity_fd(descriptor) if persistent else None
        parts: list[bytes] = []
        count = 0
        while chunk := os.read(descriptor, min(65536, MAX_DOCUMENT_BYTES + 1 - count)):
            parts.append(chunk)
            count += len(chunk)
            if count > MAX_DOCUMENT_BYTES:
                raise _refuse()
        after = os.fstat(descriptor)
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_ctime_ns, before.st_size) != (
            after.st_dev,
            after.st_ino,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_size,
        ) or (current.st_dev, current.st_ino) != (after.st_dev, after.st_ino):
            raise _refuse()
        return b"".join(parts), identity
    finally:
        os.close(descriptor)


def _nonfinite(_value: str) -> object:
    raise _refuse()


def _object(raw: bytes) -> dict[str, object]:
    result = json.loads(raw, object_pairs_hook=unique_json_object, parse_constant=_nonfinite)
    if type(result) is not dict:
        raise _refuse()
    # JSON object keys are strings; the exact dict check rejects other roots.
    return cast("dict[str, object]", result)


def load_intent(path: Path) -> TetherIntent:
    """Load one owner-only ordinary JSON request; never execute imported content."""
    try:
        if not path.is_absolute() or path.name in {"", ".", ".."}:
            raise _refuse()
        with _open_directory(path.parent) as parent:
            _directory_metadata(parent, owned=True)
            raw, _identity = _read_file(parent, path.name, mode=_PRIVATE_FILE, persistent=False)
            _same_path(path.parent, parent)
        intent = TetherIntent.model_validate_json(canonical_bytes(_object(raw)), strict=True)
        # Validate cross-object admission before original initialization writes
        # anything. Live host-address exclusion remains a preparation check.
        from lychd.domain.tether.compiler import compile_tether
        from lychd.domain.tether.models import TetherSnapshot

        compile_tether(
            rune=intent.rune,
            snapshot=TetherSnapshot(
                installation_epoch="00" * 16,
                offered_peers=intent.offered_peers,
                attachments=intent.attachments,
            ),
            runtime_root=Path("/run/user/1000/lychd-tether"),
            config_root=Path("/var/lib/lychd/tether/runtime"),
            core_web_port=intent.web_port,
            consumer_uid=1000,
            forbidden_backend_addresses=(),
        )
    except (OSError, ValueError, TypeError, RecursionError, PathIdentityError, ValidationError, TetherError):
        msg = "Tether public intent was refused"
        raise TetherError(msg) from None
    else:
        return intent


class TetherCustody:
    """Own only receipt-recorded persistent files beneath one dedicated root."""

    def __init__(self, root: Path = PATH_TETHER_STATE_DIR) -> None:
        """Select a persistent root without creating or adopting it."""
        if not root.is_absolute() or ".." in root.parts or root.name in {"", ".", ".."}:
            raise _refuse()
        self.root = root

    @contextmanager
    def _locked(self) -> Generator[tuple[int, _Receipt]]:
        try:
            with _open_directory(self.root) as descriptor:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                receipt = self._attest(descriptor)
                _same_path(self.root, descriptor)
                yield descriptor, receipt
                _same_path(self.root, descriptor)
        except (OSError, ValueError, TypeError, RecursionError, PathIdentityError, ValidationError):
            raise _refuse() from None

    def initialize(self) -> bool:
        """Create one absent root and receipt; existing roots must already attest."""
        try:
            with _open_directory(self.root.parent) as parent:
                _directory_metadata(parent, owned=True)
                fcntl.flock(parent, fcntl.LOCK_EX)
                try:
                    os.stat(self.root.name, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    os.mkdir(self.root.name, mode=_PRIVATE_DIRECTORY, dir_fd=parent)
                    os.fsync(parent)
                    created = True
                else:
                    created = False
                _same_path(self.root.parent, parent)
                with _open_directory(self.root) as descriptor:
                    fcntl.flock(descriptor, fcntl.LOCK_EX)
                    if not created:
                        self._attest(descriptor)
                        return False
                    _directory_metadata(descriptor, owned=True, mode=_PRIVATE_DIRECTORY)
                    if os.listdir(descriptor):  # noqa: PTH208 - enumerate the pinned directory descriptor
                        raise _refuse()
                    receipt = _Receipt(
                        schema="lychd.tether.custody",
                        version=1,
                        revision=1,
                        root=observe_identity_fd(descriptor),
                        directories={},
                        files={},
                    )
                    self._replace(descriptor, _RECEIPT, canonical_bytes(receipt), mode=_PRIVATE_FILE)
                    self._attest(descriptor)
                    _same_path(self.root, descriptor)
                    return True
        except (OSError, ValueError, TypeError, RecursionError, PathIdentityError, ValidationError):
            raise _refuse() from None

    def _attest(self, descriptor: int) -> _Receipt:  # noqa: C901 - exact receipt and complete-tree attestation
        _directory_metadata(descriptor, owned=True, mode=_PRIVATE_DIRECTORY)
        raw, _ = _read_file(descriptor, _RECEIPT, mode=_PRIVATE_FILE)
        receipt = _Receipt.model_validate(_object(raw))
        if raw != canonical_bytes(receipt):
            raise _refuse()
        if type(_object(raw).get("version")) is not int or receipt.root != observe_identity_fd(descriptor):
            raise _refuse()
        if len(receipt.directories) + len(receipt.files) > _MAX_PATHS or set(receipt.directories).intersection(
            receipt.files
        ):
            raise _refuse()
        for name in (*receipt.directories, *receipt.files):
            _relative(name)
            parent = Path(name).parent.as_posix()
            if parent != "." and parent not in receipt.directories:
                raise _refuse()
        expected: dict[str, set[str]] = {".": {_RECEIPT}}
        for name in receipt.directories:
            expected[name] = set()
        for name in (*receipt.directories, *receipt.files):
            relative = Path(name)
            expected[relative.parent.as_posix()].add(relative.name)
        for name, children in expected.items():
            with self._child_directory(descriptor, name, receipt) as child:
                if set(os.listdir(child)) != children:  # noqa: PTH208 - descriptor-relative inventory
                    raise _refuse()
        for name, record in receipt.files.items():
            with self._child_directory(descriptor, Path(name).parent.as_posix(), receipt) as parent:
                content, identity = _read_file(parent, Path(name).name, mode=record.mode)
                if record.identity != identity or hashlib.sha256(content).hexdigest() != record.digest:
                    raise _refuse()
        return receipt

    @contextmanager
    def _child_directory(self, root: int, name: str, receipt: _Receipt) -> Generator[int]:
        # A duplicate shares the directory open-file description and its readdir
        # state/cache. Open the pinned directory itself afresh so enumeration
        # after atomic publication sees the current inventory on overlayfs too.
        descriptor = os.open(".", _DIRECTORY_FLAGS, dir_fd=root)
        try:
            if name != ".":
                partial = Path()
                for component in Path(name).parts:
                    partial /= component
                    record = receipt.directories.get(partial.as_posix())
                    if record is None:
                        raise _refuse()
                    child = os.open(component, _DIRECTORY_FLAGS, dir_fd=descriptor)
                    os.close(descriptor)
                    descriptor = child
                    _directory_metadata(descriptor, owned=True, mode=record.mode)
                    if observe_identity_fd(descriptor) != record.identity:
                        raise _refuse()
            yield descriptor
        finally:
            os.close(descriptor)

    @staticmethod
    def _replace(
        parent: int, name: str, content: bytes, *, mode: int, expected: _File | None = None
    ) -> PersistentPathIdentity:
        temporary = ".tether-write-" + uuid.uuid4().hex
        descriptor = os.open(
            temporary, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, _PRIVATE_FILE, dir_fd=parent
        )
        try:
            os.fchmod(descriptor, mode)
            remaining = memoryview(content)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise _refuse()
                remaining = remaining[written:]
            os.fsync(descriptor)
            identity = observe_identity_fd(descriptor)
            if expected is None:
                try:
                    os.stat(name, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise _refuse()
            else:
                old, old_identity = _read_file(parent, name, mode=expected.mode)
                if old_identity != expected.identity or hashlib.sha256(old).hexdigest() != expected.digest:
                    raise _refuse()
            named = os.stat(temporary, dir_fd=parent, follow_symlinks=False)
            pinned = os.fstat(descriptor)
            if (named.st_dev, named.st_ino) != (pinned.st_dev, pinned.st_ino):
                raise _refuse()
            os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
            os.fsync(parent)
            return identity
        finally:
            os.close(descriptor)
            # Ambiguous residue is retained and refused; never broad cleanup.

    def _commit(self, root: int, previous: _Receipt, receipt: _Receipt) -> None:
        _same_path(self.root, root)
        raw, identity = _read_file(root, _RECEIPT, mode=_PRIVATE_FILE)
        if raw != canonical_bytes(previous) or identity is None:
            raise _refuse()
        expected = _File(identity=identity, mode=_PRIVATE_FILE, digest=hashlib.sha256(raw).hexdigest(), immutable=False)
        self._replace(root, _RECEIPT, canonical_bytes(receipt), mode=_PRIVATE_FILE, expected=expected)
        self._attest(root)

    def attest(self) -> None:
        """Verify exact ownership, bytes and inventory; do not repair drift."""
        with self._locked():
            pass

    def read(self, name: str) -> dict[str, object] | None:
        """Read an owned JSON record, or report a truly absent unowned name."""
        relative = _relative(name)
        with self._locked() as (root, receipt):
            raw = self._read_record(root, receipt, relative)
            return None if raw is None else _object(raw)

    def _read_record(self, root: int, receipt: _Receipt, relative: str) -> bytes | None:
        record = receipt.files.get(relative)
        if record is None:
            if relative in receipt.directories:
                raise _refuse()
            return None
        with self._child_directory(root, Path(relative).parent.as_posix(), receipt) as parent:
            raw, identity = _read_file(parent, Path(relative).name, mode=record.mode)
            if identity != record.identity or hashlib.sha256(raw).hexdigest() != record.digest:
                raise _refuse()
            return raw

    @contextmanager
    def records_snapshot(self) -> Generator[CustodyRecords]:
        """Bracket bounded reads with fresh complete-tree and unchanged-receipt proof.

        The caller may perform read-only backend observations while this lock is
        held. It must not call custody mutations or acquire this lock again.
        Returned records are detached values, never continuing effect authority.
        """
        with self._locked() as (root, receipt):
            original, identity = _read_file(root, _RECEIPT, mode=_PRIVATE_FILE)
            if original != canonical_bytes(receipt) or identity is None:
                raise _refuse()

            def read_owned(name: str) -> bytes | None:
                return self._read_record(root, receipt, name)

            view = _RecordView(tuple(sorted(receipt.files)), read_owned)
            try:
                yield view
            finally:
                view.close()
                current = self._attest(root)
                raw, current_identity = _read_file(root, _RECEIPT, mode=_PRIVATE_FILE)
                if canonical_bytes(current) != original or raw != original or current_identity != identity:
                    raise _refuse()

    def write(self, name: str, value: dict[str, object], *, immutable: bool = False) -> bool:
        """Atomically replace one owned private record and then its ownership receipt."""
        return self._publish(Path(_relative(name)), value, public=False, immutable=immutable)

    def publish(self, relative: Path, value: dict[str, object], *, public: bool = False) -> bool:
        """Publish a role document only below already receipted directories."""
        return self._publish(relative, value, public=public, immutable=False)

    def _publish(self, relative: Path, value: dict[str, object], *, public: bool, immutable: bool) -> bool:  # noqa: C901 - guarded two-record commit
        name = _relative(relative)
        if type(value) is not dict:
            raise _refuse()
        content = canonical_bytes(value)
        mode = _PUBLIC_FILE if public else _PRIVATE_FILE
        with self._locked() as (root, receipt):
            if name in receipt.directories:
                raise _refuse()
            current = receipt.files.get(name)
            if current is None:
                self._reserve_entry(receipt)
            if current is not None:
                if current.mode != mode or (immutable and not current.immutable):
                    raise _refuse()
                if current.digest == hashlib.sha256(content).hexdigest():
                    return False
                if current.immutable:
                    raise _refuse()
            with self._child_directory(root, relative.parent.as_posix(), receipt) as parent:
                _directory_metadata(parent, owned=True)
                if current is None:
                    try:
                        os.stat(relative.name, dir_fd=parent, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        raise _refuse()
                else:
                    old, identity = _read_file(parent, relative.name, mode=current.mode)
                    if identity != current.identity or hashlib.sha256(old).hexdigest() != current.digest:
                        raise _refuse()
                _same_path(self.root / relative.parent, parent)
                identity = self._replace(parent, relative.name, content, mode=mode, expected=current)
                _same_path(self.root / relative.parent, parent)
            files = dict(receipt.files)
            files[name] = _File(
                identity=identity,
                mode=mode,
                digest=hashlib.sha256(content).hexdigest(),
                immutable=immutable or bool(current and current.immutable),
            )
            self._commit(root, receipt, receipt.model_copy(update={"revision": receipt.revision + 1, "files": files}))
            return True

    def directory(self, name: str, *, public: bool = False) -> Path:
        """Create and receipt each missing directory before returning its path."""
        relative = _relative(name)
        mode = _PUBLIC_DIRECTORY if public else _PRIVATE_DIRECTORY
        with self._locked() as (root, initial_receipt):
            receipt = initial_receipt
            partial = Path()
            for component in Path(relative).parts:
                parent_name = partial.as_posix()
                partial /= component
                child_name = partial.as_posix()
                existing = receipt.directories.get(child_name)
                if existing is not None:
                    if existing.mode != mode:
                        raise _refuse()
                    continue
                if child_name in receipt.files:
                    raise _refuse()
                self._reserve_entry(receipt)
                with self._child_directory(root, parent_name, receipt) as parent:
                    _same_path(self.root / Path(parent_name), parent)
                    os.mkdir(component, mode=mode, dir_fd=parent)
                    child = os.open(component, _DIRECTORY_FLAGS, dir_fd=parent)
                    try:
                        # Mode adjustment is confined to the just-created inode.
                        os.fchmod(child, mode)
                        identity = observe_identity_fd(child)
                        _directory_metadata(child, owned=True, mode=mode)
                        os.fsync(child)
                    finally:
                        os.close(child)
                    os.fsync(parent)
                directories = dict(receipt.directories)
                directories[child_name] = _Directory(identity=identity, mode=mode)
                updated = receipt.model_copy(update={"revision": receipt.revision + 1, "directories": directories})
                self._commit(root, receipt, updated)
                receipt = updated
            return self.root / relative

    @staticmethod
    def _reserve_entry(receipt: _Receipt) -> None:
        """Refuse bounded inventory exhaustion before creating any new object."""
        if len(receipt.directories) + len(receipt.files) >= _MAX_PATHS:
            raise _refuse()
        if len(canonical_bytes(receipt)) + _RECEIPT_ENTRY_RESERVE > MAX_DOCUMENT_BYTES:
            raise _refuse()

    def known_paths(self) -> tuple[Path, ...]:
        """Return exact receipted paths, including root and its receipt."""
        with self._locked() as (_root, receipt):
            return (
                self.root,
                self.root / _RECEIPT,
                *(self.root / name for name in sorted((*receipt.directories, *receipt.files))),
            )


__all__ = ("TetherCustody", "TetherError", "TetherIntent", "digest", "load_intent")
