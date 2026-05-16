"""Typing protocols for objects that retain rune provenance."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lychd.config.runes.base import RuneConfig


@runtime_checkable
class Runic[T: RuneConfig](Protocol):
    """Protocol for objects configured by a Codex Rune.

    Any runtime object with ``rune: T`` satisfies this protocol structurally.
    Such objects are servants of the Codex: they retain the validated config
    that shaped them, but they are not themselves rune schemas.
    """

    @property
    def rune(self) -> T:
        """Return the validated source Rune.

        Returns:
            The ``RuneConfig`` instance used as this object's configuration
            provenance.

        """
        ...
