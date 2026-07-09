import os
import stat
from pathlib import Path

import structlog

from lychd.system.constants import PATH_REACTOR_INBOX_DIR

logger = structlog.get_logger()
_REGISTRY_MODE = 0o700


class PrivilegeService:
    """The Keeper of the Handshake.

    Responsible for establishing the security context and signaling registry.
    """

    def __init__(self, signals_dir: Path | None = None) -> None:
        """Initialize the Privilege Service.

        Args:
            signals_dir: Optional path for the handshakes registry.

        """
        self._signals_dir = signals_dir or PATH_REACTOR_INBOX_DIR

    def initialize(self) -> None:
        """Create the directory for Intent Handshakes.

        The Rite of Signaling.
        """
        if self._signals_dir.is_symlink():
            message = f"Privilege intent registry must not be a symlink: {self._signals_dir}"
            raise RuntimeError(message)
        if self._signals_dir.exists() and not self._signals_dir.is_dir():
            message = f"Privilege intent registry is not a directory: {self._signals_dir}"
            raise RuntimeError(message)
        if not self._signals_dir.exists():
            logger.info("registry_created", path=str(self._signals_dir))
            self._signals_dir.mkdir(parents=True, mode=_REGISTRY_MODE, exist_ok=False)
        else:
            logger.debug("registry_exists", path=str(self._signals_dir))
        self._signals_dir.chmod(_REGISTRY_MODE)
        metadata = self._signals_dir.stat()
        if metadata.st_uid != os.getuid():
            message = (
                f"Privilege intent registry must be owned by uid {os.getuid()}; "
                f"found uid {metadata.st_uid}: {self._signals_dir}"
            )
            raise RuntimeError(message)
        mode = stat.S_IMODE(metadata.st_mode)
        if mode != _REGISTRY_MODE:
            message = f"Privilege intent registry mode is {oct(mode)}, expected 0o700: {self._signals_dir}"
            raise RuntimeError(message)


def initialize_registry(signals_dir: Path | None = None) -> None:
    """Legacy wrapper for the Signaling Ritual."""
    PrivilegeService(signals_dir).initialize()
