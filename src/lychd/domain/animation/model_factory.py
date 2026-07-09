"""The ONE OpenAI-compatible model constructor.

Both the agents-layer reference (`agents.factory.build_local_model`) and the production
hydration path (`OpenAICompatibleConnector.get_model` via `AnimatorBinder`) build their
pydantic-ai `Model` here. If they diverged — as they silently did, the reference applying
a JSON-schema profile the connector did not — tool-call JSON schemas (`$defs` inlining,
strict-tool mode) would differ between what tests/CLI exercise and what the daemon runs.

The local-compat profile is the conservative choice: `InlineDefsJsonSchemaTransformer`
emits inlined `$defs` (valid schema every OpenAI-compatible endpoint accepts) and
`openai_supports_strict_tool_definition=False` avoids strict-tool mode that local
backends (llama.cpp/vLLM/SGLang) do not implement. It is safe against real OpenAI too.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles import InlineDefsJsonSchemaTransformer
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.openai import OpenAIProvider

if TYPE_CHECKING:
    from pydantic_ai.models import Model

__all__ = ["LOCAL_COMPAT_PROFILE", "build_openai_compatible_model", "openai_compatible_provider"]

LOCAL_COMPAT_PROFILE = OpenAIModelProfile(
    json_schema_transformer=InlineDefsJsonSchemaTransformer,
    openai_supports_strict_tool_definition=False,
)


def openai_compatible_provider(*, base_url: str, api_key: str | None = None) -> OpenAIProvider:
    """Build an OpenAI provider bound to a base URL, with an optional API key."""
    if api_key:
        return OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIProvider(base_url=base_url)


def build_openai_compatible_model(
    *,
    model_id: str,
    provider: OpenAIProvider,
    responses: bool = False,
) -> Model:
    """Build the canonical OpenAI-compatible model (Chat or Responses) with the shared profile.

    ``responses`` selects the Responses API surface; both surfaces carry the same
    ``LOCAL_COMPAT_PROFILE`` so tool-call schemas are identical across every call site.
    """
    if responses:
        from pydantic_ai.models.openai import OpenAIResponsesModel

        return cast("Model", OpenAIResponsesModel(model_id, provider=provider, profile=LOCAL_COMPAT_PROFILE))
    return cast("Model", OpenAIChatModel(model_id, provider=provider, profile=LOCAL_COMPAT_PROFILE))
