"""Owner-only persistence for a privileged deletion handoff."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from lychd.system.services.lifecycle.deletion_models import (
    BTRFS_FIRST_FREE_OBJECTID,
    BtrfsSubvolumeIdentity,
    DeletionPaths,
)
from lychd.system.services.lifecycle.models import LifecycleError
from lychd.system.services.lifecycle.paths import (
    is_within,
    lexically_normal,
    path_has_symlink_component,
)

_CHECKPOINT_MODE = 0o600
_CHECKPOINT_DIRECTORY_MODE = 0o700
_MAX_CHECKPOINT_BYTES = 64 * 1024
_FIRST_CONTROL_CODEPOINT = 32


class _CheckpointIdentity(BaseModel):
    """Strict on-disk form of one resumable storage identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mount_target: str
    top_level_mount: str
    source_device: str
    filesystem_uuid: str
    subvolume_uuid: str
    fs_root: str
    source_path: str
    subvolume_id: int

    @field_validator("filesystem_uuid", "subvolume_uuid")
    @classmethod
    def validate_uuid(cls, value: str) -> str:
        """Require one canonical Btrfs UUID selector."""
        normalized = str(UUID(value))
        if value.casefold() != normalized:
            msg = "Deletion checkpoint Btrfs UUID must be canonical."
            raise ValueError(msg)
        return normalized

    @field_validator("source_device")
    @classmethod
    def validate_device(cls, value: str) -> str:
        """Reject an empty or control-character-bearing source identity."""
        if not value or any(ord(character) < _FIRST_CONTROL_CODEPOINT for character in value):
            msg = "Deletion checkpoint source device is invalid."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_paths(self) -> _CheckpointIdentity:
        """Require narrow absolute paths and a non-top-level Btrfs fs-root."""
        for raw in (self.mount_target, self.source_path):
            path = Path(raw)
            if not lexically_normal(path) or path in {Path("/"), Path.home()}:
                msg = f"Deletion checkpoint contains an unsafe path: {raw}"
                raise ValueError(msg)
        top_level = Path(self.top_level_mount)
        if not lexically_normal(top_level):
            msg = "Deletion checkpoint contains an unsafe top-level mount."
            raise ValueError(msg)
        fs_root = PurePosixPath(self.fs_root)
        if not fs_root.is_absolute() or fs_root == PurePosixPath("/") or ".." in fs_root.parts:
            msg = "Deletion checkpoint contains an unsafe Btrfs fs-root."
            raise ValueError(msg)
        source_path = Path(self.source_path)
        expected_source = top_level.joinpath(*fs_root.parts[1:])
        if source_path != expected_source or not is_within(source_path, top_level):
            msg = "Deletion checkpoint Btrfs source mapping is inconsistent."
            raise ValueError(msg)
        if self.subvolume_id < BTRFS_FIRST_FREE_OBJECTID:
            msg = "Deletion checkpoint subvolume ID is in Btrfs's reserved range."
            raise ValueError(msg)
        return self


