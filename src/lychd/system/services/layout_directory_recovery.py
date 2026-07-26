"""Exact rollback and recovery for directory publication transactions."""

from __future__ import annotations

import errno
import os
from pathlib import Path
from typing import NoReturn
from uuid import uuid4

from lychd.system import atomic_paths
from lychd.system.descriptor_settlement import DescriptorSet
from lychd.system.services import layout_directory_traversal as traversal
from lychd.system.services.layout_directory_models import (
    CreatedDirectoryEntry,
    QuarantinedName,
)
from lychd.system.services.layout_directory_settlement import (
    DirectoryRollbackError,
    directory_failure_ledger,
)
from lychd.system.services.lifecycle.models import CreatedDirectory

_AUXILIARY_NAME_ATTEMPTS = 8


def rollback_unattested_staging(
    *,
    parent_fd: int,
    staging_name: str,
    path: Path,
    primary: BaseException,
) -> NoReturn:
    """Quarantine, but never delete, a candidate without creation identity."""
    quarantine = quarantine_name(
        parent_fd=parent_fd,
        source_name=staging_name,
    )
    failures = [primary]
    if quarantine.interruption is not None:
        failures.append(quarantine.interruption)
    message = (
        f"Unattested staged layout directory is retained at {quarantine.name}; manual recovery is required: {path}"
    )
    raise DirectoryRollbackError(
        message,
        failures=tuple(failures),
        outcome="recovery",
    ) from primary


def rollback_attested_staging(
    *,
    parent_fd: int,
    staging_name: str,
    path: Path,
    metadata: os.stat_result,
    primary: BaseException,
) -> NoReturn:
    """Remove an attested candidate when rollback-fd retention itself fails."""
    creation = CreatedDirectoryEntry(
        resource=CreatedDirectory(
            path=path,
            device=metadata.st_dev,
            inode=metadata.st_ino,
        ),
        parent_fd=parent_fd,
        name=staging_name,
        published=False,
    )
    try:
        interruptions = quarantine_and_remove_exact_directory(creation)
    except DirectoryRollbackError as exc:
        raise exc from primary
    cleanup = directory_failure_ledger()
    cleanup.record_all(interruptions)
    cleanup.raise_primary_after_verified_settlement(
        translated_or_terminal(
            primary,
            message=f"Could not retain rollback authority for layout directory: {path}",
        ),
        outcome="rolled_back",
        terminal_note=(f"LychD init removed the attested private staging for {path} exactly."),
    )


def raise_after_rollback(
    created: list[CreatedDirectoryEntry],
    *,
    primary: BaseException,
    descriptors: DescriptorSet | None = None,
) -> NoReturn:
    """Settle rollback before descriptors, then preserve exact outcome truth."""
    rollback_error: BaseException | None = None
    try:
        rollback_created_directories(created)
    except BaseException as exc:  # noqa: BLE001 - descriptor peers must still settle
        rollback_error = exc
    cleanup_failures = descriptors.settle() if descriptors is not None else ()
    if isinstance(primary, DirectoryRollbackError):
        failures = [*primary.failures]
        if rollback_error is not None:
            failures.append(rollback_error)
        failures.extend(cleanup_failures)
        combined = DirectoryRollbackError(
            str(primary),
            failures=tuple(failures),
            outcome=primary.outcome or "recovery",
        )
        raise combined from primary
    if isinstance(rollback_error, DirectoryRollbackError):
        combined = DirectoryRollbackError(
            str(rollback_error),
            failures=(primary, *rollback_error.failures, *cleanup_failures),
            outcome=rollback_error.outcome or "recovery",
        )
        raise combined from primary
    ledger = directory_failure_ledger()
    if rollback_error is not None:
        ledger.record(rollback_error)
    ledger.record_all(cleanup_failures)
    ledger.raise_primary_after_verified_settlement(
        primary,
        outcome="rolled_back",
        terminal_note=(
            "LychD init rolled back every proven directory effect and attempted "
            "every descriptor close before preserving this interruption."
        ),
    )


