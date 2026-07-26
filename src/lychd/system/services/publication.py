"""Journal-bound publication of initialization files and directories."""

from __future__ import annotations

import errno
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, NoReturn
from uuid import uuid4

from lychd.system import descriptor_settlement
from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.descriptor_settlement import DescriptorSet, FailureLedger
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
    ) -> None:
        """Retain peer failures and the last verified publication outcome."""
        super().__init__(message)
        self.failures = failures
        self.outcome = outcome


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
                self._resources = CreatedResources.combine(
                    self._resources,
                    result,
                )
        except BaseException as exc:  # noqa: BLE001 - mutation truth crosses native interruption
            primary = exc
            if publication is not None and not committed:
                try:
                    _rollback_file(publication)
                except PublicationRollbackError as rollback:
                    if rollback.__cause__ is None:
                        rollback.__cause__ = exc
                    primary = rollback
                    outcome = rollback.outcome or "recovery"
                else:
                    outcome = "rolled_back"

        close_failures = parent_descriptors.settle()
        if primary is not None:
            _raise_after_parent_settlement(
                primary,
                close_failures=close_failures,
                path=path,
                outcome=outcome,
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
            verified=True,
        )
        return result

    def _journal(self, resources: CreatedResources) -> None:
        """Commit one non-empty exact batch to the external lifecycle journal."""
        if self._on_created is not None and (resources.directories or resources.files or resources.subvolumes):
            self._on_created(resources)


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


def _publication_failure_ledger() -> FailureLedger:
    """Bind generic descriptor settlement to publication-specific evidence."""
    return FailureLedger(
        error_factory=PublicationRollbackError,
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
) -> NoReturn:
    """Settle the parent descriptor before surfacing exact publication truth."""
    cleanup = _publication_failure_ledger()
    if isinstance(primary, PublicationRollbackError):
        cleanup.record(primary)
        cleanup.record_all(close_failures)
        cleanup.raise_if_any(
            message=str(primary),
            outcome=primary.outcome or outcome,
            terminal_note=(
                f"LychD init retained explicit file-publication recovery truth "
                f"for {path} after settling its parent descriptor."
            ),
            verified=True,
        )
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
    descriptor = -1
    staging_name = ""
    for _ in range(_AUXILIARY_NAME_ATTEMPTS):
        staging_name = f".lychd-create-{uuid4().hex}"
        try:
            descriptor = os.open(
                staging_name,
                _FILE_OPEN_FLAGS,
                mode,
                dir_fd=parent_fd,
            )
        except FileExistsError:
            continue
        except OSError as exc:
            message = f"Could not stage initialization file {path}: {exc}"
            raise RuntimeError(message) from exc
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
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException as exc:
        if descriptor >= 0:
            os.close(descriptor)
        _remove_private_name(
            parent_fd=parent_fd,
            name=staging_name,
            expected=identity,
            path=path,
            primary=exc,
        )
        raise

    return _FilePublication(
        identity=identity,
        parent_fd=parent_fd,
        staging_name=staging_name,
        public_name=path.name,
    )


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
    staging = _observe_name(
        parent_fd=publication.parent_fd,
        name=publication.staging_name,
    )
    public = _observe_name(
        parent_fd=publication.parent_fd,
        name=publication.public_name,
    )
    staging_matches = _matches(staging, expected=publication.identity)
    public_matches = _matches(public, expected=publication.identity)
    if staging_matches and public_matches:
        publication.published = True
        return
    if staging_matches and not public_matches:
        return
    message = f"Initialization file publication became indeterminate for {publication.identity.path}"
    raise PublicationRollbackError(message) from primary


def _attest_public_file(publication: _FilePublication) -> None:
    """Require the installed public name to retain the staged identity."""
    descriptor = -1
    try:
        descriptor = os.open(
            publication.public_name,
            _READ_FILE_FLAGS,
            dir_fd=publication.parent_fd,
        )
        metadata = os.fstat(descriptor)
    except OSError as exc:
        message = f"Published initialization file became unreachable: {publication.identity.path}"
        raise PublicationRollbackError(message) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or not _matches(
        metadata,
        expected=publication.identity,
    ):
        message = f"Published initialization file changed identity: {publication.identity.path}"
        raise PublicationRollbackError(message)


