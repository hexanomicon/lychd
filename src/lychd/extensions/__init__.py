"""Public reexports for the extension package.

Re-exports are resolved lazily via module ``__getattr__`` instead of eager top
level imports. The eager form created an import cycle between
``lychd.extensions`` and ``lychd.config.runes``: while
``lychd.config.runes.extension`` initialized it pulled ``lychd.extensions.base``
 whose package init re-entered ``lychd.config.runes.extension`` for
``RuneConfigStore`` before that symbol existed. The lazy form lets the rune
extension finish initializing first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lychd.config.runes.extension import RuneConfigStore
    from lychd.domain.animation.extension import PortalStore, SoulstoneStore
    from lychd.extensions.base import ExtensionStore
    from lychd.extensions.context import ExtensionContext, VesselStore

_LAZY_REEXPORTS: dict[str, str] = {
    "ExtensionContext": "lychd.extensions.context",
    "ExtensionStore": "lychd.extensions.base",
    "PortalStore": "lychd.domain.animation.extension",
    "RuneConfigStore": "lychd.config.runes.extension",
    "SoulstoneStore": "lychd.domain.animation.extension",
    "VesselStore": "lychd.extensions.context",
}


def __getattr__(name: str) -> object:
    """Resolve a lazily reexported name on first attribute access."""
    target = _LAZY_REEXPORTS.get(name)
    if target is None:
        msg = f"module 'lychd.extensions' has no attribute {name!r}"
        raise AttributeError(msg)
    import importlib

    value = getattr(importlib.import_module(target), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(_LAZY_REEXPORTS).union(globals()))


__all__ = [
    "ExtensionContext",
    "ExtensionStore",
    "PortalStore",
    "RuneConfigStore",
    "SoulstoneStore",
    "VesselStore",
]
