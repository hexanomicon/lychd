import os
import stat
from collections.abc import Callable
from pathlib import Path

import structlog

from lychd.system.services.file_publication_transaction import JournaledCreation
from lychd.system.services.lifecycle.models import CreatedResources

logger = structlog.get_logger()
_REGISTRY_MODE = 0o700


class PrivilegeService:
    """The Keeper of the Handshake.

    Responsible for establishing the security context and signaling registry.
    """

    def __init__(self, signals_dir: Path) -> None:
        """Bind the exact handshakes registry managed by this service."""
        self._signals_dir = signals_dir

    def initialize(
        self,
        *,
        on_created: Callable[[CreatedResources], None] | None = None,
    ) -> CreatedResources:
        """Create the directory for Intent Handshakes.

        The Rite of Signaling.

        Args:
            on_created: Optional durable journal invoked after successful creation.

        """
        creation = JournaledCreation(on_created=on_created)
        resources = creation.create_directory(
            self._signals_dir,
            mode=_REGISTRY_MODE,
            validate=self._validate_registry,
        )
        if resources.directories:
            logger.info(
                "registry_created",
                paths=[str(path) for path in resources.directories],
            )
        else:
            logger.debug("registry_exists", path=str(self._signals_dir))
        return resources

    @staticmethod
    def _validate_registry(descriptor: int, path: Path) -> None:
        """Require current-user ownership and exact mode on the pinned directory."""
        metadata = os.fstat(descriptor)
        if metadata.st_uid != os.getuid():
            message = (
                f"Privilege intent registry must be owned by uid {os.getuid()}; found uid {metadata.st_uid}: {path}"
            )
            raise RuntimeError(message)
        mode = stat.S_IMODE(metadata.st_mode)
        if mode != _REGISTRY_MODE:
            message = f"Privilege intent registry mode is {oct(mode)}, expected 0o700: {path}"
            raise RuntimeError(message)
