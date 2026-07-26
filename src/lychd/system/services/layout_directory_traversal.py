"""Descriptor-relative traversal and identity checks for managed directories."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from lychd.system import descriptor_settlement
from lychd.system.descriptor_settlement import DescriptorSet
from lychd.system.services.layout_directory_models import (
    CreatedDirectoryEntry,
    ObservedDirectory,
    OpenedDirectory,
)
from lychd.system.services.layout_directory_settlement import directory_failure_ledger
from lychd.system.services.lifecycle.models import CreatedDirectory

DIRECTORY_OPEN_FLAGS = descriptor_settlement.DIRECTORY_OPEN_FLAGS


def require_existing_directory(path: Path) -> None:
    """Traverse every component without following links, then verify the leaf."""
    descriptor = open_directory_path(path)
    descriptors = DescriptorSet()
    descriptors.add(descriptor)
    try:
        metadata = os.fstat(descriptor)
        require_owned_directory(metadata, path=path)
    except BaseException as exc:  # noqa: BLE001 - observation and close both settle
        cleanup = directory_failure_ledger()
        cleanup.record_all(descriptors.settle())
        cleanup.raise_primary_after_verified_settlement(
            exc,
            outcome="observed",
            terminal_note=(
                f"LychD init preserved the existing directory observation for {path} after settling its descriptor."
            ),
        )
    cleanup = directory_failure_ledger()
    cleanup.record_all(descriptors.settle())
    cleanup.raise_if_any(
        message=f"Could not release the observed directory descriptor for {path}.",
        outcome="observed",
        terminal_note=(
            f"LychD init preserved the existing directory observation for {path} after settling its descriptor."
        ),
        verified=True,
    )


def open_directory_path(path: Path) -> int:
    """Open one complete path component-by-component without following links."""
    return descriptor_settlement.open_directory_path(
        path,
        failure_ledger=directory_failure_ledger(),
        component_error=_managed_component_error,
        unsafe_error=_managed_unsafe_path_error,
        terminal_note=(f"LychD init left the directory namespace unchanged while settling traversal of {path}."),
    )


def directory_chain_start(path: Path) -> tuple[Path, tuple[str, ...]]:
    """Resolve traversal start and reject lexical escape components."""
    return descriptor_settlement.directory_chain_start(
        path,
        unsafe_error=_managed_unsafe_path_error,
    )


def _managed_component_error(
    path: Path,
    error: OSError,
) -> BaseException:
    """Translate one ordinary managed-layout traversal failure."""
    message = f"Could not traverse managed layout directory {path}: {error}"
    return RuntimeError(message)


def _managed_unsafe_path_error(path: Path) -> BaseException:
    """Translate one lexically unsafe managed-layout path."""
    message = f"Managed layout path contains an unsafe component: {path}"
    return RuntimeError(message)


def open_existing_directory_component(
    *,
    parent_fd: int,
    component: str,
    path: Path,
) -> int:
    """Open one existing real directory relative to its verified parent."""
    try:
        return os.open(
            component,
            DIRECTORY_OPEN_FLAGS,
            dir_fd=parent_fd,
        )
    except OSError as exc:
        message = f"Could not traverse managed layout directory {path}: {exc}"
        raise RuntimeError(message) from exc


def opened_existing_directory(
    descriptor: int,
    *,
    path: Path,
    raced: bool,
) -> OpenedDirectory:
    """Inspect an opened existing directory without leaking its descriptor."""
    descriptors = DescriptorSet()
    descriptors.add(descriptor)
    try:
        metadata = os.fstat(descriptor)
    except BaseException as exc:  # noqa: BLE001 - descriptor close is part of outcome
        cleanup = directory_failure_ledger()
        cleanup.record_all(descriptors.settle())
        cleanup.raise_primary_after_verified_settlement(
            exc,
            outcome="unchanged",
            terminal_note=(f"LychD init left {path} unchanged after settling its inspection descriptor."),
        )
    descriptors.transfer(descriptor)
    return OpenedDirectory(
        descriptor=descriptor,
        metadata=metadata,
        creation=None,
        raced=raced,
    )


def require_safe_opened_directory(
    opened: OpenedDirectory,
    *,
    path: Path,
) -> None:
    """Reject non-directories and foreign resources won during a race."""
    if not stat.S_ISDIR(opened.metadata.st_mode):
        message = f"Managed layout component is not a real directory: {path}"
        raise RuntimeError(message)
    if opened.raced and opened.metadata.st_uid != os.getuid():
        message = f"Raced managed layout component is not owned by uid {os.getuid()}: {path}"
        raise RuntimeError(message)


def require_pinned_identity(
    metadata: os.stat_result,
    *,
    expected: ObservedDirectory,
    path: Path,
) -> None:
    """Reject identity drift between provisioning and pinned use."""
    if metadata.st_dev != expected.device or metadata.st_ino != expected.inode:
        message = f"Provisioned directory changed identity before use: {path}"
        raise RuntimeError(message)


def require_owned_directory(
    metadata: os.stat_result,
    *,
    path: Path,
) -> None:
    """Reject an existing layout leaf owned by another user."""
    if metadata.st_uid != os.getuid():
        message = f"Managed layout path must be owned by uid {os.getuid()}: {path}"
        raise RuntimeError(message)


def require_staged_directory(
    metadata: os.stat_result,
    *,
    path: Path,
) -> None:
    """Reject an impossible non-directory result from the private candidate."""
    if not stat.S_ISDIR(metadata.st_mode):
        message = f"Staged layout path is not a real directory: {path}"
        raise RuntimeError(message)


def validate_created_directory_paths(
    created: list[CreatedDirectoryEntry],
) -> None:
    """Prove every public name still resolves to its installed identity."""
    for entry in created:
        try:
            metadata = entry.resource.path.lstat()
        except OSError as exc:
            message = f"Created layout path became unreachable: {entry.resource.path}"
            raise RuntimeError(message) from exc
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_dev != entry.resource.device
            or metadata.st_ino != entry.resource.inode
        ):
            message = f"Created layout path changed identity during initialization: {entry.resource.path}"
            raise RuntimeError(message)


def observe_directory(
    *,
    parent_fd: int,
    name: str,
) -> os.stat_result | None:
    """Observe one directory-relative name without following it."""
    try:
        return os.stat(
            name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None


def matches_created_directory(
    metadata: os.stat_result | None,
    *,
    expected: CreatedDirectory,
) -> bool:
    """Return whether metadata is the exact created directory identity."""
    return (
        metadata is not None
        and stat.S_ISDIR(metadata.st_mode)
        and metadata.st_dev == expected.device
        and metadata.st_ino == expected.inode
    )


def same_directory_identity(
    left: os.stat_result,
    right: os.stat_result,
) -> bool:
    """Compare exact directory identities without trusting a pathname."""
    return (
        stat.S_ISDIR(left.st_mode)
        and stat.S_ISDIR(right.st_mode)
        and left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
    )


__all__ = (
    "DIRECTORY_OPEN_FLAGS",
    "directory_chain_start",
    "matches_created_directory",
    "observe_directory",
    "open_directory_path",
    "open_existing_directory_component",
    "opened_existing_directory",
    "require_existing_directory",
    "require_owned_directory",
    "require_pinned_identity",
    "require_safe_opened_directory",
    "require_staged_directory",
    "same_directory_identity",
    "validate_created_directory_paths",
)
