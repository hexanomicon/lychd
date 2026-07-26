"""Bounded Btrfs preparation used only for new PostgreSQL storage."""

from __future__ import annotations

import array
import fcntl
import os
import stat
import struct
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, NoReturn

import structlog

from lychd.system.btrfs_identity import (
    BtrfsSubvolumeObservation,
    parse_subvolume_show,
)
from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator.process import (
    DescriptorProcessRunner,
    ProcessInvocationError,
    ProcessResult,
    SubprocessRunner,
)

logger = structlog.get_logger()

_PROBE_TIMEOUT_SECONDS: Final = 3.0
_MUTATION_TIMEOUT_SECONDS: Final = 30.0
_FS_NOCOW_FL: Final = 0x00800000
_IOC_WRITE: Final = 1
_IOC_READ: Final = 2
_IOC_DIRECTION_SHIFT: Final = 30
_IOC_SIZE_SHIFT: Final = 16
_FS_IOC_GETFLAGS: Final = (
    (_IOC_READ << _IOC_DIRECTION_SHIFT) | (ord("f") << 8) | 1 | (struct.calcsize("l") << _IOC_SIZE_SHIFT)
)
_FS_IOC_SETFLAGS: Final = (
    (_IOC_WRITE << _IOC_DIRECTION_SHIFT) | (ord("f") << 8) | 2 | (struct.calcsize("l") << _IOC_SIZE_SHIFT)
)
_DIRECTORY_OPEN_FLAGS: Final = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW


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


@dataclass(frozen=True, slots=True)
class PreparedBtrfsSubvolume:
    """Descriptor-attested result of preparing one just-created subvolume."""

    observation: BtrfsSubvolumeObservation
    device: int
    inode: int
    nocow: bool


class BtrfsCreationState(StrEnum):
    """Observed namespace state after a subvolume-creation interruption."""

    ABSENT = "absent"
    PRESENT_UNATTESTED = "present_unattested"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class BtrfsCreationEvidence:
    """Pinned-leaf evidence retained after creation could not converge."""

    path: Path
    state: BtrfsCreationState
    observation: BtrfsSubvolumeObservation | None = None


class BtrfsCreationError(RuntimeError):
    """Subvolume creation stopped with explicit pinned-leaf effect truth."""

    def __init__(
        self,
        message: str,
        *,
        evidence: BtrfsCreationEvidence,
        cause: BaseException | None = None,
    ) -> None:
        """Retain both the effect classification and original interruption."""
        super().__init__(message)
        self.evidence = evidence
        self.cause = cause


