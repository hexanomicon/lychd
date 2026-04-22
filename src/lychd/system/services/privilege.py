from pathlib import Path

import structlog

from lychd.system.constants import PATH_TRIGGERS_DIR

logger = structlog.get_logger()


class PrivilegeService:
    """The Keeper of the Handshake.

    Responsible for establishing the security context and signaling registry.
    """

    def __init__(self, signals_dir: Path | None = None) -> None:
        """Initialize the Privilege Service.

        Args:
            signals_dir: Optional path for the handshakes registry.

        """
        self._signals_dir = signals_dir or PATH_TRIGGERS_DIR

    def initialize(self) -> None:
        """Create the directory for Intent Handshakes.

        The Rite of Signaling.
        """
        if not self._signals_dir.exists():
            logger.info("registry_created", path=str(self._signals_dir))
            self._signals_dir.mkdir(parents=True, exist_ok=True)
        else:
            logger.debug("registry_exists", path=str(self._signals_dir))


def initialize_registry(signals_dir: Path | None = None) -> None:
    """Legacy wrapper for the Signaling Ritual."""
    PrivilegeService(signals_dir).initialize()