def rollback_created_directories(
    created: list[CreatedDirectoryEntry],
) -> None:
    """Quarantine exact creations and remove only private candidates."""
    effect_failures: list[BaseException] = []
    verified_interruptions: list[BaseException] = []
    close_failures: list[BaseException] = []
    for entry in reversed(created):
        try:
            verified_interruptions.extend(quarantine_and_remove_exact_directory(entry))
        except BaseException as exc:  # noqa: BLE001 - settle peers before surfacing cancellation
            effect_failures.append(exc)
        finally:
            try:
                os.close(entry.parent_fd)
            except BaseException as exc:  # noqa: BLE001 - close every peer before surfacing
                close_failures.append(exc)
    all_failures = (
        *effect_failures,
        *verified_interruptions,
        *close_failures,
    )
    if effect_failures:
        detail = "; ".join(str(failure) for failure in effect_failures)
        message = f"Exact directory rollback did not complete: {detail}"
        error = DirectoryRollbackError(
            message,
            failures=all_failures,
            outcome="recovery",
        )
        raise error from effect_failures[0]
    ledger = directory_failure_ledger()
    ledger.record_all((*verified_interruptions, *close_failures))
    ledger.raise_if_any(
        message="Exact directory rollback completed with descriptor failures.",
        outcome="rolled_back",
        terminal_note=(
            "LychD init rolled back every exact directory effect and attempted "
            "every rollback-descriptor close before preserving this interruption."
        ),
        verified=True,
    )


def quarantine_and_remove_exact_directory(
    entry: CreatedDirectoryEntry,
) -> tuple[BaseException, ...]:
    """Quarantine one name, restore replacements, and retain published winners."""
    quarantine = quarantine_name(
        parent_fd=entry.parent_fd,
        source_name=entry.name,
        expected=entry.resource,
    )
    quarantine_name_value = quarantine.name
    metadata = attest_quarantined_directory(
        entry,
        quarantine_name=quarantine_name_value,
    )
    if not traversal.matches_created_directory(metadata, expected=entry.resource):
        restore_foreign_directory(
            entry,
            quarantine_name=quarantine_name_value,
            metadata=metadata,
        )
    if entry.published:
        message = (
            f"Exact created directory {entry.resource.path} is retained at "
            f"{quarantine_name_value}; Linux cannot bind rmdir to the attested inode"
        )
        failures = (quarantine.interruption,) if quarantine.interruption is not None else ()
        raise DirectoryRollbackError(
            message,
            failures=failures,
            outcome="recovery",
        ) from quarantine.interruption
    return remove_private_quarantine(
        entry,
        quarantine=quarantine,
    )


def attest_quarantined_directory(
    entry: CreatedDirectoryEntry,
    *,
    quarantine_name: str,
) -> os.stat_result:
    """Read one rollback quarantine or surface its exact recovery name."""
    try:
        return os.stat(
            quarantine_name,
            dir_fd=entry.parent_fd,
            follow_symlinks=False,
        )
    except BaseException as exc:
        message = f"Could not attest quarantined layout directory {entry.resource.path} as {quarantine_name}"
        raise DirectoryRollbackError(
            message,
            failures=(exc,),
            outcome="recovery",
        ) from exc


def restore_foreign_directory(
    entry: CreatedDirectoryEntry,
    *,
    quarantine_name: str,
    metadata: os.stat_result,
) -> NoReturn:
    """Restore a replacement identity without clobbering its public name."""
    try:
        atomic_paths.rename_noreplace_at(
            quarantine_name,
            entry.name,
            source_dir_fd=entry.parent_fd,
            destination_dir_fd=entry.parent_fd,
        )
    except BaseException as exc:
        try:
            restored = traversal.observe_directory(
                parent_fd=entry.parent_fd,
                name=entry.name,
            )
            retained = traversal.observe_directory(
                parent_fd=entry.parent_fd,
                name=quarantine_name,
            )
        except BaseException as observation_error:
            message = (
                f"Foreign replacement for {entry.resource.path} has indeterminate "
                f"recovery names {entry.name} and {quarantine_name}"
            )
            raise DirectoryRollbackError(
                message,
                failures=(exc, observation_error),
                outcome="recovery",
            ) from observation_error
        if restored is not None and traversal.same_directory_identity(restored, metadata) and retained is None:
            message = f"Refusing to remove replacement identity at {entry.resource.path}; it was restored unchanged"
            raise DirectoryRollbackError(
                message,
                failures=(exc,),
                outcome="recovery",
            ) from exc
        message = (
            f"Foreign replacement for {entry.resource.path} is preserved at "
            f"{quarantine_name}; its public name could not be restored"
        )
        raise DirectoryRollbackError(
            message,
            failures=(exc,),
            outcome="recovery",
        ) from exc
    message = f"Refusing to remove replacement identity at {entry.resource.path}; it was restored unchanged"
    raise DirectoryRollbackError(message, outcome="recovery")


