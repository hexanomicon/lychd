"""Production model-routing behavior."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import httpx2
import pytest
from pydantic_ai.messages import ModelMessage, ModelRequest
from pydantic_ai.models import ModelRequestParameters, override_allow_model_requests
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.profiles import DEFAULT_PROFILE
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.deps import LychDDeps
from lychd.agents.factory import AgentSpec, build_agent
from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC, default_forge

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pydantic_ai.profiles.openai import OpenAIModelProfile


def _model_transport(monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx2.Request], httpx2.Response]) -> None:
    """Keep production provider ownership while every model request stays in memory."""
    monkeypatch.setattr(
        "pydantic_ai.providers._openai_compatible.create_async_httpx2_client",
        lambda: httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
    )


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
        default_model_id="o3",
        provider_name="openai",
    )

    model = connector.get_model()
    profile = cast("OpenAIModelProfile", model.profile)

    assert model.profile is not LOCAL_COMPAT_PROFILE
    assert profile.get("thinking_always_enabled") is True
    assert profile.get("openai_supports_strict_tool_definition", True) is True


@pytest.mark.parametrize(
    ("provider_name", "declared_key", "expected_authorization"),
    [
        ("openai-compatible", None, "Bearer api-key-not-set"),
        ("openai", None, "Bearer api-key-not-set"),
        ("openai", "synthetic-declared-provider-token", "Bearer synthetic-declared-provider-token"),
    ],
)
@pytest.mark.asyncio
async def test_connector_authentication_uses_only_its_declared_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    provider_name: str,
    declared_key: str | None,
    expected_authorization: str,
) -> None:
    from lychd.domain.animation.links import Link
    from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

    requests: list[httpx2.Request] = []

    def capture(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://runtime.test/v1/chat/completions"
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "chatcmpl-auth-test",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            },
        )

    _model_transport(monkeypatch, capture)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-ambient-provider-token")
    monkeypatch.setenv("OPENAI_ORG_ID", "synthetic-ambient-organization")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "synthetic-ambient-project")
    monkeypatch.setenv("OPENAI_WEBHOOK_SECRET", "synthetic-ambient-webhook-secret")
    monkeypatch.setenv("OPENAI_ADMIN_KEY", "synthetic-ambient-admin-token")
    monkeypatch.setenv(
        "OPENAI_CUSTOM_HEADERS",
        "Authorization: Bearer synthetic-ambient-custom-token\n"
        "OpenAI-Organization: synthetic-ambient-custom-organization\n"
        "OpenAI-Project: synthetic-ambient-custom-project\n"
        "X-Ambient-Secret: synthetic-unrelated-secret",
    )
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(tmp_path))
    secret_name = "declared-provider" if declared_key is not None else None
    if secret_name is not None:
        (tmp_path / secret_name).write_text(cast("str", declared_key), encoding="utf-8")
    model = OpenAICompatibleConnector(
        link=Link(up=True),
        base_url="http://runtime.test/v1",
        default_model_id="test-model",
        provider_name=provider_name,
        api_key_secret_name=secret_name,
    ).get_model()
    assert isinstance(model, OpenAIChatModel)
    monkeypatch.setattr(model.client, "_platform", "Linux")

    with override_allow_model_requests(True):  # noqa: FBT003 - third-party positional API
        async with model:
            await model.request([ModelRequest.user_text_prompt("hello")], None, ModelRequestParameters())

    assert len(requests) == 1
    authorization = requests[0].headers["Authorization"]
    assert authorization == expected_authorization
    assert "synthetic-ambient-provider-token" not in authorization
    assert "OpenAI-Organization" not in requests[0].headers
    assert "OpenAI-Project" not in requests[0].headers
    assert "X-Ambient-Secret" not in requests[0].headers
    assert model.client.webhook_secret is None
    assert model.client.admin_api_key is None
    assert model.client.is_closed()


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
    # The model narrows native-tool support on a copied profile. Compare every
    # configured field, excluding that derived set, instead of object identity.
    expected_local = {**DEFAULT_PROFILE, **LOCAL_COMPAT_PROFILE}
    configured_profile = {**model.profile, "supported_native_tools": expected_local["supported_native_tools"]}
    assert (configured_profile == expected_local) is (provider_name == "openai-compatible")


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
    request_parameters = ModelRequestParameters(
        function_tools=[
            ToolDefinition(
                name="lookup",
                strict=True,
                parameters_json_schema={
                    "type": "object",
                    "properties": {"query": {"$ref": "#/$defs/Query"}},
                    "$defs": {"Query": {"type": "string"}},
                    "required": ["query"],
                    "additionalProperties": False,
                },
            )
        ]
    )

    def capture(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "POST"
        routes = {
            "http://provider.test/v1/chat/completions": "provider",
            "http://local.test/v1/chat/completions": "local",
        }
        name = routes[str(request.url)]
        assert name not in payloads
        payloads[name] = cast("dict[str, object]", json.loads(request.content))
        return httpx2.Response(200, json=response)

    _model_transport(monkeypatch, capture)
    portal = OpenAICompatibleConnector(
        link=Link(up=True),
        base_url="http://provider.test/v1",
        default_model_id="o3",
        provider_name="openai",
    ).get_model()
    assert isinstance(portal, OpenAIChatModel)
    monkeypatch.setattr(portal.client, "_platform", "Linux")

    local = OpenAICompatibleConnector(
        link=Link(up=True),
        base_url="http://local.test/v1",
        default_model_id="o3",
    ).get_model()
    assert isinstance(local, OpenAIChatModel)
    monkeypatch.setattr(local.client, "_platform", "Linux")

    response = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "o3",
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

    with (
        override_allow_model_requests(True),  # noqa: FBT003 - third-party positional API
    ):
        async with asyncio.timeout(2), portal, local:
            await portal.request(request, {"temperature": 0.4}, request_parameters)
            await local.request(request, {"temperature": 0.4}, request_parameters)

    portal_payload = payloads["provider"]
    local_payload = payloads["local"]
    assert portal_payload["messages"] == local_payload["messages"] == [{"role": "user", "content": "hello"}]
    assert "temperature" not in portal_payload
    assert local_payload["temperature"] == 0.4
    provider_tool = cast("list[dict[str, dict[str, object]]]", portal_payload["tools"])[0]["function"]
    local_tool = cast("list[dict[str, dict[str, object]]]", local_payload["tools"])[0]["function"]
    assert provider_tool["strict"] is True
    assert "strict" not in local_tool
    local_parameters = cast("dict[str, object]", local_tool["parameters"])
    assert "$defs" not in local_parameters
    assert local_parameters["properties"] == {"query": {"type": "string"}}
    assert local.profile.get("thinking_always_enabled") is False
    assert local.profile.get("supports_json_schema_output") is False
    assert local.profile.get("supports_inline_system_prompts") is True
    assert portal.client.is_closed()
    assert local.client.is_closed()
