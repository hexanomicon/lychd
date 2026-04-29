from __future__ import annotations

from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator, RuntimePlan
from lychd.domain.animation.services.adapters.runtimes.shared import build_openai_connector
from lychd.domain.animation.services.adapters.surfaces import (
    GenericStone,
    OpenAICompatibleStone,
    PassiveConnector,
    local_link_default,
)


class GenericRuntimeAdapter:
    """Fallback Soulstone planner/runtime builder for unknown runtimes."""

    runtime = "generic"

    def supports(self, runtime: str) -> bool:
        return runtime == self.runtime

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Preserve explicit command passthrough for unknown runtimes."""
        return RuntimePlan(exec_args=list(soulstone.exec), env_overrides={})

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Create a generic runtime handle with best-effort connector capabilities."""
        if soulstone.base_url:
            connector = build_openai_connector(
                soulstone=soulstone,
                runtime=soulstone.runtime_name,
                kind="generic-openai-compatible",
            )
            return OpenAICompatibleStone(rune=soulstone, connector=connector)

        connector = PassiveConnector(kind="generic", link=local_link_default(runtime=soulstone.runtime_name))
        return GenericStone(rune=soulstone, connector=connector)


__all__ = ["GenericRuntimeAdapter"]