class _CheckpointDocument(BaseModel):
    """Owner-only deletion checkpoint document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[3] = 3
    identity: _CheckpointIdentity


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate checkpoint keys."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = f"Duplicate deletion checkpoint key: {key!r}."
            raise ValueError(msg)
        result[key] = value
    return result


class DeletionCheckpointStore:
    """Persist storage identity across an operator-performed privileged handoff."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        codex_root: Path | None = None,
    ) -> None:
        """Bind the checkpoint to the dedicated Codex."""
        if codex_root is None:
            codex_root = DeletionPaths.current().codex_root
        self.codex_root = codex_root
        self.path = path or codex_root / ".lychd-del-state.json"
        self._validate_location()

    @property
    def exists(self) -> bool:
        """Return whether the checkpoint exists without following links."""
        return os.path.lexists(self.path)

    def load(self) -> BtrfsSubvolumeIdentity | None:
        """Load and validate one owner-only checkpoint."""
        if not self.exists:
            return None
        content = self._read()
        try:
            raw = json.loads(content, object_pairs_hook=_unique_json_object)
            document = _CheckpointDocument.model_validate(raw)
        except (UnicodeError, ValueError, TypeError, ValidationError) as exc:
            msg = f"Invalid deletion checkpoint at {self.path}: {exc}"
            raise LifecycleError(msg) from exc
        identity = document.identity
        return BtrfsSubvolumeIdentity(
            mount_target=Path(identity.mount_target),
            top_level_mount=Path(identity.top_level_mount),
            source_device=identity.source_device,
            filesystem_uuid=identity.filesystem_uuid,
            subvolume_uuid=identity.subvolume_uuid,
            fs_root=identity.fs_root,
            source_path=Path(identity.source_path),
            subvolume_id=identity.subvolume_id,
        )

    def record(self, identity: BtrfsSubvolumeIdentity) -> None:
        """Atomically retain an attested identity before yielding to root."""
        current = self.load()
        if current is not None:
            if current != identity:
                msg = "Refusing to replace a different pending deletion identity."
                raise LifecycleError(msg)
            return
        self._ensure_parent()
        document = _CheckpointDocument(
            identity=_CheckpointIdentity(
                mount_target=str(identity.mount_target),
                top_level_mount=str(identity.top_level_mount),
                source_device=identity.source_device,
                filesystem_uuid=identity.filesystem_uuid,
                subvolume_uuid=identity.subvolume_uuid,
                fs_root=identity.fs_root,
                source_path=str(identity.source_path),
                subvolume_id=identity.subvolume_id,
            ),
        )
        content = (json.dumps(document.model_dump(mode="json"), indent=2, sort_keys=True) + "\n").encode()
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            dir=self.path.parent,
        )
        temporary = Path(raw_path)
        try:
            os.fchmod(descriptor, _CHECKPOINT_MODE)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
            self._fsync_directory(self.path.parent)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)

    def _read(self) -> bytes:
        if symlink := path_has_symlink_component(self.path):
            msg = f"Deletion checkpoint traverses an untrusted symlink: {symlink}"
            raise LifecycleError(msg)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = -1
        try:
            descriptor = os.open(self.path, flags)
            metadata = os.fstat(descriptor)
            self._validate_metadata(metadata)
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = -1
                content = stream.read(_MAX_CHECKPOINT_BYTES + 1)
        except OSError as exc:
            msg = f"Cannot read deletion checkpoint safely: {self.path}"
            raise LifecycleError(msg) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        if len(content) > _MAX_CHECKPOINT_BYTES:
            msg = f"Deletion checkpoint exceeds {_MAX_CHECKPOINT_BYTES} bytes."
            raise LifecycleError(msg)
        return content

    def _validate_location(self) -> None:
        if (
            not lexically_normal(self.codex_root)
            or not lexically_normal(self.path)
            or not is_within(self.path, self.codex_root)
            or self.path == self.codex_root
            or self.codex_root in {Path("/"), Path.home()}
        ):
            msg = f"Deletion checkpoint is outside bounded Codex authority: {self.path}"
            raise LifecycleError(msg)

    def _ensure_parent(self) -> None:
        parent = self.path.parent
        if symlink := path_has_symlink_component(parent):
            msg = f"Deletion checkpoint parent traverses an untrusted symlink: {symlink}"
            raise LifecycleError(msg)
        if not os.path.lexists(parent):
            if not parent.parent.exists():
                msg = f"Deletion checkpoint parent namespace is absent: {parent.parent}"
                raise LifecycleError(msg)
            parent.mkdir(mode=_CHECKPOINT_DIRECTORY_MODE, exist_ok=False)
        metadata = parent.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or parent.is_symlink() or metadata.st_uid != os.getuid():
            msg = f"Deletion checkpoint parent is not a trusted user directory: {parent}"
            raise LifecycleError(msg)

    def _validate_metadata(self, metadata: os.stat_result) -> None:
        if not stat.S_ISREG(metadata.st_mode):
            msg = f"Deletion checkpoint must be a regular file: {self.path}"
            raise LifecycleError(msg)
        if metadata.st_uid != os.getuid():
            msg = f"Deletion checkpoint must be owned by uid {os.getuid()}: {self.path}"
            raise LifecycleError(msg)
        if stat.S_IMODE(metadata.st_mode) != _CHECKPOINT_MODE:
            msg = f"Deletion checkpoint must have mode 0600: {self.path}"
            raise LifecycleError(msg)
        if metadata.st_size > _MAX_CHECKPOINT_BYTES:
            msg = f"Deletion checkpoint exceeds {_MAX_CHECKPOINT_BYTES} bytes."
            raise LifecycleError(msg)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


__all__ = ("DeletionCheckpointStore",)
