"""Rollback and named-recovery mechanics for initialization file publication."""

from __future__ import annotations

import os
import stat
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import NoReturn
from uuid import uuid4

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.descriptor_settlement import DescriptorSet, FailureLedger, find_settlement_outcome
from lychd.system.interruptions import (
    find_terminal_interruption,
    iter_exception_graph,
)
from lychd.system.services import file_publication_settlement as settlement
from lychd.system.services.file_publication_models import (
    FilePublication,
    PublicationRollbackError,
)


def retain_publication_primary(
    rollback: BaseException,
    *,
    primary: BaseException,
) -> None:
    """Keep the initiating failure reachable after rollback adds a stronger peer."""
    if rollback is primary:
        return
    evidence = next(
        (candidate for candidate in iter_exception_graph(rollback) if isinstance(candidate, PublicationRollbackError)),
        None,
    )
    if evidence is not None and all(failure is not primary for failure in evidence.failures):
        evidence.failures = (primary, *evidence.failures)
    if rollback.__cause__ is None:
        rollback.__cause__ = primary


def rollback_file(publication: FilePublication) -> None:
    """Remove only the exact candidate/public winner and preserve replacements."""
    cleanup = settlement.publication_failure_ledger()
    if publication.published:
        try:
            quarantine_public_file(publication)
        except BaseException as exc:  # noqa: BLE001 - settle the private peer before reporting
            cleanup.record(exc)
    if publication.staging_present:
        try:
            remove_staging(publication)
        except BaseException as exc:  # noqa: BLE001 - retain all recovery evidence
            cleanup.record(exc)
    durable = True
    try:
        settlement.fsync_directory(publication.parent_fd, path=publication.identity.path.parent)
    except BaseException as exc:  # noqa: BLE001 - durability failure is part of rollback truth
        cleanup.record(exc)
        durable = False
    if not cleanup.failures and not publication.recovery_names:
        return

    namespace_settled, recovery_paths = observe_rollback_recovery(
        publication,
        cleanup=cleanup,
    )
    if not namespace_settled and not cleanup.failures:
        cleanup.record(
            PublicationRollbackError(
                f"File rollback retained named recovery for {publication.identity.path}.",
                outcome="recovery",
                verified=False,
                recovery_paths=recovery_paths,
            )
        )
    verified = namespace_settled and durable
    outcome = "rolled_back" if verified else "recovery"
    detail = "; ".join(str(failure) for failure in cleanup.failures)
    settled = settlement.publication_failure_ledger(
        recovery_paths=recovery_paths,
    )
    settled.record_all(tuple(cleanup.failures))
    settled.raise_if_any(
        message=f"Exact file rollback settled with failures for {publication.identity.path}: {detail}",
        outcome=outcome,
        terminal_note=(
            f"LychD init verified exact file rollback for {publication.identity.path} "
            "after attempting every rollback peer."
        ),
        verified=verified,
    )


def observe_rollback_recovery(
    publication: FilePublication,
    *,
    cleanup: FailureLedger,
) -> tuple[bool, tuple[Path, ...]]:
    """Prove every public, staging, and random rollback name is settled."""
    recovery_paths = sorted(publication.indeterminate_paths)
    try:
        public = settlement.observe_name(
            parent_fd=publication.parent_fd,
            name=publication.public_name,
        )
        staging = settlement.observe_name(
            parent_fd=publication.parent_fd,
            name=publication.staging_name,
        )
        if settlement.matches(public, expected=publication.identity):
            recovery_paths.append(publication.identity.path)
        if settlement.matches(staging, expected=publication.identity):
            recovery_paths.append(publication.identity.path.parent / publication.staging_name)
        for recovery_name in tuple(sorted(publication.recovery_names)):
            recovery = settlement.observe_name(
                parent_fd=publication.parent_fd,
                name=recovery_name,
            )
            if recovery is None:
                publication.recovery_names.discard(recovery_name)
                continue
            recovery_paths.append(publication.identity.path.parent / recovery_name)
        namespace_settled = not recovery_paths
    except BaseException as exc:  # noqa: BLE001 - postcondition evidence is a peer
        cleanup.record(exc)
        recovery_paths.extend(
            (
                publication.identity.path,
                publication.identity.path.parent / publication.staging_name,
                *(publication.identity.path.parent / name for name in sorted(publication.recovery_names)),
            )
        )
        namespace_settled = False
    return namespace_settled, tuple(dict.fromkeys(recovery_paths))


