"""Exact cleanup and descriptor settlement for Scribe workspaces."""

from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path
from typing import TYPE_CHECKING, Never

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.descriptor_settlement import (
    DescriptorSet,
    FailureLedger,
    find_settlement_outcome,
)


class WorkspaceParentIdentityError(RuntimeError):
    """A pinned site descriptor does not match its approved identity."""


class WorkspaceSettlementError(RuntimeError):
    """Workspace descriptors were relinquished with explicit close failures."""

    def __init__(
        self,
        message: str,
        *,
        failures: tuple[BaseException, ...],
        outcome: str,
        verified: bool,
        recovery_paths: tuple[Path, ...] = (),
    ) -> None:
        """Retain every peer failure and verified local ownership outcome."""
        super().__init__(message)
        self.failures = failures
        self.outcome = outcome
        self.outcome_verified = verified
        self.recovery_paths = recovery_paths


def workspace_failure_ledger(
    *,
    recovery_paths: tuple[Path, ...] = (),
) -> FailureLedger:
    """Bind generic peer settlement to Scribe workspace evidence."""

    def error_factory(
        message: str,
        *,
        failures: tuple[BaseException, ...],
        outcome: str,
        verified: bool,
    ) -> BaseException:
        return WorkspaceSettlementError(
            message,
            failures=failures,
            outcome=outcome,
            verified=verified,
            recovery_paths=recovery_paths,
        )

    return FailureLedger(
        error_factory=error_factory,
        subject="Scribe workspace settlement",
    )


