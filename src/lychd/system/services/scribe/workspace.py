"""Identity-pinned flat storage for one Scribe filesystem transaction."""

from __future__ import annotations

import os
import secrets
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Never

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.descriptor_settlement import (
    DescriptorSet,
    FailureLedger,
    find_settlement_outcome,
)
from lychd.system.services.scribe.storage import (
    AttestedPath,
    PinnedPath,
    capture_pinned_path_state,
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


def _workspace_failure_ledger(
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


@dataclass
class TransactionWorkspace:
    """One flat, same-filesystem workspace pinned to its original directory."""

    path: Path
    parent_fd: int
    directory_fd: int
    parent_device: int
    parent_inode: int
    device: int
    inode: int
    reserved_names: set[str] = field(default_factory=set)
    owned_entries: dict[str, tuple[int, int]] = field(default_factory=dict)
    recovery_names: set[str] = field(default_factory=set)

    @classmethod
    def create(
        cls,
        parent: Path,
        *,
        expected_parent_identity: tuple[int, int] | None = None,
    ) -> TransactionWorkspace:
        """Verify, then create a private workspace below the pinned site."""
        descriptors = DescriptorSet()
        parent_fd = descriptors.add(
            os.open(
                parent,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            )
        )
        path: Path | None = None
        outcome = "unchanged"
        verified = True
        try:
            parent_metadata = os.fstat(parent_fd)
            observed_parent_identity = (
                parent_metadata.st_dev,
                parent_metadata.st_ino,
            )
            if expected_parent_identity is not None and observed_parent_identity != expected_parent_identity:
                message = f"Pinned Scribe site does not match its approved identity: {parent}."
                raise WorkspaceParentIdentityError(message)  # noqa: TRY301 - transaction primary
            outcome = "recovery"
            verified = False
            path = _allocate_workspace(parent, parent_fd=parent_fd)
            outcome = "workspace_retained"
            verified = True
            directory_fd = descriptors.add(
                os.open(
                    path.name,
                    os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=parent_fd,
                )
            )
            metadata = os.fstat(directory_fd)
            workspace = cls(
                path=path,
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                parent_device=parent_metadata.st_dev,
                parent_inode=parent_metadata.st_ino,
                device=metadata.st_dev,
                inode=metadata.st_ino,
            )
            descriptors.transfer(parent_fd)
            descriptors.transfer(directory_fd)
        except BaseException as primary:  # noqa: BLE001 - settle every acquired peer
            _raise_workspace_creation_failure(
                parent=parent,
                path=path,
                primary=primary,
                descriptors=descriptors,
                outcome=outcome,
                verified=verified,
            )
        return workspace

    def prepare_file(self, content: bytes, *, mode: int, prefix: str) -> AttestedPath:
        """Create, fsync, and attest one exact staged file."""
        for _attempt in range(128):
            name = f"{prefix}{secrets.token_hex(12)}.tmp"
            path = self.path / name
            try:
                os.stat(
                    name,
                    dir_fd=self.directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                continue
            try:
                descriptor = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    mode,
                    dir_fd=self.directory_fd,
                )
            except BaseException as primary:  # noqa: BLE001 - create may complete before adapter return
                self._raise_after_prepare_open_error(
                    name=name,
                    path=path,
                    primary=primary,
                )
            descriptors = DescriptorSet()
            descriptors.add(descriptor)
            expected: tuple[int, int] | None = None
            try:
                metadata = os.fstat(descriptor)
                expected = (metadata.st_dev, metadata.st_ino)
                self.owned_entries[name] = expected
                os.fchmod(descriptor, mode)
                handle = os.fdopen(descriptor, "wb")
                descriptors.transfer(descriptor)
                with handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                pinned = self.workspace_entry(name)
                state = capture_pinned_path_state(pinned)
                if state is None or state.content != content:
                    message = f"Could not attest staged Scribe bytes at {path}."
                    raise RuntimeError(message)  # noqa: TRY301 - cleanup needs the primary
            except BaseException as primary:  # noqa: BLE001 - exact private cleanup precedes surfacing
                self._raise_staging_failure(
                    name=name,
                    path=path,
                    expected=expected,
                    primary=primary,
                    descriptors=descriptors,
                )
            else:
                return AttestedPath(path=pinned, state=state)
        message = f"Could not allocate a unique Scribe transaction entry below {self.path}."
        raise FileExistsError(message)

    def _raise_after_prepare_open_error(
        self,
        *,
        name: str,
        path: Path,
        primary: BaseException,
    ) -> Never:
        """Classify an exclusive create without adopting an un-tokened child."""
        recovery = _workspace_failure_ledger(recovery_paths=(path,))
        try:
            os.stat(
                name,
                dir_fd=self.directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            settled = _workspace_failure_ledger()
            settled.raise_primary_after_verified_settlement(
                primary,
                outcome="unchanged",
                terminal_note=(f"Scribe verified that failed staging creation left {path} absent."),
            )
        except BaseException as observation_error:  # noqa: BLE001 - exact possible name is evidence
            self.recovery_names.add(name)
            recovery.record(primary, observation_error)
            recovery.raise_if_any(
                message=f"Could not classify failed Scribe staging creation at {path}.",
                outcome="recovery",
                terminal_note="",
                verified=False,
            )
        self.recovery_names.add(name)
        recovery.record(primary)
        recovery.raise_if_any(
            message=(
                f"Scribe staging creation did not return an identity token; preserving possible recovery at {path}."
            ),
            outcome="recovery",
            terminal_note="",
            verified=False,
        )
        raise primary

    def _raise_staging_failure(
        self,
        *,
        name: str,
        path: Path,
        expected: tuple[int, int] | None,
        primary: BaseException,
        descriptors: DescriptorSet,
    ) -> Never:
        """Settle one exact staged file and preserve all cleanup peers."""
        close_failures = descriptors.settle()
        cleanup_failures: list[BaseException] = []
        removed = False
        if expected is not None:
            try:
                removed = self._quarantine_and_unlink_entry(
                    name,
                    expected=expected,
                )
            except BaseException as exc:  # noqa: BLE001 - durability remains a peer
                cleanup_failures.append(exc)
                settlement = find_settlement_outcome(exc)
                removed = bool(settlement is not None and settlement.name == "entry_removed" and settlement.verified)
        if removed:
            self.owned_entries.pop(name, None)
            self.recovery_names.discard(name)
        else:
            self.recovery_names.add(name)
        durable = True
        try:
            os.fsync(self.directory_fd)
        except BaseException as exc:  # noqa: BLE001 - retain durability failure
            cleanup_failures.append(exc)
            durable = False
        cleanup = _workspace_failure_ledger(
            recovery_paths=(() if removed else (path,)),
        )
        cleanup.record_all(close_failures)
        cleanup.record_all(tuple(cleanup_failures))
        if removed and durable:
            terminal_note = (
                f"Scribe removed the exact staged entry {path} and settled "
                "its descriptor before preserving this interruption."
            )
            if cleanup.failures:
                cleanup.record(primary)
                cleanup.raise_if_any(
                    message=f"Scribe staging rolled back exactly for {path}.",
                    outcome="rolled_back",
                    terminal_note=terminal_note,
                    verified=True,
                )
            cleanup.raise_primary_after_verified_settlement(
                primary,
                outcome="rolled_back",
                terminal_note=terminal_note,
            )
        cleanup.record(primary)
        cleanup.raise_if_any(
            message=f"Scribe staging retained recovery evidence for {path}.",
            outcome="recovery",
            terminal_note="",
            verified=False,
        )
        raise primary

    def reserve(self, *, prefix: str) -> PinnedPath:
        """Return one unpredictable absent name within this workspace."""
        for _attempt in range(128):
            name = f"{prefix}{secrets.token_hex(12)}"
            if name in self.reserved_names:
                continue
            try:
                os.stat(name, dir_fd=self.directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                self.reserved_names.add(name)
                return self.workspace_entry(name)
        message = f"Could not reserve a unique Scribe quarantine below {self.path}."
        raise FileExistsError(message)

    def parent_entry(self, name: str) -> PinnedPath:
        """Address one binding filename through the pinned site descriptor."""
        return PinnedPath(
            directory_fd=self.parent_fd,
            name=name,
            display=self.path.parent / name,
        )

    def workspace_entry(self, name: str) -> PinnedPath:
        """Address one transaction filename through the pinned workspace."""
        return PinnedPath(
            directory_fd=self.directory_fd,
            name=name,
            display=self.path / name,
        )

    def claim(self, path: PinnedPath, *, device: int, inode: int) -> None:
        """Record the exact identity now held by one workspace entry."""
        if path.directory_fd != self.directory_fd or path.name not in self.reserved_names | self.owned_entries.keys():
            message = f"Cannot claim a path outside this Scribe workspace: {path}."
            raise ValueError(message)
        self.owned_entries[path.name] = (device, inode)

    def forget(self, path: PinnedPath) -> None:
        """Forget an entry proved absent after rollback."""
        if path.directory_fd != self.directory_fd:
            message = f"Cannot forget a path outside this Scribe workspace: {path}."
            raise ValueError(message)
        self.owned_entries.pop(path.name, None)

    def namespace_drift_paths(self) -> frozenset[Path]:
        """Return public names that no longer identify the pinned directories."""
        drifted: set[Path] = set()
        try:
            parent_metadata = self.path.parent.lstat()
        except OSError:
            drifted.add(self.path.parent)
        else:
            if (
                not stat.S_ISDIR(parent_metadata.st_mode)
                or parent_metadata.st_dev != self.parent_device
                or parent_metadata.st_ino != self.parent_inode
            ):
                drifted.add(self.path.parent)
        if not self._named_path_matches():
            drifted.add(self.path)
        return frozenset(drifted)

    def fsync_parent(self) -> None:
        """Persist binding-site namespace changes through the pinned descriptor."""
        os.fsync(self.parent_fd)

    def recovery_path(self, *, descriptor: int | None = None) -> Path:
        """Resolve the current Linux path of retained descriptor-pinned evidence."""
        directory_fd = self.directory_fd if descriptor is None else descriptor
        if directory_fd < 0:
            return self.path
        try:
            return Path(f"/proc/self/fd/{directory_fd}").readlink()
        except OSError:
            return self.path

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

        cleanup = _workspace_failure_ledger(
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
            message=f"Scribe workspace cleanup settled with recovery evidence for {self.path}.",
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
        cleanup = _workspace_failure_ledger(
            recovery_paths=recovery_paths,
        )
        cleanup.record_all(tuple(observation_errors))
        cleanup.record_all(descriptors.settle())
        cleanup.raise_if_any(
            message=f"Scribe relinquished workspace descriptor ownership with close failures: {self.path}.",
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
                ledger = _workspace_failure_ledger()
                if adapter_error is not None:
                    ledger.record(adapter_error)
                ledger.record(primary)
                ledger.raise_if_any(
                    message="Scribe staged-entry removal completed after adapter failure.",
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
            ledger = _workspace_failure_ledger()
            ledger.record(adapter_error)
            ledger.raise_if_any(
                message="Scribe staged-entry quarantine completed after adapter failure.",
                outcome="entry_removed",
                terminal_note=(f"Scribe verified removal of exact staged entry {cleanup_path}."),
                verified=True,
            )
        return True

    def _entry_identity(self, name: str) -> tuple[int, int] | None:
        try:
            metadata = os.stat(name, dir_fd=self.directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if stat.S_ISDIR(metadata.st_mode):
            return None
        return metadata.st_dev, metadata.st_ino

    def _restore_foreign_entry(self, cleanup_name: str, original_name: str) -> None:
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
                ledger = _workspace_failure_ledger(
                    recovery_paths=(original_path,),
                )
                ledger.record(primary)
                ledger.raise_if_any(
                    message="Foreign staged entry was restored after adapter failure.",
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
                ledger = _workspace_failure_ledger(recovery_paths=(self.path,))
                ledger.record(primary)
                ledger.raise_if_any(
                    message="Foreign workspace replacement was restored after adapter failure.",
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


def _allocate_workspace(parent: Path, *, parent_fd: int) -> Path:
    """Allocate one unpredictable directory through the pinned site."""
    for _attempt in range(128):
        path = parent / f".lychd-transaction-{secrets.token_hex(12)}"
        try:
            os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            continue
        try:
            os.mkdir(path.name, mode=0o700, dir_fd=parent_fd)
        except BaseException as primary:  # noqa: BLE001 - mkdir may complete before adapter return
            _raise_after_workspace_allocation_error(
                path,
                parent_fd=parent_fd,
                primary=primary,
            )
        return path
    message = f"Could not allocate a unique Scribe workspace below {parent}."
    raise FileExistsError(message)


def _raise_after_workspace_allocation_error(
    path: Path,
    *,
    parent_fd: int,
    primary: BaseException,
) -> Never:
    """Classify a mkdir failure without adopting an un-tokened candidate."""
    recovery = _workspace_failure_ledger(recovery_paths=(path,))
    try:
        os.stat(
            path.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        settled = _workspace_failure_ledger()
        settled.raise_primary_after_verified_settlement(
            primary,
            outcome="unchanged",
            terminal_note=(f"Scribe verified that failed workspace allocation left {path} absent."),
        )
    except BaseException as observation_error:  # noqa: BLE001 - exact possible name is evidence
        recovery.record(primary, observation_error)
        recovery.raise_if_any(
            message=f"Could not classify failed Scribe workspace allocation at {path}.",
            outcome="recovery",
            terminal_note="",
            verified=False,
        )
    recovery.record(primary)
    recovery.raise_if_any(
        message=(
            f"Scribe workspace allocation did not return an identity token; preserving possible recovery at {path}."
        ),
        outcome="recovery",
        terminal_note="",
        verified=False,
    )
    raise primary


def _raise_workspace_creation_failure(
    *,
    parent: Path,
    path: Path | None,
    primary: BaseException,
    descriptors: DescriptorSet,
    outcome: str,
    verified: bool,
) -> Never:
    """Settle all acquired workspace descriptors before surfacing creation truth."""
    settlement = find_settlement_outcome(primary)
    if settlement is not None:
        outcome = settlement.name
        verified = settlement.verified
    primary_paths = primary.recovery_paths if isinstance(primary, WorkspaceSettlementError) else ()
    retained_paths = primary_paths or ((path,) if path is not None and outcome == "workspace_retained" else ())
    cleanup = _workspace_failure_ledger(recovery_paths=retained_paths)
    cleanup.record_all(descriptors.settle())
    if verified and retained_paths:
        cleanup.record(primary)
        cleanup.raise_if_any(
            message=(
                f"Scribe workspace creation retained exact recovery at "
                f"{', '.join(str(candidate) for candidate in retained_paths)}."
            ),
            outcome=outcome,
            terminal_note=(
                f"Scribe settled every descriptor after preserving the verified {outcome} outcome for {path or parent}."
            ),
            verified=True,
        )
    if verified:
        cleanup.raise_primary_after_verified_settlement(
            primary,
            outcome=outcome,
            terminal_note=(
                f"Scribe settled every descriptor after preserving the verified {outcome} outcome for {path or parent}."
            ),
        )
    cleanup.record(primary)
    cleanup.raise_if_any(
        message=f"Scribe workspace creation left indeterminate recovery below {parent}.",
        outcome="recovery",
        terminal_note="",
        verified=False,
    )
    raise primary


__all__ = (
    "TransactionWorkspace",
    "WorkspaceParentIdentityError",
    "WorkspaceSettlementError",
)
