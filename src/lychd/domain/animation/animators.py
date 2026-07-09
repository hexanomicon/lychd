"""Runtime Animator handle hierarchy.

Animators are runic handles for live addressable services. They bind placement
(``Soulstone`` or ``Portal``) to a typed connector while keeping protocol and
capability behavior behind the connector layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from lychd.config.runes import RuneConfig, Runic
from lychd.domain.animation.connectors import Connector
from lychd.domain.animation.schemas.runes.animators import PortalConfig, SoulstoneConfig
from lychd.system.schemas import QuadletContainer


class Animator[C: Connector, R: RuneConfig](ABC, Runic[R]):
    """Runtime handle for a live addressable service.

    Generic - Subclasses specialize:
    - ``C`` to their connector implementation
    - ``R`` to the rune (config) schema that constructed the runtime handle.
    """

    @property
    @abstractmethod
    def rune(self) -> R: ...

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
    def connector(self) -> C:
        """Return the connector that hides protocol/capability complexity."""
        ...


class Soulstone[C: Connector, R: SoulstoneConfig](Animator[C, R], ABC):
    """Local/container-backed Animator."""

    @property
    @abstractmethod
    def quadlet(self) -> QuadletContainer:
        """Generated Quadlet manifest for this local runtime."""
        ...


class Portal[C: Connector, R: PortalConfig](Animator[C, R], ABC):
    """Remote/API-backed Animator."""


# THE one runtime-animator alias. Rehomed here from three near-duplicate definitions
# (registry / adapters.contracts / binder — the binder's used the broader RuneConfig).
type RuntimeAnimator = Animator[Connector, SoulstoneConfig | PortalConfig]
