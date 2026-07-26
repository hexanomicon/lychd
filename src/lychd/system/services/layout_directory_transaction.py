"""Transaction orchestration for descriptor-safe directory provisioning."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import structlog

from lychd.system.descriptor_settlement import DescriptorSet
from lychd.system.services import layout_directory_publication as publication
from lychd.system.services import layout_directory_recovery as recovery
from lychd.system.services import layout_directory_traversal as traversal
from lychd.system.services.layout_directory_models import (
    CreatedDirectoryEntry,
    ObservedDirectory,
)
from lychd.system.services.layout_directory_settlement import directory_failure_ledger
from lychd.system.services.lifecycle.models import CreatedDirectory

logger = structlog.get_logger()


class DirectoryProvisioning:
    """Retain exact mkdir rollback authority until its caller commits."""

    def __init__(self) -> None:
        """Begin one unsettled directory-provisioning transaction."""
        self._created: list[CreatedDirectoryEntry] = []
        self._observed: dict[Path, ObservedDirectory] = {}
        self._settled = False

    @property
    def created_paths(self) -> tuple[Path, ...]:
        """Return only paths whose atomic installation this transaction won."""
        return tuple(entry.resource.path for entry in self._created)

    @property
    def created_identities(self) -> tuple[CreatedDirectory, ...]:
        """Return immutable identities captured before each path was installed."""
        return tuple(entry.resource for entry in self._created)

    def create(
        self,
        path: Path,
        *,
        mode: int | None = None,
    ) -> None:
        """Create one path chain and retain descriptor-pinned rollback tokens."""
        self._require_unsettled()
        created: list[CreatedDirectoryEntry] = []
        descriptors = DescriptorSet()
        current_path, components = traversal.directory_chain_start(path)
        current_fd = descriptors.add(os.open(current_path, traversal.DIRECTORY_OPEN_FLAGS))
        try:
            current_metadata = os.fstat(current_fd)
            for component in components:
                next_path = current_path / component
                opened = publication.open_directory_component(
                    parent_fd=current_fd,
                    component=component,
                    path=next_path,
                    mode=mode,
                )
                descriptors.add(opened.descriptor)
                if opened.creation is not None:
                    created.append(opened.creation)
                elif opened.raced:
                    logger.debug(
                        "layout_path_raced_preserved",
                        path=str(next_path),
                    )
                traversal.require_safe_opened_directory(
                    opened,
                    path=next_path,
                )
                previous_fd = current_fd
                current_fd = opened.descriptor
                current_path = next_path
                current_metadata = opened.metadata
                descriptors.close(previous_fd)
                self._remember_observation(
                    next_path,
                    metadata=opened.metadata,
                )
            traversal.validate_created_directory_paths(created)
            self._remember_observation(
                path,
                metadata=current_metadata,
            )
        except BaseException as exc:  # noqa: BLE001 - cancellation must roll back
            recovery.raise_after_rollback(
                created,
                primary=exc,
                descriptors=descriptors,
            )
        self._created.extend(created)
        close_failures = descriptors.settle()
        if close_failures:
            ledger = directory_failure_ledger()
            ledger.record_all(close_failures)
            ledger.raise_if_any(
                message=("Directory creation is tracked, but its traversal descriptor could not be released cleanly."),
                outcome="pending",
                terminal_note=(
                    "LychD init recorded every created directory before the close "
                    "interruption; the provisioning transaction remains available "
                    "for exact rollback."
                ),
                verified=True,
            )

    @contextmanager
    def pin(self, path: Path) -> Iterator[int]:
        """Yield the exact previously observed directory through a live descriptor."""
        self._require_unsettled()
        expected = self._observed.get(path)
        if expected is None:
            message = f"Directory was not observed by this provisioning transaction: {path}"
            raise RuntimeError(message)
        descriptor = traversal.open_directory_path(path)
        descriptors = DescriptorSet()
        descriptors.add(descriptor)
        try:
            metadata = os.fstat(descriptor)
            traversal.require_pinned_identity(
                metadata,
                expected=expected,
                path=path,
            )
            yield descriptor
        except BaseException as exc:  # noqa: BLE001 - body and close both must settle
            cleanup = directory_failure_ledger()
            cleanup.record_all(descriptors.settle())
            cleanup.raise_primary_after_verified_settlement(
                exc,
                outcome="pinned",
                terminal_note=(f"LychD init preserved the pinned identity for {path} after settling its descriptor."),
            )
        cleanup = directory_failure_ledger()
        cleanup.record_all(descriptors.settle())
        cleanup.raise_if_any(
            message=f"Could not release the pinned directory descriptor for {path}.",
            outcome="pinned",
            terminal_note=(f"LychD init preserved the pinned identity for {path} after settling its descriptor."),
            verified=True,
        )

    def commit(self) -> None:
        """Release rollback authority after the external journal succeeds."""
        if self._settled:
            return
        failures = recovery.close_parent_descriptors(self._created)
        self._settled = True
        ledger = directory_failure_ledger()
        ledger.record_all(failures)
        ledger.raise_if_any(
            message="Could not release every committed directory rollback descriptor.",
            outcome="committed",
            terminal_note=(
                "LychD init committed the public directory publication and attempted "
                "every rollback-descriptor close before preserving this interruption."
            ),
            verified=True,
        )

    def rollback(self) -> None:
        """Quarantine exact winners, removing only never-published candidates."""
        if self._settled:
            return
        try:
            recovery.rollback_created_directories(self._created)
        finally:
            self._settled = True

    def _require_unsettled(self) -> None:
        """Reject effects after rollback authority has been consumed."""
        if self._settled:
            message = "Directory provisioning is already settled."
            raise RuntimeError(message)

    def _remember_observation(
        self,
        path: Path,
        *,
        metadata: os.stat_result,
    ) -> None:
        """Record one path identity or reject drift from an earlier traversal."""
        observed = ObservedDirectory(
            path=path,
            device=metadata.st_dev,
            inode=metadata.st_ino,
        )
        previous = self._observed.setdefault(path, observed)
        if previous != observed:
            message = f"Provisioned directory changed identity during use: {path}"
            raise RuntimeError(message)


__all__ = ("DirectoryProvisioning",)
