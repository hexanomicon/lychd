"""Runtime animator handle hierarchy (domain layer).

These are orchestratable runtime ABCs, not rune config schemas.

This is the *first axis* of the animation domain:
- ``Soulstone`` models local/container-backed placement.
- ``Portal`` models remote/API-backed placement.

The *second axis* (protocol/capability behavior) is composition through a typed
``Connector``. Two generic parameters preserve precision through inheritance:
- ``C`` = connector type (protocol/capability surface)
- ``R`` = rune config type (provenance/config surface)

This allows code handling a concrete animator to access both connector-specific
methods and the specific rune schema type without casts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from lychd.config.runes import RuneConfig, Runic
from lychd.domain.animation.connectors import Connector
from lychd.domain.animation.schemas.runes.animators import PortalConfig, SoulstoneConfig


class Animator[C: Connector, R: RuneConfig](ABC, Runic[R]):
    """Base runtime animator handle parameterized by connector and rune types.

    ``Animator`` is the orchestratable unit used by registry/orchestration. It
    owns:
    - provenance (``.rune`` via ``Runic``)
    - endpoint identity (``name`` / ``id`` / ``base_url``)
    - a typed connector (``.connector``) that exposes capabilities

    It deliberately does *not* expose agent/runtime library objects directly on
    the animator. Connectors hide the integration details while preserving a
    stable orchestration-facing handle (identity, provenance, readiness, and
    capability access).

    ``Animator`` inherits ``Runic`` for reusable typing across the codebase, but
    also declares an explicit abstract ``rune`` property for local readability
    and ABC-style enforcement on concrete runtime animators.
    """

    @property
    @abstractmethod
    def rune(self) -> R:
        """Return the source rune config that constructed this runtime animator."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the animator identity (also the default stable id)."""
        ...

    @property
    def id(self) -> str:
        """Return a stable runtime id (defaults to ``name``)."""
        return self.name

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for this animator endpoint/runtime.

        The connector is responsible for expanding this base URL into
        protocol-specific paths and request surfaces.
        """
        ...

    @property
    @abstractmethod
    def connector(self) -> C:
        """Return the connector that hides protocol/capability complexity."""
        ...

    @property
    def orchestration_labels(self) -> frozenset[str]:
        """Return advisory labels for routing policy (locality, privacy, cost)."""
        return frozenset()


class Soulstone[C: Connector, R: SoulstoneConfig](Animator[C, R], ABC):
    """Local animator base class preserving connector and rune type parameters.

    Concrete ``*Stone`` classes define how local runtimes are prepared and how
    their connector is constructed (for example a llama.cpp-based
    OpenAI-compatible connector). ``R`` is bounded to ``SoulstoneConfig`` (or a
    subclass) so concrete stones retain precise local rune typing.
    """


class Portal[C: Connector, R: PortalConfig](Animator[C, R], ABC):
    """Remote animator base class preserving connector and rune type parameters.

    Concrete ``*Portal`` classes define how remote credentials/base URLs are
    resolved and how their connector is constructed (for example OpenAI,
    Anthropic, or Gemini connectors). ``R`` is bounded to ``PortalConfig`` (or a
    subclass) so concrete portals retain precise remote rune typing.
    """
