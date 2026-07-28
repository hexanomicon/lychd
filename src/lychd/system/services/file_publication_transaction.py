"""Journal-bound transaction for initialization files and directories."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Final, NoReturn
from uuid import uuid4

from lychd.system.descriptor_settlement import (
    DescriptorSet,
    find_settlement_outcome,
)
from lychd.system.interruptions import find_terminal_interruption
from lychd.system.services import file_publication_recovery as recovery
from lychd.system.services import file_publication_settlement as settlement
from lychd.system.services.file_publication_models import (
    FileIdentity,
    FilePublication,
    PublicationRollbackError,
)
from lychd.system.services.layout_directories import (
    DirectoryProvisioning,
    DirectoryRollbackError,
)
from lychd.system.services.lifecycle.models import (
    CreatedResources,
    created_resources,
)

type CreationJournal = Callable[[CreatedResources], None]
type DirectoryValidator = Callable[[int, Path], None]

_FILE_OPEN_FLAGS: Final = (
    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
)
_READ_FILE_FLAGS: Final = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
_AUXILIARY_NAME_ATTEMPTS: Final = 8


class JournaledCreation:
    """Create exact resources and release rollback authority only after journaling."""

    def __init__(
        self,
        *,
        on_created: CreationJournal | None = None,
    ) -> None:
        """Begin one sequential initialization creation session."""
        self._on_created = on_created
        self._resources = CreatedResources()

    @property
    def resources(self) -> CreatedResources:
        """Return the exact creations whose journal callbacks committed."""
        return self._resources

    def create_directory(
        self,
        path: Path,
        *,
        mode: int | None = None,
        validate: DirectoryValidator | None = None,
    ) -> CreatedResources:
        """Create one directory chain and journal only atomic-install winners."""
        provisioning = DirectoryProvisioning()
        committed = False
        try:
            provisioning.create(path, mode=mode)
            with provisioning.pin(path) as descriptor:
                if validate is not None:
                    validate(descriptor, path)
            resources = created_resources(
                directories=provisioning.created_paths,
                directory_identities=provisioning.created_identities,
            )
            self._journal(resources)
            committed = True
            self._resources = CreatedResources.combine(self._resources, resources)
            provisioning.commit()
        except BaseException as exc:
            if not committed:
                try:
                    provisioning.rollback()
                except DirectoryRollbackError as rollback:
                    raise rollback from exc
            raise
        return resources

    def create_text_file(
        self,
        path: Path,
        content: str,
        *,
        mode: int,
    ) -> CreatedResources:
        """Durably publish one new text file without creating its parent."""
        settlement.require_safe_file_target(path)
        parent_descriptors = DescriptorSet()
        parent_fd = parent_descriptors.add(settlement.open_existing_directory(path.parent))
        publication: FilePublication | None = None
        committed = False
        outcome = "unchanged"
        outcome_verified = True
        result = CreatedResources()
        primary: BaseException | None = None
        try:
            publication = stage_text_file(
                parent_fd=parent_fd,
                path=path,
                content=content,
                mode=mode,
            )
            if publish_file(publication):
                attest_public_file(publication)
                recovery.remove_staging(publication)
                settlement.fsync_directory(parent_fd, path=path.parent)
                result = created_resources(files=(path,))
                self._journal(result)
                committed = True
                outcome = "committed"
                outcome_verified = True
                self._resources = CreatedResources.combine(
                    self._resources,
                    result,
                )
        except BaseException as exc:  # noqa: BLE001 - mutation truth crosses native interruption
            primary = exc
            settlement_outcome = find_settlement_outcome(exc)
            if publication is None and settlement_outcome is not None:
                outcome = settlement_outcome.name
                outcome_verified = settlement_outcome.verified
            if publication is not None and not committed:
                try:
                    recovery.rollback_file(publication)
                except BaseException as rollback:  # noqa: BLE001 - rollback may preserve a native signal
                    recovery.retain_publication_primary(rollback, primary=exc)
                    primary = rollback
                    settlement_outcome = find_settlement_outcome(rollback)
                    outcome = settlement_outcome.name if settlement_outcome is not None else "recovery"
                    outcome_verified = settlement_outcome.verified if settlement_outcome is not None else False
                else:
                    outcome = "rolled_back"
                    outcome_verified = True

        close_failures = parent_descriptors.settle()
        if primary is not None:
            settlement.raise_after_parent_settlement(
                primary,
                close_failures=close_failures,
                path=path,
                outcome=outcome,
                verified=outcome_verified,
            )
        cleanup = settlement.publication_failure_ledger()
        cleanup.record_all(close_failures)
        cleanup.raise_if_any(
            message=f"Could not release the publication parent descriptor for {path}.",
            outcome=outcome,
            terminal_note=(
                f"LychD init preserved the verified {outcome} file-publication "
                f"outcome for {path} after settling its parent descriptor."
            ),
            verified=outcome_verified,
        )
        return result

    def _journal(self, resources: CreatedResources) -> None:
        """Commit one non-empty exact batch to the external lifecycle journal."""
        if self._on_created is not None and (resources.directories or resources.files or resources.subvolumes):
            self._on_created(resources)


def stage_text_file(
    *,
    parent_fd: int,
    path: Path,
    content: str,
    mode: int,
) -> FilePublication:
    """Write and attest one private same-directory candidate."""
    descriptors = DescriptorSet()
    descriptor = -1
    staging_name = ""
    for _ in range(_AUXILIARY_NAME_ATTEMPTS):
        staging_name = f".lychd-create-{uuid4().hex}"
        try:
            descriptor = descriptors.add(
                os.open(
                    staging_name,
                    _FILE_OPEN_FLAGS,
                    mode,
                    dir_fd=parent_fd,
                )
            )
        except FileExistsError:
            continue
        except BaseException as exc:  # noqa: BLE001 - create may complete before adapter return
            raise_after_staging_open_failure(
                parent_fd=parent_fd,
                staging_name=staging_name,
                path=path,
                primary=exc,
            )
        break
    if descriptor < 0:
        message = f"Could not allocate a private staging name for {path}"
        raise RuntimeError(message)

    identity: FileIdentity | None = None
    try:
        os.fchmod(descriptor, mode)
        metadata = os.fstat(descriptor)
        identity = settlement.identity(path=path, metadata=metadata)
        settlement.require_regular_file(metadata, path=path)
        stream = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptors.transfer(descriptor)
        with stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException as primary:  # noqa: BLE001 - exact staging cleanup precedes native propagation
        raise_after_staging_failure(
            parent_fd=parent_fd,
            staging_name=staging_name,
            identity=identity,
            path=path,
            primary=primary,
            close_failures=descriptors.settle(),
        )

    return FilePublication(
        identity=identity,
        parent_fd=parent_fd,
        staging_name=staging_name,
        public_name=path.name,
    )


def raise_after_staging_open_failure(
    *,
    parent_fd: int,
    staging_name: str,
    path: Path,
    primary: BaseException,
) -> NoReturn:
    """Classify an exclusive create whose adapter raised around its return."""
    recovery_path = path.parent / staging_name
    cleanup = settlement.publication_failure_ledger(
        recovery_paths=(recovery_path,),
    )
    try:
        observed = settlement.observe_name(
            parent_fd=parent_fd,
            name=staging_name,
        )
    except BaseException as observation_error:
        cleanup.record(primary, observation_error)
        cleanup.raise_if_any(
            message=(
                f"Could not classify private staging creation for {path}; possible recovery remains at {recovery_path}."
            ),
            outcome="recovery",
            terminal_note="",
            verified=False,
        )
        raise primary from observation_error
    if observed is None:
        settled = settlement.publication_failure_ledger()
        settled.record(primary)
        settled.raise_if_any(
            message=f"Staging creation failed before publishing a private candidate for {path}.",
            outcome="unchanged",
            terminal_note=(f"LychD init verified that failed staging creation left no private candidate for {path}."),
            verified=True,
        )
        raise primary
    cleanup.record(primary)
    cleanup.raise_if_any(
        message=(
            f"Exclusive staging creation for {path} did not return an identity "
            f"token; preserving possible recovery at {recovery_path}."
        ),
        outcome="recovery",
        terminal_note="",
        verified=False,
    )
    raise primary


def raise_after_staging_failure(
    *,
    parent_fd: int,
    staging_name: str,
    identity: FileIdentity | None,
    path: Path,
    primary: BaseException,
    close_failures: tuple[BaseException, ...],
) -> NoReturn:
    """Settle the staging name and descriptor without masking either peer."""
    cleanup = settlement.publication_failure_ledger()
    cleanup.record_all(close_failures)
    removed = False
    try:
        settlement.remove_private_name(
            parent_fd=parent_fd,
            name=staging_name,
            expected=identity,
            path=path,
            primary=primary,
        )
    except BaseException as exc:  # noqa: BLE001 - retain exact private recovery
        cleanup.record(exc)
        removed = settlement.private_name_is_absent(
            parent_fd=parent_fd,
            name=staging_name,
            cleanup=cleanup,
        )
    else:
        removed = True
    if removed:
        cleanup.raise_primary_after_verified_settlement(
            primary,
            outcome="rolled_back",
            terminal_note=(
                f"LychD init removed exact staging for {path} and settled its "
                "descriptor before preserving this interruption."
            ),
        )
    settled = settlement.publication_failure_ledger(
        recovery_paths=(path.parent / staging_name,),
    )
    settled.record_all(tuple(cleanup.failures))
    settled.record(primary)
    settled.raise_if_any(
        message=f"Initialization file staging retained recovery evidence for {path}.",
        outcome="recovery",
        terminal_note="",
        verified=False,
    )
    raise primary


def publish_file(publication: FilePublication) -> bool:
    """Hard-link a complete candidate to its public name without clobbering."""
    try:
        os.link(
            publication.staging_name,
            publication.public_name,
            src_dir_fd=publication.parent_fd,
            dst_dir_fd=publication.parent_fd,
            follow_symlinks=False,
        )
    except FileExistsError:
        recovery.remove_staging(publication)
        settlement.fsync_directory(publication.parent_fd, path=publication.identity.path.parent)
        return False
    except BaseException as exc:
        publication.published = True
        classify_publication_after_error(publication, primary=exc)
        raise
    publication.published = True
    settlement.fsync_directory(publication.parent_fd, path=publication.identity.path.parent)
    return True


def classify_publication_after_error(
    publication: FilePublication,
    *,
    primary: BaseException,
) -> None:
    """Recover exact publication state when a mutator raises after its effect."""
    try:
        staging = settlement.observe_name(
            parent_fd=publication.parent_fd,
            name=publication.staging_name,
        )
        public = settlement.observe_name(
            parent_fd=publication.parent_fd,
            name=publication.public_name,
        )
    except BaseException as observation_error:  # noqa: BLE001 - rollback must retain possible exposure
        message = (
            f"Initialization file publication could not classify possible public "
            f"exposure for {publication.identity.path}."
        )
        raise PublicationRollbackError(
            message,
            failures=(primary, observation_error),
            outcome="recovery",
            verified=False,
            recovery_paths=(
                publication.identity.path,
                publication.identity.path.parent / publication.staging_name,
            ),
        ) from (find_terminal_interruption(observation_error) or primary)
    staging_matches = settlement.matches(staging, expected=publication.identity)
    public_matches = settlement.matches(public, expected=publication.identity)
    if staging_matches and public_matches:
        publication.published = True
        return
    if staging_matches and not public_matches:
        publication.published = False
        return
    message = f"Initialization file publication became indeterminate for {publication.identity.path}"
    raise PublicationRollbackError(
        message,
        failures=(primary,),
        outcome="recovery",
        verified=False,
        recovery_paths=(
            publication.identity.path,
            publication.identity.path.parent / publication.staging_name,
        ),
    ) from primary


def attest_public_file(publication: FilePublication) -> None:
    """Require the installed public name to retain the staged identity."""
    descriptors = DescriptorSet()
    descriptor = -1
    primary: BaseException | None = None
    metadata: os.stat_result | None = None
    try:
        descriptor = descriptors.add(
            os.open(
                publication.public_name,
                _READ_FILE_FLAGS,
                dir_fd=publication.parent_fd,
            )
        )
        metadata = os.fstat(descriptor)
    except OSError as exc:
        message = f"Published initialization file became unreachable: {publication.identity.path}"
        primary = PublicationRollbackError(message)
        primary.__cause__ = exc
    except BaseException as exc:  # noqa: BLE001 - descriptor settlement remains a peer
        primary = exc
    close_failures: tuple[BaseException, ...] = ()
    if descriptor >= 0:
        try:
            descriptors.close(descriptor)
        except BaseException as exc:  # noqa: BLE001 - retain the sole close peer
            close_failures = (exc,)
    if primary is not None:
        cleanup = settlement.publication_failure_ledger()
        cleanup.record_all(close_failures)
        cleanup.raise_primary_after_verified_settlement(
            primary,
            outcome="published",
            terminal_note=(
                f"LychD init preserved the published candidate for "
                f"{publication.identity.path} while settling its attestation descriptor."
            ),
        )
    cleanup = settlement.publication_failure_ledger()
    cleanup.record_all(close_failures)
    cleanup.raise_if_any(
        message=f"Could not release published-file attestation for {publication.identity.path}.",
        outcome="published",
        terminal_note=(
            f"LychD init preserved the published candidate for "
            f"{publication.identity.path} while settling its attestation descriptor."
        ),
        verified=True,
    )
    if metadata is None:  # pragma: no cover - every failed capture returns above
        message = f"Published initialization file attestation produced no metadata: {publication.identity.path}"
        raise PublicationRollbackError(message)
    if not stat.S_ISREG(metadata.st_mode) or not settlement.matches(
        metadata,
        expected=publication.identity,
    ):
        message = f"Published initialization file changed identity: {publication.identity.path}"
        raise PublicationRollbackError(message)


__all__ = ("JournaledCreation",)
