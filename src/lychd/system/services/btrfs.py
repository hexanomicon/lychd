"""Bounded Btrfs preparation used only for new PostgreSQL storage."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import structlog

from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator.process import (
    ProcessInvocationError,
    ProcessResult,
    ProcessRunner,
    SubprocessRunner,
)

logger = structlog.get_logger()

_PROBE_TIMEOUT_SECONDS: Final = 3.0
_MUTATION_TIMEOUT_SECONDS: Final = 30.0


@dataclass(frozen=True, slots=True)
class BtrfsTools:
    """Trusted filesystem executables used by the preparation service."""

    btrfs: str | None
    chattr: str | None
    lsattr: str | None

    @classmethod
    def discover(cls) -> BtrfsTools:
        """Resolve tools without accepting user-controlled executables."""
        return cls(
            btrfs=trusted_host_tool("btrfs"),
            chattr=trusted_host_tool("chattr"),
            lsattr=trusted_host_tool("lsattr"),
        )


class Btrfs:
    """Prepare an optional subvolume and No-COW directory inheritance policy."""

    def __init__(
        self,
        *,
        runner: ProcessRunner | None = None,
        tools: BtrfsTools | None = None,
    ) -> None:
        """Bind effects to an injected bounded runner and trusted toolchain."""
        self._runner = runner or SubprocessRunner()
        selected = tools or BtrfsTools.discover()
        self.btrfs_bin: Final = selected.btrfs
        self.chattr_bin: Final = selected.chattr
        self.lsattr_bin: Final = selected.lsattr

    def create_subvolume(self, path: Path) -> bool:  # noqa: PLR0911 - every fallback emits distinct evidence
        """Create and verify one new Btrfs subvolume, or report fallback."""
        if self.btrfs_bin is None:
            logger.info("layout_btrfs_tool_unavailable", path=str(path))
            return False
        if path.exists():
            if self.is_subvolume(path):
                logger.debug("btrfs_subvolume_exists", path=str(path))
                return True
            logger.warning("btrfs_subvolume_path_blocked", path=str(path))
            return False

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning(
                "btrfs_parent_mkdir_failed",
                path=str(path.parent),
                error_type=type(exc).__name__,
            )
            return False

        result = self._run(
            (self.btrfs_bin, "subvolume", "create", str(path)),
            timeout_s=_MUTATION_TIMEOUT_SECONDS,
        )
        if result is None or result.returncode != 0:
            logger.warning(
                "btrfs_subvolume_failed",
                path=str(path),
                detail=self._result_detail(result),
            )
            return False
        if not self.is_subvolume(path):
            logger.warning("btrfs_subvolume_verification_failed", path=str(path))
            return False
        logger.info("btrfs_subvolume_created", path=str(path))
        return True

    def apply_no_cow(self, path: Path) -> bool:  # noqa: PLR0911 - every policy refusal is explicit
        """Apply and verify ``+C`` inheritance on an empty directory.

        On Btrfs this policy affects newly created file extents beneath the
        directory. It does not retroactively convert existing PostgreSQL data.
        """
        if self.chattr_bin is None or self.lsattr_bin is None:
            logger.info("layout_nocow_tools_unavailable", path=str(path))
            return False
        if self.is_nocow(path):
            return True
        try:
            populated = any(path.iterdir())
        except OSError as exc:
            logger.warning(
                "nocow_directory_unreadable",
                path=str(path),
                error_type=type(exc).__name__,
            )
            return False
        if populated:
            logger.warning("nocow_skipped_not_empty", path=str(path))
            return False

        result = self._run(
            (self.chattr_bin, "+C", str(path)),
            timeout_s=_MUTATION_TIMEOUT_SECONDS,
        )
        if result is None or result.returncode != 0:
            logger.info(
                "nocow_unsupported",
                path=str(path),
                detail=self._result_detail(result),
            )
            return False
        if not self.is_nocow(path):
            logger.warning("nocow_verification_failed", path=str(path))
            return False
        logger.info("nocow_applied", path=str(path))
        return True

    def delete_subvolume(self, path: Path) -> bool:
        """Delete an exact verified subvolume without privilege escalation."""
        if self.btrfs_bin is None or not self.is_subvolume(path):
            return False
        result = self._run(
            (self.btrfs_bin, "subvolume", "delete", str(path)),
            timeout_s=_MUTATION_TIMEOUT_SECONDS,
        )
        if result is None or result.returncode != 0:
            logger.warning(
                "btrfs_delete_failed",
                path=str(path),
                detail=self._result_detail(result),
                hint=f"Use the attested `lychd del` privileged handoff for {path}",
            )
            return False
        logger.info("btrfs_subvolume_deleted", path=str(path))
        return True

    def is_subvolume(self, path: Path) -> bool:
        """Ask Btrfs to prove that ``path`` is a live subvolume root."""
        if self.btrfs_bin is None or not path.exists():
            return False
        result = self._run(
            (self.btrfs_bin, "subvolume", "show", str(path)),
            timeout_s=_PROBE_TIMEOUT_SECONDS,
        )
        return result is not None and result.returncode == 0

    def is_nocow(self, path: Path) -> bool:
        """Return whether ``lsattr`` verifies the directory ``+C`` flag."""
        if self.lsattr_bin is None or not path.exists():
            return False
        result = self._run(
            (self.lsattr_bin, "-d", str(path)),
            timeout_s=_PROBE_TIMEOUT_SECONDS,
        )
        if result is None or result.returncode != 0:
            return False
        fields = result.stdout.split()
        return bool(fields) and "C" in fields[0]

    def _run(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
    ) -> ProcessResult | None:
        """Return one bounded outcome while containing host invocation failure."""
        try:
            return self._runner.run(argv, timeout_s=timeout_s)
        except ProcessInvocationError:
            return None

    @staticmethod
    def _result_detail(result: ProcessResult | None) -> str:
        if result is None:
            return "command could not be executed"
        return " ".join(result.stderr.split())[:240] or f"exit {result.returncode}"


__all__ = ("Btrfs", "BtrfsTools")
