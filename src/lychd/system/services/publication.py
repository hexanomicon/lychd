"""Journal-bound publication of initialization files and directories."""

from __future__ import annotations

import errno
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, NoReturn
from uuid import uuid4

from lychd.system import descriptor_settlement
from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.descriptor_settlement import (
    DescriptorSet,
    FailureLedger,
    find_settlement_outcome,
)
from lychd.system.interruptions import (
    find_terminal_interruption,
    iter_exception_graph,
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


class PublicationRollbackError(RuntimeError):
    """Exact creation rollback could not finish without risking foreign data."""

    def __init__(
        self,
        message: str,
        *,
        failures: tuple[BaseException, ...] = (),
        outcome: str | None = None,
        verified: bool | None = None,
        recovery_paths: tuple[Path, ...] = (),
    ) -> None:
        """Retain peer failures and the last verified publication outcome."""
        super().__init__(message)
        self.failures = failures
        self.outcome = outcome
        self.outcome_verified = outcome is not None and outcome != "recovery" if verified is None else verified
        self.recovery_paths = recovery_paths


@dataclass(frozen=True, slots=True)
class _FileIdentity:
    """One immutable regular-file identity captured before publication."""

    path: Path
    device: int
    inode: int


@dataclass(slots=True)
class _FilePublication:
    """Mutable settlement evidence for one staged file publication."""

    identity: _FileIdentity
    parent_fd: int
    staging_name: str
    public_name: str
    published: bool = False
    staging_present: bool = True
    recovery_names: set[str] = field(default_factory=set)
    indeterminate_paths: set[Path] = field(default_factory=set)


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
        _require_safe_file_target(path)
        parent_descriptors = DescriptorSet()
        parent_fd = parent_descriptors.add(_open_existing_directory(path.parent))
        publication: _FilePublication | None = None
        committed = False
        outcome = "unchanged"
        outcome_verified = True
        result = CreatedResources()
        primary: BaseException | None = None
        try:
            publication = _stage_text_file(
                parent_fd=parent_fd,
                path=path,
                content=content,
                mode=mode,
            )
            if _publish_file(publication):
                _attest_public_file(publication)
                _remove_staging(publication)
                _fsync_directory(parent_fd, path=path.parent)
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
            settlement = find_settlement_outcome(exc)
            if publication is None and settlement is not None:
                outcome = settlement.name
                outcome_verified = settlement.verified
            if publication is not None and not committed:
                try:
                    _rollback_file(publication)
                except BaseException as rollback:  # noqa: BLE001 - rollback may preserve a native signal
                    _retain_publication_primary(rollback, primary=exc)
                    primary = rollback
                    settlement = find_settlement_outcome(rollback)
                    outcome = settlement.name if settlement is not None else "recovery"
                    outcome_verified = settlement.verified if settlement is not None else False
                else:
                    outcome = "rolled_back"
                    outcome_verified = True

        close_failures = parent_descriptors.settle()
        if primary is not None:
            _raise_after_parent_settlement(
                primary,
                close_failures=close_failures,
                path=path,
                outcome=outcome,
                verified=outcome_verified,
            )
        cleanup = _publication_failure_ledger()
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


def _retain_publication_primary(
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


def _open_existing_directory(path: Path) -> int:
    """Open an existing directory component-by-component without following links."""
    descriptor = descriptor_settlement.open_directory_path(
        path,
        failure_ledger=_publication_failure_ledger(),
        component_error=_publication_component_error,
        unsafe_error=_publication_unsafe_path_error,
        terminal_note=(
            f"LychD init left the namespace unchanged while settling publication-parent traversal of {path}."
        ),
    )
    descriptors = DescriptorSet()
    descriptors.add(descriptor)
    try:
        metadata = os.fstat(descriptor)
        _require_publication_parent_owner(metadata, path=path)
    except BaseException as exc:  # noqa: BLE001 - descriptor settlement preserves native interruption
        cleanup = _publication_failure_ledger()
        cleanup.record_all(descriptors.settle())
        cleanup.raise_primary_after_verified_settlement(
            exc,
            outcome="unchanged",
            terminal_note=(f"LychD init left {path} unchanged after settling its publication-parent descriptor."),
        )
    return descriptors.transfer(descriptor)


def _publication_failure_ledger(
    *,
    recovery_paths: tuple[Path, ...] = (),
) -> FailureLedger:
    """Bind generic descriptor settlement to publication-specific evidence."""

    def error_factory(
        message: str,
        *,
        failures: tuple[BaseException, ...],
        outcome: str,
        verified: bool,
    ) -> BaseException:
        return PublicationRollbackError(
            message,
            failures=failures,
            outcome=outcome,
            verified=verified,
            recovery_paths=recovery_paths,
        )

    return FailureLedger(
        error_factory=error_factory,
        subject="File publication settlement",
    )


def _publication_component_error(
    path: Path,
    error: OSError,
) -> BaseException:
    """Translate one failed publication-parent component traversal."""
    message = f"Publication parent must already be a real directory: {path}: {error}"
    return RuntimeError(message)


def _publication_unsafe_path_error(path: Path) -> BaseException:
    """Translate one lexically unsafe publication parent."""
    message = f"Publication path contains an unsafe component: {path}"
    return RuntimeError(message)


def _require_publication_parent_owner(
    metadata: os.stat_result,
    *,
    path: Path,
) -> None:
    """Require the pinned publication parent to belong to the current UID."""
    if metadata.st_uid != os.getuid():
        message = f"Publication parent must be owned by uid {os.getuid()}: {path}"
        raise RuntimeError(message)


def _raise_after_parent_settlement(
    primary: BaseException,
    *,
    close_failures: tuple[BaseException, ...],
    path: Path,
    outcome: str,
    verified: bool,
) -> NoReturn:
    """Settle the parent descriptor before surfacing exact publication truth."""
    if isinstance(primary, PublicationRollbackError):
        cleanup = _publication_failure_ledger(
            recovery_paths=(primary.recovery_paths if not verified or outcome == "recovery" else ()),
        )
        cleanup.record(primary)
        cleanup.record_all(close_failures)
        cleanup.raise_if_any(
            message=str(primary),
            outcome=outcome,
            terminal_note=(
                f"LychD init retained explicit file-publication {outcome} truth "
                f"for {path} after settling its parent descriptor."
            ),
            verified=verified,
        )
    cleanup = _publication_failure_ledger()
    cleanup.record_all(close_failures)
    cleanup.raise_primary_after_verified_settlement(
        primary,
        outcome=outcome,
        terminal_note=(
            f"LychD init preserved the verified {outcome} file-publication "
            f"outcome for {path} after settling its parent descriptor."
        ),
    )


def _stage_text_file(
    *,
    parent_fd: int,
    path: Path,
    content: str,
    mode: int,
) -> _FilePublication:
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
            _raise_after_staging_open_failure(
                parent_fd=parent_fd,
                staging_name=staging_name,
                path=path,
                primary=exc,
            )
        break
    if descriptor < 0:
        message = f"Could not allocate a private staging name for {path}"
        raise RuntimeError(message)

    identity: _FileIdentity | None = None
    try:
        os.fchmod(descriptor, mode)
        metadata = os.fstat(descriptor)
        identity = _identity(path=path, metadata=metadata)
        _require_regular_file(metadata, path=path)
        stream = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptors.transfer(descriptor)
        with stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException as primary:  # noqa: BLE001 - exact staging cleanup precedes native propagation
        _raise_after_staging_failure(
            parent_fd=parent_fd,
            staging_name=staging_name,
            identity=identity,
            path=path,
            primary=primary,
            close_failures=descriptors.settle(),
        )

    return _FilePublication(
        identity=identity,
        parent_fd=parent_fd,
        staging_name=staging_name,
        public_name=path.name,
    )


def _raise_after_staging_open_failure(
    *,
    parent_fd: int,
    staging_name: str,
    path: Path,
    primary: BaseException,
) -> NoReturn:
    """Classify an exclusive create whose adapter raised around its return."""
    recovery_path = path.parent / staging_name
    cleanup = _publication_failure_ledger(
        recovery_paths=(recovery_path,),
    )
    try:
        observed = _observe_name(
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
        settled = _publication_failure_ledger()
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


def _raise_after_staging_failure(
    *,
    parent_fd: int,
    staging_name: str,
    identity: _FileIdentity | None,
    path: Path,
    primary: BaseException,
    close_failures: tuple[BaseException, ...],
) -> NoReturn:
    """Settle the staging name and descriptor without masking either peer."""
    cleanup = _publication_failure_ledger()
    cleanup.record_all(close_failures)
    removed = False
    try:
        _remove_private_name(
            parent_fd=parent_fd,
            name=staging_name,
            expected=identity,
            path=path,
            primary=primary,
        )
    except BaseException as exc:  # noqa: BLE001 - retain exact private recovery
        cleanup.record(exc)
        removed = _private_name_is_absent(
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
    settled = _publication_failure_ledger(
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


def _publish_file(publication: _FilePublication) -> bool:
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
        _remove_staging(publication)
        _fsync_directory(publication.parent_fd, path=publication.identity.path.parent)
        return False
    except BaseException as exc:
        publication.published = True
        _classify_publication_after_error(publication, primary=exc)
        raise
    publication.published = True
    _fsync_directory(publication.parent_fd, path=publication.identity.path.parent)
    return True


def _classify_publication_after_error(
    publication: _FilePublication,
    *,
    primary: BaseException,
) -> None:
    """Recover exact publication state when a mutator raises after its effect."""
    try:
        staging = _observe_name(
            parent_fd=publication.parent_fd,
            name=publication.staging_name,
        )
        public = _observe_name(
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
    staging_matches = _matches(staging, expected=publication.identity)
    public_matches = _matches(public, expected=publication.identity)
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


def _attest_public_file(publication: _FilePublication) -> None:
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
        cleanup = _publication_failure_ledger()
        cleanup.record_all(close_failures)
        cleanup.raise_primary_after_verified_settlement(
            primary,
            outcome="published",
            terminal_note=(
                f"LychD init preserved the published candidate for "
                f"{publication.identity.path} while settling its attestation descriptor."
            ),
        )
    cleanup = _publication_failure_ledger()
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
    if not stat.S_ISREG(metadata.st_mode) or not _matches(
        metadata,
        expected=publication.identity,
    ):
        message = f"Published initialization file changed identity: {publication.identity.path}"
        raise PublicationRollbackError(message)


def _rollback_file(publication: _FilePublication) -> None:
    """Remove only the exact candidate/public winner and preserve replacements."""
    cleanup = _publication_failure_ledger()
    if publication.published:
        try:
            _quarantine_public_file(publication)
        except BaseException as exc:  # noqa: BLE001 - settle the private peer before reporting
            cleanup.record(exc)
    if publication.staging_present:
        try:
            _remove_staging(publication)
        except BaseException as exc:  # noqa: BLE001 - retain all recovery evidence
            cleanup.record(exc)
    durable = True
    try:
        _fsync_directory(publication.parent_fd, path=publication.identity.path.parent)
    except BaseException as exc:  # noqa: BLE001 - durability failure is part of rollback truth
        cleanup.record(exc)
        durable = False
    if not cleanup.failures and not publication.recovery_names:
        return

    namespace_settled, recovery_paths = _observe_rollback_recovery(
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
    settled = _publication_failure_ledger(
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


def _observe_rollback_recovery(
    publication: _FilePublication,
    *,
    cleanup: FailureLedger,
) -> tuple[bool, tuple[Path, ...]]:
    """Prove every public, staging, and random rollback name is settled."""
    recovery_paths = sorted(publication.indeterminate_paths)
    try:
        public = _observe_name(
            parent_fd=publication.parent_fd,
            name=publication.public_name,
        )
        staging = _observe_name(
            parent_fd=publication.parent_fd,
            name=publication.staging_name,
        )
        if _matches(public, expected=publication.identity):
            recovery_paths.append(publication.identity.path)
        if _matches(staging, expected=publication.identity):
            recovery_paths.append(publication.identity.path.parent / publication.staging_name)
        for recovery_name in tuple(sorted(publication.recovery_names)):
            recovery = _observe_name(
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


def _quarantine_public_file(publication: _FilePublication) -> None:
    """Detach and compare the current public name before any unlink."""
    public = _observe_name(
        parent_fd=publication.parent_fd,
        name=publication.public_name,
    )
    if public is None or not _matches(public, expected=publication.identity):
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
        _settle_quarantine_after_error(
            publication,
            quarantine_name=quarantine_name,
            primary=exc,
        )
    _remove_or_restore_quarantine(
        publication,
        quarantine_name=quarantine_name,
    )


def _settle_quarantine_after_error(
    publication: _FilePublication,
    *,
    quarantine_name: str,
    primary: BaseException,
) -> NoReturn:
    """Classify a quarantine rename that may have completed before interruption."""
    try:
        public = _observe_name(
            parent_fd=publication.parent_fd,
            name=publication.public_name,
        )
        quarantine = _observe_name(
            parent_fd=publication.parent_fd,
            name=quarantine_name,
        )
    except BaseException as observation_error:  # noqa: BLE001 - keep exact random recovery name
        _raise_publication_recovery(
            publication,
            quarantine_name=quarantine_name,
            message=(f"Could not classify file rollback quarantine mutation for {publication.identity.path}."),
            failures=(primary, observation_error),
        )
    public_matches = _matches(public, expected=publication.identity)
    quarantine_matches = _matches(quarantine, expected=publication.identity)
    if public is None and quarantine_matches:
        _remove_or_restore_quarantine(
            publication,
            quarantine_name=quarantine_name,
        )
        raise primary
    if public is None and quarantine is None:
        publication.recovery_names.discard(quarantine_name)
        raise primary
    if public_matches and quarantine is None:
        publication.recovery_names.discard(quarantine_name)
        _raise_publication_recovery(
            publication,
            quarantine_name=None,
            message=(f"File rollback quarantine did not detach the public candidate for {publication.identity.path}."),
            failures=(primary,),
            additional_paths=(publication.identity.path,),
        )
    if isinstance(primary, FileExistsError) and public_matches:
        publication.recovery_names.discard(quarantine_name)
        _raise_publication_recovery(
            publication,
            quarantine_name=None,
            message=(f"File rollback quarantine collided before detaching {publication.identity.path}."),
            failures=(primary,),
            additional_paths=(publication.identity.path,),
        )
    _raise_publication_recovery(
        publication,
        quarantine_name=quarantine_name,
        message=f"File rollback quarantine became indeterminate for {publication.identity.path}.",
        failures=(primary,),
        additional_paths=((publication.identity.path,) if public_matches else ()),
    )


def _remove_or_restore_quarantine(
    publication: _FilePublication,
    *,
    quarantine_name: str,
) -> None:
    """Delete an exact quarantine or restore a foreign entry without clobbering."""
    try:
        quarantine = _observe_name(
            parent_fd=publication.parent_fd,
            name=quarantine_name,
        )
    except BaseException as observation_error:  # noqa: BLE001 - retain exact private recovery
        _raise_publication_recovery(
            publication,
            quarantine_name=quarantine_name,
            message=(f"Could not inspect rollback quarantine {quarantine_name} for {publication.identity.path}."),
            failures=(observation_error,),
        )
    if quarantine is None:
        publication.recovery_names.discard(quarantine_name)
        return
    if _matches(quarantine, expected=publication.identity):
        try:
            _remove_private_name(
                parent_fd=publication.parent_fd,
                name=quarantine_name,
                expected=publication.identity,
                path=publication.identity.path,
            )
        except BaseException as removal_error:
            try:
                after = _observe_name(
                    parent_fd=publication.parent_fd,
                    name=quarantine_name,
                )
            except BaseException as observation_error:  # noqa: BLE001 - retain exact recovery
                _raise_publication_recovery(
                    publication,
                    quarantine_name=quarantine_name,
                    message=(f"Could not classify rollback quarantine cleanup for {publication.identity.path}."),
                    failures=(removal_error, observation_error),
                )
            if after is None:
                publication.recovery_names.discard(quarantine_name)
                raise
            _raise_publication_recovery(
                publication,
                quarantine_name=quarantine_name,
                message=(f"Rollback quarantine cleanup retained {quarantine_name} for {publication.identity.path}."),
                failures=(removal_error,),
            )
        publication.recovery_names.discard(quarantine_name)
        return
    try:
        rename_noreplace_at(
            quarantine_name,
            publication.public_name,
            source_dir_fd=publication.parent_fd,
            destination_dir_fd=publication.parent_fd,
        )
    except BaseException as restore_error:  # noqa: BLE001 - classify both names after ambiguous return
        _settle_foreign_restore_error(
            publication,
            quarantine_name=quarantine_name,
            quarantine=quarantine,
            primary=restore_error,
        )
    publication.recovery_names.discard(quarantine_name)


def _settle_foreign_restore_error(
    publication: _FilePublication,
    *,
    quarantine_name: str,
    quarantine: os.stat_result,
    primary: BaseException,
) -> NoReturn:
    """Classify both names against the captured foreign identity after restore."""
    try:
        public = _observe_name(
            parent_fd=publication.parent_fd,
            name=publication.public_name,
        )
        after = _observe_name(
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
        _raise_publication_recovery(
            publication,
            quarantine_name=quarantine_name,
            message=(f"Could not classify foreign rollback recovery for {publication.identity.path}."),
            failures=(primary, observation_error),
        )
    if after is None and _same_regular_identity(public, quarantine):
        publication.recovery_names.discard(quarantine_name)
        raise primary
    if after is None:
        publication.recovery_names.discard(quarantine_name)
        publication.indeterminate_paths.add(publication.identity.path)
        _raise_publication_recovery(
            publication,
            quarantine_name=None,
            message=(
                f"Foreign rollback recovery lost its captured identity "
                f"between {quarantine_name} and {publication.identity.path}."
            ),
            failures=(primary,),
            additional_paths=(publication.identity.path,),
        )
    _raise_publication_recovery(
        publication,
        quarantine_name=quarantine_name,
        message=(
            f"Foreign replacement retained at private recovery name {quarantine_name} for {publication.identity.path}."
        ),
        failures=(primary,),
        additional_paths=((publication.identity.path,) if _matches(public, expected=publication.identity) else ()),
    )


def _raise_publication_recovery(
    publication: _FilePublication,
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


def _remove_staging(publication: _FilePublication) -> None:
    """Remove the exact private staging link once."""
    if not publication.staging_present:
        return
    _remove_private_name(
        parent_fd=publication.parent_fd,
        name=publication.staging_name,
        expected=publication.identity,
        path=publication.identity.path,
    )
    publication.staging_present = False


def _remove_private_name(
    *,
    parent_fd: int,
    name: str,
    expected: _FileIdentity | None,
    path: Path,
    primary: BaseException | None = None,
) -> None:
    """Unlink one private name only when its observed identity is expected."""
    try:
        observed = _observe_name(parent_fd=parent_fd, name=name)
    except OSError as exc:
        message = f"Could not inspect private file recovery name {name} for {path}"
        raise PublicationRollbackError(message) from (primary or exc)
    if observed is None:
        return
    if expected is None:
        message = f"Private file recovery name lacks captured identity and was retained: {name} for {path}"
        raise PublicationRollbackError(message) from primary
    if not _matches(observed, expected=expected):
        message = f"Private file recovery name changed identity: {name} for {path}"
        raise PublicationRollbackError(message) from primary
    try:
        os.unlink(name, dir_fd=parent_fd)
    except BaseException as exc:
        try:
            after = _observe_name(parent_fd=parent_fd, name=name)
        except OSError as observation_error:
            message = f"Could not classify private file removal {name} for {path}"
            raise PublicationRollbackError(message) from (primary or observation_error)
        if after is None:
            if isinstance(exc, Exception):
                return
            raise
        if not _matches(after, expected=expected):
            message = f"Private file recovery name changed during removal: {name} for {path}"
            raise PublicationRollbackError(message) from (primary or exc)
        message = f"Could not remove private file recovery name {name} for {path}"
        raise PublicationRollbackError(message) from (primary or exc)


def _private_name_is_absent(
    *,
    parent_fd: int,
    name: str,
    cleanup: FailureLedger,
) -> bool:
    """Observe cleanup after an exceptional unlink and retain observation peers."""
    try:
        return _observe_name(parent_fd=parent_fd, name=name) is None
    except BaseException as observation_error:  # noqa: BLE001 - caller owns final classification
        cleanup.record(observation_error)
        return False


def _observe_name(
    *,
    parent_fd: int,
    name: str,
) -> os.stat_result | None:
    """Observe one descriptor-relative name without following a symlink."""
    try:
        return os.stat(
            name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None


def _matches(
    observed: os.stat_result | None,
    *,
    expected: _FileIdentity,
) -> bool:
    """Return whether an observation is the exact expected regular file."""
    return bool(
        observed is not None
        and stat.S_ISREG(observed.st_mode)
        and observed.st_dev == expected.device
        and observed.st_ino == expected.inode
    )


def _same_regular_identity(
    observed: os.stat_result | None,
    expected: os.stat_result,
) -> bool:
    """Compare a post-error public name with one captured foreign file."""
    return bool(
        observed is not None
        and stat.S_ISREG(expected.st_mode)
        and stat.S_ISREG(observed.st_mode)
        and observed.st_dev == expected.st_dev
        and observed.st_ino == expected.st_ino
    )


def _identity(
    *,
    path: Path,
    metadata: os.stat_result,
) -> _FileIdentity:
    """Build one immutable identity from descriptor-derived metadata."""
    return _FileIdentity(
        path=path,
        device=metadata.st_dev,
        inode=metadata.st_ino,
    )


def _require_regular_file(metadata: os.stat_result, *, path: Path) -> None:
    """Reject an impossible non-file result from exclusive creation."""
    if not stat.S_ISREG(metadata.st_mode):
        message = f"Staged initialization file is not regular: {path}"
        raise RuntimeError(message)


def _require_safe_file_target(path: Path) -> None:
    """Reject target names that cannot be one descriptor-relative file leaf."""
    if path.name in {"", ".", ".."} or path.parent / path.name != path:
        message = f"Initialization file target is not lexically safe: {path}"
        raise RuntimeError(message)


def _fsync_directory(descriptor: int, *, path: Path) -> None:
    """Persist one directory namespace transition through its pinned descriptor."""
    try:
        os.fsync(descriptor)
    except OSError as exc:
        if exc.errno == errno.EINVAL:
            message = f"Filesystem cannot durably sync publication parent: {path}"
            raise RuntimeError(message) from exc
        raise
