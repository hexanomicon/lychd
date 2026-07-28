"""Descriptor and namespace settlement for initialization file publication."""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path
from typing import NoReturn

from lychd.system import descriptor_settlement
from lychd.system.descriptor_settlement import DescriptorSet, FailureLedger
from lychd.system.services.file_publication_models import (
    FileIdentity,
    PublicationRollbackError,
)


def open_existing_directory(path: Path) -> int:
    """Open an existing directory component-by-component without following links."""
    descriptor = descriptor_settlement.open_directory_path(
        path,
        failure_ledger=publication_failure_ledger(),
        component_error=publication_component_error,
        unsafe_error=publication_unsafe_path_error,
        terminal_note=(
            f"LychD init left the namespace unchanged while settling publication-parent traversal of {path}."
        ),
    )
    descriptors = DescriptorSet()
    descriptors.add(descriptor)
    try:
        metadata = os.fstat(descriptor)
        require_publication_parent_owner(metadata, path=path)
    except BaseException as exc:  # noqa: BLE001 - descriptor settlement preserves native interruption
        cleanup = publication_failure_ledger()
        cleanup.record_all(descriptors.settle())
        cleanup.raise_primary_after_verified_settlement(
            exc,
            outcome="unchanged",
            terminal_note=(f"LychD init left {path} unchanged after settling its publication-parent descriptor."),
        )
    return descriptors.transfer(descriptor)


def publication_failure_ledger(
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


def publication_component_error(
    path: Path,
    error: OSError,
) -> BaseException:
    """Translate one failed publication-parent component traversal."""
    message = f"Publication parent must already be a real directory: {path}: {error}"
    return RuntimeError(message)


def publication_unsafe_path_error(path: Path) -> BaseException:
    """Translate one lexically unsafe publication parent."""
    message = f"Publication path contains an unsafe component: {path}"
    return RuntimeError(message)


def require_publication_parent_owner(
    metadata: os.stat_result,
    *,
    path: Path,
) -> None:
    """Require the pinned publication parent to belong to the current UID."""
    if metadata.st_uid != os.getuid():
        message = f"Publication parent must be owned by uid {os.getuid()}: {path}"
        raise RuntimeError(message)


def raise_after_parent_settlement(
    primary: BaseException,
    *,
    close_failures: tuple[BaseException, ...],
    path: Path,
    outcome: str,
    verified: bool,
) -> NoReturn:
    """Settle the parent descriptor before surfacing exact publication truth."""
    if isinstance(primary, PublicationRollbackError):
        cleanup = publication_failure_ledger(
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
    cleanup = publication_failure_ledger()
    cleanup.record_all(close_failures)
    cleanup.raise_primary_after_verified_settlement(
        primary,
        outcome=outcome,
        terminal_note=(
            f"LychD init preserved the verified {outcome} file-publication "
            f"outcome for {path} after settling its parent descriptor."
        ),
    )


def remove_private_name(
    *,
    parent_fd: int,
    name: str,
    expected: FileIdentity | None,
    path: Path,
    primary: BaseException | None = None,
) -> None:
    """Unlink one private name only when its observed identity is expected."""
    try:
        observed = observe_name(parent_fd=parent_fd, name=name)
    except OSError as exc:
        message = f"Could not inspect private file recovery name {name} for {path}"
        raise PublicationRollbackError(message) from (primary or exc)
    if observed is None:
        return
    if expected is None:
        message = f"Private file recovery name lacks captured identity and was retained: {name} for {path}"
        raise PublicationRollbackError(message) from primary
    if not matches(observed, expected=expected):
        message = f"Private file recovery name changed identity: {name} for {path}"
        raise PublicationRollbackError(message) from primary
    try:
        os.unlink(name, dir_fd=parent_fd)
    except BaseException as exc:
        try:
            after = observe_name(parent_fd=parent_fd, name=name)
        except OSError as observation_error:
            message = f"Could not classify private file removal {name} for {path}"
            raise PublicationRollbackError(message) from (primary or observation_error)
        if after is None:
            if isinstance(exc, Exception):
                return
            raise
        if not matches(after, expected=expected):
            message = f"Private file recovery name changed during removal: {name} for {path}"
            raise PublicationRollbackError(message) from (primary or exc)
        message = f"Could not remove private file recovery name {name} for {path}"
        raise PublicationRollbackError(message) from (primary or exc)


def private_name_is_absent(
    *,
    parent_fd: int,
    name: str,
    cleanup: FailureLedger,
) -> bool:
    """Observe cleanup after an exceptional unlink and retain observation peers."""
    try:
        return observe_name(parent_fd=parent_fd, name=name) is None
    except BaseException as observation_error:  # noqa: BLE001 - caller owns final classification
        cleanup.record(observation_error)
        return False


def observe_name(
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


def matches(
    observed: os.stat_result | None,
    *,
    expected: FileIdentity,
) -> bool:
    """Return whether an observation is the exact expected regular file."""
    return bool(
        observed is not None
        and stat.S_ISREG(observed.st_mode)
        and observed.st_dev == expected.device
        and observed.st_ino == expected.inode
    )


def same_regular_identity(
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


def identity(
    *,
    path: Path,
    metadata: os.stat_result,
) -> FileIdentity:
    """Build one immutable identity from descriptor-derived metadata."""
    return FileIdentity(
        path=path,
        device=metadata.st_dev,
        inode=metadata.st_ino,
    )


def require_regular_file(metadata: os.stat_result, *, path: Path) -> None:
    """Reject an impossible non-file result from exclusive creation."""
    if not stat.S_ISREG(metadata.st_mode):
        message = f"Staged initialization file is not regular: {path}"
        raise RuntimeError(message)


def require_safe_file_target(path: Path) -> None:
    """Reject target names that cannot be one descriptor-relative file leaf."""
    if path.name in {"", ".", ".."} or path.parent / path.name != path:
        message = f"Initialization file target is not lexically safe: {path}"
        raise RuntimeError(message)


def fsync_directory(descriptor: int, *, path: Path) -> None:
    """Persist one directory namespace transition through its pinned descriptor."""
    try:
        os.fsync(descriptor)
    except OSError as exc:
        if exc.errno == errno.EINVAL:
            message = f"Filesystem cannot durably sync publication parent: {path}"
            raise RuntimeError(message) from exc
        raise


__all__ = (
    "fsync_directory",
    "identity",
    "matches",
    "observe_name",
    "open_existing_directory",
    "private_name_is_absent",
    "publication_failure_ledger",
    "raise_after_parent_settlement",
    "remove_private_name",
    "require_regular_file",
    "require_safe_file_target",
    "same_regular_identity",
)
