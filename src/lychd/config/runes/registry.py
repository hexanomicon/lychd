"""Validated Rune instances loaded once per composition snapshot."""

from __future__ import annotations

from copy import deepcopy
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
        """Store a detached snapshot of the validated rune instances."""
        self._runes: tuple[RuneConfig, ...] = tuple(deepcopy(rune) for rune in runes)

    def all(self) -> tuple[RuneConfig, ...]:
        """All loaded rune instances."""
        return tuple(deepcopy(rune) for rune in self._runes)

    def of(self, schema: type[R]) -> tuple[R, ...]:
        """Instances that are (subclass) instances of ``schema``."""
        return tuple(deepcopy(rune) for rune in self._runes if isinstance(rune, schema))

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
            ValueError: If two rune claims collide on the same PORT (even under an
                equal label — two distinct claimants for one port is a real conflict)
                or on the same LABEL (a repeated label would silently overwrite an
                earlier reservation and evade the §8.1 fail-at-bind guarantee).

        """
        merged: dict[str, int] = {}
        by_label: dict[str, str] = {}  # label -> claimant type name
        by_port: dict[int, tuple[str, str]] = {}  # port -> (label, claimant type name)
        for rune in self._runes:
            if not isinstance(rune, PortReserver):
                continue
            claimant = rune.__class__.__name__
            for label, port in rune.reserved_ports().items():
                if label in by_label:
                    msg = f"Port label '{label}' is claimed by both '{by_label[label]}' and '{claimant}'."
                    raise ValueError(msg)
                if port in by_port:
                    other_label, other_claimant = by_port[port]
                    msg = (
                        f"Port {port} is claimed by both '{other_label}' ({other_claimant}) and '{label}' ({claimant})."
                    )
                    raise ValueError(msg)
                by_label[label] = claimant
                by_port[port] = (label, claimant)
                merged[label] = port
        return merged


def load_rune_registry(extensions: AssembledExtensions, runes_dir: Path | None = None) -> RuneRegistry:
    """Load and validate every active rune schema into a ``RuneRegistry`` once."""
    return RuneRegistry(ConfigLoader(runes_dir).load_all(list(extensions.rune_schemas)))
