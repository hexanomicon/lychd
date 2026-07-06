"""llama.cpp connector + runtime handle (moved out of the domain per A3-U2 §5).

The domain owns generic connectors (``PassiveConnector`` /
``OpenAICompatibleConnector``) and the concrete generic ``SoulstoneAnimator``;
the llama.cpp-specific connector (router/single lifecycle metadata) and its typed
stone live here in the extension package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector, SoulstoneAnimator
from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstoneConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lychd.domain.animation.links import Link
    from lychd.domain.animation.schemas import ModelInfo


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
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Initialize llama.cpp connector with runtime lifecycle metadata."""
        super().__init__(
            kind="llamacpp",
            link=link,
            base_url=base_url,
            model_infos=model_infos,
            default_model_id=default_model_id,
        )
        self._mode: Literal["single", "router"] = mode
        self._router_query_model_id = router_query_model_id
        self._metadata = dict(metadata or {})

    @property
    def mode(self) -> Literal["single", "router"]:
        return self._mode

    @property
    def router_query_model_id(self) -> str | None:
        return self._router_query_model_id

    @property
    def metadata(self) -> dict[str, object]:
        return dict(self._metadata)


class LlamacppStone(SoulstoneAnimator[LlamacppConnector, LlamaCppSoulstoneConfig]):
    """Concrete llama.cpp Soulstone runtime handle."""


__all__ = ["LlamacppConnector", "LlamacppStone"]
