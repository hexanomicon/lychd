"""One authoritative compilation of Rune intent into Animator declarations."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lychd.domain.animation.services.loader import AnimatorLoader

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig, SoulstonePlacement


@dataclass(frozen=True, slots=True)
class AnimatorDeclarations:
    """One hydrated declaration snapshot shared by bind and live runtimes."""

    soulstones: tuple[SoulstoneConfig, ...]
    portals: tuple[PortalConfig, ...]
    lifecycle_binding_digest: str | None = None

    def __post_init__(self) -> None:
        """Require a well-formed host commitment for explicitly placed Runes."""
        if self.lifecycle_binding_digest is None:
            if any(rune.placement is not None for rune in self.soulstones):
                msg = "An explicit Soulstone placement requires a compiled lifecycle binding."
                raise ValueError(msg)
        elif re.fullmatch(r"sha256:[0-9a-f]{64}", self.lifecycle_binding_digest) is None:
            msg = "Invalid lifecycle binding digest."
            raise ValueError(msg)


def compile_animator_declarations(
    *,
    settings: Settings,
    runes: RuneRegistry,
    core_reserved_ports: Mapping[str, int] | None = None,
    lifecycle_binding_digest: str | None = None,
) -> AnimatorDeclarations:
    """Hydrate one Rune snapshot under the complete collision policy.

    Production composition leaves ``core_reserved_ports`` unset so Settings
    owns the core claims. The explicit override is a narrow fixture seam for
    tests that intentionally exercise ports used by the control plane. A caged
    replica receives its host's binding digest from its generated deployment.
    The host derives the digest from its local switching settings.
    """
    reserved_ports = merge_reserved_ports(
        (settings.server.reserved_ports_map if core_reserved_ports is None else core_reserved_ports),
        runes.reserved_ports(),
    )
    soulstones, portals = AnimatorLoader(
        reserved_ports=reserved_ports,
        core_secret_names=settings.server.privileged_secret_names,
    ).hydrate_all(runes.all())
    return AnimatorDeclarations(
        soulstones=tuple(soulstones),
        portals=tuple(portals),
        lifecycle_binding_digest=(
            _compile_lifecycle_binding(soulstones, settings)
            if lifecycle_binding_digest is None
            else lifecycle_binding_digest
        ),
    )


def _compile_lifecycle_binding(soulstones: Sequence[SoulstoneConfig], settings: Settings) -> str | None:
    """Bind effect owners to canonical names without publishing their private settings."""
    switching = settings.orchestration.switching
    desktop = switching.actuator == "native-process"
    default: SoulstonePlacement = "native" if desktop else "container"
    declared = {rune.name: rune.resolved_placement(default) for rune in soulstones}
    containers = {binding.animator: binding.model_dump(mode="json") for binding in switching.containers}
    expected = {name for name, placement in declared.items() if desktop and placement == "container"}
    if expected != containers.keys():
        msg = "Desktop container bindings must match the Soulstones with container placement exactly."
        raise ValueError(msg)
    if not any(rune.placement is not None or rune.concurrency.dedicated for rune in soulstones):
        # Older journals contain no binding identity. Keep the old digest only
        # where no local lifecycle owner could use it to change a service.
        return None
    payload: dict[str, object] = {
        "actuator": switching.actuator,
        "placements": declared,
        "containers": containers,
    }
    if "native" in declared.values():
        engine, root = switching.native_llama_server, switching.native_model_root
        if engine is None or root is None or not engine.is_absolute() or not root.is_absolute():
            msg = "Native placement requires an absolute native_llama_server and native_model_root."
            raise ValueError(msg)
        payload.update(native_llama_server=str(engine), native_model_root=str(root))
        if not desktop:
            payload["relay_image"] = settings.server.web.image
    if desktop:
        payload["native_state_dir"] = str(switching.native_state_dir)
    elif switching.actuator == "host-reactor":
        payload["host_reactor_dir"] = str(switching.host_reactor_dir)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


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
