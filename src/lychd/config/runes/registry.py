"""Validated rune instances loaded once per process."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from lychd.config.runes.base import RuneConfig
from lychd.config.runes.loader import ConfigLoader
from lychd.config.runes.protocols import PortReserver

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from lychd.extensions.host import AssembledExtensions

R = TypeVar("R", bound=RuneConfig)


class RuneRegistry:
    """Immutable set of validated rune instances from one ``ConfigLoader`` pass."""

    def __init__(self, runes: Sequence[RuneConfig]) -> None:
        """Store the validated rune instances for typed access."""
        self._runes: tuple[RuneConfig, ...] = tuple(runes)

    def all(self) -> tuple[RuneConfig, ...]:
        """All loaded rune instances."""
        return self._runes

    def of(self, schema: type[R]) -> tuple[R, ...]:
        """Instances that are (subclass) instances of ``schema``."""
        return tuple(rune for rune in self._runes if isinstance(rune, schema))

    def one(self, schema: type[R]) -> R:
        """Return the single instance of ``schema``.

        Raises:
            ValueError: If zero or more than one instance is present (loudly,
                naming the schema and the count).

        """
        matches = self.of(schema)
        if len(matches) != 1:
            msg = f"Expected exactly one '{schema.__name__}' rune, found {len(matches)}."
            raise ValueError(msg)
        return matches[0]

    def one_or_none(self, schema: type[R]) -> R | None:
        """Return the single instance of ``schema``, or None if absent.

        Raises:
            ValueError: If more than one instance is present.

        """
        matches = self.of(schema)
        if len(matches) > 1:
            msg = f"Expected at most one '{schema.__name__}' rune, found {len(matches)}."
            raise ValueError(msg)
        return matches[0] if matches else None

    def reserved_ports(self) -> dict[str, int]:
        """Merge port claims from every rune implementing ``PortReserver``.

        Raises:
            ValueError: If two rune port claims collide on the same port.

        """
        merged: dict[str, int] = {}
        seen: dict[int, str] = {}
        for rune in self._runes:
            if not isinstance(rune, PortReserver):
                continue
            for label, port in rune.reserved_ports().items():
                if port in seen and seen[port] != label:
                    msg = f"Port {port} is claimed by both '{seen[port]}' and '{label}'."
                    raise ValueError(msg)
                seen[port] = label
                merged[label] = port
        return merged


def load_rune_registry(extensions: AssembledExtensions, runes_dir: Path | None = None) -> RuneRegistry:
    """Load and validate every active rune schema into a ``RuneRegistry`` once."""
    return RuneRegistry(ConfigLoader(runes_dir).load_all(list(extensions.rune_schemas)))
