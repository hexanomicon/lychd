"""Recovery and authority finalization for a detached protected root."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.atomic_retirement import (
    AtomicRetirementError,
    AtomicRetirementService,
    RetirementIdentity,
)
from lychd.system.descriptor_settlement import FailureLedger
from lychd.system.interruptions import find_terminal_interruption
from lychd.system.protected_retirement_models import (
    AuthorityTransfer,
    ProtectedRootRecovery,
    ProtectedRootRetirementError,
    RetainedAuthority,
)
from lychd.system.protected_retirement_observation import observe_retirement_name


@dataclass(slots=True)
class _AuthorityRestoreReport:
    """All peer-settlement failures observed while restoring authorities."""

    failures: list[str] = field(default_factory=list)
    errors: list[BaseException] = field(default_factory=list)


class ProtectedRootSettlement:
    """Restore a detached root or finalize its externalized authorities."""

    def __init__(
        self,
        *,
        entries: AtomicRetirementService,
    ) -> None:
        """Bind the single-entry primitive used for final authority deletion."""
        self._entries = entries

    @staticmethod
    def _failure_ledger() -> FailureLedger:
        """Bind complete peer settlement to protected-root evidence."""
        return FailureLedger(
            error_factory=ProtectedRootRetirementError,
            subject="Protected root settlement",
        )

    def recover_root(
        self,
        *,
        parent_fd: int,
        directory_fd: int,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
        quarantine_name: str,
        quarantine_path: Path,
        transfers: tuple[AuthorityTransfer, ...],
        primary: BaseException,
    ) -> NoReturn:
        """Restore moved authorities and the detached root without clobbering."""
        self._recover_root(
            parent_fd=parent_fd,
            directory_fd=directory_fd,
            leaf=leaf,
            expected=expected,
            display_path=display_path,
            quarantine_name=quarantine_name,
            quarantine_path=quarantine_path,
            transfers=transfers,
            primary=primary,
        )

    def _recover_root(
        self,
        *,
        parent_fd: int,
        directory_fd: int,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
        quarantine_name: str,
        quarantine_path: Path,
        transfers: tuple[AuthorityTransfer, ...],
        primary: BaseException,
    ) -> NoReturn:
        """Settle every authority before proving or exposing root recovery."""
        report = self._restore_authorities(
            parent_fd=parent_fd,
            directory_fd=directory_fd,
            transfers=transfers,
        )
        public_root = self._observe_for_settlement(
            parent_fd=parent_fd,
            name=leaf,
            label=str(display_path),
            report=report,
        )
        quarantined_root = self._observe_for_settlement(
            parent_fd=parent_fd,
            name=quarantine_name,
            label=str(quarantine_path),
            report=report,
        )
        restore_error: BaseException | None = None
        if public_root is None and quarantined_root == expected:
            restore_error = self._restore_root_name(
                parent_fd=parent_fd,
                leaf=leaf,
                quarantine_name=quarantine_name,
            )
            if restore_error is not None:
                report.errors.append(restore_error)

        errors_before_final_observation = len(report.errors)
        recovery_is_exact = self._root_recovery_is_exact(
            parent_fd=parent_fd,
            directory_fd=directory_fd,
            leaf=leaf,
            expected=expected,
            quarantine_name=quarantine_name,
            transfers=transfers,
            report=report,
        )
        final_observation_verified = len(report.errors) == errors_before_final_observation
        if recovery_is_exact:
            cleanup = self._failure_ledger()
            cleanup.record_all(tuple(report.errors))
            settled_primary = self._classified_primary(
                primary,
                message=(
                    f"Protected root retirement failed; exact public state was restored for retry: {display_path}"
                ),
                outcome="restored",
            )
            cleanup.raise_primary_after_verified_settlement(
                settled_primary,
                outcome="restored",
                terminal_note=(
                    f"LychD del recovery: protected root {display_path} and its authorities were restored exactly."
                ),
            )
        if restore_error is not None:
            report.failures.append(f"{display_path}: {restore_error}")

        errors_before_quarantine_observation = len(report.errors)
        recovery_quarantine = self._observe_for_settlement(
            parent_fd=parent_fd,
            name=quarantine_name,
            label=str(quarantine_path),
            report=report,
        )
        quarantine_observation_failed = len(report.errors) != errors_before_quarantine_observation

        errors_before_collection = len(report.errors)
        recovery = self._collect_recovery(
            parent_fd=parent_fd,
            root=display_path,
            root_quarantine=(
                quarantine_path if recovery_quarantine is not None or quarantine_observation_failed else None
            ),
            root_retired=False,
            transfers=transfers,
            reason="; ".join(report.failures) or "root recovery could not be proven exact",
            failures=report.errors,
        )
        final_observation_verified = final_observation_verified and len(report.errors) == errors_before_collection
        settled_failures = (*report.errors, primary)
        terminal = self._first_terminal(*settled_failures)
        message = f"Protected root retirement retained recovery evidence for {display_path}"
        raise ProtectedRootRetirementError(
            message,
            root_recovery=recovery,
            failures=settled_failures,
            outcome="recovery",
            verified=final_observation_verified,
        ) from (terminal or primary)

    @staticmethod
    def _restore_root_name(
        *,
        parent_fd: int,
        leaf: str,
        quarantine_name: str,
    ) -> BaseException | None:
        """Attempt no-clobber root restoration and return a caught interruption."""
        try:
            rename_noreplace_at(
                quarantine_name,
                leaf,
                source_dir_fd=parent_fd,
                destination_dir_fd=parent_fd,
            )
        except BaseException as exc:  # noqa: BLE001 - caller verifies postcondition
            return exc
        return None

    def _restore_authorities(
        self,
        *,
        parent_fd: int,
        directory_fd: int,
        transfers: tuple[AuthorityTransfer, ...],
    ) -> _AuthorityRestoreReport:
        """Restore every transferred authority and report incomplete moves."""
        report = _AuthorityRestoreReport()
        for transfer in transfers:
            try:
                original = observe_retirement_name(
                    parent_fd=directory_fd,
                    name=transfer.entry.leaf,
                )
                backup = observe_retirement_name(
                    parent_fd=parent_fd,
                    name=transfer.backup_name,
                )
            except BaseException as exc:  # noqa: BLE001 - settle remaining peers
                report.errors.append(exc)
                report.failures.append(f"{transfer.entry.resource}: observation failed: {exc}")
                continue
            if original == transfer.entry.expected and backup is None:
                continue
            if original is None and backup == transfer.entry.expected:
                restore_error: BaseException | None = None
                try:
                    rename_noreplace_at(
                        transfer.backup_name,
                        transfer.entry.leaf,
                        source_dir_fd=parent_fd,
                        destination_dir_fd=directory_fd,
                    )
                except BaseException as exc:  # noqa: BLE001 - settle peers and postcondition
                    restore_error = exc
                    report.errors.append(exc)
                try:
                    restored_original = observe_retirement_name(
                        parent_fd=directory_fd,
                        name=transfer.entry.leaf,
                    )
                    restored_backup = observe_retirement_name(
                        parent_fd=parent_fd,
                        name=transfer.backup_name,
                    )
                except BaseException as exc:  # noqa: BLE001 - settle remaining peers
                    report.errors.append(exc)
                    report.failures.append(f"{transfer.entry.resource}: restoration observation failed: {exc}")
                    continue
                if restored_original == transfer.entry.expected and restored_backup is None:
                    continue
                if restore_error is not None:
                    report.failures.append(f"{transfer.entry.resource}: {restore_error}")
                    continue
            report.failures.append(f"{transfer.entry.resource}: source={original!r}, backup={backup!r}")
        return report

    @staticmethod
    def _root_recovery_is_exact(
        *,
        parent_fd: int,
        directory_fd: int,
        leaf: str,
        expected: RetirementIdentity,
        quarantine_name: str,
        transfers: tuple[AuthorityTransfer, ...],
        report: _AuthorityRestoreReport,
    ) -> bool:
        """Observe every peer and prove the complete public recovery state."""
        errors_before_observation = len(report.errors)
        exact = (
            ProtectedRootSettlement._observe_for_settlement(
                parent_fd=parent_fd,
                name=leaf,
                label=leaf,
                report=report,
            )
            == expected
        )
        exact = (
            ProtectedRootSettlement._observe_for_settlement(
                parent_fd=parent_fd,
                name=quarantine_name,
                label=quarantine_name,
                report=report,
            )
            is None
            and exact
        )
        for transfer in transfers:
            original = ProtectedRootSettlement._observe_for_settlement(
                parent_fd=directory_fd,
                name=transfer.entry.leaf,
                label=str(transfer.entry.resource),
                report=report,
            )
            backup = ProtectedRootSettlement._observe_for_settlement(
                parent_fd=parent_fd,
                name=transfer.backup_name,
                label=str(transfer.backup_path),
                report=report,
            )
            exact = original == transfer.entry.expected and backup is None and exact
        return exact and len(report.errors) == errors_before_observation

    def finalize_authorities(
        self,
        *,
        parent_fd: int,
        root: Path,
        transfers: tuple[AuthorityTransfer, ...],
        post_retirement_error: BaseException | None,
    ) -> None:
        """Finalize detached authorities, preserving every incomplete backup."""
        failures: list[BaseException] = []
        retained: dict[str, RetainedAuthority] = {}
        for transfer in transfers:
            try:
                observed = observe_retirement_name(
                    parent_fd=parent_fd,
                    name=transfer.backup_name,
                )
            except BaseException as exc:  # noqa: BLE001 - finalize remaining peers
                failures.append(exc)
                retained[transfer.entry.leaf] = RetainedAuthority(
                    resource=transfer.entry.resource,
                    recovery_path=transfer.backup_path,
                    expected=transfer.entry.expected,
                    observed=None,
                )
                continue
            if observed is None:
                continue
            if observed != transfer.entry.expected:
                retained[transfer.entry.leaf] = RetainedAuthority(
                    resource=transfer.entry.resource,
                    recovery_path=transfer.backup_path,
                    expected=transfer.entry.expected,
                    observed=observed,
                )
                failures.append(
                    ProtectedRootRetirementError(f"Detached authority changed identity: {transfer.backup_path}")
                )
                continue
            try:
                self._entries.retire_file(
                    parent_fd=parent_fd,
                    leaf=transfer.backup_name,
                    expected=transfer.entry.expected,
                    display_path=transfer.backup_path,
                )
            except BaseException as exc:  # noqa: BLE001 - finalize peers first
                failures.append(exc)
                recovery = exc.recovery if isinstance(exc, AtomicRetirementError) else None
                if recovery is not None:
                    retained[transfer.entry.leaf] = RetainedAuthority(
                        resource=transfer.entry.resource,
                        recovery_path=recovery.quarantine,
                        expected=transfer.entry.expected,
                        observed=recovery.observed,
                    )

        failures_before_collection = len(failures)
        collected_recovery = self._collect_recovery(
            parent_fd=parent_fd,
            root=root,
            root_quarantine=None,
            root_retired=True,
            transfers=transfers,
            reason="authority finalization did not complete",
            failures=failures,
        )
        recovery_verified = len(failures) == failures_before_collection
        for authority in collected_recovery.authorities:
            retained.setdefault(authority.resource.name, authority)

        self._raise_after_finalization(
            root=root,
            retained=retained,
            failures=failures,
            post_retirement_error=post_retirement_error,
            recovery_verified=recovery_verified,
        )

    @staticmethod
    def _raise_after_finalization(
        *,
        root: Path,
        retained: dict[str, RetainedAuthority],
        failures: list[BaseException],
        post_retirement_error: BaseException | None,
        recovery_verified: bool,
    ) -> None:
        """Surface retained recovery, terminal intent, or classified failure."""
        all_failures = tuple(failure for failure in (*failures, post_retirement_error) if failure is not None)
        terminal = ProtectedRootSettlement._first_terminal(*all_failures)
        if retained:
            recovery = ProtectedRootRecovery(
                root=root,
                root_quarantine=None,
                root_retired=True,
                authorities=tuple(retained.values()),
                reason="authority finalization did not complete",
            )
            primary = all_failures[0] if all_failures else None
            message = f"Root retired with protected authority recovery retained for {root}"
            raise ProtectedRootRetirementError(
                message,
                root_recovery=recovery,
                failures=all_failures,
                outcome="recovery",
                verified=recovery_verified,
            ) from (terminal or primary)

        if all_failures:
            primary = post_retirement_error if post_retirement_error is not None else all_failures[0]
            cleanup = ProtectedRootSettlement._failure_ledger()
            removed_primary = False
            peers: list[BaseException] = []
            for failure in all_failures:
                if failure is primary and not removed_primary:
                    removed_primary = True
                    continue
                peers.append(failure)
            cleanup.record_all(tuple(peers))
            settled_primary = ProtectedRootSettlement._classified_primary(
                primary,
                message=(f"Root retirement completed with a classified postcondition error: {root}"),
                outcome="retired",
            )
            cleanup.raise_primary_after_verified_settlement(
                settled_primary,
                outcome="retired",
                terminal_note=(f"LychD del recovery: {root} was retired and its protected authorities were finalized."),
            )

    @staticmethod
    def _classified_primary(
        primary: BaseException,
        *,
        message: str,
        outcome: str,
    ) -> BaseException:
        """Keep native intent or translate an ordinary classified failure."""
        if find_terminal_interruption(primary) is not None:
            return primary
        evidence = ProtectedRootRetirementError(
            message,
            failures=(primary,),
            outcome=outcome,
            verified=True,
        )
        evidence.__cause__ = primary
        return evidence

    @staticmethod
    def _collect_recovery(
        *,
        parent_fd: int,
        root: Path,
        root_quarantine: Path | None,
        root_retired: bool,
        transfers: tuple[AuthorityTransfer, ...],
        reason: str,
        failures: list[BaseException] | None = None,
    ) -> ProtectedRootRecovery:
        """Collect authority backups that remain at exact private names."""
        retained: list[RetainedAuthority] = []
        for transfer in transfers:
            try:
                observed = observe_retirement_name(
                    parent_fd=parent_fd,
                    name=transfer.backup_name,
                )
            except BaseException as exc:  # noqa: BLE001 - collect every recovery candidate
                if failures is not None:
                    failures.append(exc)
                observed = None
                retained.append(
                    RetainedAuthority(
                        resource=transfer.entry.resource,
                        recovery_path=transfer.backup_path,
                        expected=transfer.entry.expected,
                        observed=None,
                    )
                )
                continue
            if observed is not None:
                retained.append(
                    RetainedAuthority(
                        resource=transfer.entry.resource,
                        recovery_path=transfer.backup_path,
                        expected=transfer.entry.expected,
                        observed=observed,
                    )
                )
        return ProtectedRootRecovery(
            root=root,
            root_quarantine=root_quarantine,
            root_retired=root_retired,
            authorities=tuple(retained),
            reason=reason,
        )

    @staticmethod
    def _observe_for_settlement(
        *,
        parent_fd: int,
        name: str,
        label: str,
        report: _AuthorityRestoreReport,
    ) -> RetirementIdentity | None:
        """Observe one name while retaining interruption truth for final settlement."""
        try:
            return observe_retirement_name(
                parent_fd=parent_fd,
                name=name,
            )
        except BaseException as exc:  # noqa: BLE001 - caller settles remaining peers
            report.errors.append(exc)
            report.failures.append(f"{label}: observation failed: {exc}")
            return None

    @staticmethod
    def _first_terminal(
        *failures: BaseException | None,
    ) -> BaseException | None:
        """Find the first native terminal nested in any settled failure."""
        return next(
            (
                terminal
                for failure in failures
                if failure is not None and (terminal := find_terminal_interruption(failure)) is not None
            ),
            None,
        )


__all__ = ("ProtectedRootSettlement",)
