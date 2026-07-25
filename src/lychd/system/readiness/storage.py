"""Btrfs substrate and PostgreSQL No-COW directory-policy probes."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Final

from lychd.system.operator.process import (
    ProcessInvocationError,
    ProcessRunner,
)
from lychd.system.operator.storage import StorageInventoryService
from lychd.system.path_safety import path_has_symlink_component
from lychd.system.readiness.models import (
    HostReadinessItem,
    ReadinessSection,
    ReadinessState,
)
from lychd.system.readiness.tools import HostReadinessTools

_PROBE_TIMEOUT_SECONDS: Final = 3.0


class StorageReadinessProbe:
    """Inspect the target's covering filesystem and current +C policy."""

    def __init__(
        self,
        *,
        runner: ProcessRunner,
        tools: HostReadinessTools,
        postgres_data: Path,
    ) -> None:
        """Bind storage observation to one exact PostgreSQL target."""
        self._runner = runner
        self._tools = tools
        self._postgres_data = postgres_data

    def inspect(self) -> tuple[HostReadinessItem, HostReadinessItem]:
        """Return Btrfs capability followed by exact PostgreSQL storage state."""
        if symlink := path_has_symlink_component(self._postgres_data):
            return (
                self._failed_btrfs("PostgreSQL storage shape is unsafe"),
                self._failed_postgres(f"symlink component is not trusted: {symlink}"),
            )
        if os.path.lexists(self._postgres_data):
            metadata = self._postgres_data.lstat()
            if not stat.S_ISDIR(metadata.st_mode):
                return (
                    self._failed_btrfs("PostgreSQL storage target is not a directory"),
                    self._failed_postgres("target exists but is not a directory"),
                )

        observation = StorageInventoryService(
            self._runner,
            findmnt_bin=self._tools.findmnt,
        ).observe(self._nearest_existing(self._postgres_data))
        filesystem = observation.filesystem
        missing_tools = tuple(
            name
            for name, value in (
                ("btrfs", self._tools.btrfs),
                ("chattr", self._tools.chattr),
                ("lsattr", self._tools.lsattr),
            )
            if value is None
        )
        btrfs = self._btrfs_item(
            filesystem=filesystem,
            warning=observation.warning,
            missing_tools=missing_tools,
        )
        postgres = self._postgres_item(
            filesystem=filesystem,
            warning=observation.warning,
            missing_tools=missing_tools,
            mount_options=observation.options,
        )
        return (btrfs, postgres)

    def _btrfs_item(
        self,
        *,
        filesystem: str | None,
        warning: str | None,
        missing_tools: tuple[str, ...],
    ) -> HostReadinessItem:
        if warning is not None or filesystem is None:
            state = ReadinessState.UNKNOWN
            detail = warning or "PostgreSQL substrate is unknown"
        elif filesystem == "btrfs" and not missing_tools:
            state = ReadinessState.VERIFIED
            detail = "PostgreSQL substrate eligible · toolchain available"
        elif filesystem == "btrfs":
            state = ReadinessState.DEGRADED
            detail = f"substrate detected · missing {', '.join(missing_tools)}"
        else:
            state = ReadinessState.OPTIONAL
            detail = f"PostgreSQL parent uses {filesystem} · directory fallback"
        return HostReadinessItem(
            key="btrfs",
            label="Btrfs",
            section=ReadinessSection.FOUNDATION,
            state=state,
            detail=detail,
        )

    def _postgres_item(
        self,
        *,
        filesystem: str | None,
        warning: str | None,
        missing_tools: tuple[str, ...],
        mount_options: tuple[str, ...],
    ) -> HostReadinessItem:
        if not os.path.lexists(self._postgres_data):
            if filesystem == "btrfs" and not missing_tools:
                detail = "absent · Btrfs subvolume + No-COW policy will be attempted"
            elif filesystem == "btrfs":
                detail = "absent · Btrfs directory fallback; No-COW toolchain incomplete"
            elif filesystem is not None:
                detail = f"absent · {filesystem} directory will be prepared; No-COW not applicable"
            else:
                detail = "absent · directory will be prepared; filesystem unknown"
            return HostReadinessItem(
                key="postgres-data",
                label="PostgreSQL data",
                section=ReadinessSection.FOUNDATION,
                state=ReadinessState.PLANNED,
                detail=detail,
                target=self._postgres_data,
            )

        if warning is not None or filesystem is None:
            return self._postgres(
                state=ReadinessState.UNKNOWN,
                detail=warning or "filesystem is unknown",
            )
        if filesystem != "btrfs":
            return self._postgres(
                state=ReadinessState.OPTIONAL,
                detail=f"{filesystem} directory · No-COW not applicable",
            )

        kind = "external Btrfs mount" if self._postgres_data.is_mount() else "Btrfs directory"
        nocow = True if "nodatacow" in mount_options else self._inspect_nocow()
        if nocow is True:
            return self._postgres(
                state=ReadinessState.VERIFIED,
                detail=f"{kind} · No-COW directory policy active",
            )
        if nocow is False:
            return self._postgres(
                state=ReadinessState.DEGRADED,
                detail=f"{kind} · COW active · existing storage preserved",
            )
        return self._postgres(
            state=ReadinessState.UNKNOWN,
            detail=f"{kind} · No-COW state unknown",
        )

    def _inspect_nocow(self) -> bool | None:
        lsattr = self._tools.lsattr
        if lsattr is None:
            return None
        try:
            result = self._runner.run(
                (lsattr, "-d", str(self._postgres_data)),
                timeout_s=_PROBE_TIMEOUT_SECONDS,
            )
        except ProcessInvocationError:
            return None
        if result.returncode != 0:
            return None
        fields = result.stdout.split()
        return "C" in fields[0] if fields else None

    def _postgres(
        self,
        *,
        state: ReadinessState,
        detail: str,
    ) -> HostReadinessItem:
        return HostReadinessItem(
            key="postgres-data",
            label="PostgreSQL data",
            section=ReadinessSection.FOUNDATION,
            state=state,
            detail=detail,
            target=self._postgres_data,
        )

    @staticmethod
    def _nearest_existing(path: Path) -> Path:
        candidate = path
        while not candidate.exists() and candidate != candidate.parent:
            candidate = candidate.parent
        return candidate

    @staticmethod
    def _failed_btrfs(detail: str) -> HostReadinessItem:
        return HostReadinessItem.failed(
            key="btrfs",
            label="Btrfs",
            detail=detail,
        )

    def _failed_postgres(self, detail: str) -> HostReadinessItem:
        return HostReadinessItem.failed(
            key="postgres-data",
            label="PostgreSQL data",
            detail=detail,
            target=self._postgres_data,
        )


__all__ = ("StorageReadinessProbe",)
