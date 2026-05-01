from __future__ import annotations

import shutil
from pathlib import Path

import structlog

from lychd.system.services.btrfs import Btrfs

logger = structlog.get_logger()


class Layout:
    """Orchestrate the application's filesystem layout and state."""

    def __init__(self) -> None:
        self.btrfs = Btrfs()

    def provision_storage(self, path: Path) -> None:
        """Provision a storage path, prioritizing Btrfs No-COW optimization.

        Args:
            path (Path): Target path to provision.

        """
        # Try the Subvolume Ritual first
        if self.btrfs.create_subvolume(path):
            if not self.btrfs.apply_no_cow(path):
                # The subvolume exists, but No-COW failed (e.g., non-empty or unsupported)
                logger.warning("storage_subvolume_unoptimized", path=str(path))
        else:
            # The subvolume failed entirely (e.g., non-Btrfs FS, missing binaries).
            # Fallback to standard directory creation.
            path.mkdir(parents=True, exist_ok=True)
            logger.info("fallback_standard_directory_provisioned", path=str(path))

    def teardown_storage(self, path: Path) -> None:
        """Safely dismantle a storage path, respecting kernel-level boundaries.

        Args:
            path (Path): Target path to remove.

        """
        if not path.exists():
            logger.debug("teardown_skipped_path_not_found", path=str(path))
            return

        # Routing logic: Kernel subvolume vs User directory
        if self.btrfs.is_subvolume(path):
            # Attempt subvolume destruction.
            # If this hits an EPERM, the Btrfs primitive will internally log the
            # exact 'sudo btrfs subvolume delete <path>' instruction as CRITICAL.
            if not self.btrfs.delete_subvolume(path):
                logger.critical(
                    "layout_teardown_blocked_by_kernel",
                    path=str(path),
                    detail="Subvolume must be removed manually before teardown can complete.",
                )
        else:
            # It's a standard directory; safe for rmtree
            try:
                shutil.rmtree(path)
            except OSError as e:
                logger.critical("layout_rmtree_failed", path=str(path), error=str(e))
            else:
                logger.info("layout_directory_removed", path=str(path))
