"""One authoritative compilation of Rune intent into Animator declarations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lychd.domain.animation.services.loader import AnimatorLoader

if TYPE_CHECKING:
    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig


@dataclass(frozen=True, slots=True)
class AnimatorDeclarations:
    """One hydrated declaration snapshot shared by bind and live runtimes."""

    runes: RuneRegistry
    soulstones: tuple[SoulstoneConfig, ...]
    portals: tuple[PortalConfig, ...]
    port_reservations: tuple[tuple[str, int], ...]

    @property
    def reserved_ports(self) -> dict[str, int]:
        """Return a detached mapping of the policy used for hydration."""
        return dict(self.port_reservations)


def compile_animator_declarations(
    *,
    settings: Settings,
    runes: RuneRegistry,
    core_reserved_ports: Mapping[str, int] | None = None,
) -> AnimatorDeclarations:
    """Hydrate one Rune snapshot under the complete collision policy.

    Production composition leaves ``core_reserved_ports`` unset so Settings
    owns the core claims. The explicit override is a narrow fixture seam for
    tests that intentionally exercise ports used by the control plane.
    """
    reserved_ports = merge_reserved_ports(
        (settings.server.reserved_ports_map if core_reserved_ports is None else core_reserved_ports),
        runes.reserved_ports(),
    )
    soulstones, portals = AnimatorLoader(
        reserved_ports=reserved_ports,
        core_secret_names=(
            settings.server.web.secret_key_secret,
            settings.server.database.password_secret,
        ),
    ).hydrate_all(runes.all())
    return AnimatorDeclarations(
        runes=runes,
        soulstones=tuple(soulstones),
        portals=tuple(portals),
        port_reservations=tuple(reserved_ports.items()),
    )


def merge_reserved_ports(
    core: Mapping[str, int],
    extension: Mapping[str, int],
) -> dict[str, int]:
    """Merge core and Rune claims without losing a label or port owner."""
    by_port = {port: label for label, port in core.items()}
    merged = dict(core)
    for label, port in extension.items():
        if label in merged:
            message = (
                f"Port label '{label}' is claimed by both a core service "
                f"(port {merged[label]}) and an extension rune (port {port})."
            )
            raise ValueError(message)
        if port in by_port and by_port[port] != label:
            message = f"Port {port} is claimed by both '{by_port[port]}' (core) and '{label}' (extension)."
            raise ValueError(message)
        by_port[port] = label
        merged[label] = port
    return merged


__all__ = (
    "AnimatorDeclarations",
    "compile_animator_declarations",
    "merge_reserved_ports",
)
