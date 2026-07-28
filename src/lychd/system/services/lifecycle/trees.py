"""No-follow, no-cross-mount removal of exact dedicated LychD roots."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from lychd.system.atomic_retirement import (
    AtomicRetirementError,
    AtomicRetirementService,
    RetirementIdentity,
    is_retirement_quarantine_name,
)
from lychd.system.btrfs_identity import BTRFS_SUBVOLUME_BOUNDARY_INODES
from lychd.system.descriptor_settlement import (
    DescriptorSet,
    FailureLedger,
    SettlementOutcome,
    find_settlement_outcome,
)
from lychd.system.interruptions import find_terminal_interruption
from lychd.system.protected_retirement import (
    ProtectedRetirementEntry,
    ProtectedRootRetirementError,
    ProtectedRootRetirementService,
    is_protected_authority_name,
)
from lychd.system.services.lifecycle.models import (
    DedicatedRootIdentity,
    LifecycleError,
)
from lychd.system.services.lifecycle.mount_identity import mount_id_for_fd
from lychd.system.services.lifecycle.paths import (
    lexically_normal,
    path_has_symlink_component,
)

_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
_PATH_FLAGS = getattr(os, "O_PATH", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)

_mount_id_for_fd = mount_id_for_fd


class ManagedTreeSettlementError(LifecycleError):
    """Recursive retirement settled with explicit descriptor-close evidence."""

    def __init__(
        self,
        message: str,
        *,
        failures: tuple[BaseException, ...],
        outcome: str,
        verified: bool,
    ) -> None:
        """Retain every peer failure and the verified local retirement outcome."""
        super().__init__(message)
        self.failures = failures
        self.outcome = outcome
        self.outcome_verified = verified


def _tree_failure_ledger() -> FailureLedger:
    """Bind generic descriptor settlement to recursive-retirement evidence."""
    return FailureLedger(
        error_factory=ManagedTreeSettlementError,
        subject="Managed tree settlement",
    )


def _scoped_tree_outcome(
    settlement: SettlementOutcome | None,
    *,
    phase: str,
) -> tuple[str, bool]:
    """Translate a nested proof without claiming that its parent also retired."""
    if settlement is None:
        return "recovery", False
    if phase == "retirement":
        return settlement.name, settlement.verified
    if phase == "contents":
        return "partial", settlement.verified
    return ("unchanged", True) if settlement.verified else ("recovery", False)


def _settle_tree_descriptors(
    descriptors: DescriptorSet,
    *,
    primary: BaseException | None,
    outcome: str,
    verified: bool,
    display_path: Path,
    activity: str,
) -> None:
    """Settle every descriptor without overstating an indeterminate outcome."""
    close_failures = descriptors.settle()
    cleanup = _tree_failure_ledger()
    if primary is not None:
        if verified:
            if isinstance(primary, ManagedTreeSettlementError) and (
                primary.outcome != outcome or primary.outcome_verified != verified
            ):
                if not close_failures and find_terminal_interruption(primary) is None:
                    primary.outcome = outcome
                    primary.outcome_verified = verified
                    raise primary
                cleanup.record(primary)
                cleanup.record_all(close_failures)
                cleanup.raise_if_any(
                    message=(
                        f"{activity.capitalize()} retained the verified {outcome} outcome for {display_path}: {primary}"
                    ),
                    outcome=outcome,
                    terminal_note=(
                        f"LychD del retained the verified {outcome} outcome for "
                        f"{display_path} after settling {activity}."
                    ),
                    verified=True,
                )
            cleanup.record_all(close_failures)
            cleanup.raise_primary_after_verified_settlement(
                primary,
                outcome=outcome,
                terminal_note=(
                    f"LychD del retained the verified {outcome} outcome for {display_path} after settling {activity}."
                ),
            )
        if isinstance(primary, ManagedTreeSettlementError) and not close_failures:
            raise primary
        if close_failures or find_terminal_interruption(primary) is not None:
            cleanup.record(primary)
            cleanup.record_all(close_failures)
            cleanup.raise_if_any(
                message=(f"{activity.capitalize()} retained recovery evidence for {display_path}."),
                outcome="recovery",
                terminal_note="",
                verified=False,
            )
        raise primary
    cleanup.record_all(close_failures)
    cleanup.raise_if_any(
        message=f"Could not cleanly release {activity} for {display_path}.",
        outcome=outcome,
        terminal_note=(
            f"LychD del verified the {outcome} outcome for {display_path} "
            f"before preserving this descriptor interruption."
        ),
        verified=verified,
    )


def _same_identity(expected: os.stat_result, observed: os.stat_result) -> bool:
    """Compare every stable entry attribute required before deletion."""
    return RetirementIdentity.from_stat(expected) == RetirementIdentity.from_stat(observed)


def _ordinary_names(
    names: tuple[str, ...],
    *,
    protected_names: tuple[str, ...],
    display_path: Path,
) -> tuple[str, ...]:
    """Exclude protected recovery authorities from ordinary tree traversal."""
    if not protected_names:
        return names
    missing = next((name for name in protected_names if name not in names), None)
    if missing is not None:
        msg = f"Protected final entry disappeared before deletion: {display_path / missing}"
        raise LifecycleError(msg)
    protected = frozenset(protected_names)
    return tuple(name for name in names if name not in protected)


def _validated_final_names(
    root: Path,
    final_entries: tuple[Path, ...],
) -> tuple[str, ...]:
    """Return protected direct-child names or reject an unsafe request."""
    names: list[str] = []
    for final_entry in final_entries:
        if final_entry.parent != root or final_entry.name in {"", ".", ".."}:
            msg = f"Final protected entry is not a direct child of {root}: {final_entry}"
            raise LifecycleError(msg)
        if final_entry.name in names:
            msg = f"Protected final entries contain a duplicate: {final_entry}"
            raise LifecycleError(msg)
        names.append(final_entry.name)
    return tuple(names)


def _require_mount_identity(
    descriptor: int,
    *,
    expected_mount_id: int,
    message: str,
) -> None:
    """Reject a descriptor that crossed or became a mount boundary."""
    if _mount_id_for_fd(descriptor) != expected_mount_id:
        raise LifecycleError(message)


def _attest_open_root_descriptor(
    descriptor: int,
    *,
    before_open: os.stat_result,
    parent_mount_id: int,
    expected_identity: DedicatedRootIdentity,
    root: Path,
) -> tuple[os.stat_result, int]:
    """Revalidate an opened dedicated root against both prior attestations."""
    metadata = os.fstat(descriptor)
    if not _same_identity(before_open, metadata):
        msg = f"Dedicated root identity changed before deletion: {root}"
        raise LifecycleError(msg)
    if metadata.st_dev != expected_identity.device or metadata.st_ino != expected_identity.inode:
        msg = f"Dedicated root no longer matches attested identity: {root}"
        raise LifecycleError(msg)
    mount_id = _mount_id_for_fd(descriptor)
    if mount_id != parent_mount_id:
        msg = f"Dedicated root became a mount boundary before deletion: {root}"
        raise LifecycleError(msg)
    return metadata, mount_id


def _open_root_descriptor(
    root: Path,
    *,
    parent_descriptor: int,
    parent_mount_id: int,
    expected_identity: DedicatedRootIdentity,
) -> tuple[int, os.stat_result, int]:
    """Open and revalidate one root relative to its anchored parent."""
    before_open = os.stat(
        root.name,
        dir_fd=parent_descriptor,
        follow_symlinks=False,
    )
    if not stat.S_ISDIR(before_open.st_mode) or before_open.st_uid != os.getuid():
        msg = f"Dedicated root became unsafe before descriptor open: {root}"
        raise LifecycleError(msg)
    descriptor = os.open(
        root.name,
        _DIRECTORY_FLAGS,
        dir_fd=parent_descriptor,
    )
    descriptors = DescriptorSet()
    descriptors.add(descriptor)
    try:
        metadata, mount_id = _attest_open_root_descriptor(
            descriptor,
            before_open=before_open,
            parent_mount_id=parent_mount_id,
            expected_identity=expected_identity,
            root=root,
        )
    except BaseException as exc:
        failures = descriptors.settle()
        if not failures:
            raise
        cleanup = _tree_failure_ledger()
        cleanup.record_all(failures)
        cleanup.raise_primary_after_verified_settlement(
            exc,
            outcome="unchanged",
            terminal_note=(f"LychD del left {root} unchanged after settling its root-attestation descriptor."),
        )
    return descriptors.transfer(descriptor), metadata, mount_id


@dataclass(frozen=True)
class ManagedTreeInspection:
    """Read-only verdict for one exact dedicated root."""

    root: Path
    exists: bool
    removable: bool
    detail: str


class ManagedTreeService:
    """Inspect and remove only constructor-authorized dedicated roots."""

    def __init__(
        self,
        allowed_roots: tuple[Path, ...],
        *,
        retirement: AtomicRetirementService | None = None,
    ) -> None:
        """Bind the exact roots; every possible subvolume root remains a barrier."""
        if len(set(allowed_roots)) != len(allowed_roots):
            msg = "Dedicated deletion roots must be unique."
            raise LifecycleError(msg)
        self._allowed_roots = frozenset(allowed_roots)
        self._retirement = retirement or AtomicRetirementService()
        self._protected_retirement = ProtectedRootRetirementService(
            entries=self._retirement,
        )

    def inspect(  # noqa: C901, PLR0911 - every unsafe filesystem shape has a distinct verdict
        self,
        root: Path,
        *,
        deferred_mounts: frozenset[Path] = frozenset(),
        deferred_subvolumes: frozenset[Path] = frozenset(),
    ) -> ManagedTreeInspection:
        """Prove one root can be traversed without links or mount crossings."""
        unsafe = self._unsafe_root(root)
        if unsafe is not None:
            return ManagedTreeInspection(
                root=root,
                exists=os.path.lexists(root),
                removable=False,
                detail=unsafe,
            )
        try:
            residue = self._retained_sibling_residue(root)
        except OSError as exc:
            return ManagedTreeInspection(
                root=root,
                exists=os.path.lexists(root),
                removable=False,
                detail=f"cannot inspect sibling retirement recovery safely: {exc}",
            )
        if residue is not None:
            return ManagedTreeInspection(
                root=root,
                exists=os.path.lexists(root),
                removable=False,
                detail=f"retained retirement recovery requires operator review: {residue}",
            )
        if not os.path.lexists(root):
            return ManagedTreeInspection(
                root=root,
                exists=False,
                removable=True,
                detail="dedicated root is already absent",
            )

        try:
            metadata = root.lstat()
        except OSError as exc:
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail=f"cannot inspect root: {exc}",
            )
        if not stat.S_ISDIR(metadata.st_mode):
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail="dedicated root is not a directory",
            )
        if metadata.st_uid != os.getuid():
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail=f"dedicated root is owned by uid {metadata.st_uid}, expected {os.getuid()}",
            )
        if self._is_possible_subvolume_boundary(metadata):
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail="possible Btrfs subvolume boundary occupies the dedicated root",
            )
        try:
            if root.is_mount():
                return ManagedTreeInspection(
                    root=root,
                    exists=True,
                    removable=False,
                    detail="dedicated root is itself a mountpoint",
                )
            blocker, deferred_count = self._scan(
                root,
                expected_device=metadata.st_dev,
                deferred_boundaries=(deferred_mounts | deferred_subvolumes),
            )
        except OSError as exc:
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail=f"cannot inspect tree safely: {exc}",
            )
        if blocker is not None:
            return ManagedTreeInspection(
                root=root,
                exists=True,
                removable=False,
                detail=blocker,
            )
        return ManagedTreeInspection(
            root=root,
            exists=True,
            removable=True,
            detail=(
                f"safe after {deferred_count} attested mount handoff(s)"
                if deferred_count
                else "dedicated root contains no symlink traversal or mount boundary"
            ),
        )

    def remove(
        self,
        root: Path,
        *,
        expected_identity: DedicatedRootIdentity,
        final_entries: tuple[Path, ...] = (),
    ) -> None:
        """Remove one revalidated root through directory-relative descriptors."""
        final_names, exists = self._validate_removal_request(
            root,
            expected_identity=expected_identity,
            final_entries=final_entries,
        )
        if not exists:
            return

        descriptors = DescriptorSet()
        primary: BaseException | None = None
        outcome = "unchanged"
        outcome_verified = True
        phase = "attestation"
        try:
            parent_descriptor = descriptors.add(os.open(root.parent, _DIRECTORY_FLAGS))
            parent_mount_id = _mount_id_for_fd(parent_descriptor)
            descriptor, metadata, mount_id = _open_root_descriptor(
                root,
                parent_descriptor=parent_descriptor,
                parent_mount_id=parent_mount_id,
                expected_identity=expected_identity,
            )
            descriptors.add(descriptor)
            outcome = "recovery"
            outcome_verified = False
            phase = "contents"
            self._remove_contents(
                descriptor,
                display_path=root,
                expected_device=metadata.st_dev,
                expected_mount_id=mount_id,
                protected_names=final_names,
            )
            _require_mount_identity(
                descriptor,
                expected_mount_id=mount_id,
                message=f"Dedicated root mount identity changed before final retirement: {root}",
            )
            if final_names:
                protected = self._protected_entries(
                    descriptor,
                    display_path=root,
                    expected_device=metadata.st_dev,
                    expected_mount_id=mount_id,
                    names=final_names,
                )
                phase = "retirement"
                self._protected_retirement.retire(
                    parent_fd=parent_descriptor,
                    directory_fd=descriptor,
                    leaf=root.name,
                    expected=RetirementIdentity.from_stat(metadata),
                    display_path=root,
                    protected=protected,
                )
            else:
                phase = "retirement"
                self._retirement.retire_directory(
                    parent_fd=parent_descriptor,
                    leaf=root.name,
                    expected=RetirementIdentity.from_stat(metadata),
                    display_path=root,
                )
            outcome = "retired"
            outcome_verified = True
        except AtomicRetirementError as exc:
            settlement = find_settlement_outcome(exc)
            outcome, outcome_verified = _scoped_tree_outcome(
                settlement,
                phase=phase,
            )
            try:
                self._raise_retirement_error(exc)
            except BaseException as surfaced:  # noqa: BLE001 - descriptors remain peers
                primary = surfaced
        except OSError as exc:
            msg = f"Could not remove dedicated root safely: {root}: {exc}"
            primary = LifecycleError(msg)
            primary.__cause__ = exc
        except BaseException as exc:  # noqa: BLE001 - settle descriptors before surfacing
            primary = exc
            settlement = find_settlement_outcome(exc)
            if settlement is not None:
                outcome, outcome_verified = _scoped_tree_outcome(
                    settlement,
                    phase=phase,
                )

        _settle_tree_descriptors(
            descriptors,
            primary=primary,
            outcome=outcome,
            verified=outcome_verified,
            display_path=root,
            activity="every recursive-retirement descriptor",
        )

    def _validate_removal_request(
        self,
        root: Path,
        *,
        expected_identity: DedicatedRootIdentity,
        final_entries: tuple[Path, ...],
    ) -> tuple[tuple[str, ...], bool]:
        """Validate the public request before acquiring recursive authority."""
        if expected_identity.path != root:
            msg = f"Attested dedicated-root identity targets a different path: {expected_identity.path}"
            raise LifecycleError(msg)
        final_names = _validated_final_names(root, final_entries)
        inspection = self.inspect(root)
        if not inspection.removable:
            msg = f"Refusing to remove unsafe dedicated root {root}: {inspection.detail}"
            raise LifecycleError(msg)
        return final_names, inspection.exists

    def _unsafe_root(self, root: Path) -> str | None:
        if root not in self._allowed_roots:
            return "root is outside the exact deletion allowlist"
        if not lexically_normal(root):
            return "root is not an absolute canonical lexical path"
        if root in {Path("/"), Path.home()}:
            return "root is too broad for recursive deletion"
        if symlink := path_has_symlink_component(root):
            return f"root traverses an untrusted symlink component: {symlink}"
        for other in self._allowed_roots:
            if other == root:
                continue
            if root in other.parents or other in root.parents:
                return f"dedicated roots unexpectedly overlap: {root} and {other}"
        return None

    @staticmethod
    def _retained_sibling_residue(root: Path) -> Path | None:
        """Find private recovery left beside a root by an earlier transaction."""
        try:
            with os.scandir(root.parent) as entries:
                for entry in entries:
                    if is_retirement_quarantine_name(entry.name) or is_protected_authority_name(entry.name):
                        return root.parent / entry.name
        except FileNotFoundError:
            return None
        return None

    @staticmethod
    def _recovery_detail(error: AtomicRetirementError) -> str | None:
        """Render exact retained paths without erasing the typed cause."""
        if isinstance(error, ProtectedRootRetirementError):
            recovery = error.root_recovery
            if recovery is None:
                return None
            paths = [
                *((str(recovery.root_quarantine),) if recovery.root_quarantine is not None else ()),
                *(str(authority.recovery_path) for authority in recovery.authorities),
            ]
            location = ", ".join(paths) or "no retained path remained"
            return f"{location} ({recovery.reason})"
        if error.recovery is not None:
            return f"{error.recovery.quarantine} ({error.recovery.reason})"
        return None

    @classmethod
    def _raise_retirement_error(
        cls,
        error: AtomicRetirementError,
    ) -> NoReturn:
        """Preserve terminal intent and attach exact recovery paths."""
        recovery = cls._recovery_detail(error)
        suffix = f"; recovery: {recovery}" if recovery is not None else ""
        message = f"Could not retire dedicated tree entry safely: {error}{suffix}"
        terminal = find_terminal_interruption(error)
        settlement = find_settlement_outcome(error)
        if settlement is not None:
            evidence: LifecycleError = ManagedTreeSettlementError(
                message,
                failures=(error,),
                outcome=settlement.name,
                verified=settlement.verified,
            )
        else:
            evidence = LifecycleError(message)
        if terminal is not None and settlement is not None and settlement.verified:
            terminal.add_note(message)
            raise terminal from evidence
        raise evidence from error

    def _scan(
        self,
        directory: Path,
        *,
        expected_device: int,
        deferred_boundaries: frozenset[Path],
    ) -> tuple[str | None, int]:
        deferred_count = 0
        with os.scandir(directory) as entries:
            for entry in entries:
                child = directory / entry.name
                if is_retirement_quarantine_name(entry.name):
                    return (
                        f"retained atomic-retirement quarantine requires recovery: {child}",
                        deferred_count,
                    )
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode):
                    if child in deferred_boundaries:
                        deferred_count += 1
                        continue
                    if self._is_possible_subvolume_boundary(metadata):
                        return (
                            f"possible Btrfs subvolume boundary exists beneath dedicated root: {child}",
                            deferred_count,
                        )
                    if metadata.st_dev != expected_device:
                        return (
                            f"filesystem boundary exists beneath dedicated root: {child}",
                            deferred_count,
                        )
                    if child.is_mount():
                        return (
                            f"nested mount exists beneath dedicated root: {child}",
                            deferred_count,
                        )
                    blocker, nested_deferred = self._scan(
                        child,
                        expected_device=expected_device,
                        deferred_boundaries=deferred_boundaries,
                    )
                    deferred_count += nested_deferred
                    if blocker is not None:
                        return blocker, deferred_count
        return None, deferred_count

    def _remove_contents(
        self,
        descriptor: int,
        *,
        display_path: Path,
        expected_device: int,
        expected_mount_id: int,
        protected_names: tuple[str, ...] = (),
    ) -> None:
        with os.scandir(descriptor) as entries:
            names = tuple(entry.name for entry in entries)
        names = _ordinary_names(
            names,
            protected_names=protected_names,
            display_path=display_path,
        )

        for name in names:
            if is_retirement_quarantine_name(name):
                msg = f"Retained atomic-retirement quarantine requires recovery: {display_path / name}"
                raise LifecycleError(msg)
            metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            child = display_path / name
            if stat.S_ISDIR(metadata.st_mode):
                self._remove_directory(
                    descriptor,
                    name=name,
                    metadata=metadata,
                    child=child,
                    expected_device=expected_device,
                    expected_mount_id=expected_mount_id,
                )
            else:
                self._remove_file(
                    descriptor,
                    name=name,
                    metadata=metadata,
                    child=child,
                    expected_device=expected_device,
                    expected_mount_id=expected_mount_id,
                )

    @staticmethod
    def _protected_entries(
        descriptor: int,
        *,
        display_path: Path,
        expected_device: int,
        expected_mount_id: int,
        names: tuple[str, ...],
    ) -> tuple[ProtectedRetirementEntry, ...]:
        """Pin and attest the authority files retained for root retirement."""
        protected: list[ProtectedRetirementEntry] = []
        for name in names:
            child = display_path / name
            descriptors = DescriptorSet()
            entry_descriptor = descriptors.add(
                os.open(
                    name,
                    _PATH_FLAGS,
                    dir_fd=descriptor,
                )
            )
            primary: BaseException | None = None
            try:
                metadata = ManagedTreeService._attest_protected_entry(
                    descriptor,
                    entry_descriptor=entry_descriptor,
                    name=name,
                    child=child,
                    expected_device=expected_device,
                    expected_mount_id=expected_mount_id,
                )
                protected.append(
                    ProtectedRetirementEntry(
                        leaf=name,
                        resource=child,
                        expected=RetirementIdentity.from_stat(metadata),
                    )
                )
            except BaseException as exc:  # noqa: BLE001 - descriptor close is a peer
                primary = exc
            _settle_tree_descriptors(
                descriptors,
                primary=primary,
                outcome="unchanged",
                verified=True,
                display_path=child,
                activity="its protected-entry descriptor",
            )
        return tuple(protected)

    @staticmethod
    def _attest_protected_entry(
        descriptor: int,
        *,
        entry_descriptor: int,
        name: str,
        child: Path,
        expected_device: int,
        expected_mount_id: int,
    ) -> os.stat_result:
        """Attest one protected final child through both pinned names."""
        metadata = os.fstat(entry_descriptor)
        if stat.S_ISDIR(metadata.st_mode) or metadata.st_dev != expected_device:
            msg = f"Protected final entry became unsafe before root retirement: {child}"
            raise LifecycleError(msg)
        _require_mount_identity(
            entry_descriptor,
            expected_mount_id=expected_mount_id,
            message=f"Protected final entry became unsafe before root retirement: {child}",
        )
        current = os.stat(
            name,
            dir_fd=descriptor,
            follow_symlinks=False,
        )
        if not _same_identity(metadata, current):
            msg = f"Protected final entry changed before root retirement: {child}"
            raise LifecycleError(msg)
        return metadata

    def _remove_directory(
        self,
        descriptor: int,
        *,
        name: str,
        metadata: os.stat_result,
        child: Path,
        expected_device: int,
        expected_mount_id: int,
    ) -> None:
        """Revalidate, empty, and unlink one real child directory."""
        if self._is_possible_subvolume_boundary(metadata):
            msg = f"Possible Btrfs subvolume boundary appeared during dedicated-root deletion: {child}"
            raise LifecycleError(msg)
        if metadata.st_dev != expected_device:
            msg = f"Mount boundary appeared during dedicated-root deletion: {child}"
            raise LifecycleError(msg)
        descriptors = DescriptorSet()
        child_descriptor = descriptors.add(
            os.open(
                name,
                _DIRECTORY_FLAGS,
                dir_fd=descriptor,
            )
        )
        primary: BaseException | None = None
        outcome = "unchanged"
        outcome_verified = True
        phase = "attestation"
        try:
            child_metadata = self._attest_child_directory(
                metadata,
                child_descriptor=child_descriptor,
                child=child,
                expected_device=expected_device,
                expected_mount_id=expected_mount_id,
            )
            outcome = "recovery"
            outcome_verified = False
            phase = "contents"
            self._remove_contents(
                child_descriptor,
                display_path=child,
                expected_device=expected_device,
                expected_mount_id=expected_mount_id,
            )
            _require_mount_identity(
                child_descriptor,
                expected_mount_id=expected_mount_id,
                message=f"Mount boundary appeared before directory retirement: {child}",
            )
            phase = "retirement"
            self._retirement.retire_directory(
                parent_fd=descriptor,
                leaf=name,
                expected=RetirementIdentity.from_stat(child_metadata),
                display_path=child,
            )
            outcome = "retired"
            outcome_verified = True
        except BaseException as exc:  # noqa: BLE001 - descriptor close is a peer
            primary = exc
            settlement = find_settlement_outcome(exc)
            if settlement is not None:
                outcome, outcome_verified = _scoped_tree_outcome(
                    settlement,
                    phase=phase,
                )
        _settle_tree_descriptors(
            descriptors,
            primary=primary,
            outcome=outcome,
            verified=outcome_verified,
            display_path=child,
            activity="its recursive directory descriptor",
        )

    @staticmethod
    def _attest_child_directory(
        expected: os.stat_result,
        *,
        child_descriptor: int,
        child: Path,
        expected_device: int,
        expected_mount_id: int,
    ) -> os.stat_result:
        """Revalidate one opened child directory before recursive mutation."""
        observed = os.fstat(child_descriptor)
        if not _same_identity(expected, observed) or observed.st_dev != expected_device:
            msg = f"Filesystem identity changed during deletion: {child}"
            raise LifecycleError(msg)
        _require_mount_identity(
            child_descriptor,
            expected_mount_id=expected_mount_id,
            message=f"Mount boundary appeared during dedicated-root deletion: {child}",
        )
        return observed

    def _remove_file(
        self,
        descriptor: int,
        *,
        name: str,
        metadata: os.stat_result,
        child: Path,
        expected_device: int,
        expected_mount_id: int,
    ) -> None:
        """Revalidate and unlink one non-directory entry without following it."""
        descriptors = DescriptorSet()
        entry_descriptor = descriptors.add(
            os.open(
                name,
                _PATH_FLAGS,
                dir_fd=descriptor,
            )
        )
        primary: BaseException | None = None
        outcome = "unchanged"
        outcome_verified = True
        try:
            opened = self._attest_file_entry(
                metadata,
                entry_descriptor=entry_descriptor,
                child=child,
                expected_device=expected_device,
                expected_mount_id=expected_mount_id,
            )
            outcome = "recovery"
            outcome_verified = False
            self._retirement.retire_file(
                parent_fd=descriptor,
                leaf=name,
                expected=RetirementIdentity.from_stat(opened),
                display_path=child,
            )
            outcome = "retired"
            outcome_verified = True
        except BaseException as exc:  # noqa: BLE001 - descriptor close is a peer
            primary = exc
            settlement = find_settlement_outcome(exc)
            if settlement is not None:
                outcome = settlement.name
                outcome_verified = settlement.verified
        _settle_tree_descriptors(
            descriptors,
            primary=primary,
            outcome=outcome,
            verified=outcome_verified,
            display_path=child,
            activity="its entry-attestation descriptor",
        )

    @staticmethod
    def _attest_file_entry(
        expected: os.stat_result,
        *,
        entry_descriptor: int,
        child: Path,
        expected_device: int,
        expected_mount_id: int,
    ) -> os.stat_result:
        """Revalidate one opened non-directory entry before retirement."""
        observed = os.fstat(entry_descriptor)
        if not _same_identity(expected, observed) or observed.st_dev != expected_device:
            msg = f"Entry identity changed during deletion: {child}"
            raise LifecycleError(msg)
        _require_mount_identity(
            entry_descriptor,
            expected_mount_id=expected_mount_id,
            message=f"Mount boundary appeared during dedicated-root deletion: {child}",
        )
        return observed

    @staticmethod
    def _is_possible_subvolume_boundary(metadata: os.stat_result) -> bool:
        """Treat every Btrfs root/stub inode signature as a fail-closed barrier."""
        return metadata.st_ino in BTRFS_SUBVOLUME_BOUNDARY_INODES


__all__ = ("ManagedTreeInspection", "ManagedTreeService")
