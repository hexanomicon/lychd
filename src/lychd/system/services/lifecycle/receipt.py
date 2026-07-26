"""Owner-only initialization receipts and exact reversible cleanup."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from lychd.system.services.lifecycle._authority import LifecycleAuthority, current_authority
from lychd.system.services.lifecycle.models import (
    CreatedBtrfsSubvolume,
    CreatedDirectory,
    CreatedResources,
    DedicatedRootIdentity,
    LifecycleAction,
    LifecycleDisposition,
    LifecycleError,
    LifecyclePlan,
    LifecycleResourceKind,
)
from lychd.system.services.lifecycle.mount_identity import (
    directory_identity_on_parent_mount,
)
from lychd.system.services.lifecycle.paths import (
    digest_file,
    is_allowed_init_directory,
    is_allowed_init_file,
    is_persistent_directory,
    is_shared_xdg_root,
    is_within,
    lexically_normal,
    path_has_symlink_component,
    validate_receipt_path,
)

_RECEIPT_MODE = 0o600
_MAX_RECEIPT_BYTES = 1024 * 1024
_SHA256_PREFIX = "sha256:"
_SHA256_HEX_LENGTH = 64
_UNKNOWN_PREVIEW_LIMIT = 3


class _ReceiptPath(BaseModel):
    """Stable kernel identity of one path created by initialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    device: int
    inode: int

    @model_validator(mode="after")
    def validate_identity(self) -> _ReceiptPath:
        """Require a meaningful device/inode pair."""
        if self.device < 0 or self.inode <= 0:
            msg = "Lifecycle path identity must contain a valid device and inode."
            raise ValueError(msg)
        return self


class _ReceiptDirectory(_ReceiptPath):
    """One exact init-created directory eligible for empty-only removal."""