def quarantine_public_file(publication: FilePublication) -> None:
    """Detach and compare the current public name before any unlink."""
    public = settlement.observe_name(
        parent_fd=publication.parent_fd,
        name=publication.public_name,
    )
    if public is None or not settlement.matches(public, expected=publication.identity):
        return
    quarantine_name = f".lychd-rollback-{uuid4().hex}"
    publication.recovery_names.add(quarantine_name)
    try:
        rename_noreplace_at(
            publication.public_name,
            quarantine_name,
            source_dir_fd=publication.parent_fd,
            destination_dir_fd=publication.parent_fd,
        )
    except BaseException as exc:  # noqa: BLE001 - classify both names after ambiguous return
        settle_quarantine_after_error(
            publication,
            quarantine_name=quarantine_name,
            primary=exc,
        )
    remove_or_restore_quarantine(
        publication,
        quarantine_name=quarantine_name,
    )


def settle_quarantine_after_error(
    publication: FilePublication,
    *,
    quarantine_name: str,
    primary: BaseException,
) -> NoReturn:
    """Classify a quarantine rename that may have completed before interruption."""
    try:
        public = settlement.observe_name(
            parent_fd=publication.parent_fd,
            name=publication.public_name,
        )
        quarantine = settlement.observe_name(
            parent_fd=publication.parent_fd,
            name=quarantine_name,
        )
    except BaseException as observation_error:  # noqa: BLE001 - keep exact random recovery name
        raise_publication_recovery(
            publication,
            quarantine_name=quarantine_name,
            message=(f"Could not classify file rollback quarantine mutation for {publication.identity.path}."),
            failures=(primary, observation_error),
        )
    public_matches = settlement.matches(public, expected=publication.identity)
    quarantine_matches = settlement.matches(quarantine, expected=publication.identity)
    if public is None and quarantine_matches:
        remove_or_restore_quarantine(
            publication,
            quarantine_name=quarantine_name,
        )
        raise primary
    if public is None and quarantine is None:
        publication.recovery_names.discard(quarantine_name)
        raise primary
    if public_matches and quarantine is None:
        publication.recovery_names.discard(quarantine_name)
        raise_publication_recovery(
            publication,
            quarantine_name=None,
            message=(f"File rollback quarantine did not detach the public candidate for {publication.identity.path}."),
            failures=(primary,),
            additional_paths=(publication.identity.path,),
        )
    if isinstance(primary, FileExistsError) and public_matches:
        publication.recovery_names.discard(quarantine_name)
        raise_publication_recovery(
            publication,
            quarantine_name=None,
            message=(f"File rollback quarantine collided before detaching {publication.identity.path}."),
            failures=(primary,),
            additional_paths=(publication.identity.path,),
        )
    raise_publication_recovery(
        publication,
        quarantine_name=quarantine_name,
        message=f"File rollback quarantine became indeterminate for {publication.identity.path}.",
        failures=(primary,),
        additional_paths=((publication.identity.path,) if public_matches else ()),
    )


