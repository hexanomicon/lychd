"""Scribe ownership receipt validation, encoding, and generation fingerprints."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from lychd.system.services.scribe.errors import ScribeOwnershipError
from lychd.system.services.scribe.models import (
    BindingWriteSet,
    OwnershipManifest,
    SitePlan,
)
from lychd.system.services.scribe.storage import capture_path_state

OWNERSHIP_FILENAME = ".lychd-owned.json"
AUTHORITY_MODE = 0o600
ABSENT_AUTHORITY_BYTES = b"\0absent-authority"


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON keys instead of silently accepting the last one."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = f"Duplicate ownership manifest key: {key!r}."
            raise ValueError(msg)
        result[key] = value
    return result


class BindingAuthority:
    """Read and validate the exact receipt that grants replacement authority."""

    def __init__(self, output_dir: Path) -> None:
        """Bind authority to the Quadlet site that contains its receipt."""
        self._output_dir = output_dir

    @property
    def path(self) -> Path:
        """Return the hidden authority receipt path."""
        return self._output_dir / OWNERSHIP_FILENAME

    def load(self) -> OwnershipManifest:
        """Load a validated receipt, or an empty manifest when none exists."""
        return self.snapshot()[1]

    def snapshot(self) -> tuple[bytes, OwnershipManifest]:
        """Return exact authority bytes and the manifest parsed from those bytes."""
        if not os.path.lexists(self.path):
            return ABSENT_AUTHORITY_BYTES, OwnershipManifest(version=1)
        try:
            content = self.read()
            return content, self.parse(content)
        except ScribeOwnershipError:
            raise
        except (OSError, UnicodeError, ValueError, ValidationError, TypeError) as exc:
            msg = f"Invalid Scribe ownership manifest at {self.path}: {exc}"
            raise ScribeOwnershipError(msg) from exc

    @staticmethod
    def parse(content: bytes) -> OwnershipManifest:
        """Parse one already authority-checked manifest byte sequence."""
        decoded = content.decode("utf-8")
        raw = json.loads(decoded, object_pairs_hook=_unique_json_object)
        return OwnershipManifest.model_validate(raw)

    def read(self) -> bytes:
        """Read one internally coherent no-follow authority observation."""
        try:
            state = capture_path_state(self.path)
        except OSError as exc:
            msg = f"Unsafe Scribe ownership manifest path: {self.path}."
            raise ScribeOwnershipError(msg) from exc
        if state is None or state.content is None:
            msg = f"Unsafe Scribe ownership manifest path: {self.path}."
            raise ScribeOwnershipError(msg)
        self.validate_metadata(
            self.path,
            mode=state.mode,
            user_id=state.user_id,
        )
        return state.content

    def validate_path(self) -> None:
        """Validate the live receipt after an atomic replacement."""
        try:
            state = capture_path_state(self.path)
        except OSError as exc:
            msg = f"Scribe ownership manifest is unavailable: {self.path}."
            raise ScribeOwnershipError(msg) from exc
        if state is None:
            msg = f"Scribe ownership manifest is unavailable: {self.path}."
            raise ScribeOwnershipError(msg)
        self.validate_metadata(
            self.path,
            mode=state.mode,
            user_id=state.user_id,
        )

    @staticmethod
    def validate_metadata(path: Path, *, mode: int, user_id: int) -> None:
        """Validate receipt authority from one pinned metadata observation."""
        if not stat.S_ISREG(mode):
            msg = f"Scribe ownership manifest must be a regular non-symlink file: {path}."
            raise ScribeOwnershipError(msg)
        current_uid = os.getuid()
        if user_id != current_uid:
            msg = f"Scribe ownership manifest must be owned by uid {current_uid}; found uid {user_id}: {path}."
            raise ScribeOwnershipError(msg)
        permission_mode = stat.S_IMODE(mode)
        if permission_mode != AUTHORITY_MODE:
            msg = f"Scribe ownership manifest must have mode 0600; found {permission_mode:04o}: {path}."
            raise ScribeOwnershipError(msg)

    @staticmethod
    def _validate_stat(path: Path, manifest_stat: os.stat_result) -> None:
        BindingAuthority.validate_metadata(
            path,
            mode=manifest_stat.st_mode,
            user_id=manifest_stat.st_uid,
        )

    @staticmethod
    def encode(ownership: OwnershipManifest) -> bytes:
        """Encode authority identically for preview and atomic commit."""
        return (json.dumps(ownership.model_dump(mode="json"), indent=2, sort_keys=True) + "\n").encode()

    @staticmethod
    def generation(*, authority: bytes, sources: Sequence[Path]) -> str:
        """Fingerprint the authority and exact source identities/content."""
        digest = hashlib.sha256(authority)
        for path in sorted(sources):
            digest.update(os.fsencode(path))
            try:
                state = capture_path_state(path)
            except OSError as exc:
                msg = f"Could not safely observe owned binding source: {path}."
                raise ScribeOwnershipError(msg) from exc
            if state is None:
                digest.update(b"\0missing")
                continue
            if state.content is None:
                msg = f"Owned binding source is not a regular file: {path}."
                raise ScribeOwnershipError(msg)
            digest.update(f"\0{state.device}:{state.inode}:".encode())
            digest.update(state.content)
        return digest.hexdigest()

    def observe(self, sources: Sequence[Path]) -> tuple[bytes, str]:
        """Read authority bytes and fingerprint one exact full source set."""
        authority, _ownership = self.snapshot()
        return authority, self.generation(authority=authority, sources=sources)

    def observed_generation(self, plans: Sequence[SitePlan]) -> str:
        """Fingerprint the live authority and every source a write set affects."""
        sources = tuple(
            plan.directory / name for plan in plans for name in sorted(plan.previous_names | frozenset(plan.files))
        )
        return self.observe(sources)[1]

    @classmethod
    def desired_generation(cls, write_set: BindingWriteSet) -> str:
        """Fingerprint exact desired paths, bytes, and resulting authority."""
        digest = hashlib.sha256(b"lychd-binding-desired-v1\0")
        for plan in sorted(write_set.plans, key=lambda item: os.fsencode(item.directory)):
            directory = os.fsencode(plan.directory)
            digest.update(len(directory).to_bytes(8, byteorder="big"))
            digest.update(directory)
            for name, content in sorted(plan.files.items()):
                encoded_name = os.fsencode(name)
                digest.update(len(encoded_name).to_bytes(8, byteorder="big"))
                digest.update(encoded_name)
                digest.update(len(content).to_bytes(8, byteorder="big"))
                digest.update(content)
        ownership = cls.encode(write_set.ownership)
        digest.update(len(ownership).to_bytes(8, byteorder="big"))
        digest.update(ownership)
        return digest.hexdigest()