def _rollback_file(publication: _FilePublication) -> None:
    """Remove only the exact candidate/public winner and preserve replacements."""
    failures: list[BaseException] = []
    if publication.published:
        try:
            _quarantine_public_file(publication)
        except BaseException as exc:  # noqa: BLE001 - settle the private peer before reporting
            failures.append(exc)
    if publication.staging_present:
        try:
            _remove_staging(publication)
        except BaseException as exc:  # noqa: BLE001 - retain all recovery evidence
            failures.append(exc)
    try:
        _fsync_directory(publication.parent_fd, path=publication.identity.path.parent)
    except BaseException as exc:  # noqa: BLE001 - durability failure is part of rollback truth
        failures.append(exc)
    if failures:
        detail = "; ".join(str(failure) for failure in failures)
        message = f"Exact file rollback did not complete for {publication.identity.path}: {detail}"
        raise PublicationRollbackError(message) from failures[0]


def _quarantine_public_file(publication: _FilePublication) -> None:
    """Detach and compare the current public name before any unlink."""
    public = _observe_name(
        parent_fd=publication.parent_fd,
        name=publication.public_name,
    )
    if public is None or not _matches(public, expected=publication.identity):
        return
    quarantine_name = f".lychd-rollback-{uuid4().hex}"
    try:
        rename_noreplace_at(
            publication.public_name,
            quarantine_name,
            source_dir_fd=publication.parent_fd,
            destination_dir_fd=publication.parent_fd,
        )
    except FileNotFoundError:
        return
    except BaseException as exc:
        if _settle_quarantine_after_error(
            publication,
            quarantine_name=quarantine_name,
            primary=exc,
        ):
            return
        raise
    _remove_or_restore_quarantine(
        publication,
        quarantine_name=quarantine_name,
    )


def _settle_quarantine_after_error(
    publication: _FilePublication,
    *,
    quarantine_name: str,
    primary: BaseException,
) -> bool:
    """Classify a quarantine rename that may have completed before interruption."""
    public = _observe_name(
        parent_fd=publication.parent_fd,
        name=publication.public_name,
    )
    quarantine = _observe_name(
        parent_fd=publication.parent_fd,
        name=quarantine_name,
    )
    if public is None and quarantine is not None:
        _remove_or_restore_quarantine(
            publication,
            quarantine_name=quarantine_name,
        )
        return True
    if public is not None and quarantine is None:
        return False
    message = f"File rollback quarantine became indeterminate for {publication.identity.path}"
    raise PublicationRollbackError(message) from primary


def _remove_or_restore_quarantine(
    publication: _FilePublication,
    *,
    quarantine_name: str,
) -> None:
    """Delete an exact quarantine or restore a foreign entry without clobbering."""
    quarantine = _observe_name(
        parent_fd=publication.parent_fd,
        name=quarantine_name,
    )
    if _matches(quarantine, expected=publication.identity):
        _remove_private_name(
            parent_fd=publication.parent_fd,
            name=quarantine_name,
            expected=publication.identity,
            path=publication.identity.path,
            suppress_completed_interruption=True,
        )
        return
    try:
        rename_noreplace_at(
            quarantine_name,
            publication.public_name,
            source_dir_fd=publication.parent_fd,
            destination_dir_fd=publication.parent_fd,
        )
    except FileNotFoundError:
        return
    except FileExistsError as exc:
        message = (
            f"Foreign replacement retained at private recovery name {quarantine_name} for {publication.identity.path}"
        )
        raise PublicationRollbackError(message) from exc


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
    suppress_completed_interruption: bool = False,
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
            if isinstance(exc, Exception) or suppress_completed_interruption:
                return
            raise
        if not _matches(after, expected=expected):
            message = f"Private file recovery name changed during removal: {name} for {path}"
            raise PublicationRollbackError(message) from (primary or exc)
        message = f"Could not remove private file recovery name {name} for {path}"
        raise PublicationRollbackError(message) from (primary or exc)


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
