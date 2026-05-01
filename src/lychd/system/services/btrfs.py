from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from typing import Final

import structlog

logger = structlog.get_logger()


class Btrfs:
    """Orchestrate filesystem-level optimizations using standard Linux tools."""

    def __init__(self) -> None:
        """Probe for required system binaries without side effects."""
        self.btrfs_bin: Final[str | None] = shutil.which("btrfs")
        self.chattr_bin: Final[str | None] = shutil.which("chattr")
        self.lsattr_bin: Final[str | None] = shutil.which("lsattr")

    def create_subvolume(self, path: Path) -> bool:
        """Create a Btrfs subvolume at the target path, including parents.

        Args:
            path (Path): Path to create the subvolume.

        Returns:
            bool: True if created successfully or already exists as a subvolume.

        """
        if not self.btrfs_bin:
            logger.critical("btrfs_bin_missing", path=str(path))
            return False

        if self.is_subvolume(path):
            logger.debug("btrfs_subvolume_exists", path=str(path))
            return True

        if path.exists():
            logger.critical("btrfs_subvolume_path_blocked", path=str(path))
            return False

        # Defensive parent creation
        try:
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                logger.info("btrfs_parent_path_provisioned", path=str(path.parent))
        except OSError:
            logger.critical("btrfs_parent_mkdir_failed", path=str(path.parent))
            return False  # Early exit required here so we don't try subvol creation

        try:
            subprocess.run(  # noqa: S603
                [self.btrfs_bin, "subvolume", "create", str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except (subprocess.CalledProcessError, OSError):
            logger.critical("btrfs_subvolume_failed", path=str(path))
        else:
            # Trust but Verify
            if self.is_subvolume(path):
                logger.info("btrfs_subvolume_created", path=str(path))
                return True

            logger.critical("btrfs_subvolume_verification_failed", path=str(path))

        # Unified failure exit
        return False

    def apply_no_cow(self, path: Path) -> bool:
        """Apply the No-COW policy to an empty directory.

        Args:
            path (Path): Target path for optimization.

        Returns:
            bool: True if policy is active or successfully applied.

        """
        if not self.chattr_bin or not self.lsattr_bin:
            logger.critical("attr_bins_missing", path=str(path))
            return False

        if self.is_nocow(path):
            return True

        if any(path.iterdir()):
            logger.warning("nocow_skipped_not_empty", path=str(path))
            return False

        try:
            subprocess.run([self.chattr_bin, "+C", str(path)], check=True)  # noqa: S603
        except (subprocess.CalledProcessError, OSError):
            logger.debug("nocow_unsupported", path=str(path))
        else:
            # Trust but Verify
            if self.is_nocow(path):
                logger.info("nocow_applied", path=str(path))
                return True

            logger.critical("nocow_verification_failed", path=str(path))

        # Unified failure exit
        return False

    def delete_subvolume(self, path: Path) -> bool:
        """Execute the Destruction Ritual for a subvolume.

        Args:
            path (Path): Subvolume path to remove.

        Returns:
            bool: True if successfully deleted.

        """
        if not self.btrfs_bin or not self.is_subvolume(path):
            return False

        try:
            subprocess.run(  # noqa: S603
                [self.btrfs_bin, "subvolume", "delete", str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            if "Operation not permitted" in e.stderr:
                logger.critical(
                    "btrfs_delete_denied",
                    path=str(path),
                    instruction=f"Run: 'sudo btrfs subvolume delete {path}'",
                )
            else:
                logger.critical("btrfs_delete_failed", path=str(path))
        except OSError:
            logger.critical("btrfs_delete_oserror", path=str(path))
        else:
            logger.info("btrfs_subvolume_deleted", path=str(path))
            return True

        # Unified failure exit
        return False

    def is_subvolume(self, path: Path) -> bool:
        """Check if a path is a Btrfs subvolume via Inode 2/256."""
        try:
            return path.exists() and path.stat().st_ino in {2, 256}
        except OSError:
            return False

    def is_nocow(self, path: Path) -> bool:
        """Check if the No-COW attribute (+C) is active via lsattr."""
        if not self.lsattr_bin or not path.exists():
            return False
        try:
            res: CompletedProcess[str] = subprocess.run(  # noqa: S603
                [self.lsattr_bin, "-d", str(path)], capture_output=True, text=True, check=True
            )
        except (subprocess.CalledProcessError, OSError, IndexError):
            return False
        else:
            return "C" in res.stdout.split()[0]
