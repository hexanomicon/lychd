"""Atomic retirement of a root whose recovery authorities must survive it."""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path
from typing import NoReturn

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.atomic_retirement import (
    AtomicRetirementService,
    RetirementIdentity,
    new_retirement_quarantine_name,
)
from lychd.system.interruptions import find_terminal_interruption
from lychd.system.protected_retirement_models import (
    AuthorityTransfer,
    ProtectedRetirementEntry,
    ProtectedRootRecovery,
    ProtectedRootRetirementError,
    RetainedAuthority,
)
from lychd.system.protected_retirement_naming import (
    is_protected_authority_name,
    new_protected_authority_name,
)
from lychd.system.protected_retirement_observation import (
    observe_retirement_name,
)
from lychd.system.protected_retirement_recovery import (
    ProtectedRootSettlement,
)

_QUARANTINE_ATTEMPTS = 8


class ProtectedRootRetirementService:
    """Retire a root while retaining authority until deletion is proven."""

    def __init__(
        self,
        *,
        entries: AtomicRetirementService | None = None,
    ) -> None:
        """Compose detachment with the independent settlement service."""
        self._settlement = ProtectedRootSettlement(
            entries=entries or AtomicRetirementService(),
        )

    def retire(
        self,
        *,
        parent_fd: int,
        directory_fd: int,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
        protected: tuple[ProtectedRetirementEntry, ...],
    ) -> None:
        """Detach the root, preserve authorities, then retire both."""
        self._validate_root(
            leaf=leaf,
            expected=expected,
            display_path=display_path,
        )
        self._validate_authorities(
            directory_fd=directory_fd,
            root=display_path,
            protected=protected,
        )
        if (
            observe_retirement_name(
                parent_fd=parent_fd,
                name=leaf,
            )
            != expected
        ):
            message = f"Protected root changed before detachment: {display_path}"
            raise ProtectedRootRetirementError(message)

        quarantine_name = self._detach_root(
            parent_fd=parent_fd,
            leaf=leaf,
            expected=expected,
            display_path=display_path,
        )
        quarantine_path = display_path.with_name(quarantine_name)
        transfers = self._authority_transfers(
            root=display_path,
            protected=protected,
        )
        self._retire_detached_root(
            parent_fd=parent_fd,
            directory_fd=directory_fd,
            leaf=leaf,
            expected=expected,
            display_path=display_path,
            quarantine_name=quarantine_name,
            quarantine_path=quarantine_path,
            transfers=transfers,
        )

    def _retire_detached_root(
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
    ) -> None:
        """Transfer authorities and retire the already detached root."""
        try:
            quarantined_root = observe_retirement_name(
                parent_fd=parent_fd,
                name=quarantine_name,
            )
        except BaseException as exc:  # noqa: BLE001 - namespace proof is post-effect
            self._raise_observation_recovery(
                display_path=display_path,
                quarantine_path=quarantine_path,
                primary=exc,
                reason="detached protected-root identity could not be observed",
            )
        if quarantined_root != expected:
            self._settlement.recover_root(
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                leaf=leaf,
                expected=expected,
                display_path=display_path,
                quarantine_name=quarantine_name,
                quarantine_path=quarantine_path,
                transfers=transfers,
                primary=ProtectedRootRetirementError(
                    f"Protected root identity changed before retirement: {display_path}"
                ),
            )

        post_retirement_error = self._remove_detached_root(
            parent_fd=parent_fd,
            directory_fd=directory_fd,
            leaf=leaf,
            expected=expected,
            display_path=display_path,
            quarantine_name=quarantine_name,
            quarantine_path=quarantine_path,
            transfers=transfers,
        )
        self._settlement.finalize_authorities(
            parent_fd=parent_fd,
            root=display_path,
            transfers=transfers,
            post_retirement_error=post_retirement_error,
        )

    def _remove_detached_root(
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
    ) -> BaseException | None:
        """Move authorities out and return only a post-effect root error."""
        try:
            self._transfer_authorities(
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                transfers=transfers,
            )
            try:
                os.rmdir(quarantine_name, dir_fd=parent_fd)
            except BaseException as exc:  # noqa: BLE001 - classify root postcondition
                if (
                    observe_retirement_name(
                        parent_fd=parent_fd,
                        name=quarantine_name,
                    )
                    is not None
                ):
                    self._settlement.recover_root(
                        parent_fd=parent_fd,
                        directory_fd=directory_fd,
                        leaf=leaf,
                        expected=expected,
                        display_path=display_path,
                        quarantine_name=quarantine_name,
                        quarantine_path=quarantine_path,
                        transfers=transfers,
                        primary=exc,
                    )
                return exc
        except ProtectedRootRetirementError:
            raise
        except BaseException as exc:  # noqa: BLE001 - settle partial transfer
            self._settlement.recover_root(
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                leaf=leaf,
                expected=expected,
                display_path=display_path,
                quarantine_name=quarantine_name,
                quarantine_path=quarantine_path,
                transfers=transfers,
                primary=exc,
            )
        return None

    @staticmethod
    def _transfer_authorities(
        *,
        parent_fd: int,
        directory_fd: int,
        transfers: tuple[AuthorityTransfer, ...],
    ) -> None:
        """Move every authority to its collision-resistant parent backup."""
        for transfer in transfers:
            rename_noreplace_at(
                transfer.entry.leaf,
                transfer.backup_name,
                source_dir_fd=directory_fd,
                destination_dir_fd=parent_fd,
            )

    @staticmethod
    def _authority_transfers(
        *,
        root: Path,
        protected: tuple[ProtectedRetirementEntry, ...],
    ) -> tuple[AuthorityTransfer, ...]:
        """Allocate private sibling names before moving any authority."""
        return tuple(
            AuthorityTransfer(
                entry=entry,
                backup_name=(backup_name := new_protected_authority_name()),
                backup_path=root.parent / backup_name,
            )
            for entry in protected
        )

    @staticmethod
    def _validate_root(
        *,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
    ) -> None:
        """Reject an incoherent root request before namespace mutation."""
        if (
            not leaf
            or leaf in {".", ".."}
            or "/" in leaf
            or display_path.name != leaf
            or expected.file_type != stat.S_IFDIR
        ):
            message = f"Protected retirement target must be one exact directory leaf: {display_path}"
            raise ProtectedRootRetirementError(message)

    @staticmethod
    def _validate_authorities(
        *,
        directory_fd: int,
        root: Path,
        protected: tuple[ProtectedRetirementEntry, ...],
    ) -> None:
        """Require distinct, exact non-directory authorities before detachment."""
        seen: set[str] = set()
        for entry in protected:
            if (
                entry.leaf in seen
                or entry.leaf in {"", ".", ".."}
                or "/" in entry.leaf
                or entry.resource.parent != root
                or entry.resource.name != entry.leaf
                or entry.expected.file_type == stat.S_IFDIR
            ):
                message = f"Invalid protected root authority: {entry.resource}"
                raise ProtectedRootRetirementError(message)
            seen.add(entry.leaf)
            if (
                observe_retirement_name(
                    parent_fd=directory_fd,
                    name=entry.leaf,
                )
                != entry.expected
            ):
                message = f"Protected root authority changed before detachment: {entry.resource}"
                raise ProtectedRootRetirementError(message)

    def _detach_root(
        self,
        *,
        parent_fd: int,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
    ) -> str:
        """Move the root aside and settle interruptions by postcondition."""
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
                message = f"Could not atomically detach protected root: {display_path}"
                raise ProtectedRootRetirementError(message) from exc
            except BaseException as exc:  # noqa: BLE001 - settle rename signal
                self._settle_detach_interruption(
                    parent_fd=parent_fd,
                    leaf=leaf,
                    expected=expected,
                    display_path=display_path,
                    quarantine_name=quarantine_name,
                    primary=exc,
                )
            return quarantine_name
        message = f"Could not allocate a private protected-root quarantine: {display_path}"
        raise ProtectedRootRetirementError(message)

    @staticmethod
    def _settle_detach_interruption(
        *,
        parent_fd: int,
        leaf: str,
        expected: RetirementIdentity,
        display_path: Path,
        quarantine_name: str,
        primary: BaseException,
    ) -> NoReturn:
        """Restore a detached root or expose exact recovery evidence."""
        quarantine_path = display_path.with_name(quarantine_name)
        try:
            public = observe_retirement_name(parent_fd=parent_fd, name=leaf)
            quarantined = observe_retirement_name(
                parent_fd=parent_fd,
                name=quarantine_name,
            )
        except BaseException as exc:  # noqa: BLE001 - classify terminal observation
            ProtectedRootRetirementService._raise_observation_recovery(
                display_path=display_path,
                quarantine_path=quarantine_path,
                primary=primary,
                additional_failures=(exc,),
                reason="protected-root detachment postcondition could not be observed",
            )
        if public == expected and quarantined is None:
            raise primary
        recovery_quarantine = quarantined
        settled_failures: list[BaseException] = [primary]
        if public is None and quarantined == expected:
            restore_error: BaseException | None = None
            try:
                rename_noreplace_at(
                    quarantine_name,
                    leaf,
                    source_dir_fd=parent_fd,
                    destination_dir_fd=parent_fd,
                )
            except BaseException as exc:  # noqa: BLE001 - exact postcondition decides
                restore_error = exc
                settled_failures.append(exc)
            try:
                restored_public = observe_retirement_name(
                    parent_fd=parent_fd,
                    name=leaf,
                )
                restored_quarantine = observe_retirement_name(
                    parent_fd=parent_fd,
                    name=quarantine_name,
                )
            except BaseException as exc:  # noqa: BLE001 - classify terminal observation
                ProtectedRootRetirementService._raise_observation_recovery(
                    display_path=display_path,
                    quarantine_path=quarantine_path,
                    primary=primary,
                    additional_failures=(
                        *(failure for failure in (restore_error,) if failure is not None),
                        exc,
                    ),
                    reason="protected-root restoration postcondition could not be observed",
                )
            recovery_quarantine = restored_quarantine
            if restored_public == expected and restored_quarantine is None:
                terminal = next(
                    (
                        nested
                        for failure in settled_failures
                        if (nested := find_terminal_interruption(failure)) is not None
                    ),
                    None,
                )
                surfaced = terminal or primary
                surfaced.add_note(f"LychD del recovery: protected root {display_path} was restored after interruption.")
                raise surfaced

        recovery = ProtectedRootRecovery(
            root=display_path,
            root_quarantine=(quarantine_path if recovery_quarantine is not None else None),
            root_retired=False,
            authorities=(),
            reason=("protected-root detachment interruption could not be restored exactly"),
        )
        message = f"Protected-root detachment retained or lost indeterminate recovery state: {display_path}"
        raise ProtectedRootRetirementError(
            message,
            root_recovery=recovery,
            failures=tuple(settled_failures),
        ) from (
            next(
                (
                    terminal
                    for failure in settled_failures
                    if (terminal := find_terminal_interruption(failure)) is not None
                ),
                primary,
            )
        )

    @staticmethod
    def _raise_observation_recovery(
        *,
        display_path: Path,
        quarantine_path: Path,
        primary: BaseException,
        additional_failures: tuple[BaseException, ...] = (),
        reason: str,
    ) -> NoReturn:
        """Name the detached candidate when its namespace state is unknowable."""
        recovery = ProtectedRootRecovery(
            root=display_path,
            root_quarantine=quarantine_path,
            root_retired=False,
            authorities=(),
            reason=reason,
        )
        failures = (primary, *additional_failures)
        terminal = next(
            (nested for failure in failures if (nested := find_terminal_interruption(failure)) is not None),
            None,
        )
        message = f"Protected-root retirement retained indeterminate recovery evidence for {display_path}"
        raise ProtectedRootRetirementError(
            message,
            root_recovery=recovery,
            failures=failures,
        ) from (terminal or primary)


__all__ = (
    "ProtectedRetirementEntry",
    "ProtectedRootRecovery",
    "ProtectedRootRetirementError",
    "ProtectedRootRetirementService",
    "RetainedAuthority",
    "is_protected_authority_name",
)
