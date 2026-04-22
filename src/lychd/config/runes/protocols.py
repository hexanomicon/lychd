"""Typing protocols for runtime objects that compose rune configs."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lychd.config.runes.base import RuneConfig


@runtime_checkable
class Runic[T: RuneConfig](Protocol):
    """Composition contract for runtime objects backed by a rune config.

    The ``rune`` reference is intended to be a construction-time invariant:
    runtime objects may derive effective state from it, but should not replace it
    after initialization. Concrete implementations should expose ``rune`` as a
    read-only property and back it with ``_rune: Final[T]`` when practical.
    """

    @property
    def rune(self) -> T:
        """Return the owned source rune config (read-only provenance handle)."""
        ...