class WorkspaceSettlementMixin:
    """Cleanup state machine shared by the stable workspace facade."""

    path: Path
    parent_fd: int
    directory_fd: int
    device: int
    inode: int
    owned_entries: dict[str, tuple[int, int]]
    recovery_names: set[str]

    if TYPE_CHECKING:

        def recovery_path(self, *, descriptor: int | None = None) -> Path:
            """Resolve retained descriptor-pinned evidence."""
            raise NotImplementedError

    def cleanup(self) -> None:  # noqa: C901, PLR0912, PLR0915 - explicit settlement state machine
        """Remove only the pinned flat workspace; preserve any pathname replacement."""
        removed = False
        failures: list[BaseException] = []
        outcome = "recovery"
        verified = False
        recovery_paths: tuple[Path, ...] = ()
        active_name = self.path.name
        try:
            if not self._unlink_pinned_entries() or not self._named_path_matches():
                outcome = "retained"
                verified = True
                recovery_paths = self._retained_paths(active_name)
            else:
                cleanup_name = f".lychd-cleanup-{secrets.token_hex(12)}"
                try:
                    rename_noreplace_at(
                        self.path.name,
                        cleanup_name,
                        source_dir_fd=self.parent_fd,
                        destination_dir_fd=self.parent_fd,
                    )
                except BaseException as exc:  # noqa: BLE001 - classify both names after return
                    rename_outcome = self._classify_cleanup_rename_error(
                        cleanup_name,
                        primary=exc,
                    )
                    failures.append(exc)
                    if rename_outcome == "retained":
                        outcome = "retained"
                        verified = True
                        recovery_paths = (self.path,)
                    else:
                        active_name = cleanup_name
                else:
                    active_name = cleanup_name
                if outcome == "retained":
                    pass
                elif not self._relative_path_matches(cleanup_name):
                    self._restore_foreign_cleanup_name(cleanup_name)
                    outcome = "recovery"
                    recovery_paths = self._retained_paths(cleanup_name)
                else:
                    try:
                        os.rmdir(cleanup_name, dir_fd=self.parent_fd)
                    except BaseException as exc:  # noqa: BLE001 - rmdir may complete before return
                        failures.append(exc)
                        (
                            removed,
                            outcome,
                            verified,
                            recovery_paths,
                        ) = self._classify_cleanup_rmdir_error(cleanup_name)
                    else:
                        removed = True
                        outcome = "removed"
                        verified = True
                    if removed:
                        try:
                            os.fsync(self.parent_fd)
                        except BaseException as exc:  # noqa: BLE001 - durability is settlement evidence
                            failures.append(exc)
                            verified = False
        except BaseException as exc:  # noqa: BLE001 - close remains a settlement peer
            failures.append(exc)
            settlement = find_settlement_outcome(exc)
            if settlement is not None:
                if settlement.name in {
                    "entry_removed",
                    "entry_retained",
                    "foreign_restored",
                }:
                    outcome = "retained"
                    verified = settlement.verified
                else:
                    outcome = settlement.name
                    verified = settlement.verified
            try:
                pinned_paths = () if removed else self._retained_paths(active_name)
            except BaseException as observation_error:  # noqa: BLE001 - close must still settle
                failures.append(observation_error)
                outcome = "recovery"
                verified = False
                fallback_paths = (
                    self.path,
                    self.path.parent / active_name,
                )
                try:
                    descriptor_path = self.recovery_path()
                except BaseException as fallback_error:  # noqa: BLE001 - lexical paths remain total
                    failures.append(fallback_error)
                    pinned_paths = tuple(dict.fromkeys(fallback_paths))
                else:
                    pinned_paths = tuple(dict.fromkeys((descriptor_path, *fallback_paths)))
            if isinstance(exc, WorkspaceSettlementError):
                recovery_paths = tuple(
                    dict.fromkeys(
                        (
                            *recovery_paths,
                            *exc.recovery_paths,
                            *pinned_paths,
                        )
                    )
                )
            elif not recovery_paths:
                recovery_paths = pinned_paths

        close_error: BaseException | None = None
        try:
            self.close()
        except BaseException as exc:  # noqa: BLE001 - combine namespace and close truth
            close_error = exc

        cleanup = workspace_failure_ledger(
            recovery_paths=tuple(dict.fromkeys(recovery_paths)),
        )
        cleanup.record_all(tuple(failures))
        if close_error is not None:
            cleanup.record(close_error)
        if not removed and not cleanup.failures:
            cleanup.record(
                WorkspaceSettlementError(
                    f"Scribe retained workspace recovery at {self.path}.",
                    failures=(),
                    outcome=outcome,
                    verified=verified,
                    recovery_paths=recovery_paths,
                )
            )
        cleanup.raise_if_any(
            message=(f"Scribe workspace cleanup settled with recovery evidence for {self.path}."),
            outcome=outcome,
            terminal_note=(
                f"Scribe preserved the verified {outcome} workspace outcome "
                f"for {self.path} after settling every descriptor."
            ),
            verified=verified,
        )

    def _classify_cleanup_rename_error(
        self,
        cleanup_name: str,
        *,
        primary: BaseException,
    ) -> str:
        """Classify workspace detachment against both exact directory names."""
        paths = (self.path, self.path.parent / cleanup_name)
        try:
            original_matches = self._relative_path_matches(self.path.name)
            cleanup_matches = self._relative_path_matches(cleanup_name)
        except BaseException as observation_error:  # noqa: BLE001 - both names remain possible
            self._raise_recovery(
                "Could not classify Scribe workspace detachment.",
                failures=(primary, observation_error),
                recovery_paths=paths,
            )
        if cleanup_matches and not original_matches:
            return "detached"
        if original_matches:
            return "retained"
        self._raise_recovery(
            "Scribe workspace detachment lost its captured directory identity.",
            failures=(primary,),
            recovery_paths=paths,
        )
        raise AssertionError  # pragma: no cover - _raise_recovery is NoReturn

    def _classify_cleanup_rmdir_error(
        self,
        cleanup_name: str,
    ) -> tuple[bool, str, bool, tuple[Path, ...]]:
        """Classify an exceptional rmdir by the exact detached directory."""
        path = self.path.parent / cleanup_name
        try:
            metadata = os.stat(
                cleanup_name,
                dir_fd=self.parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return True, "removed", True, ()
        except BaseException as observation_error:  # noqa: BLE001 - exact name remains possible
            self._raise_recovery(
                "Could not classify Scribe workspace removal.",
                failures=(observation_error,),
                recovery_paths=(path,),
            )
        if stat.S_ISDIR(metadata.st_mode) and metadata.st_dev == self.device and metadata.st_ino == self.inode:
            return False, "retained", True, (path,)
        self._raise_recovery(
            "Scribe workspace removal name changed identity.",
            failures=(),
            recovery_paths=(path,),
        )
        raise AssertionError  # pragma: no cover - _raise_recovery is NoReturn

    def _retained_paths(
        self,
        active_name: str,
        *,
        parent_fd: int | None = None,
        directory_fd: int | None = None,
    ) -> tuple[Path, ...]:
        """Capture exact root and child names before descriptors are closed."""
        parent_descriptor = self.parent_fd if parent_fd is None else parent_fd
        directory_descriptor = self.directory_fd if directory_fd is None else directory_fd
        root = self.path.parent / active_name
        if not self._relative_path_matches(
            active_name,
            parent_fd=parent_descriptor,
        ):
            root = self.recovery_path(descriptor=directory_descriptor)
        names = tuple(sorted(self.recovery_names | self.owned_entries.keys()))
        return tuple(dict.fromkeys((root, *(root / name for name in names))))

    @staticmethod
    def _raise_recovery(
        message: str,
        *,
        failures: tuple[BaseException, ...],
        recovery_paths: tuple[Path, ...],
    ) -> Never:
        """Raise exact unverified workspace recovery evidence."""
        raise WorkspaceSettlementError(
            message,
            failures=failures,
            outcome="recovery",
            verified=False,
            recovery_paths=tuple(dict.fromkeys(recovery_paths)),
        ) from (failures[0] if failures else None)

    def close(self) -> None:
        """Close pinned descriptors without mutating recovery evidence."""
        descriptors = DescriptorSet()
        parent_fd = self.parent_fd
        directory_fd = self.directory_fd
        if self.parent_fd >= 0:
            descriptors.add(self.parent_fd)
            self.parent_fd = -1
        if self.directory_fd >= 0:
            descriptors.add(self.directory_fd)
            self.directory_fd = -1
        observation_errors: list[BaseException] = []
        try:
            recovery_paths = (
                self._retained_paths(
                    self.path.name,
                    parent_fd=parent_fd,
                    directory_fd=directory_fd,
                )
                if parent_fd >= 0 and directory_fd >= 0
                else (self.path,)
            )
        except BaseException as exc:  # noqa: BLE001 - descriptor settlement cannot be skipped
            observation_errors.append(exc)
            try:
                descriptor_path = self.recovery_path(
                    descriptor=directory_fd,
                )
            except BaseException as fallback_error:  # noqa: BLE001 - lexical fallback is total
                observation_errors.append(fallback_error)
                recovery_paths = (self.path,)
            else:
                recovery_paths = tuple(
                    dict.fromkeys(
                        (
                            descriptor_path,
                            self.path,
                        )
                    )
                )
        cleanup = workspace_failure_ledger(
            recovery_paths=recovery_paths,
        )
        cleanup.record_all(tuple(observation_errors))
        cleanup.record_all(descriptors.settle())
        cleanup.raise_if_any(
            message=(f"Scribe relinquished workspace descriptor ownership with close failures: {self.path}."),
            outcome="ownership_released",
            terminal_note=(
                f"Scribe relinquished every local descriptor for {self.path} before preserving this interruption."
            ),
            verified=True,
        )

    def _unlink_pinned_entries(self) -> bool:
        """Delete only exact claimed children through the pinned descriptor."""
        os.lseek(self.directory_fd, 0, os.SEEK_SET)
        names = os.listdir(self.directory_fd)  # noqa: PTH208 - descriptor-pinned enumeration
        for name in names:
            expected = self.owned_entries.get(name)
            if expected is None or self._entry_identity(name) != expected:
                self.recovery_names.add(name)
                return False
        for name in names:
            expected = self.owned_entries[name]
            if not self._quarantine_and_unlink_entry(name, expected=expected):
                return False
        os.fsync(self.directory_fd)
        return True

    def _quarantine_and_unlink_entry(  # noqa: C901 - explicit two-mutation settlement
        self,
        name: str,
        *,
        expected: tuple[int, int],
    ) -> bool:
        """Move one exact child to an unpredictable name before unlinking it."""
        cleanup_name = f".entry-cleanup-{secrets.token_hex(12)}"
        cleanup_path = self.path / cleanup_name
        self.recovery_names.add(cleanup_name)
        adapter_error: BaseException | None = None
        try:
            rename_noreplace_at(
                name,
                cleanup_name,
                source_dir_fd=self.directory_fd,
                destination_dir_fd=self.directory_fd,
            )
        except BaseException as primary:
            try:
                original = self._entry_identity(name)
                cleanup = self._entry_identity(cleanup_name)
            except BaseException as observation_error:  # noqa: BLE001 - exact names remain possible
                self._raise_recovery(
                    "Could not classify staged-entry quarantine.",
                    failures=(primary, observation_error),
                    recovery_paths=(self.path / name, cleanup_path),
                )
            if cleanup == expected and original is None:
                adapter_error = primary
            elif original == expected:
                self.recovery_names.discard(cleanup_name)
                message = f"Scribe retained exact staged entry {self.path / name}."
                raise WorkspaceSettlementError(
                    message,
                    failures=(primary,),
                    outcome="entry_retained",
                    verified=True,
                    recovery_paths=(self.path / name,),
                ) from primary
            else:
                self._raise_recovery(
                    "Staged-entry quarantine lost its captured identity.",
                    failures=(primary,),
                    recovery_paths=(self.path / name, cleanup_path),
                )
        if self._entry_identity(cleanup_name) != expected:
            self._restore_foreign_entry(cleanup_name, name)
            return False
        try:
            os.unlink(cleanup_name, dir_fd=self.directory_fd)
        except BaseException as primary:  # noqa: BLE001 - unlink may complete before return
            try:
                after = self._entry_identity(cleanup_name)
            except BaseException as observation_error:  # noqa: BLE001 - exact name remains possible
                self._raise_recovery(
                    "Could not classify staged-entry removal.",
                    failures=(primary, observation_error),
                    recovery_paths=(cleanup_path,),
                )
            if after is None:
                self.recovery_names.discard(cleanup_name)
                self.owned_entries.pop(name, None)
                ledger = workspace_failure_ledger()
                if adapter_error is not None:
                    ledger.record(adapter_error)
                ledger.record(primary)
                ledger.raise_if_any(
                    message=("Scribe staged-entry removal completed after adapter failure."),
                    outcome="entry_removed",
                    terminal_note=(f"Scribe verified removal of exact staged entry {cleanup_path}."),
                    verified=True,
                )
            self._raise_recovery(
                "Scribe retained staged-entry recovery after failed unlink.",
                failures=(
                    *((adapter_error,) if adapter_error is not None else ()),
                    primary,
                ),
                recovery_paths=(cleanup_path,),
            )
        self.recovery_names.discard(cleanup_name)
        self.owned_entries.pop(name, None)
        if adapter_error is not None:
            ledger = workspace_failure_ledger()
            ledger.record(adapter_error)
            ledger.raise_if_any(
                message=("Scribe staged-entry quarantine completed after adapter failure."),
                outcome="entry_removed",
                terminal_note=(f"Scribe verified removal of exact staged entry {cleanup_path}."),
                verified=True,
            )
        return True

    def _entry_identity(self, name: str) -> tuple[int, int] | None:
        try:
            metadata = os.stat(
                name,
                dir_fd=self.directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return None
        if stat.S_ISDIR(metadata.st_mode):
            return None
        return metadata.st_dev, metadata.st_ino

    def _restore_foreign_entry(
        self,
        cleanup_name: str,
        original_name: str,
    ) -> None:
        """Restore an entry moved after its claimed identity drifted."""
        cleanup_path = self.path / cleanup_name
        original_path = self.path / original_name
        captured = self._entry_identity(cleanup_name)
        try:
            rename_noreplace_at(
                cleanup_name,
                original_name,
                source_dir_fd=self.directory_fd,
                destination_dir_fd=self.directory_fd,
            )
        except BaseException as primary:  # noqa: BLE001 - classify both names after return
            try:
                source = self._entry_identity(cleanup_name)
                target = self._entry_identity(original_name)
            except BaseException as observation_error:  # noqa: BLE001 - retain both exact names
                self._raise_recovery(
                    "Could not classify foreign staged-entry restoration.",
                    failures=(primary, observation_error),
                    recovery_paths=(cleanup_path, original_path),
                )
            if source is None and captured is not None and target == captured:
                self.recovery_names.discard(cleanup_name)
                ledger = workspace_failure_ledger(
                    recovery_paths=(original_path,),
                )
                ledger.record(primary)
                ledger.raise_if_any(
                    message=("Foreign staged entry was restored after adapter failure."),
                    outcome="foreign_restored",
                    terminal_note=(f"Scribe restored the captured foreign entry at {original_path}."),
                    verified=True,
                )
            self._raise_recovery(
                "Foreign staged entry remains at a private recovery name.",
                failures=(primary,),
                recovery_paths=(cleanup_path, original_path),
            )
        self.recovery_names.discard(cleanup_name)

    def _named_path_matches(self) -> bool:
        """Return whether the public workspace name still identifies the pinned inode."""
        return self._relative_path_matches(self.path.name)

    def _relative_path_matches(
        self,
        name: str,
        *,
        parent_fd: int | None = None,
    ) -> bool:
        parent_descriptor = self.parent_fd if parent_fd is None else parent_fd
        try:
            metadata = os.stat(
                name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return False
        return stat.S_ISDIR(metadata.st_mode) and metadata.st_dev == self.device and metadata.st_ino == self.inode

    def _restore_foreign_cleanup_name(self, cleanup_name: str) -> None:
        """Put a mistakenly moved replacement back without overwriting another path."""
        cleanup_path = self.path.parent / cleanup_name
        captured = self._relative_identity(cleanup_name)
        try:
            rename_noreplace_at(
                cleanup_name,
                self.path.name,
                source_dir_fd=self.parent_fd,
                destination_dir_fd=self.parent_fd,
            )
        except BaseException as primary:  # noqa: BLE001 - classify both names after return
            try:
                source = self._relative_identity(cleanup_name)
                target = self._relative_identity(self.path.name)
            except BaseException as observation_error:  # noqa: BLE001 - retain both exact names
                self._raise_recovery(
                    "Could not classify foreign workspace-name restoration.",
                    failures=(primary, observation_error),
                    recovery_paths=(cleanup_path, self.path),
                )
            if source is None and captured is not None and target == captured:
                ledger = workspace_failure_ledger(recovery_paths=(self.path,))
                ledger.record(primary)
                ledger.raise_if_any(
                    message=("Foreign workspace replacement was restored after adapter failure."),
                    outcome="foreign_restored",
                    terminal_note=(f"Scribe restored the captured foreign directory at {self.path}."),
                    verified=True,
                )
            self._raise_recovery(
                "Foreign workspace replacement remains at a cleanup name.",
                failures=(primary,),
                recovery_paths=(cleanup_path, self.path),
            )

    def _relative_identity(self, name: str) -> tuple[int, int, int] | None:
        """Capture descriptor-relative directory identity and file kind."""
        try:
            metadata = os.stat(
                name,
                dir_fd=self.parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return None
        return (
            metadata.st_dev,
            metadata.st_ino,
            stat.S_IFMT(metadata.st_mode),
        )


__all__ = (
    "WorkspaceParentIdentityError",
    "WorkspaceSettlementError",
    "WorkspaceSettlementMixin",
    "workspace_failure_ledger",
)
