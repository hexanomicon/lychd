"""Descriptor-bound retirement of one already-authorized filesystem entry."""

from __future__ import annotations

import errno
import os
import stat
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import NoReturn
from uuid import uuid4

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.interruptions import find_terminal_interruption

_PATH_OPEN_FLAGS = getattr(os, "O_PATH", 0) | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
_QUARANTINE_ATTEMPTS = 8
_QUARANTINE_PREFIX = ".lychd-retire-"
_UUID_HEX_LENGTH = 32


class RetirementKind(StrEnum):
    """Filesystem operation selected after identity attestation."""

    DIRECTORY = "directory"
    FILE = "file"


@dataclass(frozen=True, slots=True)
class RetirementIdentity:
    """Stable entry attributes required to authorize one retirement."""

    device: int
    inode: int
    owner_uid: int
    file_type: int

    @classmethod
    def from_stat(cls, metadata: os.stat_result) -> RetirementIdentity:
        """Capture the stable identity fields used by the retirement protocol."""
        return cls(
            device=metadata.st_dev,
            inode=metadata.st_ino,
            owner_uid=metadata.st_uid,
            file_type=stat.S_IFMT(metadata.st_mode),
        )


@dataclass(frozen=True, slots=True)
class RetainedQuarantine:
    """Recovery evidence for an entry deliberately left at a private name."""

    resource: Path
    quarantine: Path
    kind: RetirementKind
    expected: RetirementIdentity
    observed: RetirementIdentity | None
    reason: str


class AtomicRetirementError(RuntimeError):
    """One retirement stopped without deleting an unverified namespace entry."""

    def __init__(
        self,
        message: str,
        *,
        recovery: RetainedQuarantine | None = None,
        failures: tuple[BaseException, ...] = (),
    ) -> None:
        """Retain recovery evidence and every settled adapter failure."""
        super().__init__(message)
        self.recovery = recovery
        self.failures = failures


