from __future__ import annotations


class ExtensionStore:
    """Mutable during assembly, read-only after the composition root seals it."""

    def __init__(self) -> None:
        """Create an open registration store."""
        self._frozen = False

    def freeze(self) -> None:
        """Seal the store after the one sanctioned registration pass."""
        self._frozen = True

    def _require_mutable(self) -> None:
        if getattr(self, "_frozen", False):
            msg = f"{type(self).__name__} is frozen after extension assembly."
            raise RuntimeError(msg)
