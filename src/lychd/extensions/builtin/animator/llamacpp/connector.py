"""llama.cpp connector + runtime handle (moved out of the domain per A3-U2 §5).

The domain owns the generic ``OpenAICompatibleConnector`` and concrete
``SoulstoneAnimator``;
the llama.cpp-specific connector (router/single lifecycle metadata) and its typed
Soulstone live here in the extension package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lychd.domain.animation.links import Link
    from lychd.domain.animation.schemas import GenerationProfile, ModelInfo


class LlamacppConnector(OpenAICompatibleConnector):
    """OpenAI-compatible connector with llama.cpp router/single lifecycle metadata."""

    def __init__(
        self,
        *,
        link: Link,
        base_url: str,
        model_infos: Sequence[ModelInfo],
        default_model_id: str | None,
        mode: Literal["single", "router"],
        router_query_model_id: str | None,
        generation_defaults: GenerationProfile,
    ) -> None:
        """Initialize llama.cpp connector with runtime lifecycle metadata."""
        super().__init__(
            link=link,
            base_url=base_url,
            model_infos=model_infos,
            default_model_id=default_model_id,
        )
        self._mode: Literal["single", "router"] = mode
        self._router_query_model_id = router_query_model_id
        self._generation_defaults = generation_defaults

    @property
    def generation_defaults(self) -> GenerationProfile:
        """Frozen runtime defaults captured with this connector's catalogue."""
        return self._generation_defaults

    @property
    def mode(self) -> Literal["single", "router"]:
        return self._mode

    @property
    def router_query_model_id(self) -> str | None:
        return self._router_query_model_id


__all__ = ["LlamacppConnector"]
