from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from lychd.config.runes.extension import RuneConfigStore
from lychd.domain.animation.extension import PortalStore, SoulstoneStore
from lychd.extensions.base import ExtensionStore

if TYPE_CHECKING:
    from collections.abc import Iterator


class VesselStore(ExtensionStore):
    """Reserved store for web/API contributions.

    Keep this intentionally empty until route, middleware, auth, and event-hook
    bundles have a stable shape. The important boundary is that Vessel
    registration is not flattened onto ExtensionContext.
    """

    # Future shape, deliberately not active yet: HTTP routes, middleware,
    # event hooks, and auth policies should arrive as shaped sub-stores/bundles.


class ExtensionContext:
    """Host-provided root of explicit extension registration stores."""

    def __init__(self) -> None:
        """Create the extension registration stores for one assembly pass."""
        self._current_extension_id: str | None = None
        self.runes = RuneConfigStore()
        self.soulstones = SoulstoneStore(self.runes)
        self.portals = PortalStore()
        self.vessel = VesselStore()

    @contextmanager
    def provenance(self, extension_id: str) -> Iterator[None]:
        """Manager-only: attribute registrations inside the block to ``extension_id``."""
        previous = self._current_extension_id
        self._current_extension_id = extension_id
        try:
            yield
        finally:
            self._current_extension_id = previous

    @property
    def current_extension_id(self) -> str:
        """The extension whose ``register()`` is executing.

        Raises:
            RuntimeError: If accessed outside a ``provenance`` block.

        """
        if self._current_extension_id is None:
            msg = "current_extension_id is only defined inside an ExtensionContext.provenance(...) block."
            raise RuntimeError(msg)
        return self._current_extension_id
