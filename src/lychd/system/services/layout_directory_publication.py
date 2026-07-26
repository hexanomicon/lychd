"""Atomic staging and publication of one managed directory component."""

from __future__ import annotations

import os
from pathlib import Path

from lychd.system import atomic_paths
from lychd.system.descriptor_settlement import DescriptorSet
from lychd.system.services import layout_directory_recovery as recovery
from lychd.system.services import layout_directory_traversal as traversal
from lychd.system.services.layout_directory_models import (
    CreatedDirectoryEntry,
    OpenedDirectory,
)
from lychd.system.services.layout_directory_settlement import (
    DirectoryRollbackError,
    directory_failure_ledger,
)
from lychd.system.services.lifecycle.models import CreatedDirectory

_AUXILIARY_NAME_ATTEMPTS = 8


def open_directory_component(
    *,
    parent_fd: int,
    component: str,
    path: Path,
    mode: int | None,
) -> OpenedDirectory:
    """Open one real directory or atomically install one attested candidate."""
    try:
        descriptor = os.open(
            component,
            traversal.DIRECTORY_OPEN_FLAGS,
            dir_fd=parent_fd,
        )
    except FileNotFoundError:
        installed = stage_and_install_directory(
            parent_fd=parent_fd,
            component=component,
            path=path,
            mode=mode,
        )
        if installed is not None:
            return installed
        descriptor = traversal.open_existing_directory_component(
            parent_fd=parent_fd,
            component=component,
            path=path,
        )
        return traversal.opened_existing_directory(
            descriptor,
            path=path,
            raced=True,
        )
    except OSError as exc:
        message = f"Could not traverse managed layout directory {path}: {exc}"
        raise RuntimeError(message) from exc
    return traversal.opened_existing_directory(
        descriptor,
        path=path,
        raced=False,
    )


def stage_and_install_directory(
    *,
    parent_fd: int,
    component: str,
    path: Path,
    mode: int | None,
) -> OpenedDirectory | None:
    """Attest a private candidate, then install it without replacing a racer."""
    staging_name = mkdir_private_staging(
        parent_fd=parent_fd,
        mode=mode or 0o777,
        path=path,
    )
    descriptors = DescriptorSet()
    staging_fd = -1
    rollback_parent_fd = -1
    creation: CreatedDirectoryEntry | None = None
    try:
        try:
            staging_fd = descriptors.add(
                os.open(
                    staging_name,
                    traversal.DIRECTORY_OPEN_FLAGS,
                    dir_fd=parent_fd,
                )
            )
            if mode is not None:
                os.fchmod(staging_fd, mode)
            metadata = os.fstat(staging_fd)
        except BaseException as exc:  # noqa: BLE001 - candidate may already exist
            recovery.rollback_unattested_staging(
                parent_fd=parent_fd,
                staging_name=staging_name,
                path=path,
                primary=exc,
            )
        try:
            rollback_parent_fd = descriptors.add(os.dup(parent_fd))
        except BaseException as exc:  # noqa: BLE001 - candidate must settle first
            recovery.rollback_attested_staging(
                parent_fd=parent_fd,
                staging_name=staging_name,
                path=path,
                metadata=metadata,
                primary=exc,
            )
        creation = CreatedDirectoryEntry(
            resource=CreatedDirectory(
                path=path,
                device=metadata.st_dev,
                inode=metadata.st_ino,
            ),
            parent_fd=descriptors.transfer(rollback_parent_fd),
            name=staging_name,
            published=False,
        )
        traversal.require_staged_directory(metadata, path=path)
        try:
            atomic_paths.rename_noreplace_at(
                staging_name,
                component,
                source_dir_fd=parent_fd,
                destination_dir_fd=parent_fd,
            )
        except BaseException as exc:
            published = publication_completed(
                parent_fd=parent_fd,
                staging_name=staging_name,
                component=component,
                expected=creation.resource,
                path=path,
                primary=exc,
            )
            if published:
                creation = CreatedDirectoryEntry(
                    resource=creation.resource,
                    parent_fd=creation.parent_fd,
                    name=component,
                    published=True,
                )
            elif isinstance(exc, FileExistsError):
                losing_creation = creation
                creation = None
                rollback_parent_fd = -1
                settle_race_loser(
                    losing_creation,
                    descriptors=descriptors,
                    path=path,
                )
                return None
            raise
        creation = CreatedDirectoryEntry(
            resource=creation.resource,
            parent_fd=creation.parent_fd,
            name=component,
            published=True,
        )
        rollback_parent_fd = -1
        return OpenedDirectory(
            descriptor=descriptors.transfer(staging_fd),
            metadata=metadata,
            creation=creation,
            raced=False,
        )
    except BaseException as exc:
        if creation is not None and rollback_parent_fd >= 0:
            recovery.raise_after_rollback(
                [creation],
                primary=exc,
                descriptors=descriptors,
            )
        close_failures = descriptors.settle()
        if isinstance(exc, DirectoryRollbackError):
            combined = DirectoryRollbackError(
                str(exc),
                failures=(*exc.failures, *close_failures),
                outcome=exc.outcome or "recovery",
            )
            raise combined from exc
        cleanup = directory_failure_ledger()
        cleanup.record_all(close_failures)
        cleanup.raise_primary_after_verified_settlement(
            exc,
            outcome="rolled_back",
            terminal_note=(f"LychD init settled the private staging for {path} before preserving this interruption."),
        )


