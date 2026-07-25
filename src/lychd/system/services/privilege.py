import os
import stat
from collections.abc import Callable
from pathlib import Path

import structlog

from lychd.system.constants import PATH_REACTOR_INBOX_DIR
from lychd.system.services.lifecycle import CreatedResources, created_resources

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
        self._validate_path_shape()
        created_paths = self._create_missing()
        try:
            self._validate_registry()
            resources = created_resources(directories=created_paths)
            if on_created is not None:
                on_created(resources)
        except BaseException:
            self._rollback_empty(created_paths)
            raise
        return resources

    def _validate_path_shape(self) -> None:
        """Reject an existing leaf that is not a real directory."""
        if self._signals_dir.is_symlink():
            message = f"Privilege intent registry must not be a symlink: {self._signals_dir}"
            raise RuntimeError(message)
        if self._signals_dir.exists() and not self._signals_dir.is_dir():
            message = f"Privilege intent registry is not a directory: {self._signals_dir}"
            raise RuntimeError(message)

    def _create_missing(self) -> tuple[Path, ...]:
        """Create an absent registry chain privately, rolling it back on failure."""
        if self._signals_dir.exists():
            logger.debug("registry_exists", path=str(self._signals_dir))
            return ()
        logger.info("registry_created", path=str(self._signals_dir))
        created_paths: list[Path] = []
        try:
            for path in self._missing_path_chain(self._signals_dir):
                path.mkdir(mode=_REGISTRY_MODE, exist_ok=False)
                created_paths.append(path)
        except BaseException:
            self._rollback_empty(created_paths)
            raise
        return tuple(created_paths)

    def _validate_registry(self) -> None:
        """Require current-user ownership and the exact private mode."""
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

    @staticmethod
    def _missing_path_chain(path: Path) -> tuple[Path, ...]:
        """Return every absent parent the registry creation will materialize."""
        missing: list[Path] = []
        current = path
        while current != current.parent and not os.path.lexists(current):
            missing.append(current)
            current = current.parent
        return tuple(reversed(missing))

    @staticmethod
    def _rollback_empty(paths: list[Path] | tuple[Path, ...]) -> None:
        """Best-effort removal of only the exact empty directories just created."""
        for path in reversed(paths):
            try:
                path.rmdir()
            except OSError:
                continue


def initialize_registry(signals_dir: Path | None = None) -> None:
    """Legacy wrapper for the Signaling Ritual."""
    PrivilegeService(signals_dir).initialize()
