from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import structlog

from lychd.system.constants import HOST_LAYOUT, PATH_CRYPT_ROOT, PATH_POSTGRES_DIR

logger = structlog.get_logger()


class LayoutService:
    """The Architect of the Physical Body.

    Responsible for:
    - Establishing the XDG directory structure (The Trinity).
    - Optimistic Btrfs subvolume and No-COW optimizations.
    """

    def __init__(self, layout: list[Path] | None = None) -> None:
        """Initialize the Layout Service."""
        self._layout = layout or HOST_LAYOUT

    def initialize(self) -> None:
        """Establish the Physical Body.

        Rite of Folder Genesis and Speculative Btrfs optimization.
        """
        is_btrfs = self._is_btrfs(PATH_CRYPT_ROOT)

        # 1. Folder Genesis
        for path in self._layout:
            # Skip postgres dir if we are going to handle it via btrfs ritual
            if is_btrfs and path == PATH_POSTGRES_DIR:
                continue

            # We only mkdir for directories (paths without a suffix)
            if not path.exists() and not path.suffix:
                logger.info("creating_directory", path=str(path))
                path.mkdir(parents=True, exist_ok=True)
            elif not path.exists():
                logger.debug("skipping_file_creation", path=str(path))
            else:
                logger.debug("directory_exists", path=str(path))

        # 2. Speculative Genesis (Btrfs)
        self._apply_btrfs_rituals(is_btrfs=is_btrfs)

    def _apply_btrfs_rituals(self, *, is_btrfs: bool) -> None:
        """Apply Btrfs optimizations if applicable.

        Optimistically attempts subvolume creation and No-COW.
        """
        if not is_btrfs:
            logger.debug("btrfs_not_detected", skipping="speculative_genesis")
            return

        logger.info("btrfs_detected", root=str(PATH_CRYPT_ROOT))

        # Ensure POSTGRES_ROOT is a subvolume
        if not PATH_POSTGRES_DIR.exists():
            # Ensure parent exists (we skipped it in the loop if it was PATH_POSTGRES_DIR
            # but usually it's nested in CRYPT_ROOT which was created)
            PATH_POSTGRES_DIR.parent.mkdir(parents=True, exist_ok=True)
            btrfs_path = shutil.which("btrfs")
            if btrfs_path:
                try:
                    subprocess.run(  # noqa: S603
                        [btrfs_path, "subvolume", "create", str(PATH_POSTGRES_DIR)],
                        check=True,
                        capture_output=True,
                    )
                    logger.info("btrfs_subvolume_created", path=str(PATH_POSTGRES_DIR))
                except (subprocess.CalledProcessError, OSError):
                    logger.warning("btrfs_subvolume_failed_falling_back_to_mkdir")
                    PATH_POSTGRES_DIR.mkdir(parents=True, exist_ok=True)
            else:
                PATH_POSTGRES_DIR.mkdir(parents=True, exist_ok=True)

        # Apply No_COW (+C)
        chattr_path = shutil.which("chattr")
        if chattr_path:
            try:
                subprocess.run([chattr_path, "+C", str(PATH_POSTGRES_DIR)], check=False)  # noqa: S603
                logger.info("btrfs_nocow_applied", path=str(PATH_POSTGRES_DIR))
            except (subprocess.SubprocessError, OSError):
                logger.debug("btrfs_nocow_failed")

    def _is_btrfs(self, path: Path) -> bool:
        """Check if path is on a Btrfs filesystem."""
        df_path = shutil.which("df")
        if not df_path:
            return False

        # Walk up to find an existing parent
        check_path = path
        while not check_path.exists() and check_path != check_path.parent:
            check_path = check_path.parent

        try:
            output = subprocess.check_output(  # noqa: S603
                [df_path, "--output=fstype", str(check_path)],
                text=True,
            ).splitlines()
            return len(output) > 1 and "btrfs" in output[1]
        except (subprocess.SubprocessError, OSError):
            return False


def initialize_layout() -> None:
    LayoutService().initialize()