def settle_race_loser(
    creation: CreatedDirectoryEntry,
    *,
    descriptors: DescriptorSet,
    path: Path,
) -> None:
    """Roll back one private publication loser before closing its descriptors."""
    settlement_error: BaseException | None = None
    try:
        recovery.rollback_created_directories([creation])
    except BaseException as exc:  # noqa: BLE001 - descriptor peers still settle
        settlement_error = exc
    close_failures = descriptors.settle()
    if isinstance(settlement_error, DirectoryRollbackError):
        combined = DirectoryRollbackError(
            str(settlement_error),
            failures=(*settlement_error.failures, *close_failures),
            outcome=settlement_error.outcome,
        )
        raise combined from settlement_error
    cleanup = directory_failure_ledger()
    if settlement_error is not None:
        cleanup.record(settlement_error)
    cleanup.record_all(close_failures)
    cleanup.raise_if_any(
        message="Race-loser directory rollback did not settle cleanly.",
        outcome="rolled_back",
        terminal_note=(f"LychD init removed the private race-loser candidate for {path} and settled every descriptor."),
        verified=True,
    )


def mkdir_private_staging(
    *,
    parent_fd: int,
    mode: int,
    path: Path,
) -> str:
    """Create one collision-resistant private candidate name."""
    for _ in range(_AUXILIARY_NAME_ATTEMPTS):
        name = recovery.auxiliary_name("mkdir")
        try:
            os.mkdir(name, mode, dir_fd=parent_fd)
        except FileExistsError:
            continue
        except BaseException as exc:
            try:
                candidate = traversal.observe_directory(
                    parent_fd=parent_fd,
                    name=name,
                )
            except BaseException as observation_error:
                message = f"Staged layout directory creation became indeterminate at {name}: {path}"
                raise DirectoryRollbackError(
                    message,
                    failures=(exc, observation_error),
                    outcome="recovery",
                ) from observation_error
            if candidate is not None:
                recovery.rollback_unattested_staging(
                    parent_fd=parent_fd,
                    staging_name=name,
                    path=path,
                    primary=exc,
                )
            if not isinstance(exc, Exception):
                exc.add_note(f"LychD init verified that interrupted mkdir left no candidate for {path}.")
                raise
            message = f"Could not create staged layout directory {name}: {exc}"
            raise RuntimeError(message) from exc
        return name
    message = "Could not allocate a private layout staging name."
    raise RuntimeError(message)


def publication_completed(
    *,
    parent_fd: int,
    staging_name: str,
    component: str,
    expected: CreatedDirectory,
    path: Path,
    primary: BaseException,
) -> bool:
    """Classify a publication interruption by both descriptor-relative names."""
    try:
        staging = traversal.observe_directory(
            parent_fd=parent_fd,
            name=staging_name,
        )
        public = traversal.observe_directory(
            parent_fd=parent_fd,
            name=component,
        )
    except BaseException as exc:
        message = f"Directory publication became indeterminate during interruption: {path}"
        raise DirectoryRollbackError(
            message,
            failures=(primary, exc),
            outcome="recovery",
        ) from exc
    if staging is None and traversal.matches_created_directory(
        public,
        expected=expected,
    ):
        return True
    if traversal.matches_created_directory(
        staging,
        expected=expected,
    ) and not traversal.matches_created_directory(
        public,
        expected=expected,
    ):
        return False
    message = (
        f"Directory publication interruption left indeterminate names for {path}: "
        f"staging={staging_name}, public={component}"
    )
    raise DirectoryRollbackError(
        message,
        failures=(primary,),
        outcome="recovery",
    ) from primary


__all__ = ("open_directory_component",)
