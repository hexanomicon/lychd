from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import RuneConfig
from .protocols import Runic

if TYPE_CHECKING:
    from .extension import RuneConfigStore
    from .loader import ConfigLoader
    from .writer import ConfigWriter

__all__ = [
    "ConfigLoader",
    "ConfigWriter",
    "RuneConfig",
    "RuneConfigStore",
    "Runic",
]


def __getattr__(name: str) -> Any:
    """Load Rune infrastructure only when its compatibility export is requested."""
    if name == "ConfigLoader":
        from .loader import ConfigLoader

        return ConfigLoader
    if name == "ConfigWriter":
        from .writer import ConfigWriter

        return ConfigWriter
    if name == "RuneConfigStore":
        from .extension import RuneConfigStore

        return RuneConfigStore
    raise AttributeError(name)
