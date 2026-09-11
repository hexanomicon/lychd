"""The OpenAI-compatible model constructor used by runtime hydration.

Local generic runtimes explicitly select `LOCAL_COMPAT_PROFILE`: its inlined `$defs`
and non-strict tools fit llama.cpp/vLLM/SGLang-style endpoints. Provider portals route
through the matching Pydantic AI OpenAI-interface provider or profile resolver.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles import DEFAULT_PROFILE, InlineDefsJsonSchemaTransformer
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers import Provider
from pydantic_ai.providers.openai import OpenAIProvider

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from types import TracebackType
    from typing import Self

    from pydantic_ai.models import Model
    from pydantic_ai.profiles import ModelProfile, ModelProfileSpec

__all__ = [
    "LOCAL_COMPAT_PROFILE",
    "build_openai_compatible_model",
    "openai_compatible_provider",
    "openai_interface_route",
    "validate_openai_interface_target",
]

LOCAL_COMPAT_PROFILE = OpenAIModelProfile(
    json_schema_transformer=InlineDefsJsonSchemaTransformer,
    openai_supports_strict_tool_definition=False,
    supports_inline_system_prompts=True,
)


def _local_compat_profile(_resolved: ModelProfile) -> ModelProfile:
    """Replace provider defaults: a local model alias does not identify OpenAI policy."""
    return {**DEFAULT_PROFILE, **LOCAL_COMPAT_PROFILE}


class _ProfiledOpenAIProvider(Provider[AsyncOpenAI]):
    """Give an OpenAI-shaped transport its truthful provider identity."""

    def __init__(
        self,
        *,
        transport: OpenAIProvider,
        name: str,
        model_profile: Callable[[str], ModelProfile | None],
    ) -> None:
        self._transport = transport
        self._name = name
        # Keep the Provider protocol's keyword parameter while accepting a positional resolver.
        self.model_profile = lambda model_name: model_profile(model_name)  # noqa: PLW0108

    @property
    def name(self) -> str:
        return self._name

    @property
    def base_url(self) -> str:
        return self._transport.base_url

    @property
    def client(self) -> AsyncOpenAI:
        return self._transport.client

    async def __aenter__(self) -> Self:
        """Enter the transport that owns this profile's HTTP client."""
        await self._transport.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """Close the owning transport after its final model consumer exits."""
        return await self._transport.__aexit__(exc_type, exc_val, exc_tb)


def _profiled_transport(
    transport: OpenAIProvider,
    profile_provider: Provider[AsyncOpenAI],
) -> tuple[_ProfiledOpenAIProvider, None]:
    """Keep the configured transport while borrowing provider identity and profiles."""
    return (
        _ProfiledOpenAIProvider(
            transport=transport,
            name=profile_provider.name,
            model_profile=profile_provider.model_profile,
        ),
        None,
    )


def openai_compatible_provider(
    *,
    base_url: str,
    api_key: str | None = None,
    default_query: Mapping[str, str] | None = None,
) -> OpenAIProvider:
    """Bind only the declared endpoint and credential before exposing the SDK client."""
    # The SDK reads OPENAI_API_KEY when no key is passed. A local runtime or
    # credential-free Portal has no authority to receive that unrelated secret.
    provider = OpenAIProvider(base_url=base_url, api_key=api_key if api_key is not None else "api-key-not-set")
    # The SDK imports account metadata, admin credentials, and custom headers.
    # This endpoint is authorized only for its declared credential. The pinned
    # provider has no constructor seam to suppress ambient SDK headers.
    provider.client.organization = None
    provider.client.project = None
    provider.client.webhook_secret = None
    provider.client.admin_api_key = None
    provider.client._custom_headers = {}  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    provider.client._ambient_authorizations = frozenset()  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    if default_query:
        # The pinned provider owns this client but exposes no query constructor
        # option; SDK with_options would create a second client ownership path.
        provider.client._custom_query = dict(default_query)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    return provider


def openai_interface_route(
    *,
    provider_name: str,
    base_url: str,
    model_id: str,
    responses: bool,
    api_key: str | None = None,
    default_query: Mapping[str, str] | None = None,
) -> tuple[Provider[AsyncOpenAI], ModelProfileSpec | None]:
    """Select transport identity and model-profile policy for one OpenAI-shaped endpoint."""
    provider = provider_name.strip().lower()
    validate_openai_interface_target(
        provider_name=provider,
        model_id=model_id,
        responses=responses,
    )
    transport = openai_compatible_provider(base_url=base_url, api_key=api_key, default_query=default_query)

    if provider == "openrouter":
        from pydantic_ai.providers.openrouter import OpenRouterProvider

        return _profiled_transport(transport, OpenRouterProvider(openai_client=transport.client))
    if provider == "litellm":
        from pydantic_ai.providers.litellm import LiteLLMProvider

        return _profiled_transport(transport, LiteLLMProvider(openai_client=transport.client))
    if provider == "ollama":
        from pydantic_ai.providers.ollama import OllamaProvider

        return _profiled_transport(transport, OllamaProvider(openai_client=transport.client))
    if provider == "google-gemini":
        from pydantic_ai.profiles.google import google_model_profile

        # This leaf deliberately targets Google's OpenAI-compatible endpoint, not
        # the native google-genai interface.
        return (
            _ProfiledOpenAIProvider(
                transport=transport,
                name="google-gla",
                model_profile=google_model_profile,
            ),
            None,
        )
    if provider == "openai":
        return transport, None

    return transport, _local_compat_profile


def validate_openai_interface_target(
    *,
    provider_name: str,
    model_id: str,
    responses: bool,
) -> None:
    """Reject provider/model/surface combinations unsupported by the pinned adapter."""
    provider = provider_name.strip().lower()
    if provider == "openrouter" and "/" not in model_id:
        msg = "OpenRouter model ids must use the provider/model form."
        raise ValueError(msg)
    if responses and provider in {"google-gemini", "litellm", "ollama"}:
        msg = f"Provider '{provider}' supports only the Chat surface through LychD's current adapter."
        raise ValueError(msg)


def build_openai_compatible_model(
    *,
    model_id: str,
    provider: Provider[AsyncOpenAI],
    responses: bool = False,
    profile: ModelProfileSpec | None = None,
) -> Model:
    """Build the canonical OpenAI-compatible model on the selected API surface.

    Generic local compatibility replaces resolved provider defaults through the
    profile callback. With ``None``, the provider supplies its model-aware profile.
    """
    if responses:
        from pydantic_ai.models.openai import OpenAIResponsesModel

        return cast("Model", OpenAIResponsesModel(model_id, provider=provider, profile=profile))
    return cast("Model", OpenAIChatModel(model_id, provider=provider, profile=profile))