def remove_private_quarantine(
    entry: CreatedDirectoryEntry,
    *,
    quarantine: QuarantinedName,
) -> tuple[BaseException, ...]:
    """Remove a never-published candidate and settle any terminal signal."""
    interruptions: list[BaseException] = []
    try:
        os.rmdir(quarantine.name, dir_fd=entry.parent_fd)
    except OSError as exc:
        message = f"Exact created directory {entry.resource.path} is retained at {quarantine.name}; removal failed"
        raise DirectoryRollbackError(
            message,
            failures=(exc,),
            outcome="recovery",
        ) from exc
    except BaseException as exc:
        try:
            retained = traversal.observe_directory(
                parent_fd=entry.parent_fd,
                name=quarantine.name,
            )
        except BaseException as observation_error:
            message = f"Exact created directory {entry.resource.path} has indeterminate recovery at {quarantine.name}"
            raise DirectoryRollbackError(
                message,
                failures=(exc, observation_error),
                outcome="recovery",
            ) from observation_error
        if retained is not None:
            message = (
                f"Exact created directory {entry.resource.path} is retained at "
                f"{quarantine.name}; removal was interrupted"
            )
            raise DirectoryRollbackError(
                message,
                failures=(exc,),
                outcome="recovery",
            ) from exc
        interruptions.append(exc)
    if quarantine.interruption is not None:
        interruptions.insert(0, quarantine.interruption)
    return tuple(interruptions)


def quarantine_name(
    *,
    parent_fd: int,
    source_name: str,
    expected: CreatedDirectory | None = None,
) -> QuarantinedName:
    """Atomically move one source name to a collision-resistant quarantine."""
    for _ in range(_AUXILIARY_NAME_ATTEMPTS):
        quarantine_name_value = auxiliary_name("rollback")
        try:
            atomic_paths.rename_noreplace_at(
                source_name,
                quarantine_name_value,
                source_dir_fd=parent_fd,
                destination_dir_fd=parent_fd,
            )
        except BaseException as exc:
            if isinstance(exc, OSError) and exc.errno == errno.EEXIST:
                continue
            try:
                source = traversal.observe_directory(
                    parent_fd=parent_fd,
                    name=source_name,
                )
                quarantine = traversal.observe_directory(
                    parent_fd=parent_fd,
                    name=quarantine_name_value,
                )
            except BaseException as observation_error:
                message = (
                    f"Layout rollback interruption left indeterminate names: {source_name}, {quarantine_name_value}"
                )
                raise DirectoryRollbackError(
                    message,
                    failures=(exc, observation_error),
                    outcome="recovery",
                ) from observation_error
            expected_in_quarantine = (
                quarantine is not None
                if expected is None
                else traversal.matches_created_directory(
                    quarantine,
                    expected=expected,
                )
            )
            if source is None and expected_in_quarantine:
                return QuarantinedName(
                    name=quarantine_name_value,
                    interruption=exc,
                )
            recovery_name = source_name if source is not None else quarantine_name_value
            message = f"Layout rollback interruption retained recovery at {recovery_name}"
            raise DirectoryRollbackError(
                message,
                failures=(exc,),
                outcome="recovery",
            ) from exc
        return QuarantinedName(name=quarantine_name_value)
    message = f"Could not allocate a rollback quarantine for {source_name}."
    raise DirectoryRollbackError(message, outcome="recovery")


def translated_or_terminal(
    error: BaseException,
    *,
    message: str,
) -> BaseException:
    """Translate ordinary adapter failures without flattening native signals."""
    if not isinstance(error, Exception):
        return error
    translated = RuntimeError(message)
    translated.__cause__ = error
    return translated


def close_parent_descriptors(
    created: list[CreatedDirectoryEntry],
) -> tuple[BaseException, ...]:
    """Close every held parent descriptor without hiding peer failures."""
    failures: list[BaseException] = []
    for entry in created:
        try:
            os.close(entry.parent_fd)
        except BaseException as exc:  # noqa: BLE001 - committed peers still settle
            failures.append(exc)
    return tuple(failures)


def auxiliary_name(purpose: str) -> str:
    """Return one unguessable, same-directory transaction name."""
    return f".lychd-{purpose}-{uuid4().hex}"


__all__ = (
    "close_parent_descriptors",
    "raise_after_rollback",
    "rollback_attested_staging",
    "rollback_created_directories",
    "rollback_unattested_staging",
)