class _ReceiptFile(_ReceiptPath):
    """One pristine generated file owned by initialization."""

    digest: str

    @field_validator("digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        """Require one canonical SHA-256 digest."""
        payload = value.removeprefix(_SHA256_PREFIX)
        if not value.startswith(_SHA256_PREFIX) or len(payload) != _SHA256_HEX_LENGTH:
            msg = "Lifecycle file digest must be canonical sha256."
            raise ValueError(msg)
        try:
            bytes.fromhex(payload)
        except ValueError as exc:
            msg = "Lifecycle file digest contains non-hexadecimal data."
            raise ValueError(msg) from exc
        return value


class _ReceiptSubvolume(_ReceiptPath):
    """One exact init-created Btrfs subvolume eligible for storage handoff."""

    subvolume_uuid: str
    subvolume_id: int

    @field_validator("subvolume_uuid")
    @classmethod
    def validate_uuid(cls, value: str) -> str:
        """Require one canonical Btrfs UUID."""
        normalized = str(UUID(value))
        if value.casefold() != normalized:
            message = "Lifecycle subvolume UUID must be canonical."
            raise ValueError(message)
        return normalized

    @field_validator("subvolume_id")
    @classmethod
    def validate_subvolume_id(cls, value: int) -> int:
        """Reject Btrfs's reserved object-ID range."""
        from lychd.system.btrfs_identity import BTRFS_FIRST_FREE_OBJECTID

        if value < BTRFS_FIRST_FREE_OBJECTID:
            message = "Lifecycle subvolume ID is in Btrfs's reserved range."
            raise ValueError(message)
        return value


class _LifecycleReceipt(BaseModel):
    """Owner-only record of removable resources created by ``lychd init``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1, 2] = 2
    dedicated_roots: tuple[_ReceiptDirectory, ...] = ()
    directories: tuple[_ReceiptDirectory, ...] = ()
    files: tuple[_ReceiptFile, ...] = ()
    subvolumes: tuple[_ReceiptSubvolume, ...] = ()

    @model_validator(mode="after")
    def validate_unique_paths(self) -> _LifecycleReceipt:
        """Reject authority unavailable to the declared schema and path overlap."""
        if self.version == 1 and self.subvolumes:
            msg = "Lifecycle receipt version 1 cannot carry Btrfs subvolume authority."
            raise ValueError(msg)
        dedicated_roots = [entry.path for entry in self.dedicated_roots]
        directories = [entry.path for entry in self.directories]
        files = [entry.path for entry in self.files]
        subvolumes = [entry.path for entry in self.subvolumes]
        if (
            len(set(dedicated_roots)) != len(dedicated_roots)
            or len(set(directories)) != len(directories)
            or len(set(files)) != len(files)
            or len(set(subvolumes)) != len(subvolumes)
        ):
            msg = "Lifecycle receipt contains duplicate paths."
            raise ValueError(msg)
        overlap = (
            set(directories).intersection(files)
            | set(directories).intersection(subvolumes)
            | set(files).intersection(subvolumes)
        )
        if overlap:
            msg = f"Lifecycle receipt path has conflicting kinds: {sorted(overlap)[0]}"
            raise ValueError(msg)
        return self


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON keys instead of accepting the final value."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = f"Duplicate lifecycle receipt key: {key!r}."
            raise ValueError(msg)
        result[key] = value
    return result


class LifecycleReceiptStore:
    """Read, validate, update, and consume initialization ownership."""

    def __init__(self, path: Path | None = None) -> None:
        """Bind the store to one owner-only receipt path."""
        self.path = current_authority().lifecycle_receipt if path is None else path

    @property
    def exists(self) -> bool:
        """Return whether a receipt path exists without following symlinks."""
        return os.path.lexists(self.path)

    def load(self) -> _LifecycleReceipt:
        """Load one bounded, owner-only receipt or return an empty record."""
        if not self.exists:
            return _LifecycleReceipt()
        content = self._read_receipt_bytes()
        if len(content) > _MAX_RECEIPT_BYTES:
            msg = f"Lifecycle receipt exceeds {_MAX_RECEIPT_BYTES} bytes: {self.path}"
            raise LifecycleError(msg)
        try:
            raw = json.loads(content, object_pairs_hook=_unique_json_object)
            receipt = _LifecycleReceipt.model_validate(raw)
        except (UnicodeError, ValueError, TypeError, ValidationError) as exc:
            msg = f"Invalid lifecycle receipt at {self.path}: {exc}"
            raise LifecycleError(msg) from exc
        authority = current_authority()
        for directory in receipt.directories:
            validate_receipt_path(
                Path(directory.path),
                kind=LifecycleResourceKind.DIRECTORY,
                authority=authority,
            )
        expected_roots = {
            authority.codex_root,
            authority.crypt_root,
            authority.cache_root,
        }
        for root in receipt.dedicated_roots:
            path = Path(root.path)
            if path not in expected_roots:
                msg = f"Lifecycle receipt contains an unknown dedicated root: {path}"
                raise LifecycleError(msg)
        for entry in receipt.files:
            validate_receipt_path(
                Path(entry.path),
                kind=LifecycleResourceKind.FILE,
                authority=authority,
            )
        for entry in receipt.subvolumes:
            path = Path(entry.path)
            if path != authority.postgres_data:
                message = f"Lifecycle receipt contains an unknown Btrfs subvolume: {path}"
                raise LifecycleError(message)
            validate_receipt_path(
                path,
                kind=LifecycleResourceKind.DIRECTORY,
                authority=authority,
            )
        return receipt

    def _read_receipt_bytes(self) -> bytes:
        """Read a bounded receipt through a no-follow descriptor."""
        authority = current_authority()
        if not lexically_normal(self.path) or not is_within(self.path, authority.codex_root):
            msg = f"Lifecycle receipt is outside the current Codex authority: {self.path}"
            raise LifecycleError(msg)
        if symlink := path_has_symlink_component(self.path):
            msg = f"Unsafe lifecycle receipt path component: {symlink}"
            raise LifecycleError(msg)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.path, flags)
        except OSError as exc:
            msg = f"Unsafe lifecycle receipt path: {self.path}"
            raise LifecycleError(msg) from exc
        try:
            metadata = os.fstat(descriptor)
            self._validate_receipt_metadata(metadata)
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = -1
                try:
                    return stream.read(_MAX_RECEIPT_BYTES + 1)
                except OSError as exc:
                    msg = f"Cannot read lifecycle receipt safely: {self.path}"
                    raise LifecycleError(msg) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def _validate_receipt_metadata(self, metadata: os.stat_result) -> None:
        """Validate receipt authority metadata outside the descriptor read."""
        if not stat.S_ISREG(metadata.st_mode):
            msg = f"Lifecycle receipt must be a regular file: {self.path}"
            raise LifecycleError(msg)
        if metadata.st_uid != os.getuid():
            msg = f"Lifecycle receipt must be owned by uid {os.getuid()}: {self.path}"
            raise LifecycleError(msg)
        if stat.S_IMODE(metadata.st_mode) != _RECEIPT_MODE:
            msg = f"Lifecycle receipt must have mode 0600: {self.path}"
            raise LifecycleError(msg)
        if metadata.st_size > _MAX_RECEIPT_BYTES:
            msg = f"Lifecycle receipt exceeds {_MAX_RECEIPT_BYTES} bytes: {self.path}"
            raise LifecycleError(msg)

    def record(
        self,
        resources: CreatedResources,
        *,
        attest_dedicated_roots: bool = False,
    ) -> None:
        """Merge one init effect and optionally seal the dedicated-root authority."""
        current = self.load()
        authority = current_authority()
        directories = {Path(entry.path): entry for entry in current.directories}
        files = {Path(entry.path): entry for entry in current.files}
        subvolumes = {Path(entry.path): entry for entry in current.subvolumes}
        created_directory_by_path = {identity.path: identity for identity in resources.directory_identities}
        for directory in resources.directories:
            if is_shared_xdg_root(
                directory,
                authority=authority,
            ) or is_persistent_directory(directory, authority=authority):
                continue
            identity = created_directory_by_path.get(directory)
            directories[directory] = (
                self._directory_entry(directory, authority=authority)
                if identity is None
                else self._created_directory_entry(
                    identity,
                    authority=authority,
                )
            )
        for path in resources.files:
            files[path] = self._file_entry(path, authority=authority)
        for subvolume in resources.subvolumes:
            subvolumes[subvolume.path] = self._subvolume_entry(
                subvolume,
                authority=authority,
            )
        dedicated_roots = current.dedicated_roots
        if attest_dedicated_roots:
            dedicated_roots = tuple(
                self._dedicated_root_entry(root, authority=authority)
                for root in self._expected_dedicated_roots(authority)
            )
        next_receipt = _LifecycleReceipt(
            version=2,
            dedicated_roots=dedicated_roots,
            directories=tuple(directories[path] for path in sorted(directories)),
            files=tuple(files[path] for path in sorted(files)),
            subvolumes=tuple(subvolumes[path] for path in sorted(subvolumes)),
        )
        if next_receipt == current and self.exists:
            return
        self._write(next_receipt)

    def seal_dedicated_roots(self) -> None:
        """Commit the final init attestation after every root exists."""
        self.record(CreatedResources(), attest_dedicated_roots=True)

    def created_subvolume(
        self,
        path: Path,
    ) -> CreatedBtrfsSubvolume | None:
        """Return init-issued subvolume authority for one exact path."""
        receipt = self.load()
        matches = tuple(entry for entry in receipt.subvolumes if Path(entry.path) == path)
        if not matches:
            return None
        if len(matches) != 1:
            message = f"Lifecycle receipt contains ambiguous Btrfs subvolume authority: {path}"
            raise LifecycleError(message)
        entry = matches[0]
        return CreatedBtrfsSubvolume(
            path=path,
            device=entry.device,
            inode=entry.inode,
            subvolume_uuid=entry.subvolume_uuid,
            subvolume_id=entry.subvolume_id,
        )

    def plan_dedicated_root_attestation(self) -> LifecycleAction:
        """Plan the final init seal over all exact dedicated root identities."""
        authority = current_authority()
        expected = self._expected_dedicated_roots(authority)
        receipt = self.load()
        current: list[_ReceiptDirectory] = []
        missing: list[Path] = []
        for root in expected:
            if not os.path.lexists(root):
                missing.append(root)
                continue
            try:
                current.append(self._dedicated_root_entry(root, authority=authority))
            except LifecycleError as exc:
                return LifecycleAction(
                    LifecycleDisposition.BLOCKED,
                    LifecycleResourceKind.RECEIPT,
                    str(self.path),
                    f"dedicated-root authority cannot be sealed: {exc}",
                )
        if missing:
            return LifecycleAction(
                LifecycleDisposition.WOULD_CREATE,
                LifecycleResourceKind.RECEIPT,
                str(self.path),
                ("after creation, deliberately adopt the exact dedicated XDG roots as recursively removable"),
            )
        current_identities = tuple(current)
        if receipt.dedicated_roots == current_identities:
            return LifecycleAction(
                LifecycleDisposition.PRESERVE,
                LifecycleResourceKind.RECEIPT,
                str(self.path),
                "dedicated-root authority matches the current device and inode identities",
            )
        return LifecycleAction(
            LifecycleDisposition.WOULD_CREATE,
            LifecycleResourceKind.RECEIPT,
            str(self.path),
            (
                "successful init will deliberately adopt these exact dedicated XDG "
                "roots as recursively removable and refresh their device/inode seal"
            ),
        )

    def require_dedicated_root_identities(
        self,
        expected_roots: tuple[Path, ...],
    ) -> tuple[DedicatedRootIdentity, ...]:
        """Return current receipt-bound identities or fail closed."""
        if len(set(expected_roots)) != len(expected_roots):
            msg = "Dedicated root authority request contains duplicate roots."
            raise LifecycleError(msg)
        receipt = self.load()
        recorded = {Path(entry.path): entry for entry in receipt.dedicated_roots}
        if set(recorded) != set(expected_roots):
            msg = (
                "Lifecycle receipt does not authorize the exact dedicated-root set; "
                "run `lychd init` successfully before deletion."
            )
            raise LifecycleError(msg)

        identities: list[DedicatedRootIdentity] = []
        for root in expected_roots:
            entry = recorded[root]
            if not os.path.lexists(root):
                identities.append(
                    DedicatedRootIdentity(
                        path=root,
                        device=entry.device,
                        inode=entry.inode,
                    )
                )
                continue
            if symlink := path_has_symlink_component(root):
                msg = f"Dedicated root traverses an untrusted symlink component: {symlink}"
                raise LifecycleError(msg)
            metadata = directory_identity_on_parent_mount(root)
            if metadata.st_uid != os.getuid():
                msg = f"Dedicated root is no longer a safe owner directory: {root}"
                raise LifecycleError(msg)
            if metadata.st_dev != entry.device or metadata.st_ino != entry.inode:
                msg = f"Dedicated root identity drifted after initialization: {root}"
                raise LifecycleError(msg)
            identities.append(
                DedicatedRootIdentity(
                    path=root,
                    device=entry.device,
                    inode=entry.inode,
                )
            )
        return tuple(identities)

    @staticmethod
    def _expected_dedicated_roots(
        authority: LifecycleAuthority,
    ) -> tuple[Path, Path, Path]:
        """Return the canonical root set in final deletion order."""
        return (
            authority.crypt_root,
            authority.cache_root,
            authority.codex_root,
        )

    @staticmethod
    def _dedicated_root_entry(
        root: Path,
        *,
        authority: LifecycleAuthority,
    ) -> _ReceiptDirectory:
        """Capture one exact recursively removable root after successful init."""
        if root not in LifecycleReceiptStore._expected_dedicated_roots(authority):
            msg = f"Refusing to attest an unknown dedicated root: {root}"
            raise LifecycleError(msg)
        if not lexically_normal(root) or root in {Path("/"), Path.home()}:
            msg = f"Refusing to attest a broad or non-canonical dedicated root: {root}"
            raise LifecycleError(msg)
        if symlink := path_has_symlink_component(root):
            msg = f"Refusing to attest a root through a symlink component: {symlink}"
            raise LifecycleError(msg)
        try:
            metadata = directory_identity_on_parent_mount(root)
        except LifecycleError as exc:
            msg = f"Refusing to attest an unsafe dedicated root: {root}: {exc}"
            raise LifecycleError(msg) from exc
        if metadata.st_uid != os.getuid():
            msg = f"Refusing to attest an unsafe dedicated root: {root}"
            raise LifecycleError(msg)
        return _ReceiptDirectory(
            path=str(root),
            device=metadata.st_dev,
            inode=metadata.st_ino,
        )

    @staticmethod
    def _directory_entry(
        directory: Path,
        *,
        authority: LifecycleAuthority,
    ) -> _ReceiptDirectory:
        """Validate and capture one exact init-created directory."""
        if not is_allowed_init_directory(directory, authority=authority):
            msg = f"Initialization created an unreceiptable directory: {directory}"
            raise LifecycleError(msg)
        validate_receipt_path(
            directory,
            kind=LifecycleResourceKind.DIRECTORY,
            authority=authority,
        )
        if symlink := path_has_symlink_component(directory):
            msg = f"Refusing to record a directory through a symlink component: {symlink}"
            raise LifecycleError(msg)
        metadata = directory.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or directory.is_mount():
            msg = f"Refusing to record unsafe generated directory: {directory}"
            raise LifecycleError(msg)
        return _ReceiptDirectory(path=str(directory), device=metadata.st_dev, inode=metadata.st_ino)

    @staticmethod
    def _created_directory_entry(
        directory: CreatedDirectory,
        *,
        authority: LifecycleAuthority,
    ) -> _ReceiptDirectory:
        """Record the creation-time identity without restatting a replaceable path."""
        if not is_allowed_init_directory(directory.path, authority=authority):
            msg = f"Initialization created an unreceiptable directory: {directory.path}"
            raise LifecycleError(msg)
        validate_receipt_path(
            directory.path,
            kind=LifecycleResourceKind.DIRECTORY,
            authority=authority,
        )
        return _ReceiptDirectory(
            path=str(directory.path),
            device=directory.device,
            inode=directory.inode,
        )

    @staticmethod
    def _file_entry(path: Path, *, authority: LifecycleAuthority) -> _ReceiptFile:
        """Validate and capture one exact init-created generated file."""
        if not is_allowed_init_file(path, authority=authority):
            msg = f"Initialization created an unreceiptable file: {path}"
            raise LifecycleError(msg)
        validate_receipt_path(
            path,
            kind=LifecycleResourceKind.FILE,
            authority=authority,
        )
        if symlink := path_has_symlink_component(path):
            msg = f"Refusing to record a file through a symlink component: {symlink}"
            raise LifecycleError(msg)
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink() or metadata.st_uid != os.getuid():
            msg = f"Refusing to record non-regular generated file: {path}"
            raise LifecycleError(msg)
        return _ReceiptFile(
            path=str(path),
            device=metadata.st_dev,
            inode=metadata.st_ino,
            digest=digest_file(path),
        )

    @staticmethod
    def _subvolume_entry(
        subvolume: CreatedBtrfsSubvolume,
        *,
        authority: LifecycleAuthority,
    ) -> _ReceiptSubvolume:
        """Record one descriptor-attested creation without restatting its path."""
        path = subvolume.path
        if path != authority.postgres_data:
            message = f"Initialization created an unreceiptable Btrfs subvolume: {path}"
            raise LifecycleError(message)
        validate_receipt_path(
            path,
            kind=LifecycleResourceKind.DIRECTORY,
            authority=authority,
        )
        return _ReceiptSubvolume(
            path=str(path),
            device=subvolume.device,
            inode=subvolume.inode,
            subvolume_uuid=subvolume.subvolume_uuid,
            subvolume_id=subvolume.subvolume_id,
        )

    def plan_destroy(self, *, anticipated_removals: Iterable[Path] = ()) -> LifecyclePlan:
        """Plan removal of pristine, exactly recorded init resources."""
        receipt = self.load()
        actions = [self._plan_owned_file(entry) for entry in receipt.files]

        directory_entries = sorted(
            receipt.directories,
            key=lambda entry: (-len(Path(entry.path).parts), entry.path),
        )
        directories = [Path(entry.path) for entry in directory_entries]
        owned_paths = {
            *anticipated_removals,
            *(Path(entry.path) for entry in receipt.files),
            *directories,
        }
        authority = current_authority()
        durable_paths: set[Path] = {authority.postgres_data} if os.path.lexists(authority.postgres_data) else set()
        durable_ancestors = {
            directory for directory in directories if any(is_within(durable, directory) for durable in durable_paths)
        }
        actions.extend(
            self._plan_owned_directory(
                entry,
                owned_paths=owned_paths,
                preserve=Path(entry.path) in durable_ancestors,
            )
            for entry in directory_entries
        )

        if self.exists:
            actions.append(
                LifecycleAction(
                    LifecycleDisposition.WOULD_REMOVE,
                    LifecycleResourceKind.RECEIPT,
                    str(self.path),
                    "remove lifecycle authority after successful cleanup",
                )
            )

        actions.extend(
            self._known_preservations(
                recorded=owned_paths.union({self.path}),
                authority=authority,
            )
        )
        return LifecyclePlan.combine(LifecyclePlan(actions=tuple(actions)))

    def _plan_owned_file(self, entry: _ReceiptFile) -> LifecycleAction:  # noqa: PLR0911
        """Plan one digest-bound generated-file removal."""
        path = Path(entry.path)
        if symlink := path_has_symlink_component(path):
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.FILE,
                str(path),
                f"recorded file traverses an untrusted symlink component: {symlink}",
            )
        if not os.path.lexists(path):
            return LifecycleAction(
                LifecycleDisposition.PRESERVE,
                LifecycleResourceKind.FILE,
                str(path),
                "recorded file is already absent",
            )
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.FILE,
                str(path),
                "recorded file was replaced by a non-regular path",
            )
        if metadata.st_dev != entry.device or metadata.st_ino != entry.inode:
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.FILE,
                str(path),
                "recorded file identity changed after initialization",
            )
        if metadata.st_uid != os.getuid():
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.FILE,
                str(path),
                f"recorded file is now owned by uid {metadata.st_uid}",
            )
        if digest_file(path) != entry.digest:
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.FILE,
                str(path),
                "file was modified after initialization",
            )
        return LifecycleAction(
            LifecycleDisposition.WOULD_REMOVE,
            LifecycleResourceKind.FILE,
            str(path),
            "pristine file recorded as created by initialization",
        )

    def _plan_owned_directory(  # noqa: PLR0911
        self,
        entry: _ReceiptDirectory,
        *,
        owned_paths: set[Path],
        preserve: bool,
    ) -> LifecycleAction:
        """Plan one empty-only init-created directory removal."""
        path = Path(entry.path)
        if symlink := path_has_symlink_component(path):
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.DIRECTORY,
                str(path),
                f"recorded directory traverses an untrusted symlink component: {symlink}",
            )
        if not os.path.lexists(path):
            return LifecycleAction(
                LifecycleDisposition.PRESERVE,
                LifecycleResourceKind.DIRECTORY,
                str(path),
                "recorded directory is already absent",
            )
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.DIRECTORY,
                str(path),
                "recorded directory was replaced by an unsafe path",
            )
        if metadata.st_dev != entry.device or metadata.st_ino != entry.inode:
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.DIRECTORY,
                str(path),
                "recorded directory identity changed after initialization",
            )
        if metadata.st_uid != os.getuid():
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.DIRECTORY,
                str(path),
                f"recorded directory is now owned by uid {metadata.st_uid}",
            )
        if path.is_mount():
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.MOUNT,
                str(path),
                "a mount now occupies an init-created directory",
            )
        if preserve:
            return LifecycleAction(
                LifecycleDisposition.PRESERVE,
                LifecycleResourceKind.DIRECTORY,
                str(path),
                "ancestor of durable Postgres state; deletion never removes through it",
            )
        unknown = [child.name for child in path.iterdir() if child != self.path and child not in owned_paths]
        if unknown:
            summary = ", ".join(sorted(unknown)[:_UNKNOWN_PREVIEW_LIMIT])
            suffix = ", …" if len(unknown) > _UNKNOWN_PREVIEW_LIMIT else ""
            return LifecycleAction(
                LifecycleDisposition.BLOCKED,
                LifecycleResourceKind.DIRECTORY,
                str(path),
                f"directory contains unowned entries: {summary}{suffix}",
            )
        return LifecycleAction(
            LifecycleDisposition.WOULD_REMOVE,
            LifecycleResourceKind.DIRECTORY,
            str(path),
            "empty after removal of recorded children",
        )

    @staticmethod
    def _known_preservations(
        *,
        recorded: set[Path],
        authority: LifecycleAuthority,
    ) -> list[LifecycleAction]:
        """Report important pre-existing roots and mounts outside receipt authority."""
        actions: list[LifecycleAction] = []
        for path in (
            authority.codex_root,
            authority.crypt_root,
            authority.cache_root,
            authority.postgres_data,
            authority.systemd_units,
            authority.systemd_user_units,
        ):
            persistent = is_persistent_directory(path, authority=authority)
            if os.path.lexists(path) and (path not in recorded or persistent):
                kind = LifecycleResourceKind.MOUNT if path.is_mount() else LifecycleResourceKind.DIRECTORY
                detail = (
                    "external mount was not created by this initialization"
                    if kind is LifecycleResourceKind.MOUNT
                    else (
                        "durable Postgres path is outside deletion authority"
                        if persistent
                        else "path was not recorded as created by this initialization"
                    )
                )
                actions.append(LifecycleAction(LifecycleDisposition.PRESERVE, kind, str(path), detail))
        return actions

    def _write(self, receipt: _LifecycleReceipt) -> None:
        """Atomically write one owner-only lifecycle receipt."""
        authority = current_authority()
        if not lexically_normal(self.path) or not is_within(self.path, authority.codex_root):
            msg = f"Lifecycle receipt is outside the current Codex authority: {self.path}"
            raise LifecycleError(msg)
        if symlink := path_has_symlink_component(self.path.parent):
            msg = f"Unsafe lifecycle receipt parent component: {symlink}"
            raise LifecycleError(msg)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, raw_path = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        temporary = Path(raw_path)
        try:
            os.fchmod(descriptor, _RECEIPT_MODE)
            content = (json.dumps(receipt.model_dump(mode="json"), indent=2, sort_keys=True) + "\n").encode()
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

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        """Durably commit a directory-entry mutation."""
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