def remove_or_restore_quarantine(
    publication: FilePublication,
    *,
    quarantine_name: str,
) -> None:
    """Delete an exact quarantine or restore a foreign entry without clobbering."""
    try:
        quarantine = settlement.observe_name(
            parent_fd=publication.parent_fd,
            name=quarantine_name,
        )
    except BaseException as observation_error:  # noqa: BLE001 - retain exact private recovery
        raise_publication_recovery(
            publication,
            quarantine_name=quarantine_name,
            message=(f"Could not inspect rollback quarantine {quarantine_name} for {publication.identity.path}."),
            failures=(observation_error,),
        )
    if quarantine is None:
        publication.recovery_names.discard(quarantine_name)
        return
    if settlement.matches(quarantine, expected=publication.identity):
        try:
            settlement.remove_private_name(
                parent_fd=publication.parent_fd,
                name=quarantine_name,
                expected=publication.identity,
                path=publication.identity.path,
            )
        except BaseException as removal_error:
            try:
                after = settlement.observe_name(
                    parent_fd=publication.parent_fd,
                    name=quarantine_name,
                )
            except BaseException as observation_error:  # noqa: BLE001 - retain exact recovery
                raise_publication_recovery(
                    publication,
                    quarantine_name=quarantine_name,
                    message=(f"Could not classify rollback quarantine cleanup for {publication.identity.path}."),
                    failures=(removal_error, observation_error),
                )
            if after is None:
                publication.recovery_names.discard(quarantine_name)
                raise
            raise_publication_recovery(
                publication,
                quarantine_name=quarantine_name,
                message=(f"Rollback quarantine cleanup retained {quarantine_name} for {publication.identity.path}."),
                failures=(removal_error,),
            )
        publication.recovery_names.discard(quarantine_name)
        return
    with pin_foreign_quarantine(publication, quarantine_name=quarantine_name, expected=quarantine) as pinned:
        try:
            rename_noreplace_at(
                quarantine_name,
                publication.public_name,
                source_dir_fd=publication.parent_fd,
                destination_dir_fd=publication.parent_fd,
            )
        except BaseException as restore_error:  # noqa: BLE001 - classify both names after ambiguous return
            settle_foreign_restore_error(
                publication,
                quarantine_name=quarantine_name,
                quarantine=pinned,
                primary=restore_error,
            )
        attest_foreign_restore(publication, quarantine_name=quarantine_name, pinned=pinned)
    publication.recovery_names.discard(quarantine_name)


def attest_foreign_restore(
    publication: FilePublication,
    *,
    quarantine_name: str,
    pinned: os.stat_result,
) -> None:
    """Prove a normal restore return moved the pinned foreign inode."""
    paths = (publication.identity.path, publication.identity.path.parent / quarantine_name)
    try:
        source = settlement.observe_name(parent_fd=publication.parent_fd, name=quarantine_name)
        target = settlement.observe_name(parent_fd=publication.parent_fd, name=publication.public_name)
    except BaseException as observation_error:  # noqa: BLE001 - preserve both names without proof
        publication.indeterminate_paths.update(paths)
        raise_publication_recovery(
            publication,
            quarantine_name=quarantine_name,
            message="Could not attest the returned foreign rollback restoration.",
            failures=(observation_error,),
            additional_paths=(publication.identity.path,),
        )
    target_identity = None if target is None else (target.st_dev, target.st_ino, stat.S_IFMT(target.st_mode))
    pinned_identity = (pinned.st_dev, pinned.st_ino, stat.S_IFMT(pinned.st_mode))
    if source is not None or target_identity != pinned_identity:
        publication.indeterminate_paths.update(paths)
        message = "Returned foreign rollback restoration did not move the pinned inode."
        raise PublicationRollbackError(message, outcome="recovery", verified=False, recovery_paths=paths)


