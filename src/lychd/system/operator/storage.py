"""Read-only mount and filesystem inventory shared by status and deletion."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast
from uuid import UUID

from lychd.system.operator.process import ProcessInvocationError, ProcessRunner

_FINDMNT_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class MountObservation:
    """One target's exact mount status and covering filesystem."""

    target: Path
    exists: bool
    mounted: bool
    mount_target: Path | None = None
    source: str | None = None
    source_device: str | None = None
    filesystem: str | None = None
    filesystem_uuid: str | None = None
    fs_root: str | None = None
    subvolume_id: int | None = None
    options: tuple[str, ...] = ()
    top_level_mount: Path | None = None
    warning: str | None = None

    @property
    def read_only(self) -> bool | None:
        """Return the observed mount writability when findmnt supplied options."""
        if not self.options:
            return None
        return "ro" in self.options

    @property
    def btrfs_source_path(self) -> Path | None:
        """Map a Btrfs fs-root under an observed top-level mount.

        This proves only a filesystem path. Callers must still attest that the
        result is a Btrfs subvolume before requesting subvolume deletion.
        """
        if not self.mounted or self.filesystem != "btrfs" or self.top_level_mount is None or self.fs_root is None:
            return None
        relative = PurePosixPath(self.fs_root)
        if not relative.is_absolute() or ".." in relative.parts:
            return None
        return self.top_level_mount.joinpath(*relative.parts[1:])


@dataclass(frozen=True)
class MountTreeObservation:
    """Exact mountpoints found at or beneath a set of lexical roots."""

    roots: tuple[Path, ...]
    mounts: tuple[MountObservation, ...] = ()
    warning: str | None = None


