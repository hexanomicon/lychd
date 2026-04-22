from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from lychd.domain.animation.schemas import Animator, Portal, Soulstone
from lychd.domain.animation.services.loader import AnimatorLoader

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = structlog.get_logger()


class AnimatorRegistry:
    """The Memory Bank.

    Holds the live state of all discovered inhabitants (Soulstones and Portals).
    Acts as the source of truth for the Dispatcher.

    Architecture Note:
    This class employs "Atomic Reference Swapping" for reloading.
    Reads are lock-free. Writes replace the entire dictionary reference,
    ensuring that a 'get' operation never sees an empty or partial state.
    """

    def __init__(self, loader: AnimatorLoader | None = None) -> None:
        """Initialize the Registry.

        Args:
            loader: The Librarian instance. If None, a default one is created.

        """
        self._loader = loader or AnimatorLoader()

        # Primary Indices (Name -> Entity)
        self._soulstones: dict[str, Soulstone] = {}
        self._portals: dict[str, Portal] = {}

        # Secondary Indices (Group -> List[Entity])
        self._groups: dict[str, list[Soulstone]] = {}

        self._loaded: bool = False

    def load(self) -> None:
        """Perform the Awakening Ritual.

        Reads the Codex via the Loader and populates the in-memory registry.
        Can be called repeatedly to Hot-Reload configurations safely.
        """
        # 1. Load fresh data into isolated scope
        # (This is the slow IO part, done before touching live state)
        raw_soulstones, raw_portals = self._loader.load_all()

        # 2. Build new indices
        new_soulstones: dict[str, Soulstone] = {s.name: s for s in raw_soulstones}
        new_portals: dict[str, Portal] = {p.name: p for p in raw_portals}
        new_groups: dict[str, list[Soulstone]] = {}

        # Build Group Index
        for s in raw_soulstones:
            for group in s.groups:
                if group not in new_groups:
                    new_groups[group] = []
                new_groups[group].append(s)

        # 3. Atomic Swap (The "Gil" Switch)
        # Replacing the dict reference is atomic in Python.
        # Readers will either see the old world or the new world, never a partial world.
        self._soulstones = new_soulstones
        self._portals = new_portals
        self._groups = new_groups
        self._loaded = True

        logger.info(
            "registry_loaded",
            soulstones=len(self._soulstones),
            portals=len(self._portals),
            groups=list(self._groups.keys()),
        )

    def get(self, name: str) -> Animator | None:
        """Find any inhabitant by name (Polymorphic)."""
        if not self._loaded:
            self.load()
        # Check Soulstones first (Local power is preferred), then Portals
        return self._soulstones.get(name) or self._portals.get(name)

    def get_soulstone(self, name: str) -> Soulstone | None:
        """Find a local Soulstone by name."""
        if not self._loaded:
            self.load()
        return self._soulstones.get(name)

    def get_portal(self, name: str) -> Portal | None:
        """Find a cloud Portal by name."""
        if not self._loaded:
            self.load()
        return self._portals.get(name)

    def get_group(self, group_name: str) -> Sequence[Soulstone]:
        """Find all Soulstones belonging to a specific Coven (Group)."""
        if not self._loaded:
            self.load()
        return self._groups.get(group_name, [])

    def list_all(self) -> list[Animator]:
        """Return all inhabitants."""
        if not self._loaded:
            self.load()
        # Create a new list to avoid leaking internal mutable state
        return [*self._soulstones.values(), *self._portals.values()]

    @property
    def is_loaded(self) -> bool:
        """Check if the registry has been initialized."""
        return self._loaded
