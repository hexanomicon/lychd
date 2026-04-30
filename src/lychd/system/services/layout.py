from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import structlog

from lychd.system.constants import HOST_LAYOUT, PATH_CRYPT_ROOT, PATH_POSTGRES_DIR

logger = structlog.get_logger()


class LayoutService:
    """Directory management.

    Responsibilities:
    - Initialize the XDG directory structure (The Trinity CONFIG, DATA, CACHE encoded in ../constants).
    - Optimistic Btrfs subvolume and No-COW optimizatio TODO
    """

    def __init__(self, layout: list[Path] | None = None) -> None:
        """If Linux and Btrfs present, Initialize the Layout Service, otherwise fail."""
        # Perform checks
        _error_linux_absent = "The operating system is not linux. layout service is not implemented,"
        _error_btrfs_root_absent = "The file system is not btrfs. layout service is not implemented,"

        # TODO: Support other systems as part of Thralls in ADR42 or as native Vessels perhaps?
        # Confirm we are on linux Just In case
        self.is_linux: bool = sys.platform == "linux"
        if not self.is_linux:
            logger.error("linux_not_detected", skipping="speculative_genesis")
            raise NotImplementedError(_error_linux_absent)

        # TODO: Make special implementation for other filesystems later and allow going further here
        self.is_root_btrfs: bool = self._is_btrfs(Path("/"))
        if not self.is_root_btrfs:
            logger.error("btrfs_not_detected", skipping="speculative_genesis")

            raise NotImplementedError(_error_btrfs_root_absent)

        # Create dirs:

        _layout_cow_mod: list[Path] = layout or HOST_LAYOUT

        # Remove the btrfs CoW sensitive directory for pg db from the list of dirs to be created
        _layout_cow_mod.remove(PATH_POSTGRES_DIR)

        # Create all the dirs just normally
        for path in _layout_cow_mod:
            if not path.exists():
                logger.info("creating_directory", path=str(path))

                if path != PATH_POSTGRES_DIR:
                    path.mkdir(parents=True, exist_ok=False)
                else:
                    path.mkdir(parents=True, exist_ok=False)

            else:
                logger.debug("directory_exists_skipping_creation_check", path=str(path))

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
        _error_path_doesnt_exist = "Entered path doesnt exist on the system"
        if not path.exists():
            raise ValueError(_error_path_doesnt_exist)

        df_path = shutil.which("df")
        if not df_path:
            return False

        # Walk up to find an existing parent
        # So pointing even to ~/anything will give us ~ what is
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
