"""Real model client routing and retransmission with an inert transport boundary."""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

import httpx2
import pytest
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.messages import ModelRequest, TextPart
from pydantic_ai.models import ModelRequestParameters, override_allow_model_requests
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel

from lychd.domain.animation.capabilities import (
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
)
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import ModelSurface
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

if TYPE_CHECKING:
    from pydantic_ai.models import Model


def _model(surface: ModelSurface, *, model_id: str = "synthetic-model") -> OpenAIChatModel | OpenAIResponsesModel:
    model = OpenAICompatibleConnector(
        link=Link(up=True),
        base_url="http://127.0.0.1:23117/v1",
        default_model_id=model_id,
        default_surface=surface,
    ).get_model()
    assert isinstance(model, OpenAIChatModel | OpenAIResponsesModel)
    return model


def _answer(surface: ModelSurface) -> httpx2.Response:
    if surface is ModelSurface.RESPONSES:
        return httpx2.Response(
            200,
            json={
                "id": "resp_transport",
                "object": "response",
                "created_at": 1,
                "model": "synthetic-model",
                "status": "completed",
                "output": [],
            },
        )
    return httpx2.Response(
        200,
        json={
            "id": "chatcmpl-transport",
            "object": "chat.completion",
            "created": 1,
            "model": "synthetic-model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", [ModelSurface.CHAT, ModelSurface.RESPONSES])
async def test_model_ignores_ambient_proxies_after_client_reentry(
    monkeypatch: pytest.MonkeyPatch, surface: ModelSurface
) -> None:
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(name, "http://undeclared-proxy.test:8888")
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(name, "")
    pools: list[str] = []
    bodies: list[bytes] = []

    async def observe(transport: httpx2.AsyncHTTPTransport, request: httpx2.Request) -> httpx2.Response:
        pools.append(type(transport._pool).__name__)
        bodies.append(await request.aread())
        return _answer(surface)

    monkeypatch.setattr(httpx2.AsyncHTTPTransport, "handle_async_request", observe)
    # A positive control proves the environment would route even this loopback URL through the proxy.
    async with httpx2.AsyncClient() as ambient:
        await ambient.post("http://127.0.0.1:23117/v1/control", content=b"control")
    assert pools.pop() == "AsyncHTTPProxy"
    bodies.clear()

    model = _model(surface)
    monkeypatch.setattr(model.client, "_platform", "Linux")
    for _ in range(2):
        with override_allow_model_requests(True):  # noqa: FBT003 - third-party positional API
            async with model:
                await model.request(
                    [ModelRequest.user_text_prompt("synthetic-private-input")], None, ModelRequestParameters()
                )
        assert model.client.is_closed()
    assert pools == ["AsyncConnectionPool", "AsyncConnectionPool"]
    assert all(b"synthetic-private-input" in body for body in bodies)


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", [ModelSurface.CHAT, ModelSurface.RESPONSES])
@pytest.mark.parametrize("failure", ["server", "disconnect", "redirect"])
async def test_model_failure_does_not_retransmit_or_follow_redirect(
    monkeypatch: pytest.MonkeyPatch, surface: ModelSurface, failure: str
) -> None:
    requests: list[httpx2.Request] = []

    async def fail(_transport: httpx2.AsyncHTTPTransport, request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if failure == "disconnect":
            message = "synthetic lost acknowledgement"
            raise httpx2.ReadError(message, request=request)
        if failure == "redirect":
            return httpx2.Response(307, headers={"Location": "https://undeclared-provider.test/v1/other"})
        return httpx2.Response(500, json={"error": {"message": "synthetic failure"}})

    monkeypatch.setattr(httpx2.AsyncHTTPTransport, "handle_async_request", fail)
    model = _model(surface)
    monkeypatch.setattr(model.client, "_platform", "Linux")
    with override_allow_model_requests(True):  # noqa: FBT003 - third-party positional API
        async with model:
            with pytest.raises(ModelAPIError):
                await model.request([ModelRequest.user_text_prompt("synthetic-input")], None, ModelRequestParameters())
    assert len(requests) == 1
    assert requests[0].url.host == "127.0.0.1"
    assert model.client.is_closed()


def _qwen_grant(model: Model | None, thinking: Literal["qwen3.8-non-thinking"] | None) -> CapabilityGrant:
    spec = CapabilitySpec.model_validate(
        {
            "key": "desk:chat:Qwen3.8-27B",
            "animator_name": "desk",
            "source_kind": "soulstone",
            "runtime": "vllm",
            "family": "chat",
            "model_id": "Qwen3.8-27B",
            "generation_profile": {"max_tokens": 32, "temperature": 0.2, "thinking": thinking},
        }
    )
    return CapabilityGrant(
        spec=spec,
        state=CapabilityState(capability_key=spec.key, phase=CapabilityPhase.WARM),
        lease=GrantLease(grant_id="test", holder="run:test", issued_at=datetime(2026, 10, 17, tzinfo=UTC)),
        model=model,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("thinking", [None, "qwen3.8-non-thinking"])
@pytest.mark.parametrize("streaming", [False, True])
async def test_qwen_policy_reaches_exact_real_sdk_wire_without_changing_defaults(
    monkeypatch: pytest.MonkeyPatch,
    thinking: Literal["qwen3.8-non-thinking"] | None,
    *,
    streaming: bool,
) -> None:
    requests: list[httpx2.Request] = []

    async def answer(_transport: httpx2.AsyncHTTPTransport, request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        expected: dict[str, object] = {
            "model": "Qwen3.8-27B",
            "messages": [{"role": "user", "content": "synthetic-input"}],
            "stream": streaming,
            "max_completion_tokens": 32,
            "temperature": 0.2,
        }
        if streaming:
            expected["stream_options"] = {"include_usage": True}
        if thinking is not None:
            expected["chat_template_kwargs"] = {"enable_thinking": False}
        assert json.loads(await request.aread()) == expected
        assert request.method == "POST"
        assert str(request.url) == "http://127.0.0.1:23117/v1/chat/completions"
        if streaming:
            chunk = {
                "id": "chatcmpl-policy",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "Qwen3.8-27B",
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            }
            return httpx2.Response(
                200,
                headers={"content-type": "text/event-stream"},
                text=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n",
            )
        payload = json.loads(_answer(ModelSurface.CHAT).content)
        payload["model"] = "Qwen3.8-27B"
        return httpx2.Response(200, json=payload)

    monkeypatch.setattr(httpx2.AsyncHTTPTransport, "handle_async_request", answer)
    model = _model(ModelSurface.CHAT, model_id="Qwen3.8-27B")
    monkeypatch.setattr(model.client, "_platform", "Linux")
    grant = _qwen_grant(model, thinking)
    with override_allow_model_requests(True):  # noqa: FBT003 - third-party positional API
        async with model:
            if streaming:
                async with model.request_stream(
                    [ModelRequest.user_text_prompt("synthetic-input")], grant.model_settings(), ModelRequestParameters()
                ) as stream:
                    async for _event in stream:
                        pass
                    result = stream.get()
            else:
                result = await model.request(
                    [ModelRequest.user_text_prompt("synthetic-input")], grant.model_settings(), ModelRequestParameters()
                )
    assert [part.content for part in result.parts if isinstance(part, TextPart)] == ["ok"]
    assert result.finish_reason == "stop"
    assert model.settings is None
    assert len(requests) == 1
    assert model.client.is_closed()


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", [ModelSurface.RESPONSES, ModelSurface.CHAT])
async def test_qwen_policy_refuses_a_changed_hydrated_surface_or_identity_before_transmission(
    monkeypatch: pytest.MonkeyPatch, surface: ModelSurface
) -> None:
    requests: list[httpx2.Request] = []

    async def forbidden(_transport: httpx2.AsyncHTTPTransport, request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        pytest.fail("unqualified hydrated model transmitted")

    monkeypatch.setattr(httpx2.AsyncHTTPTransport, "handle_async_request", forbidden)
    model = _model(surface, model_id="Qwen3.8-27B" if surface is ModelSurface.RESPONSES else "other")
    grant = _qwen_grant(model, "qwen3.8-non-thinking")
    with override_allow_model_requests(True):  # noqa: FBT003 - third-party positional API
        async with model:
            with pytest.raises(CapabilityUnavailable, match="hydrated Chat model"):
                await model.request(
                    [ModelRequest.user_text_prompt("synthetic-input")], grant.model_settings(), ModelRequestParameters()
                )
    assert requests == []
    assert model.client.is_closed()
