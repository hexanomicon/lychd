"""One extension assembly per process, owned by the application assembly root.

This is the single sanctioned place a process-wide extension assembly lives.
``AppInit.on_app_init`` and CLI command bodies obtain
the assembly via ``get_extensions()``. Domain code never imports this module;
it receives the projections it needs as constructor arguments.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

from lychd.config.settings.root import get_settings
from lychd.extensions.manager import ExtensionManager

if TYPE_CHECKING:
    from lychd.config.runes.base import RuneConfig
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.extension import RegisteredPortalDefinition, RegisteredSoulstoneDefinition
    from lychd.domain.animation.services.adapters.contracts import (
        PortalDefinition,
        SoulstoneRuntimeAdapter,
    )
    from lychd.domain.animation.transmute import QuadletContributor
    from lychd.domain.delegation.ports import DelegatedAgentRuntime
    from lychd.domain.oculus.runtime import RegisteredInspection, RegisteredObservation
    from lychd.extensions.context import ExtensionContext
    from lychd.extensions.delegation import RegisteredDelegatedRuntime


@dataclass(frozen=True)
class AssembledExtensions:
    """Immutable result of exactly one assembly pass."""

    context: ExtensionContext

    def __post_init__(self) -> None:
        """Seal even test/bootstrap assemblies constructed outside the manager."""
        self.context.freeze()

    @property
    def rune_schemas(self) -> tuple[type[RuneConfig], ...]:
        return self.context.runes.rune_schemas

    @property
    def soulstone_registrations(self) -> tuple[RegisteredSoulstoneDefinition, ...]:
        """Selected Soulstone definitions with host-assigned provenance."""
        return self.context.soulstones.registrations

    @property
    def portal_registrations(self) -> tuple[RegisteredPortalDefinition, ...]:
        """Selected Portal definitions with host-assigned provenance."""
        return self.context.portals.registrations

    @property
    def runtime_adapters(self) -> tuple[SoulstoneRuntimeAdapter, ...]:
        return self.context.soulstones.runtime_adapters

    @property
    def portal_definitions(self) -> tuple[PortalDefinition, ...]:
        return self.context.portals.definitions

    @property
    def quadlet_contributors(self) -> tuple[QuadletContributor, ...]:
        return self.context.transmutation.contributors

    @property
    def delegated_runtime_catalog(self) -> tuple[RegisteredDelegatedRuntime, ...]:
        """Discoverable delegated runtimes with registration provenance."""
        return self.context.delegated_runtimes.registrations

    @property
    def delegated_runtime_adapters(self) -> dict[str, DelegatedAgentRuntime]:
        """Runnable delegated adapters admitted by the selected extensions."""
        return dict(self.context.delegated_runtimes.runtime_adapters)

    @property
    def observation_registrations(self) -> tuple[RegisteredObservation, ...]:
        """Selected structural declarations with host-bound registration provenance."""
        return self.context.observations.registrations

    @property
    def inspection_registrations(self) -> tuple[RegisteredInspection, ...]:
        """Selected pure Pattern descriptions, never executable workflow registrations."""
        return self.context.inspections.registrations


def assemble_extensions(settings: Settings | None = None) -> AssembledExtensions:
    """Pure assembly — importable and testable without app or memo."""
    active = (settings or get_settings()).extensions
    context = ExtensionManager(builtins=active.builtins, crypt=active.crypt).assemble()
    return AssembledExtensions(context=context)


@cache
def get_extensions() -> AssembledExtensions:
    """Return the process-wide assembly, assembling on first call."""
    return assemble_extensions()
