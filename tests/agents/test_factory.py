"""Production model-routing behavior."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from typing import cast

import httpx
import pytest
import respx
from pydantic_ai.messages import ModelMessage, ModelRequest
from pydantic_ai.models import ModelRequestParameters, override_allow_model_requests
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.deps import LychDDeps
from lychd.agents.factory import AgentSpec, build_agent
from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC, default_forge


def test_forge_caches_by_complete_specification() -> None:
    forge = default_forge()

    first = forge.agent_for(THE_FIRST_ONE_SPEC)

    assert forge.agent_for(THE_FIRST_ONE_SPEC) is first
    assert forge.agent_for(replace(THE_FIRST_ONE_SPEC, max_tokens=1024)) is not first


def test_forge_rejects_an_unregistered_agent_name() -> None:
    forge = default_forge()

    with pytest.raises(KeyError, match="No agent builder registered"):
        forge.agent_for(replace(THE_FIRST_ONE_SPEC, name="unknown"))


def test_agent_construction_omits_mutating_toolset_without_write_authority() -> None:
    spec = AgentSpec(
        name="boundary",
        instructions_key="boundary",
        instructions="boundary",
        output_types=(str,),
        toolset_names=("writer",),
    )

    def writer() -> FunctionToolset[LychDDeps]:
        return FunctionToolset(id="writer")

    read_only = build_agent(spec, toolset_factories={"writer": writer}, mutating=frozenset({"writer"}))
    writable = build_agent(
        replace(spec, writes=True),
        toolset_factories={"writer": writer},
        mutating=frozenset({"writer"}),
    )

    assert all(getattr(toolset, "id", None) != "writer" for toolset in read_only.toolsets)
    assert any(getattr(toolset, "id", None) == "writer" for toolset in writable.toolsets)


def test_agent_construction_rejects_an_unknown_declared_toolset() -> None:
    spec = AgentSpec(
        name="boundary",
        instructions_key="boundary",
        instructions="boundary",
        output_types=(str,),
        toolset_names=("missing",),
    )

    with pytest.raises(KeyError, match="no registered factory"):
        build_agent(spec, toolset_factories={})


def test_provider_connector_retains_model_profile() -> None:
    from lychd.domain.animation.links import Link
    from lychd.domain.animation.model_factory import LOCAL_COMPAT_PROFILE
    from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

    connector = OpenAICompatibleConnector(
        link=Link(up=True),
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
    ("provider_name", "model_id", "expected_system"),
    [
        ("openai", "gpt-5.2", "openai"),
        ("google-gemini", "gemini-2.5-pro", "google-gla"),
        ("openrouter", "anthropic/claude-sonnet-4", "openrouter"),
        ("litellm", "google/gemini-2.5-pro", "litellm"),
        ("ollama", "qwen3:8b", "ollama"),
        ("openai-compatible", "qwen3:8b", "openai"),
    ],
)
def test_portal_factory_routes_provider_profile(
    provider_name: str,
    model_id: str,
    expected_system: str,
) -> None:
    from lychd.domain.animation.connectors import ModelConnector
    from lychd.domain.animation.model_factory import LOCAL_COMPAT_PROFILE
    from lychd.domain.animation.schemas import OpenAIPortalConfig
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

    assert isinstance(runtime.connector, ModelConnector)
    model = runtime.connector.get_model(model_id=model_id)
    assert isinstance(model, OpenAIChatModel)
    assert model.system == expected_system
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
    from lychd.domain.animation.connectors import ModelConnector
    from lychd.domain.animation.schemas import OpenAIPortalConfig
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

    assert isinstance(runtime.connector, ModelConnector)
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
async def test_provider_profile_filters_payload_while_generic_compat_preserves_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lychd.domain.animation.links import Link
    from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

    request: list[ModelMessage] = [ModelRequest.user_text_prompt("hello")]
    request_parameters = ModelRequestParameters()

    portal = OpenAICompatibleConnector(
        link=Link(up=True),
        base_url="http://provider.test/v1",
        default_model_id="gpt-5.2",
        provider_name="openai",
    ).get_model()
    assert isinstance(portal, OpenAIChatModel)
    monkeypatch.setattr(portal.client, "_platform", "Linux")

    local = OpenAICompatibleConnector(
        link=Link(up=True),
        base_url="http://local.test/v1",
        default_model_id="gpt-5.2",
    ).get_model()
    assert isinstance(local, OpenAIChatModel)
    monkeypatch.setattr(local.client, "_platform", "Linux")

    response = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-5.2",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }
    payloads: dict[str, dict[str, object]] = {}

    def capture_provider(request: httpx.Request) -> httpx.Response:
        payloads["provider"] = cast("dict[str, object]", json.loads(request.content))
        return httpx.Response(200, json=response)

    def capture_local(request: httpx.Request) -> httpx.Response:
        payloads["local"] = cast("dict[str, object]", json.loads(request.content))
        return httpx.Response(200, json=response)

    with (
        override_allow_model_requests(True),  # noqa: FBT003 - third-party positional API
        respx.mock(assert_all_called=True, assert_all_mocked=True) as router,
    ):
        router.post("http://provider.test/v1/chat/completions").mock(side_effect=capture_provider)
        router.post("http://local.test/v1/chat/completions").mock(side_effect=capture_local)
        async with asyncio.timeout(2):
            await portal.request(request, {"temperature": 0.4}, request_parameters)
            await local.request(request, {"temperature": 0.4}, request_parameters)

    portal_payload = payloads["provider"]
    local_payload = payloads["local"]
    assert portal_payload["messages"] == local_payload["messages"] == [{"role": "user", "content": "hello"}]
    assert "temperature" not in portal_payload
    assert local_payload["temperature"] == 0.4
