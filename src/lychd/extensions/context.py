from __future__ import annotations

from lychd.config.runes.extension import RuneConfigStore
from lychd.domain.animation.extension import PortalStore, SoulstoneStore
from lychd.extensions.base import ExtensionStore


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
        self.runes = RuneConfigStore()
        self.soulstones = SoulstoneStore(self.runes)
        self.portals = PortalStore()
        self.vessel = VesselStore()
