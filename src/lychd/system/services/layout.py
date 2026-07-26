"""Journal-aware creation of the initialization filesystem geography."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, NoReturn

import structlog

from lychd.system.binding_sites import (
    DEFAULT_BINDING_SITES,
    PRIVATE_BINDING_SITE_MODE,
)
from lychd.system.constants import (
    HOST_LAYOUT,
    PATH_POSTGRESS_DATA_DIR,
)
from lychd.system.interruptions import find_terminal_interruption
from lychd.system.services.btrfs import (
    Btrfs,
    BtrfsCreationError,
    BtrfsCreationEvidence,
    BtrfsCreationState,
    BtrfsSubvolumeObservation,
)
from lychd.system.services.layout_directories import (
    DirectoryProvisioning,
    require_existing_directory,
)
from lychd.system.services.lifecycle.models import (
    CreatedBtrfsSubvolume,
    CreatedResources,
    created_resources,
)

logger = structlog.get_logger()

_BINDING_SITES = frozenset(DEFAULT_BINDING_SITES.paths)


@dataclass(frozen=True, slots=True)
class _ProvisionedPath:
    """Created resources plus rollback authority held until journaling succeeds."""

    resources: CreatedResources
    directories: DirectoryProvisioning


@dataclass(slots=True)
class _SubvolumeAttempt:
    """Mutable evidence crossing the subvolume call/assignment boundary."""

    created: list[CreatedBtrfsSubvolume] = field(default_factory=list)
    materialized: BtrfsSubvolumeObservation | None = None
    in_flight: bool = False


class Layout:
    """Create missing layout paths without adopting existing host resources."""

    def __init__(
        self,
        paths: tuple[Path, ...] | list[Path] | None = None,
        *,
        layout: tuple[Path, ...] | list[Path] | None = None,
    ) -> None:
        """Initialize the layout orchestrator with defined architectural paths.

        Args:
            paths: System directories to manage. Defaults to HOST_LAYOUT constant.
            layout: Legacy alias for paths retained for older call sites.

        """
        if paths is not None and layout is not None:
            msg = "Use either paths or layout, not both."
            raise ValueError(msg)

        selected_paths = layout if layout is not None else paths
        self.paths: Final[tuple[Path, ...]] = HOST_LAYOUT if selected_paths is None else tuple(selected_paths)
        self.btrfs: Final[Btrfs] = Btrfs()

    def initialize(
        self,
        *,
        on_created: Callable[[CreatedResources], None] | None = None,
    ) -> CreatedResources:
        """Synchronize the physical layout using the public CLI-facing API."""
        return self.mkdirs(on_created=on_created)

    def mkdirs(
        self,
        *,
        on_created: Callable[[CreatedResources], None] | None = None,
    ) -> CreatedResources:
        """Synchronize the physical layout with the system blueprint."""
        created_batches: list[CreatedResources] = []
        skipped_paths: list[str] = []

        for path in self.paths:
            if os.path.lexists(path):
                require_existing_directory(path)
                logger.debug("layout_path_exists_skipped", path=str(path))
                skipped_paths.append(str(path))
                continue

            provisioned = self._provision_path(path)
            try:
                if on_created is not None:
                    on_created(provisioned.resources)
            except BaseException:
                retained_subvolume = self._defer_created_subvolume_rollback(
                    provisioned.resources.subvolumes,
                )
                if retained_subvolume:
                    provisioned.directories.commit()
                else:
                    provisioned.directories.rollback()
                raise
            provisioned.directories.commit()
            created_batches.append(provisioned.resources)

        combined = CreatedResources.combine(*created_batches)
        logger.info(
            "layout_synchronization_complete",
            created=[
                str(path)
                for path in (
                    *combined.directories,
                    *(item.path for item in combined.subvolumes),
                )
            ],
            skipped=skipped_paths,
        )
        return combined

    def _provision_path(self, path: Path) -> _ProvisionedPath:
        """Provision one path while keeping rollback evidence private."""
        directories = DirectoryProvisioning()
        attempt = _SubvolumeAttempt()
        try:
            if path in _BINDING_SITES:
                return self._provision_binding_site(path, directories)
            if path == PATH_POSTGRESS_DATA_DIR:
                return self._provision_postgres(path, directories, attempt)
            directories.create(path)
            logger.info("layout_directory_created", path=str(path))
            return self._provisioned_path(directories)
        except BaseException as exc:  # noqa: BLE001 - settle cancellation after filesystem effects
            self._settle_failed_provision(
                path=path,
                directories=directories,
                attempt=attempt,
                error=exc,
            )

    @staticmethod
    def _provision_binding_site(
        path: Path,
        directories: DirectoryProvisioning,
    ) -> _ProvisionedPath:
        """Create one private binding site."""
        directories.create(
            path,
            mode=PRIVATE_BINDING_SITE_MODE,
        )
        logger.info(
            "layout_binding_site_created",
            path=str(path),
            mode="0700",
        )
        return Layout._provisioned_path(directories)

    def _provision_postgres(
        self,
        path: Path,
        directories: DirectoryProvisioning,
        attempt: _SubvolumeAttempt,
    ) -> _ProvisionedPath:
        """Provision PostgreSQL storage with optional Btrfs specialization."""
        directories.create(path.parent)
        if raced := self._preserve_raced_path(path, directories):
            return raced
        with directories.pin(path.parent) as parent_fd:
            provisioned = self._create_postgres_subvolume(
                path,
                parent_fd=parent_fd,
                directories=directories,
                attempt=attempt,
            )
        if provisioned is not None:
            return provisioned
        if raced := self._preserve_raced_path(path, directories):
            return raced
        logger.info(
            "layout_btrfs_fallback",
            path=str(path),
            hint=(f"Using an ordinary directory; inspect optional Btrfs/No-COW preparation for {path}"),
        )
        directories.create(path)
        logger.info("layout_directory_created", path=str(path))
        return self._provisioned_path(directories)

    def _create_postgres_subvolume(
        self,
        path: Path,
        *,
        parent_fd: int,
        directories: DirectoryProvisioning,
        attempt: _SubvolumeAttempt,
    ) -> _ProvisionedPath | None:
        """Create, prepare, and bind one optional PostgreSQL subvolume."""
        attempt.in_flight = True
        subvolume = self.btrfs.create_subvolume(
            path,
            parent_fd=parent_fd,
        )
        if subvolume is not None:
            attempt.materialized = subvolume
        attempt.in_flight = False
        if subvolume is None:
            return None
        preparation = self.btrfs.prepare_created_subvolume(
            path,
            parent_fd=parent_fd,
            expected=subvolume,
        )
        attempt.created.append(
            CreatedBtrfsSubvolume(
                path=path,
                device=preparation.device,
                inode=preparation.inode,
                subvolume_uuid=subvolume.uuid,
                subvolume_id=subvolume.subvolume_id,
            )
        )
        if not preparation.nocow:
            logger.warning(
                "layout_db_subvolume_unoptimized",
                path=str(path),
            )
        return self._provisioned_path(
            directories,
            subvolumes=attempt.created,
        )

    @staticmethod
    def _preserve_raced_path(
        path: Path,
        directories: DirectoryProvisioning,
    ) -> _ProvisionedPath | None:
        """Preserve an entry that appeared after the initial absence check."""
        if not os.path.lexists(path):
            return None
        require_existing_directory(path)
        logger.info("layout_path_raced_preserved", path=str(path))
        return Layout._provisioned_path(directories)

    def _settle_failed_provision(
        self,
        *,
        path: Path,
        directories: DirectoryProvisioning,
        attempt: _SubvolumeAttempt,
        error: BaseException,
    ) -> NoReturn:
        """Retain possible subvolume substrate, otherwise roll back exactly."""
        retained = self._failure_requires_retention(
            path=path,
            attempt=attempt,
            error=error,
        )
        if retained:
            directories.commit()
        else:
            directories.rollback()
        if isinstance(error, BtrfsCreationError):
            terminal = find_terminal_interruption(error)
            if terminal is not None:
                outcome = "retained" if retained else "rolled back"
                terminal.add_note(
                    f"LychD init {outcome} the Btrfs target ancestry after "
                    f"{error.evidence.state.value} creation evidence at {path}."
                )
                raise terminal from None
        raise error

    def _failure_requires_retention(
        self,
        *,
        path: Path,
        attempt: _SubvolumeAttempt,
        error: BaseException,
    ) -> bool:
        """Classify whether automated directory rollback remains authorized."""
        if self._defer_created_subvolume_rollback(tuple(attempt.created)):
            return True
        if isinstance(error, BtrfsCreationError):
            if error.evidence.state is BtrfsCreationState.ABSENT:
                return False
            self._defer_creation_evidence(error.evidence)
            return True
        if attempt.in_flight:
            self._defer_indeterminate_creation(path)
            return True
        if attempt.materialized is not None:
            self._defer_unattested_subvolume_rollback(
                path,
                observation=attempt.materialized,
            )
            return True
        return False

    @staticmethod
    def _provisioned_path(
        directories: DirectoryProvisioning,
        *,
        subvolumes: list[CreatedBtrfsSubvolume] | None = None,
    ) -> _ProvisionedPath:
        """Build the public report without discarding private rollback tokens."""
        resources = created_resources(
            directories=directories.created_paths,
            directory_identities=directories.created_identities,
            subvolumes=() if subvolumes is None else subvolumes,
        )
        return _ProvisionedPath(
            resources=resources,
            directories=directories,
        )

    @staticmethod
    def _defer_created_subvolume_rollback(
        subvolumes: tuple[CreatedBtrfsSubvolume, ...],
    ) -> bool:
        """Emit exact recovery evidence and report whether substrate was retained."""
        for created in reversed(subvolumes):
            logger.error(
                "layout_created_subvolume_rollback_handoff_required",
                path=str(created.path),
                device=created.device,
                inode=created.inode,
                subvolume_uuid=created.subvolume_uuid,
                subvolume_id=created.subvolume_id,
                reason=(
                    "local preparation lacks the filesystem-attested selector "
                    "authority required for safe ID-based deletion"
                ),
                hint=(
                    "Re-attest the containing filesystem, then recover by this "
                    "subvolume ID; never delete the replaceable leaf pathname."
                ),
            )
        return bool(subvolumes)

    @staticmethod
    def _defer_unattested_subvolume_rollback(
        path: Path,
        *,
        observation: BtrfsSubvolumeObservation,
    ) -> None:
        """Retain a materialized subvolume whose kernel identity never converged."""
        logger.error(
            "layout_unattested_subvolume_rollback_handoff_required",
            path=str(path),
            subvolume_uuid=observation.uuid,
            subvolume_id=observation.subvolume_id,
            reason=("the created Btrfs identity could not be bound to the public pathname without drift"),
            hint=(
                "Inspect this UUID and subvolume ID through an attested Btrfs "
                "top-level mount; do not delete the replaceable pathname."
            ),
        )

    @staticmethod
    def _defer_creation_evidence(evidence: BtrfsCreationEvidence) -> None:
        """Log the exact pinned-leaf state retained after creation failure."""
        logger.error(
            "layout_btrfs_creation_rollback_handoff_required",
            path=str(evidence.path),
            creation_state=evidence.state.value,
            subvolume_uuid=(evidence.observation.uuid if evidence.observation is not None else None),
            subvolume_id=(evidence.observation.subvolume_id if evidence.observation is not None else None),
            reason=(
                "the Btrfs creation command may have materialized a target "
                "without enough identity authority for automatic rollback"
            ),
            hint=(
                "Inspect the retained target through an attested Btrfs top-level mount before retrying initialization."
            ),
        )

    @staticmethod
    def _defer_indeterminate_creation(path: Path) -> None:
        """Retain ancestry across the tiny return-to-assignment signal window."""
        logger.error(
            "layout_btrfs_creation_indeterminate_handoff_required",
            path=str(path),
            creation_state=BtrfsCreationState.INDETERMINATE.value,
            reason=(
                "execution was interrupted while subvolume creation was in "
                "flight, before its return value could be bound"
            ),
            hint="Inspect the retained target before retrying initialization.",
        )


LayoutService = Layout