class AtomicRetirementService:
    """Quarantine, re-attest, and remove one entry below a pinned parent."""

    def retire_directory(
        self,
        *,
        parent_fd: int,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
    ) -> None:
        """Retire an empty directory without a predictable-name rmdir window."""
        self._retire(
            parent_fd=parent_fd,
            leaf=leaf,
            expected=expected,
            display_path=display_path,
            kind=RetirementKind.DIRECTORY,
        )

    def retire_file(
        self,
        *,
        parent_fd: int,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
    ) -> None:
        """Retire a non-directory entry without a predictable-name unlink window."""
        self._retire(
            parent_fd=parent_fd,
            leaf=leaf,
            expected=expected,
            display_path=display_path,
            kind=RetirementKind.FILE,
        )

    def _retire(
        self,
        *,
        parent_fd: int,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
        kind: RetirementKind,
    ) -> None:
        """Move the live name aside before its final identity/delete sequence."""
        self._validate_request(
            leaf=leaf,
            expected=expected,
            display_path=display_path,
            kind=kind,
        )
        quarantine_name = self._quarantine(
            parent_fd=parent_fd,
            leaf=leaf,
            display_path=display_path,
            expected=expected,
            kind=kind,
        )
        if quarantine_name is None:
            return
        quarantine_path = display_path.with_name(quarantine_name)

        try:
            self._retire_quarantined(
                parent_fd=parent_fd,
                leaf=leaf,
                quarantine_name=quarantine_name,
                display_path=display_path,
                quarantine_path=quarantine_path,
                kind=kind,
                expected=expected,
            )
        except AtomicRetirementError:
            raise
        except BaseException as exc:  # noqa: BLE001 - classify cancellation after namespace mutation
            self._raise_after_interruption(
                parent_fd=parent_fd,
                leaf=leaf,
                quarantine_name=quarantine_name,
                display_path=display_path,
                quarantine_path=quarantine_path,
                kind=kind,
                expected=expected,
                primary=exc,
            )

    def _retire_quarantined(
        self,
        *,
        parent_fd: int,
        leaf: str,
        quarantine_name: str,
        display_path: Path,
        quarantine_path: Path,
        kind: RetirementKind,
        expected: RetirementIdentity,
    ) -> None:
        """Re-attest and remove one already detached public entry."""
        descriptor = -1
        observed: RetirementIdentity | None = None
        try:
            try:
                descriptor = os.open(
                    quarantine_name,
                    _PATH_OPEN_FLAGS,
                    dir_fd=parent_fd,
                )
                observed = RetirementIdentity.from_stat(os.fstat(descriptor))
            except OSError as exc:
                self._raise_after_restore(
                    parent_fd=parent_fd,
                    leaf=leaf,
                    quarantine_name=quarantine_name,
                    display_path=display_path,
                    quarantine_path=quarantine_path,
                    kind=kind,
                    expected=expected,
                    observed=None,
                    reason=f"Could not attest quarantined {kind.value} {display_path}",
                    primary=exc,
                )

            if observed != expected:
                self._raise_after_restore(
                    parent_fd=parent_fd,
                    leaf=leaf,
                    quarantine_name=quarantine_name,
                    display_path=display_path,
                    quarantine_path=quarantine_path,
                    kind=kind,
                    expected=expected,
                    observed=observed,
                    reason=f"{kind.value.capitalize()} identity changed before retirement: {display_path}",
                )

            try:
                current = RetirementIdentity.from_stat(
                    os.stat(
                        quarantine_name,
                        dir_fd=parent_fd,
                        follow_symlinks=False,
                    )
                )
            except OSError as exc:
                self._raise_after_restore(
                    parent_fd=parent_fd,
                    leaf=leaf,
                    quarantine_name=quarantine_name,
                    display_path=display_path,
                    quarantine_path=quarantine_path,
                    kind=kind,
                    expected=expected,
                    observed=observed,
                    reason=f"Could not re-attest quarantined {kind.value} {display_path}",
                    primary=exc,
                )
            if current != observed:
                self._raise_after_restore(
                    parent_fd=parent_fd,
                    leaf=leaf,
                    quarantine_name=quarantine_name,
                    display_path=display_path,
                    quarantine_path=quarantine_path,
                    kind=kind,
                    expected=expected,
                    observed=current,
                    reason=f"Quarantined {kind.value} identity changed before retirement: {display_path}",
                )

            try:
                if kind is RetirementKind.DIRECTORY:
                    os.rmdir(quarantine_name, dir_fd=parent_fd)
                else:
                    os.unlink(quarantine_name, dir_fd=parent_fd)
            except OSError as exc:
                self._raise_after_restore(
                    parent_fd=parent_fd,
                    leaf=leaf,
                    quarantine_name=quarantine_name,
                    display_path=display_path,
                    quarantine_path=quarantine_path,
                    kind=kind,
                    expected=expected,
                    observed=observed,
                    reason=f"Could not retire quarantined {kind.value} {display_path}",
                    primary=exc,
                )
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    @staticmethod
    def _validate_request(
        *,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
        kind: RetirementKind,
    ) -> None:
        """Reject an incoherent request before any namespace mutation."""
        if not leaf or leaf in {".", ".."} or "/" in leaf or display_path.name != leaf:
            message = f"Retirement target must be one matching filename component: {display_path}"
            raise AtomicRetirementError(message)
        expected_is_directory = expected.file_type == stat.S_IFDIR
        if expected_is_directory != (kind is RetirementKind.DIRECTORY):
            message = f"Retirement behavior does not match the expected entry type: {display_path}"
            raise AtomicRetirementError(message)

    @staticmethod
    def _quarantine(
        *,
        parent_fd: int,
        leaf: str,
        display_path: Path,
        expected: RetirementIdentity,
        kind: RetirementKind,
    ) -> str | None:
        """Atomically move one public name to a collision-resistant private name."""
        for _ in range(_QUARANTINE_ATTEMPTS):
            quarantine_name = new_retirement_quarantine_name()
            try:
                rename_noreplace_at(
                    leaf,
                    quarantine_name,
                    source_dir_fd=parent_fd,
                    destination_dir_fd=parent_fd,
                )
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    continue
                if exc.errno == errno.ENOENT:
                    return None
                message = f"Could not atomically quarantine retirement target: {display_path}"
                raise AtomicRetirementError(message) from exc
            except BaseException as exc:  # noqa: BLE001 - classify signal around rename return
                AtomicRetirementService._raise_after_interruption(
                    parent_fd=parent_fd,
                    leaf=leaf,
                    quarantine_name=quarantine_name,
                    display_path=display_path,
                    quarantine_path=display_path.with_name(quarantine_name),
                    kind=kind,
                    expected=expected,
                    primary=exc,
                )
            return quarantine_name
        message = f"Could not allocate a private retirement quarantine: {display_path}"
        raise AtomicRetirementError(message)

    @staticmethod
    def _raise_after_restore(
        *,
        parent_fd: int,
        leaf: str,
        quarantine_name: str,
        display_path: Path,
        quarantine_path: Path,
        kind: RetirementKind,
        expected: RetirementIdentity,
        observed: RetirementIdentity | None,
        reason: str,
        primary: BaseException | None = None,
    ) -> NoReturn:
        """Restore without clobbering, or surface exact retained recovery evidence."""
        try:
            rename_noreplace_at(
                quarantine_name,
                leaf,
                source_dir_fd=parent_fd,
                destination_dir_fd=parent_fd,
            )
        except OSError as restore_error:
            if restore_error.errno == errno.ENOENT:
                message = (
                    f"{reason}; the quarantine disappeared before it could be "
                    "restored, so no retained-path claim was issued"
                )
                raise AtomicRetirementError(message) from (primary or restore_error)
            recovery = RetainedQuarantine(
                resource=display_path,
                quarantine=quarantine_path,
                kind=kind,
                expected=expected,
                observed=observed,
                reason=f"{reason}; public-name restoration failed: {restore_error}",
            )
            message = (
                f"{reason}; preserved the quarantined entry at "
                f"{quarantine_path} because its public name could not be restored"
            )
            raise AtomicRetirementError(
                message,
                recovery=recovery,
            ) from (primary or restore_error)
        except BaseException as restore_error:  # noqa: BLE001 - classify signal around restore return
            AtomicRetirementService._raise_after_interruption(
                parent_fd=parent_fd,
                leaf=leaf,
                quarantine_name=quarantine_name,
                display_path=display_path,
                quarantine_path=quarantine_path,
                kind=kind,
                expected=expected,
                primary=restore_error,
            )
        message = f"{reason}; the quarantined entry was restored without clobbering"
        raise AtomicRetirementError(message) from primary

    @staticmethod
    def _raise_after_interruption(
        *,
        parent_fd: int,
        leaf: str,
        quarantine_name: str,
        display_path: Path,
        quarantine_path: Path,
        kind: RetirementKind,
        expected: RetirementIdentity,
        primary: BaseException,
    ) -> NoReturn:
        """Classify both names after cancellation and expose exact effect truth."""
        try:
            public = AtomicRetirementService._observe_name(
                parent_fd=parent_fd,
                name=leaf,
            )
            quarantined = AtomicRetirementService._observe_name(
                parent_fd=parent_fd,
                name=quarantine_name,
            )
        except BaseException as observation_error:  # noqa: BLE001 - observation is post-effect
            failures = (primary, observation_error)
            recovery = RetainedQuarantine(
                resource=display_path,
                quarantine=quarantine_path,
                kind=kind,
                expected=expected,
                observed=None,
                reason="post-interruption namespace observation failed",
            )
            terminal = AtomicRetirementService._first_terminal(*failures)
            message = f"Retirement interruption left indeterminate namespace state: {display_path}"
            raise AtomicRetirementError(
                message,
                recovery=recovery,
                failures=failures,
            ) from (terminal or primary)

        if public == expected and quarantined is None:
            raise primary
        if public is None and quarantined is None:
            raise primary
        if public is None and quarantined == expected:
            try:
                rename_noreplace_at(
                    quarantine_name,
                    leaf,
                    source_dir_fd=parent_fd,
                    destination_dir_fd=parent_fd,
                )
            except BaseException as restore_error:
                try:
                    restored_public = AtomicRetirementService._observe_name(
                        parent_fd=parent_fd,
                        name=leaf,
                    )
                    restored_quarantine = AtomicRetirementService._observe_name(
                        parent_fd=parent_fd,
                        name=quarantine_name,
                    )
                except BaseException as observation_error:  # noqa: BLE001 - typed residue
                    failures = (primary, restore_error, observation_error)
                    recovery = RetainedQuarantine(
                        resource=display_path,
                        quarantine=quarantine_path,
                        kind=kind,
                        expected=expected,
                        observed=None,
                        reason="restoration postcondition observation failed",
                    )
                    terminal = AtomicRetirementService._first_terminal(*failures)
                    message = f"Retirement restoration left indeterminate recovery evidence at {quarantine_path}"
                    raise AtomicRetirementError(
                        message,
                        recovery=recovery,
                        failures=failures,
                    ) from (terminal or primary)
                if restored_public == expected and restored_quarantine is None:
                    terminal = AtomicRetirementService._first_terminal(
                        restore_error,
                        primary,
                    )
                    surfaced = terminal or primary
                    surfaced.add_note(f"LychD del recovery: {display_path} was restored after interruption.")
                    if surfaced is restore_error:
                        raise surfaced from primary
                    raise surfaced from restore_error
                recovery = RetainedQuarantine(
                    resource=display_path,
                    quarantine=quarantine_path,
                    kind=kind,
                    expected=expected,
                    observed=quarantined,
                    reason=(
                        "terminal interruption left the exact entry quarantined; "
                        f"public-name restoration failed: {restore_error}"
                    ),
                )
                message = (
                    f"Retirement interruption preserved the exact entry at "
                    f"{quarantine_path}; public restoration did not complete"
                )
                raise AtomicRetirementError(
                    message,
                    recovery=recovery,
                    failures=(primary, restore_error),
                ) from (
                    AtomicRetirementService._first_terminal(
                        restore_error,
                        primary,
                    )
                    or primary
                )
            raise primary
        if quarantined is not None:
            recovery = RetainedQuarantine(
                resource=display_path,
                quarantine=quarantine_path,
                kind=kind,
                expected=expected,
                observed=quarantined,
                reason="terminal interruption left a classified quarantine",
            )
            message = f"Retirement interruption retained recovery evidence at {quarantine_path}"
            raise AtomicRetirementError(
                message,
                recovery=recovery,
            ) from primary
        message = f"Retirement interruption changed the public identity without a retained quarantine: {display_path}"
        raise AtomicRetirementError(message) from primary

    @staticmethod
    def _first_terminal(
        *failures: BaseException,
    ) -> BaseException | None:
        """Find the first nested terminal across settled adapter failures."""
        return next(
            (terminal for failure in failures if (terminal := find_terminal_interruption(failure)) is not None),
            None,
        )

    @staticmethod
    def _observe_name(
        *,
        parent_fd: int,
        name: str,
    ) -> RetirementIdentity | None:
        """Observe one descriptor-relative name without following it."""
        try:
            metadata = os.stat(
                name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return None
        return RetirementIdentity.from_stat(metadata)


def is_retirement_quarantine_name(name: str) -> bool:
    """Return whether one leaf carries the private atomic-retirement marker."""
    suffix = name.removeprefix(_QUARANTINE_PREFIX)
    if len(suffix) != _UUID_HEX_LENGTH:
        return False
    try:
        int(suffix, 16)
    except ValueError:
        return False
    return name.startswith(_QUARANTINE_PREFIX)


def new_retirement_quarantine_name() -> str:
    """Allocate one private retirement leaf recognized by lifecycle recovery."""
    return f"{_QUARANTINE_PREFIX}{uuid4().hex}"


__all__ = (
    "AtomicRetirementError",
    "AtomicRetirementService",
    "RetainedQuarantine",
    "RetirementIdentity",
    "RetirementKind",
    "is_retirement_quarantine_name",
    "new_retirement_quarantine_name",
)
