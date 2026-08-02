"""One extension assembly per process, owned by the application assembly root.

This is the single sanctioned place a process-wide extension assembly lives.
``AppInit.on_app_init``, SAQ ``worker_startup``, and CLI command bodies obtain
the assembly via ``get_extensions()``. Domain code never imports this module;
it receives the projections it needs as constructor arguments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from lychd.config.settings.root import get_settings
from lychd.extensions.builtin.catalog import builtin_registration_order
from lychd.extensions.manager import ExtensionManager

if TYPE_CHECKING:
    from lychd.config.runes.base import RuneConfig
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.services.adapters.contracts import (
        PortalDefinition,
        SoulstoneDefinition,
        SoulstoneRuntimeAdapter,
    )
    from lychd.domain.animation.transmute import QuadletContributor, RegisteredQuadletContributor
    from lychd.domain.cortex.operations import RunOperationCatalog
    from lychd.domain.delegation.ports import DelegatedAgentRuntime
    from lychd.extensions.context import ExtensionContext
    from lychd.extensions.delegation import RegisteredDelegatedRuntime


@dataclass(frozen=True)
class AssembledExtensions:
    """Immutable result of exactly one assembly pass."""

    context: ExtensionContext
    active_ids: tuple[str, ...]  # builtins + crypt, in activation order

    def __post_init__(self) -> None:
        """Seal even test/bootstrap assemblies constructed outside the manager."""
        self.context.freeze()

    @property
    def rune_schemas(self) -> tuple[type[RuneConfig], ...]:
        return self.context.runes.rune_schemas

    @property
    def runtime_adapters(self) -> tuple[SoulstoneRuntimeAdapter, ...]:
        return self.context.soulstones.runtime_adapters

    @property
    def soulstone_definitions(self) -> tuple[SoulstoneDefinition, ...]:
        return self.context.soulstones.definitions

    @property
    def portal_definitions(self) -> tuple[PortalDefinition, ...]:
        return self.context.portals.definitions

    @property
    def quadlet_contributors(self) -> tuple[QuadletContributor, ...]:
        return self.context.transmutation.contributors

    @property
    def quadlet_contributor_registrations(self) -> tuple[RegisteredQuadletContributor, ...]:
        return self.context.transmutation.registrations

    @property
    def run_operation_catalog(self) -> RunOperationCatalog:
        """Read-only catalogue admitted beneath ``lychd run``."""
        return self.context.run_operations

    @property
    def delegated_runtime_catalog(self) -> tuple[RegisteredDelegatedRuntime, ...]:
        """Discoverable delegated runtimes with registration provenance."""
        return self.context.delegated_runtimes.registrations

    @property
    def delegated_runtime_adapters(self) -> dict[str, DelegatedAgentRuntime]:
        """Runnable delegated adapters admitted by the selected extensions."""
        return dict(self.context.delegated_runtimes.runtime_adapters)


def assemble_extensions(settings: Settings | None = None) -> AssembledExtensions:
    """Pure assembly — importable and testable without app or memo."""
    active = (settings or get_settings()).extensions
    context = ExtensionManager(builtins=active.builtins, crypt=active.crypt).assemble()
    return AssembledExtensions(
        context=context,
        active_ids=(*builtin_registration_order(active.builtins), *active.crypt),
    )


# --- process memo (the ONLY sanctioned global) ---
_assembled: AssembledExtensions | None = None


def get_extensions() -> AssembledExtensions:
    """Return the process-wide assembly, assembling on first call."""
    global _assembled  # noqa: PLW0603
    if _assembled is None:
        _assembled = assemble_extensions()
    return _assembled


def install_extensions(assembled: AssembledExtensions) -> None:
    """Test/bootstrap seam: install a prebuilt assembly.

    Raises:
        RuntimeError: If an assembly is already installed.

    """
    global _assembled  # noqa: PLW0603
    if _assembled is not None:
        msg = "An extension assembly is already installed; call reset_extensions() first."
        raise RuntimeError(msg)
    _assembled = assembled


def reset_extensions() -> None:
    """Test-only teardown of the process memo."""
    global _assembled  # noqa: PLW0603
    _assembled = None
