"""Private-file preparation inside one descriptor-pinned workspace."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Never

from lychd.system.descriptor_settlement import (
    DescriptorSet,
    find_settlement_outcome,
)
from lychd.system.services.scribe.storage import (
    AttestedPath,
    PinnedPath,
    capture_pinned_path_state,
)
from lychd.system.services.scribe.workspace_settlement import (
    workspace_failure_ledger,
)


class WorkspaceStagingMixin:
    """Stage and attest exact private files for the stable workspace facade."""

    path: Path
    directory_fd: int
    owned_entries: dict[str, tuple[int, int]]
    recovery_names: set[str]

    if TYPE_CHECKING:

        def workspace_entry(self, name: str) -> PinnedPath:
            """Address one transaction filename."""
            raise NotImplementedError

        def _quarantine_and_unlink_entry(
            self,
            name: str,
            *,
            expected: tuple[int, int],
        ) -> bool:
            """Remove one exact staged entry."""
            raise NotImplementedError

    def prepare_file(
        self,
        content: bytes,
        *,
        mode: int,
        prefix: str,
    ) -> AttestedPath:
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
                    raise RuntimeError(  # noqa: TRY301 - cleanup needs the primary
                        message
                    )
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
        recovery = workspace_failure_ledger(recovery_paths=(path,))
        try:
            os.stat(
                name,
                dir_fd=self.directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            settled = workspace_failure_ledger()
            settled.raise_primary_after_verified_settlement(
                primary,
                outcome="unchanged",
                terminal_note=(f"Scribe verified that failed staging creation left {path} absent."),
            )
        except BaseException as observation_error:  # noqa: BLE001 - exact possible name is evidence
            self.recovery_names.add(name)
            recovery.record(primary, observation_error)
            recovery.raise_if_any(
                message=(f"Could not classify failed Scribe staging creation at {path}."),
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
        cleanup = workspace_failure_ledger(
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


__all__ = ("WorkspaceStagingMixin",)