class Btrfs:
    """Prepare an optional subvolume and No-COW directory inheritance policy."""

    def __init__(
        self,
        *,
        runner: DescriptorProcessRunner | None = None,
        tools: BtrfsTools | None = None,
    ) -> None:
        """Bind effects to an injected bounded runner and trusted toolchain."""
        self._runner = runner or SubprocessRunner()
        selected = tools or BtrfsTools.discover()
        self.btrfs_bin: Final = selected.btrfs
        self.chattr_bin: Final = selected.chattr
        self.lsattr_bin: Final = selected.lsattr

    def create_subvolume(
        self,
        path: Path,
        *,
        parent_fd: int,
    ) -> BtrfsSubvolumeObservation | None:
        """Create one absent subvolume through its pinned parent descriptor."""
        if self.btrfs_bin is None:
            logger.info("layout_btrfs_tool_unavailable", path=str(path))
            return None
        leaf = self._safe_leaf(path)
        if self._entry_exists(parent_fd, leaf):
            logger.warning("btrfs_subvolume_path_blocked", path=str(path))
            message = f"Pinned Btrfs target appeared after layout planning: {path}"
            raise RuntimeError(message)
        descriptor_path = self._descriptor_path(parent_fd, leaf)
        try:
            result = self._runner.run_with_fds(
                (self.btrfs_bin, "subvolume", "create", str(descriptor_path)),
                timeout_s=_MUTATION_TIMEOUT_SECONDS,
                pass_fds=(parent_fd,),
            )
        except BaseException as exc:  # noqa: BLE001 - inspect the mutation postcondition
            evidence = self._creation_evidence(
                path=path,
                parent_fd=parent_fd,
                leaf=leaf,
            )
            logger.warning(
                "btrfs_subvolume_failed",
                path=str(path),
                detail=str(exc),
                creation_state=evidence.state.value,
            )
            if evidence.state is BtrfsCreationState.ABSENT and isinstance(
                exc,
                ProcessInvocationError,
            ):
                return None
            self._raise_creation_error(
                path=path,
                evidence=evidence,
                cause=exc,
            )
        if result.returncode != 0:
            evidence = self._creation_evidence(
                path=path,
                parent_fd=parent_fd,
                leaf=leaf,
            )
            logger.warning(
                "btrfs_subvolume_failed",
                path=str(path),
                detail=self._result_detail(result),
                creation_state=evidence.state.value,
            )
            if evidence.state is not BtrfsCreationState.ABSENT:
                self._raise_creation_error(
                    path=path,
                    evidence=evidence,
                )
            return None
        try:
            observation = self._inspect_subvolume_at(
                parent_fd=parent_fd,
                leaf=leaf,
            )
        except BaseException as exc:  # noqa: BLE001 - creation already reported success
            evidence = self._creation_evidence(
                path=path,
                parent_fd=parent_fd,
                leaf=leaf,
                absence_is_indeterminate=True,
            )
            self._raise_creation_error(
                path=path,
                evidence=evidence,
                cause=exc,
            )
        if observation is None:
            evidence = self._creation_evidence(
                path=path,
                parent_fd=parent_fd,
                leaf=leaf,
                absence_is_indeterminate=True,
            )
            self._raise_creation_error(
                path=path,
                evidence=evidence,
            )
        logger.info(
            "btrfs_subvolume_created",
            path=str(path),
            subvolume_uuid=observation.uuid,
            subvolume_id=observation.subvolume_id,
        )
        return observation

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

    def prepare_created_subvolume(
        self,
        path: Path,
        *,
        parent_fd: int,
        expected: BtrfsSubvolumeObservation,
    ) -> PreparedBtrfsSubvolume:
        """Pin, prepare, and re-attest one just-created subvolume.

        The No-COW mutation is issued through the opened directory descriptor,
        so a concurrent pathname replacement can never redirect it.
        """
        leaf = self._safe_leaf(path)
        try:
            descriptor = os.open(
                leaf,
                _DIRECTORY_OPEN_FLAGS,
                dir_fd=parent_fd,
            )
        except OSError as exc:
            message = f"Could not pin newly created Btrfs subvolume: {path}"
            raise RuntimeError(message) from exc
        try:
            metadata = os.fstat(descriptor)
            self._require_current_created_subvolume(
                path,
                parent_fd=parent_fd,
                leaf=leaf,
                expected=expected,
                metadata=metadata,
            )
            nocow = self._apply_no_cow_descriptor(
                descriptor,
                path=path,
            )
            self._require_current_created_subvolume(
                path,
                parent_fd=parent_fd,
                leaf=leaf,
                expected=expected,
                metadata=metadata,
            )
            return PreparedBtrfsSubvolume(
                observation=expected,
                device=metadata.st_dev,
                inode=metadata.st_ino,
                nocow=nocow,
            )
        finally:
            os.close(descriptor)

    def _require_current_created_subvolume(
        self,
        path: Path,
        *,
        parent_fd: int,
        leaf: str,
        expected: BtrfsSubvolumeObservation,
        metadata: os.stat_result,
    ) -> None:
        """Require both pinned and public names to resolve to the creation."""
        if not stat.S_ISDIR(metadata.st_mode):
            message = f"Newly created Btrfs subvolume is not a directory: {path}"
            raise RuntimeError(message)
        pinned_live = self._inspect_subvolume_at(
            parent_fd=parent_fd,
            leaf=leaf,
        )
        public_live = self.inspect_subvolume(path)
        try:
            public_metadata = path.lstat()
        except OSError as exc:
            message = f"Newly created Btrfs subvolume became unreachable: {path}"
            raise RuntimeError(message) from exc
        if (
            pinned_live != expected
            or public_live != expected
            or not stat.S_ISDIR(public_metadata.st_mode)
            or public_metadata.st_dev != metadata.st_dev
            or public_metadata.st_ino != metadata.st_ino
        ):
            message = f"Newly created Btrfs subvolume changed identity: {path}"
            raise RuntimeError(message)

    @staticmethod
    def _apply_no_cow_descriptor(
        descriptor: int,
        *,
        path: Path,
    ) -> bool:
        """Apply and verify the No-COW inode flag through one pinned descriptor."""
        try:
            current = Btrfs._inode_flags(descriptor)
            if current & _FS_NOCOW_FL:
                return True
            if os.listdir(descriptor):
                logger.warning("nocow_skipped_not_empty", path=str(path))
                return False
            Btrfs._write_inode_flags(
                descriptor,
                current | _FS_NOCOW_FL,
            )
            applied = bool(Btrfs._inode_flags(descriptor) & _FS_NOCOW_FL)
        except OSError as exc:
            logger.warning(
                "nocow_descriptor_policy_unavailable",
                path=str(path),
                error_type=type(exc).__name__,
            )
            return False
        if not applied:
            logger.warning("nocow_verification_failed", path=str(path))
            return False
        logger.info("nocow_applied", path=str(path))
        return True

    @staticmethod
    def _inode_flags(descriptor: int) -> int:
        """Read Linux inode flags through ``FS_IOC_GETFLAGS``."""
        flags = array.array("l", [0])
        fcntl.ioctl(
            descriptor,
            _FS_IOC_GETFLAGS,
            flags,
            True,  # noqa: FBT003 - fcntl exposes mutate_flag as positional-only
        )
        return int(flags[0])

    @staticmethod
    def _write_inode_flags(descriptor: int, flags: int) -> None:
        """Write Linux inode flags through ``FS_IOC_SETFLAGS``."""
        buffer = array.array("l", [flags])
        fcntl.ioctl(
            descriptor,
            _FS_IOC_SETFLAGS,
            buffer,
            True,  # noqa: FBT003 - fcntl exposes mutate_flag as positional-only
        )

    def is_subvolume(self, path: Path) -> bool:
        """Ask Btrfs to prove that ``path`` is a live subvolume root."""
        return self.inspect_subvolume(path) is not None

    def inspect_subvolume(
        self,
        path: Path,
    ) -> BtrfsSubvolumeObservation | None:
        """Return UUID/ID evidence for one live subvolume."""
        if self.btrfs_bin is None or not path.exists():
            return None
        result = self._run(
            (self.btrfs_bin, "subvolume", "show", str(path)),
            timeout_s=_PROBE_TIMEOUT_SECONDS,
        )
        if result is None or result.returncode != 0:
            return None
        return parse_subvolume_show(result.stdout)

    def _inspect_subvolume_at(
        self,
        *,
        parent_fd: int,
        leaf: str,
    ) -> BtrfsSubvolumeObservation | None:
        """Inspect one subvolume through an inherited pinned-parent descriptor."""
        if self.btrfs_bin is None:
            return None
        result = self._run_with_fds(
            (
                self.btrfs_bin,
                "subvolume",
                "show",
                str(self._descriptor_path(parent_fd, leaf)),
            ),
            timeout_s=_PROBE_TIMEOUT_SECONDS,
            pass_fds=(parent_fd,),
        )
        if result is None or result.returncode != 0:
            return None
        return parse_subvolume_show(result.stdout)

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

    def _run_with_fds(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        pass_fds: tuple[int, ...],
    ) -> ProcessResult | None:
        """Run a bounded command while preserving its pinned descriptor authority."""
        try:
            return self._runner.run_with_fds(
                argv,
                timeout_s=timeout_s,
                pass_fds=pass_fds,
            )
        except ProcessInvocationError:
            return None

    @staticmethod
    def _safe_leaf(path: Path) -> str:
        """Return one canonical leaf name for descriptor-relative creation."""
        leaf = path.name
        if not path.is_absolute() or not leaf or leaf in {".", ".."} or path != path.parent / leaf:
            message = f"Btrfs target must be one canonical absolute leaf: {path}"
            raise RuntimeError(message)
        return leaf

    @staticmethod
    def _descriptor_path(parent_fd: int, leaf: str) -> Path:
        """Project a pinned parent into one child process without re-resolution."""
        return Path("/proc/self/fd") / str(parent_fd) / leaf

    @staticmethod
    def _entry_exists(parent_fd: int, leaf: str) -> bool:
        """Inspect one leaf relative to its pinned parent without following it."""
        try:
            os.stat(
                leaf,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return False
        except OSError as exc:
            message = f"Could not inspect pinned Btrfs target leaf: {leaf}"
            raise RuntimeError(message) from exc
        return True

    @staticmethod
    def _creation_evidence(
        *,
        path: Path,
        parent_fd: int,
        leaf: str,
        absence_is_indeterminate: bool = False,
    ) -> BtrfsCreationEvidence:
        """Classify only the pinned leaf after a mutating command returns."""
        try:
            os.stat(
                leaf,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            state = BtrfsCreationState.INDETERMINATE if absence_is_indeterminate else BtrfsCreationState.ABSENT
        except OSError:
            state = BtrfsCreationState.INDETERMINATE
        else:
            state = BtrfsCreationState.PRESENT_UNATTESTED
        return BtrfsCreationEvidence(
            path=path,
            state=state,
        )

    @staticmethod
    def _raise_creation_error(
        *,
        path: Path,
        evidence: BtrfsCreationEvidence,
        cause: BaseException | None = None,
    ) -> NoReturn:
        """Raise typed evidence instead of guessing ownership or fallback safety."""
        message = f"Btrfs subvolume creation did not converge; pinned target state is {evidence.state.value}: {path}"
        raise BtrfsCreationError(
            message,
            evidence=evidence,
            cause=cause,
        ) from cause

    @staticmethod
    def _result_detail(result: ProcessResult | None) -> str:
        if result is None:
            return "command could not be executed"
        return " ".join(result.stderr.split())[:240] or f"exit {result.returncode}"


__all__ = (
    "Btrfs",
    "BtrfsCreationError",
    "BtrfsCreationEvidence",
    "BtrfsCreationState",
    "BtrfsSubvolumeObservation",
    "BtrfsTools",
    "PreparedBtrfsSubvolume",
)
