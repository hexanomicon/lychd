"""Journal-aware creation of the initialization filesystem geography."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Final

import structlog

from lychd.system.constants import (
    HOST_LAYOUT,
    PATH_POSTGRESS_DATA_DIR,
)
from lychd.system.services.btrfs import Btrfs
from lychd.system.services.lifecycle import CreatedResources, created_resources

logger = structlog.get_logger()


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
        created_paths: list[Path] = []
        skipped_paths: list[str] = []

        for path in self.paths:
            if os.path.lexists(path):
                self._validate_existing_directory(path)
                logger.debug("layout_path_exists_skipped", path=str(path))
                skipped_paths.append(str(path))
                continue

            missing = self._missing_path_chain(path)
            try:
                created = self._provision_path(path)
                resources = created_resources(directories=created)
                if on_created is not None:
                    on_created(resources)
            except BaseException:
                self._rollback_empty_directories(missing)
                raise
            created_paths.extend(created)

        logger.info(
            "layout_synchronization_complete",
            created=[str(path) for path in created_paths],
            skipped=skipped_paths,
        )
        return created_resources(directories=created_paths)

    @staticmethod
    def _validate_existing_directory(path: Path) -> None:
        """Fail closed when a managed layout path is not a safe user directory."""
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            msg = f"Managed layout path must be a real directory: {path}"
            raise RuntimeError(msg)
        if metadata.st_uid != os.getuid():
            msg = f"Managed layout path must be owned by uid {os.getuid()}: {path}"
            raise RuntimeError(msg)

    def _provision_path(self, path: Path) -> tuple[Path, ...]:
        """Provision a specific path, applying filesystem optimizations if targeted.

        Args:
            path: The directory path to provision.

        Returns:
            Every directory created while provisioning the target, shallowest first.

        """
        missing = self._missing_path_chain(path)
        if path == PATH_POSTGRESS_DATA_DIR:
            if self.btrfs.create_subvolume(path):
                if not self.btrfs.apply_no_cow(path):
                    logger.warning("layout_db_subvolume_unoptimized", path=str(path))
                return missing

            logger.info(
                "layout_btrfs_fallback",
                path=str(path),
                hint=f"Using an ordinary directory; inspect optional Btrfs/No-COW preparation for {path}",
            )

        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            msg = f"Could not create managed layout directory {path}: {e}"
            raise RuntimeError(msg) from e
        else:
            logger.info("layout_directory_created", path=str(path))
            return missing

    @staticmethod
    def _missing_path_chain(path: Path) -> tuple[Path, ...]:
        """Return missing ancestors that ``mkdir(parents=True)`` will create."""
        missing: list[Path] = []
        current = path
        while current != current.parent and not os.path.lexists(current):
            missing.append(current)
            current = current.parent
        return tuple(reversed(missing))

    @staticmethod
    def _rollback_empty_directories(paths: tuple[Path, ...]) -> None:
        """Best-effort rollback for directories materialized by one failed step."""
        for path in reversed(paths):
            try:
                path.rmdir()
            except OSError:
                continue


LayoutService = Layout
