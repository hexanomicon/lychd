"""Shared runtime-adapter helpers.

These helpers keep adapter modules focused on runtime-specific planning while
centralizing repeated type-guard and connector construction logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import (
    default_model_id_for_soulstone,
    model_infos_from_soulstone,
)
from lychd.domain.animation.services.adapters.surfaces import (
    OpenAICompatibleConnector,
    local_link_default,
)
from lychd.system.schemas import QuadletContainer

if TYPE_CHECKING:
    from lychd.domain.animation.services.adapters.contracts import SoulstoneRuntimePlanner


def require_runtime_soulstone[RuntimeSoulstone: SoulstoneConfig](
    soulstone: SoulstoneConfig,
    *,
    expected_type: type[RuntimeSoulstone],
    runtime: str,
) -> RuntimeSoulstone:
    """Validate adapter input type and return the narrowed soulstone."""
    if not isinstance(soulstone, expected_type):
        msg = f"{runtime} adapter received unsupported soulstone type: {type(soulstone)}"
        raise TypeError(msg)
    return soulstone


def build_openai_connector(
    *,
    soulstone: SoulstoneConfig,
    runtime: str,
    kind: str | None = None,
    metadata: dict[str, object] | None = None,
) -> OpenAICompatibleConnector:
    """Build a standard OpenAI-compatible connector for a local runtime."""
    model_infos = model_infos_from_soulstone(soulstone)
    return OpenAICompatibleConnector(
        kind=kind or runtime,
        link=local_link_default(runtime=runtime),
        base_url=resolved_soulstone_base_url(soulstone),
        model_infos=model_infos,
        default_model_id=default_model_id_for_soulstone(soulstone, model_infos),
        metadata=metadata,
    )


def resolved_soulstone_port(soulstone: SoulstoneConfig) -> int:
    """Return a hydrated Soulstone port or fail with a domain-facing error."""
    if soulstone.port is None:
        msg = f"Soulstone '{soulstone.name}' has no hydrated port. Load it through AnimatorLoader first."
        raise ValueError(msg)
    return soulstone.port


def resolved_soulstone_base_url(soulstone: SoulstoneConfig) -> str:
    """Return a hydrated Soulstone connector base URL."""
    if soulstone.base_url is not None:
        return str(soulstone.base_url)
    return f"http://localhost:{resolved_soulstone_port(soulstone)}/v1"


def transmute_single_soulstone_quadlet(
    soulstone: SoulstoneConfig,
    *,
    runtime_planner: SoulstoneRuntimePlanner | None = None,
) -> QuadletContainer:
    """Build the generated Quadlet manifest for a single Soulstone context."""
    from lychd.domain.animation.transmute import Transmuter

    manifests = Transmuter(runtime_planner=runtime_planner).transmute_all([soulstone])
    container_name = f"lychd-{soulstone.name}"
    for manifest in manifests:
        if isinstance(manifest, QuadletContainer) and manifest.container_name == container_name:
            return manifest

    msg = f"Transmutation did not produce QuadletContainer for Soulstone '{soulstone.name}'."
    raise RuntimeError(msg)


__all__ = [
    "build_openai_connector",
    "require_runtime_soulstone",
    "resolved_soulstone_base_url",
    "resolved_soulstone_port",
    "transmute_single_soulstone_quadlet",
]
