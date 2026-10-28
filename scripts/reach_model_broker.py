"""Trusted host HTTP transport for one frozen operator model binding.

This module constructs no Core, Graph, registry or model runtime. The offline
native worker owns cognition; this broker performs only its closed HTTP dialect.
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

import httpx

from lychd.compositions.reach.operator_model_wire import (
    MAX_MODEL_PAYLOAD_BYTES,
    OperatorConversationProfile,
    OperatorModelProbe,
    OperatorModelRequest,
    OperatorModelResponse,
    canonical_json,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_wire import strict_json

MODEL_ENDPOINT = "http://127.0.0.1:28000"
MAX_MODEL_IDS = 32
MAX_MODEL_ID_CHARS = 256


def validate_endpoint(endpoint: str) -> str:
    """Pin the one literal local transport; caller frames cannot alter its road."""
    if endpoint != MODEL_ENDPOINT:
        msg = "model_endpoint"
        raise ValueError(msg)
    return endpoint


def _object(value: Any, code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(code)
    return cast("dict[str, Any]", value)


def _array(value: Any, code: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(code)
    return cast("list[Any]", value)


class OperatorModelBroker:
    """Serialize one bounded call without retries, proxies or lifecycle effects."""

    def __init__(
        self,
        profile: OperatorConversationProfile,
        *,
        endpoint: str = MODEL_ENDPOINT,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Bind transport to a frozen profile without opening any network connection."""
        self.profile = profile
        self.endpoint = validate_endpoint(endpoint)
        self.transport = transport
        self._busy = False

    async def _request(self, client: httpx.AsyncClient, method: str, route: str, body: bytes | None = None) -> Any:
        async with client.stream(method, self.endpoint + route, content=body) as response:
            response.raise_for_status()
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                msg = "model_response_encoding"
                raise ValueError(msg)
            raw = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=8192):
                raw.extend(chunk)
                if len(raw) > MAX_MODEL_PAYLOAD_BYTES:
                    msg = "model_response_limit"
                    raise ValueError(msg)
            return strict_json(bytes(raw)) if raw else None

    async def _probe(self, client: httpx.AsyncClient) -> str:
        await self._request(client, "GET", "/health")
        value = _object(await self._request(client, "GET", "/v1/models"), "model_inventory")
        entries = _array(value.get("data"), "model_inventory")
        if len(entries) > MAX_MODEL_IDS:
            msg = "model_inventory"
            raise ValueError(msg)
        model_ids: list[str] = []
        for item in entries:
            record = _object(item, "model_inventory")
            identity = record.get("id")
            if not isinstance(identity, str):
                msg = "model_inventory"
                raise TypeError(msg)
            if not 1 <= len(identity) <= MAX_MODEL_ID_CHARS:
                msg = "model_inventory"
                raise ValueError(msg)
            model_ids.append(identity)
        ids = tuple(model_ids)
        if self.profile.model_id not in ids:
            msg = "model_identity"
            raise LookupError(msg)
        return canonical_json(OperatorModelProbe(healthy=True, model_ids=ids).model_dump(mode="json"))

    async def _generate(self, client: httpx.AsyncClient, payload: str) -> str:
        body = canonical_json(validate_generation_payload(self.profile, payload)).encode()
        if len(body) > MAX_MODEL_PAYLOAD_BYTES:
            msg = "model_request_limit"
            raise ValueError(msg)
        value = _object(await self._request(client, "POST", "/v1/chat/completions", body), "model_completion")
        if value.get("model") != self.profile.model_id:
            msg = "model_completion"
            raise ValueError(msg)
        choices = _array(value.get("choices"), "model_choices")
        if len(choices) != 1:
            msg = "model_choices"
            raise ValueError(msg)
        choice = _object(choices[0], "model_choices")
        message = _object(choice.get("message"), "model_completion")
        if (
            message.get("role") != "assistant"
            or not isinstance(message.get("content"), str)
            or message.get("tool_calls")
            or message.get("function_call")
            or choice.get("finish_reason") in {"tool_calls", "function_call"}
        ):
            msg = "model_tool_result"
            raise ValueError(msg)
        return canonical_json(value)

    async def handle(self, request: OperatorModelRequest) -> OperatorModelResponse:
        """Finish or cancel the HTTP context before releasing this one-call slot."""
        if self._busy or request.binding_digest != self.profile.digest:
            msg = "model_binding"
            raise ValueError(msg)
        self._busy = True
        budget = min(5, self.profile.timeout_seconds) if request.operation == "probe" else self.profile.timeout_seconds
        try:
            async with (
                asyncio.timeout(budget),
                httpx.AsyncClient(
                    transport=self.transport,
                    timeout=httpx.Timeout(budget),
                    follow_redirects=False,
                    trust_env=False,
                    headers={"Content-Type": "application/json", "Accept-Encoding": "identity"},
                ) as client,
            ):
                payload = await (
                    self._probe(client)
                    if request.operation == "probe"
                    else self._generate(client, request.payload_json)
                )
            return OperatorModelResponse(
                call_id=request.call_id, binding_digest=request.binding_digest, status="ok", payload_json=payload
            )
        except (TimeoutError, httpx.TimeoutException):
            return OperatorModelResponse(
                call_id=request.call_id,
                binding_digest=request.binding_digest,
                status="unavailable",
                reason="model_timeout",
            )
        except (httpx.HTTPError, LookupError):
            return OperatorModelResponse(
                call_id=request.call_id,
                binding_digest=request.binding_digest,
                status="unavailable",
                reason="model_unavailable",
            )
        except (ValueError, TypeError, KeyError):
            return OperatorModelResponse(
                call_id=request.call_id,
                binding_digest=request.binding_digest,
                status="error",
                reason="model_protocol",
            )
        finally:
            self._busy = False