class StorageInventoryService:
    """Inspect mounts through bounded ``findmnt`` calls without changing them."""

    def __init__(self, runner: ProcessRunner, *, findmnt_bin: str | None) -> None:
        """Bind one injected process port and an already-resolved executable."""
        self._runner = runner
        self._findmnt = findmnt_bin

    def observe(self, target: Path) -> MountObservation:
        """Describe an exact target and the filesystem currently covering it."""
        exists = os.path.lexists(target)
        mounted = os.path.ismount(target)
        if self._findmnt is None:
            return MountObservation(
                target=target,
                exists=exists,
                mounted=mounted,
                warning="findmnt is unavailable; filesystem identity is unknown",
            )

        argv = (
            self._findmnt,
            "--json",
            "--target",
            str(target),
            "--output",
            "TARGET,SOURCE,FSTYPE,OPTIONS,FSROOT,UUID",
        )
        try:
            result = self._runner.run(argv, timeout_s=_FINDMNT_TIMEOUT_SECONDS)
        except ProcessInvocationError as exc:
            return MountObservation(
                target=target,
                exists=exists,
                mounted=mounted,
                warning=f"findmnt probe failed: {exc}",
            )
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit {result.returncode}"
            return MountObservation(
                target=target,
                exists=exists,
                mounted=mounted,
                warning=f"findmnt could not inspect target: {detail}",
            )

        try:
            entry = self._first_filesystem(result.stdout)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return MountObservation(
                target=target,
                exists=exists,
                mounted=mounted,
                warning=f"findmnt returned invalid inventory: {exc}",
            )
        if entry is None:
            return MountObservation(
                target=target,
                exists=exists,
                mounted=mounted,
                warning="findmnt returned no covering filesystem",
            )

        source = self._text(entry, "source")
        source_device = source.split("[", maxsplit=1)[0] if source else None
        filesystem_uuid = self._canonical_uuid(entry)
        top_level = self._top_level_mount(source_device, filesystem_uuid) if source_device and filesystem_uuid else None
        options = tuple(part for part in (self._text(entry, "options") or "").split(",") if part)
        mount_target = self._path(entry, "target")
        return MountObservation(
            target=target,
            exists=exists,
            mounted=mounted,
            mount_target=mount_target,
            source=source,
            source_device=source_device,
            filesystem=self._text(entry, "fstype"),
            filesystem_uuid=filesystem_uuid,
            fs_root=self._text(entry, "fsroot"),
            subvolume_id=self._subvolume_id(options),
            options=options,
            top_level_mount=top_level,
        )

    def observe_under(self, roots: tuple[Path, ...]) -> MountTreeObservation:
        """Return every exact mountpoint lexically at or beneath ``roots``."""
        normalized_roots = tuple(sorted(set(roots)))
        if self._findmnt is None:
            return MountTreeObservation(
                roots=normalized_roots,
                warning="findmnt is unavailable; nested mount boundaries are unknown",
            )
        argv = (
            self._findmnt,
            "--json",
            "--output",
            "TARGET,SOURCE,FSTYPE,OPTIONS,FSROOT,UUID",
        )
        try:
            result = self._runner.run(argv, timeout_s=_FINDMNT_TIMEOUT_SECONDS)
            if result.returncode != 0:
                detail = result.stderr.strip() or f"exit {result.returncode}"
                return MountTreeObservation(
                    roots=normalized_roots,
                    warning=f"findmnt could not inspect mount tree: {detail}",
                )
            payload: object = json.loads(result.stdout)
            entries = self._filesystem_entries(payload)
        except (ProcessInvocationError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return MountTreeObservation(
                roots=normalized_roots,
                warning=f"findmnt returned invalid mount tree: {exc}",
            )

        top_levels = self._top_level_mounts(entries)
        mounts: list[MountObservation] = []
        for entry in entries:
            mount_target = self._path(entry, "target")
            if mount_target is None or not any(self._at_or_beneath(mount_target, root) for root in normalized_roots):
                continue
            source = self._text(entry, "source")
            source_device = source.split("[", maxsplit=1)[0] if source else None
            filesystem_uuid = self._canonical_uuid(entry)
            options = tuple(part for part in (self._text(entry, "options") or "").split(",") if part)
            mounts.append(
                MountObservation(
                    target=mount_target,
                    exists=os.path.lexists(mount_target),
                    mounted=True,
                    mount_target=mount_target,
                    source=source,
                    source_device=source_device,
                    filesystem=self._text(entry, "fstype"),
                    filesystem_uuid=filesystem_uuid,
                    fs_root=self._text(entry, "fsroot"),
                    subvolume_id=self._subvolume_id(options),
                    options=options,
                    top_level_mount=top_levels.get((source_device, filesystem_uuid)),
                )
            )
        return MountTreeObservation(
            roots=normalized_roots,
            mounts=tuple(sorted(mounts, key=lambda item: (len(item.target.parts), str(item.target)))),
        )

    def _top_level_mount(
        self,
        source_device: str,
        filesystem_uuid: str,
    ) -> Path | None:
        argv = (
            self._findmnt or "findmnt",
            "--json",
            "--source",
            source_device,
            "--output",
            "TARGET,SOURCE,FSTYPE,OPTIONS,FSROOT,UUID",
        )
        try:
            result = self._runner.run(argv, timeout_s=_FINDMNT_TIMEOUT_SECONDS)
            if result.returncode != 0:
                return None
            payload: object = json.loads(result.stdout)
            entries = self._filesystem_entries(payload)
        except (ProcessInvocationError, TypeError, ValueError, json.JSONDecodeError):
            return None
        return self._top_level_mounts(entries).get((source_device, filesystem_uuid))

    @classmethod
    def _top_level_mounts(
        cls,
        entries: list[dict[str, object]],
    ) -> dict[tuple[str | None, str | None], Path]:
        candidates: dict[tuple[str | None, str | None], list[Path]] = {}
        for entry in entries:
            if cls._text(entry, "fsroot") != "/" or (target := cls._path(entry, "target")) is None:
                continue
            source = cls._text(entry, "source")
            source_device = source.split("[", maxsplit=1)[0] if source else None
            filesystem_uuid = cls._canonical_uuid(entry)
            candidates.setdefault((source_device, filesystem_uuid), []).append(target)
        return {
            identity: min(paths, key=lambda path: (len(path.parts), str(path)))
            for identity, paths in candidates.items()
        }

    @classmethod
    def _first_filesystem(cls, content: str) -> dict[str, object] | None:
        payload: object = json.loads(content)
        entries = cls._filesystem_entries(payload)
        return entries[0] if entries else None

    @classmethod
    def _filesystem_entries(cls, payload: object) -> list[dict[str, object]]:
        if not isinstance(payload, dict):
            message = "top-level JSON value is not an object"
            raise TypeError(message)
        payload_dict = cast("dict[object, object]", payload)
        raw_filesystems = payload_dict.get("filesystems")
        if not isinstance(raw_filesystems, list):
            message = "filesystems is not a list"
            raise TypeError(message)
        entries: list[dict[str, object]] = []
        for raw in cast("list[object]", raw_filesystems):
            if not isinstance(raw, dict):
                message = "filesystem entry is not an object"
                raise TypeError(message)
            raw_dict = cast("dict[object, object]", raw)
            entry: dict[str, object] = {str(key).lower(): value for key, value in raw_dict.items()}
            entries.append(entry)
            children = entry.get("children")
            if children is not None:
                entries.extend(cls._filesystem_entries({"filesystems": children}))
        return entries

    @staticmethod
    def _text(entry: dict[str, object], key: str) -> str | None:
        value: Any = entry.get(key)
        return value if isinstance(value, str) and value else None

    @classmethod
    def _path(cls, entry: dict[str, object], key: str) -> Path | None:
        value = cls._text(entry, key)
        return Path(value) if value else None

    @classmethod
    def _canonical_uuid(cls, entry: dict[str, object]) -> str | None:
        """Return one canonical filesystem UUID supplied by ``findmnt``."""
        raw = cls._text(entry, "uuid")
        if raw is None:
            return None
        try:
            normalized = str(UUID(raw))
        except ValueError:
            return None
        return normalized if raw.casefold() == normalized else None

    @staticmethod
    def _subvolume_id(options: tuple[str, ...]) -> int | None:
        """Return the one positive Btrfs ``subvolid`` mount option."""
        values = [option.removeprefix("subvolid=") for option in options if option.startswith("subvolid=")]
        if len(values) != 1 or not values[0].isascii() or not values[0].isdecimal():
            return None
        parsed = int(values[0])
        return parsed if parsed > 0 else None

    @staticmethod
    def _at_or_beneath(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True
