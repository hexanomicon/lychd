"""AgentForge / AgentSpec / build_agent / build_local_model (A5 §4, FINAL C6)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from openai._types import Omit
from pydantic_ai.messages import ModelRequest
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.factory import AgentForge, build_local_model
from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC, build_the_first_one, default_forge


def _function_tool_names(agent: object) -> list[str]:
    """Return the names of every function tool bound on the agent."""
    names: list[str] = []
    for toolset in agent.toolsets:  # type: ignore[attr-defined]
        if isinstance(toolset, FunctionToolset):
            names.extend(toolset.tools.keys())
    return names


def test_forge_caches_per_spec() -> None:
    """A forge returns the same agent instance for an identical spec (cache hit)."""
    forge = default_forge()
    first = forge.agent_for(THE_FIRST_ONE_SPEC)
    second = forge.agent_for(THE_FIRST_ONE_SPEC)
    assert first is second


def test_forge_distinct_specs_distinct_agents() -> None:
    """A changed spec is a distinct cache key -> a distinct agent."""
    forge = default_forge()
    short_spec = replace(THE_FIRST_ONE_SPEC, max_tokens=1024)
    forge.register(short_spec.name, build_the_first_one)
    assert forge.agent_for(THE_FIRST_ONE_SPEC) is not forge.agent_for(short_spec)


def test_minimal_spec_binds_no_lifecycle_tool() -> None:
    """The default First One has no in-lease hardware transition capability."""
    agent = build_the_first_one(THE_FIRST_ONE_SPEC)
    assert "request_coven_swap" not in _function_tool_names(agent)


def test_forge_unknown_spec_raises() -> None:
    """`agent_for` on an unregistered spec name fails loudly."""
    forge = AgentForge()
    with pytest.raises(KeyError):
        forge.agent_for(THE_FIRST_ONE_SPEC)


def test_build_local_model_uses_base_url() -> None:
    """`build_local_model` constructs an OpenAIChatModel at the given base_url (no network)."""
    model = build_local_model(model_id="qwen", base_url="http://localhost:8080/v1")
    assert isinstance(model, OpenAIChatModel)
    assert str(model.client.base_url).rstrip("/") == "http://localhost:8080/v1"


def test_reference_and_local_connector_share_compat_profile() -> None:
    """Reference and local runtime connector build the same compatibility profile.

    Portals deliberately retain their provider/model profile instead.
    """
    from lychd.domain.animation.links import Link
    from lychd.domain.animation.model_factory import LOCAL_COMPAT_PROFILE
    from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

    reference = build_local_model(model_id="qwen", base_url="http://localhost:8080/v1")
    assert reference.profile is LOCAL_COMPAT_PROFILE

    connector = OpenAICompatibleConnector(
        kind="openai_compat",
        link=Link(up=True, activatable=False),
        base_url="http://localhost:8080/v1",
        default_model_id="qwen",
    )
    production = connector.get_model()
    assert production.profile is LOCAL_COMPAT_PROFILE


def test_provider_connector_retains_model_profile() -> None:
    from lychd.domain.animation.links import Link
    from lychd.domain.animation.model_factory import LOCAL_COMPAT_PROFILE
    from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

    connector = OpenAICompatibleConnector(
        kind="portal:openai",
        link=Link(up=True, activatable=False),
        base_url="https://api.openai.com/v1",
        default_model_id="gpt-5.2",
        provider_name="openai",
    )

    model = connector.get_model()
    profile = OpenAIModelProfile.from_profile(model.profile)

    assert model.profile is not LOCAL_COMPAT_PROFILE
    assert "temperature" in profile.openai_unsupported_model_settings
    assert profile.openai_supports_strict_tool_definition is True


@pytest.mark.parametrize(
    ("provider_name", "model_id", "expected_system", "expected_transformer"),
    [
        ("openai", "gpt-5.2", "openai", "OpenAIJsonSchemaTransformer"),
        ("google-gemini", "gemini-2.5-pro", "google-gla", "GoogleJsonSchemaTransformer"),
        ("openrouter", "anthropic/claude-sonnet-4", "openrouter", "AnthropicJsonSchemaTransformer"),
        ("litellm", "google/gemini-2.5-pro", "litellm", "GoogleJsonSchemaTransformer"),
        ("ollama", "qwen3:8b", "ollama", "InlineDefsJsonSchemaTransformer"),
        ("openai-compatible", "qwen3:8b", "openai", "InlineDefsJsonSchemaTransformer"),
    ],
)
def test_portal_factory_routes_provider_profile(
    provider_name: str,
    model_id: str,
    expected_system: str,
    expected_transformer: str,
) -> None:
    from lychd.domain.animation.model_factory import LOCAL_COMPAT_PROFILE
    from lychd.domain.animation.schemas import OpenAIPortalConfig
    from lychd.domain.animation.services.adapters.surfaces import OpenAIPortal
    from lychd.extensions.builtin.animator.register import build_openai_portal

    portal = OpenAIPortalConfig.model_validate(
        {
            "name": f"test-{provider_name}",
            "provider_name": provider_name,
            "base_url": "http://provider.test/v1",
            "models": [{"id": model_id}],
        }
    )
    runtime = build_openai_portal(portal)

    assert isinstance(runtime, OpenAIPortal)
    model = runtime.connector.get_model(model_id=model_id)
    assert isinstance(model, OpenAIChatModel)
    assert model.system == expected_system
    assert model.profile.json_schema_transformer is not None
    assert model.profile.json_schema_transformer.__name__ == expected_transformer
    assert (model.profile is LOCAL_COMPAT_PROFILE) is (provider_name == "openai-compatible")


def test_openrouter_rejects_unqualified_model_id_when_portal_is_built() -> None:
    from lychd.domain.animation.schemas import OpenAIPortalConfig
    from lychd.extensions.builtin.animator.register import build_openai_portal

    portal = OpenAIPortalConfig.model_validate(
        {
            "name": "bad-openrouter",
            "provider_name": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "models": [{"id": "gpt-5.2"}],
        }
    )

    with pytest.raises(ValueError, match="provider/model"):
        build_openai_portal(portal)


def test_portal_factory_preserves_declared_responses_surface_at_hydration() -> None:
    from lychd.domain.animation.schemas import ModelSurface, OpenAIPortalConfig
    from lychd.domain.animation.services.adapters.surfaces import OpenAIPortal
    from lychd.extensions.builtin.animator.register import build_openai_portal

    portal = OpenAIPortalConfig.model_validate(
        {
            "name": "responses-openai",
            "models": [
                {
                    "id": "gpt-5.2",
                    "capabilities": {"surface": "responses"},
                }
            ],
        }
    )

    runtime = build_openai_portal(portal)

    assert isinstance(runtime, OpenAIPortal)
    assert runtime.connector.list_models()[0].surface is ModelSurface.RESPONSES
    assert isinstance(runtime.connector.get_model(), OpenAIResponsesModel)


@pytest.mark.parametrize("provider_name", ["google-gemini", "litellm", "ollama"])
def test_chat_only_provider_alias_rejects_responses_when_portal_is_built(provider_name: str) -> None:
    from lychd.domain.animation.schemas import OpenAIPortalConfig
    from lychd.extensions.builtin.animator.register import build_openai_portal

    portal = OpenAIPortalConfig.model_validate(
        {
            "name": f"bad-{provider_name}",
            "provider_name": provider_name,
            "base_url": "http://provider.test/v1",
            "models": [
                {
                    "id": "qualified/model",
                    "capabilities": {"surface": "responses"},
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="only the Chat surface"):
        build_openai_portal(portal)


@pytest.mark.asyncio
async def test_provider_profile_filters_payload_while_generic_compat_preserves_it() -> None:
    from lychd.domain.animation.links import Link
    from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

    request = [ModelRequest.user_text_prompt("hello")]
    request_parameters = ModelRequestParameters()

    portal = OpenAICompatibleConnector(
        kind="portal:openai",
        link=Link(up=True, activatable=False),
        base_url="https://api.openai.com/v1",
        default_model_id="gpt-5.2",
        provider_name="openai",
    ).get_model()
    assert isinstance(portal, OpenAIChatModel)
    portal_create = AsyncMock(return_value=object())
    cast("Any", portal.client.chat.completions).create = portal_create
    await cast("Any", portal)._completions_create(
        messages=request,
        stream=False,
        model_settings={"temperature": 0.4},
        model_request_parameters=request_parameters,
    )

    local = OpenAICompatibleConnector(
        kind="openai_compat",
        link=Link(up=True, activatable=False),
        base_url="http://localhost:8080/v1",
        default_model_id="gpt-5.2",
    ).get_model()
    assert isinstance(local, OpenAIChatModel)
    local_create = AsyncMock(return_value=object())
    cast("Any", local.client.chat.completions).create = local_create
    await cast("Any", local)._completions_create(
        messages=request,
        stream=False,
        model_settings={"temperature": 0.4},
        model_request_parameters=request_parameters,
    )

    assert portal_create.await_args is not None
    assert local_create.await_args is not None
    assert isinstance(portal_create.await_args.kwargs["temperature"], Omit)
    assert local_create.await_args.kwargs["temperature"] == 0.4
