"""Shared runtime-adapter helpers.

These helpers keep adapter modules focused on runtime-specific planning while
centralizing repeated type-guard and connector construction logic.
"""

from __future__ import annotations

from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import (
    default_model_id_for_soulstone,
    model_infos_from_soulstone,
)
from lychd.domain.animation.services.adapters.surfaces import (
    OpenAICompatibleConnector,
    local_link_default,
)


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
) -> OpenAICompatibleConnector:
    """Build a standard OpenAI-compatible connector for a local runtime."""
    model_infos = model_infos_from_soulstone(soulstone)
    return OpenAICompatibleConnector(
        kind=kind or runtime,
        link=local_link_default(runtime=runtime),
        base_url=soulstone.base_url,
        model_infos=model_infos,
        default_model_id=default_model_id_for_soulstone(soulstone, model_infos),
    )


__all__ = ["build_openai_connector", "require_runtime_soulstone"]
