"""llama.cpp connector + runtime handle (moved out of the domain per A3-U2 §5).

The domain owns the generic ``OpenAICompatibleConnector`` and concrete
``SoulstoneAnimator``;
the llama.cpp-specific connector (router/single lifecycle metadata) and its typed
Soulstone live here in the extension package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from lychd.domain.animation.connectors import EmbeddingConnector
from lychd.domain.animation.embeddings import (
    EmbeddingBinding,
    EmbeddingDriver,
    EmbeddingOperation,
    EmbeddingProfile,
    EmbeddingRefused,
)
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector
from lychd.extensions.builtin.animator.llamacpp.embedding import LlamaCppEmbeddingDriver
from lychd.extensions.builtin.animator.llamacpp.embedding_profile import PROFILE

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic_ai.models import Model

    from lychd.domain.animation.links import Link
    from lychd.domain.animation.schemas import GenerationProfile, ModelInfo


class LlamacppConnector(OpenAICompatibleConnector, EmbeddingConnector):
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
        embedding_profile: EmbeddingProfile | None = None,
        schema_without_tools: bool = False,
    ) -> None:
        """Initialize llama.cpp connector with runtime lifecycle metadata."""
        super().__init__(
            link=link,
            base_url=base_url,
            model_infos=model_infos,
            default_model_id=default_model_id,
            schema_without_tools=schema_without_tools,
            # A lease authorizes inference, never router loading or LRU eviction.
            default_query={"autoload": "false"} if mode == "router" else None,
        )
        self._mode: Literal["single", "router"] = mode
        self._router_query_model_id = router_query_model_id
        self._generation_defaults = generation_defaults
        self.embedding_profile = embedding_profile

    def get_model(self, *, model_id: str | None = None) -> Model:
        """Keep embedding-only declarations out of the inherited chat surface."""
        if self.embedding_profile is not None:
            raise EmbeddingRefused("interface")  # noqa: EM101 - closed refusal code
        return super().get_model(model_id=model_id)

    def require_embedding(self, binding: EmbeddingBinding, operation: EmbeddingOperation) -> None:
        """Match the closed reviewed dialect rather than trusting a self-signed profile."""
        if (
            self.embedding_profile != PROFILE
            or binding.profile_digest != PROFILE.digest
            or binding.interface != PROFILE.interface
            or self._mode != "single"
        ):
            raise EmbeddingRefused("profile")  # noqa: EM101 - closed machine-readable refusal code
        if operation not in {"embed_document", "embed_query"}:
            raise EmbeddingRefused("operation")  # noqa: EM101 - closed machine-readable refusal code

    def get_embedding(self, binding: EmbeddingBinding, operation: EmbeddingOperation) -> EmbeddingDriver:
        """Hydrate only the fixed local dialect."""
        self.require_embedding(binding, operation)
        return LlamaCppEmbeddingDriver(base_url=self.base_url, operation=operation)

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
