from __future__ import annotations

import shutil
from pathlib import Path
from typing import Final

import structlog

from lychd.system.constants import (
    HOST_LAYOUT,
    PATH_POSTGRESS_DATA_DIR,
)
from lychd.system.services.btrfs import Btrfs

logger = structlog.get_logger()


class Layout:
    """Orchestrate the host physical directory architecture and lifecycles."""

    def __init__(self, paths: tuple[Path, ...] | None = None) -> None:
        """Initialize the layout orchestrator with defined architectural paths.

        Args:
            paths: System directories to manage. Defaults to HOST_LAYOUT constant.

        """
        # Strictly check for None so an empty tuple () can be respected if passed.
        self.paths: Final[tuple[Path, ...]] = HOST_LAYOUT if paths is None else paths
        self.btrfs: Final[Btrfs] = Btrfs()

    def mkdirs(self) -> None:
        """Synchronize the physical layout with the system blueprint."""
        created_paths: list[str] = []
        skipped_paths: list[str] = []

        for path in self.paths:
            if path.exists():
                logger.debug("layout_path_exists_skipped", path=str(path))
                skipped_paths.append(str(path))
                continue

            if self._provision_path(path):
                created_paths.append(str(path))

        # Single summary log at the end, perfect for JSON and CLI rendering
        logger.info(
            "layout_synchronization_complete",
            created=created_paths,
            skipped=skipped_paths,
        )

    def teardown(self) -> None:
        """Erase the physical layout with Btrfs safety boundaries."""
        # Reverse iteration ensures we clean children before parents if nested
        for path in reversed(self.paths):
            if not path.exists():
                logger.debug("layout_teardown_skipped_not_found", path=str(path))
                continue

            # The Routing Logic: Kernel Subvolume vs User Directory
            if self.btrfs.is_subvolume(path):
                if not self.btrfs.delete_subvolume(path):
                    logger.critical(
                        "layout_teardown_blocked_by_kernel",
                        path=str(path),
                        detail="Subvolume must be removed manually.",
                        instruction=f"sudo btrfs subvolume delete {path}",
                    )
                continue

            # Standard Deletion Fallback
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except OSError as e:
                logger.critical("layout_teardown_failed", path=str(path), error=str(e))
            else:
                logger.info("layout_path_removed", path=str(path))

    def _provision_path(self, path: Path) -> bool:
        """Provision a specific path, applying filesystem optimizations if targeted.

        Args:
            path: The directory path to provision.

        Returns:
            bool: True if the path was successfully created.

        """
        # Specialized Provisioning: Postgres Data Subvolume
        if path == PATH_POSTGRESS_DATA_DIR:
            if self.btrfs.create_subvolume(path):
                if not self.btrfs.apply_no_cow(path):
                    logger.warning("layout_db_subvolume_unoptimized", path=str(path))
                return True

            # If Btrfs ritual fails completely, log the fallback hint
            logger.info(
                "layout_btrfs_fallback",
                path=str(path),
                hint=f"For optimal DB performance, manually create a No-COW Btrfs subvolume at: {path}",
            )

        # Standard Provisioning (or Fallback from Btrfs failure)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.critical("layout_mkdir_failed", path=str(path), error=str(e))
            return False
        else:
            logger.info("layout_directory_created", path=str(path))
            return True
