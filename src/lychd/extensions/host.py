"""One extension assembly per process, owned by the composition root.

This is the single sanctioned place a process-wide extension assembly lives.
``AppInit.on_app_init``, SAQ ``worker_startup``, and CLI command bodies obtain
the assembly via ``get_extensions()``. Domain code never imports this module;
it receives the projections it needs as constructor arguments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from lychd.config.settings import get_settings
from lychd.extensions.manager import ExtensionManager

if TYPE_CHECKING:
    from lychd.config.runes.base import RuneConfig
    from lychd.config.settings import Settings
    from lychd.domain.animation.services.adapters.contracts import (
        PortalRuntimeFactory,
        SoulstoneDefinition,
        SoulstoneRuntimeAdapter,
    )
    from lychd.extensions.context import ExtensionContext


@dataclass(frozen=True)
class AssembledExtensions:
    """Immutable result of exactly one assembly pass."""

    context: ExtensionContext
    active_ids: tuple[str, ...]  # builtins + crypt, in activation order

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
    def portal_factories(self) -> tuple[PortalRuntimeFactory, ...]:
        return self.context.portals.factories


def assemble_extensions(settings: Settings | None = None) -> AssembledExtensions:
    """Pure assembly — importable and testable without app or memo."""
    active = (settings or get_settings()).extensions
    context = ExtensionManager(builtins=active.builtins, crypt=active.crypt).assemble()
    return AssembledExtensions(context=context, active_ids=(*active.builtins, *active.crypt))


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