@contextmanager
def pin_foreign_quarantine(
    publication: FilePublication,
    *,
    quarantine_name: str,
    expected: os.stat_result,
) -> Generator[os.stat_result]:
    """Keep the foreign inode alive until restore classification and close settle."""
    descriptors = DescriptorSet()
    primary: BaseException | None = None
    try:
        descriptor = descriptors.add(
            os.open(
                quarantine_name,
                os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=publication.parent_fd,
            )
        )
        pinned = os.fstat(descriptor)
        if (pinned.st_dev, pinned.st_ino, stat.S_IFMT(pinned.st_mode)) != (
            expected.st_dev,
            expected.st_ino,
            stat.S_IFMT(expected.st_mode),
        ):
            message = "Foreign rollback source changed before its inode could be pinned."
            raise PublicationRollbackError(  # noqa: TRY301 - settle the pin before reporting identity drift
                message,
                outcome="recovery",
                verified=False,
                recovery_paths=(publication.identity.path.parent / quarantine_name,),
            )
        yield pinned
    except BaseException as exc:  # noqa: BLE001 - the pin must settle alongside every restore outcome
        primary = exc
    cleanup = settlement.publication_failure_ledger(
        recovery_paths=(publication.identity.path, publication.identity.path.parent / quarantine_name),
    )
    cleanup.record_all(descriptors.settle())
    if primary is not None:
        if not cleanup.failures:
            raise primary
        outcome = find_settlement_outcome(primary)
        if outcome is not None and outcome.verified:
            cleanup.raise_primary_after_verified_settlement(
                primary,
                outcome=outcome.name,
                terminal_note="LychD settled the foreign rollback inode pin after verified restoration.",
            )
        cleanup.record(primary)
        cleanup.raise_if_any(
            message="Could not settle foreign rollback restoration and its inode pin.",
            outcome="recovery",
            terminal_note="",
            verified=False,
        )
    cleanup.raise_if_any(
        message="Could not release the restored foreign rollback inode pin.",
        outcome="foreign_restored",
        terminal_note="LychD restored the foreign rollback entry before settling its inode pin.",
        verified=True,
    )


def settle_foreign_restore_error(
    publication: FilePublication,
    *,
    quarantine_name: str,
    quarantine: os.stat_result,
    primary: BaseException,
) -> NoReturn:
    """Classify both names against the captured foreign identity after restore."""
    try:
        public = settlement.observe_name(
            parent_fd=publication.parent_fd,
            name=publication.public_name,
        )
        after = settlement.observe_name(
            parent_fd=publication.parent_fd,
            name=quarantine_name,
        )
    except BaseException as observation_error:  # noqa: BLE001 - retain exact private name
        publication.indeterminate_paths.update(
            (
                publication.identity.path,
                publication.identity.path.parent / quarantine_name,
            )
        )
        raise_publication_recovery(
            publication,
            quarantine_name=quarantine_name,
            message=(f"Could not classify foreign rollback recovery for {publication.identity.path}."),
            failures=(primary, observation_error),
        )
    if after is None and settlement.same_regular_identity(public, quarantine):
        publication.recovery_names.discard(quarantine_name)
        raise primary
    if after is None:
        publication.recovery_names.discard(quarantine_name)
        publication.indeterminate_paths.add(publication.identity.path)
        raise_publication_recovery(
            publication,
            quarantine_name=None,
            message=(
                f"Foreign rollback recovery lost its captured identity "
                f"between {quarantine_name} and {publication.identity.path}."
            ),
            failures=(primary,),
            additional_paths=(publication.identity.path,),
        )
    raise_publication_recovery(
        publication,
        quarantine_name=quarantine_name,
        message=(
            f"Foreign replacement retained at private recovery name {quarantine_name} for {publication.identity.path}."
        ),
        failures=(primary,),
        additional_paths=(
            (publication.identity.path,) if settlement.matches(public, expected=publication.identity) else ()
        ),
    )


def raise_publication_recovery(
    publication: FilePublication,
    *,
    quarantine_name: str | None,
    message: str,
    failures: tuple[BaseException, ...],
    additional_paths: tuple[Path, ...] = (),
) -> NoReturn:
    """Surface exact named publication recovery without native flattening."""
    recovery_paths = (
        *additional_paths,
        *((publication.identity.path.parent / quarantine_name,) if quarantine_name is not None else ()),
    )
    terminal = next(
        (nested for failure in failures if (nested := find_terminal_interruption(failure)) is not None),
        None,
    )
    raise PublicationRollbackError(
        message,
        failures=failures,
        outcome="recovery",
        verified=False,
        recovery_paths=tuple(dict.fromkeys(recovery_paths)),
    ) from (terminal or failures[0])


def remove_staging(publication: FilePublication) -> None:
    """Remove the exact private staging link once."""
    if not publication.staging_present:
        return
    settlement.remove_private_name(
        parent_fd=publication.parent_fd,
        name=publication.staging_name,
        expected=publication.identity,
        path=publication.identity.path,
    )
    publication.staging_present = False


__all__ = (
    "remove_staging",
    "retain_publication_primary",
    "rollback_file",
)
