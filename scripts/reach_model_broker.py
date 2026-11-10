"""Trusted host HTTP transport for one frozen operator model binding.

This module constructs no Core, Graph, registry or model runtime. The offline
native worker owns cognition; this broker performs only its closed HTTP dialect.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import time
from collections.abc import Callable
from typing import Any, cast

import httpx2

from lychd.compositions.reach.operator_model_wire import (
    MAX_MODEL_PAYLOAD_BYTES,
    OperatorConversationProfile,
    OperatorModelProbe,
    OperatorModelRequest,
    OperatorModelResponse,
    canonical_json,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_trace import TraceEmitter, TraceName, TraceSink
from lychd.compositions.reach.operator_wire import strict_json
from lychd.lib.http import create_async_http_client

MODEL_ENDPOINT = "http://127.0.0.1:28000"
MAX_MODEL_IDS = 32
MAX_REMOTE_MODEL_IDS = 4096
MAX_MODEL_ID_CHARS = 256
_ORIGIN = re.compile(
    r"^(?P<scheme>https?)://(?P<host>\[[0-9a-fA-F:.]+\]|[A-Za-z0-9.-]+)(?::(?P<port>[0-9]{1,5}))?(?P<path>(?:/[A-Za-z0-9._~-]+)*)$"
)
_API_KEY = re.compile(r"^[\x21-\x7e]{1,4096}$")


def is_loopback_endpoint(endpoint: str) -> bool:
    """Whether the endpoint is a plain-HTTP loopback IP literal, the original local road."""
    matched = _ORIGIN.fullmatch(endpoint)
    if matched is None or matched["scheme"] != "http":
        return False
    try:
        return ipaddress.ip_address(matched["host"].strip("[]")).is_loopback
    except ValueError:
        return False


def validate_endpoint(endpoint: str) -> str:
    """Admit a loopback HTTP origin or an HTTPS endpoint; caller frames cannot alter it.

    Plain HTTP is limited to a loopback IP literal with an explicit port and no path.
    HTTPS may name any host and an optional path prefix. Credentials, queries,
    fragments, trailing slashes and port zero are refused.
    """
    matched = _ORIGIN.fullmatch(endpoint)
    port = int(matched["port"]) if matched is not None and matched["port"] is not None else None
    if (
        matched is None
        or (port is not None and not 1 <= port <= 65535)  # noqa: PLR2004 - TCP port range
        or (matched["scheme"] == "http" and (port is None or matched["path"] or not is_loopback_endpoint(endpoint)))
    ):
        msg = "model_endpoint"
        raise ValueError(msg)
    return endpoint


def validate_api_key(value: str) -> str:
    """Admit one printable header-safe bearer credential without echoing it."""
    if _API_KEY.fullmatch(value) is None:
        msg = "model_api_key"
        raise ValueError(msg)
    return value


def _object(value: Any, code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(code)
    return cast("dict[str, Any]", value)


def _array(value: Any, code: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(code)
    return cast("list[Any]", value)


def _completion_content_state(message: dict[str, Any]) -> str:
    """Reduce an observed message field to a closed state without retaining its value."""
    content = message.get("content")
    if "content" not in message:
        return "missing"
    if content is None:
        return "null"
    if not isinstance(content, str):
        return "non_string"
    if not content:
        return "empty"
    return "text" if content.strip() else "blank"


def _completion_observation(value: dict[str, Any]) -> dict[str, str]:
    """Observe only finite categories from an actual parsed single-choice completion."""
    supplied = value.get("choices")
    if not isinstance(supplied, list):
        return {}
    choices = cast("list[object]", supplied)
    if len(choices) != 1 or not isinstance(choices[0], dict):
        return {}
    choice = cast("dict[str, Any]", choices[0])
    finish = choice.get("finish_reason")
    if "finish_reason" not in choice:
        reason = "missing"
    elif finish is None:
        reason = "null"
    elif isinstance(finish, str) and finish in {"stop", "length", "tool_calls", "function_call", "content_filter"}:
        reason = finish
    else:
        reason = "other"
    observation = {"completion_finish_reason": reason}
    supplied_message = choice.get("message")
    if isinstance(supplied_message, dict):
        observation["content_state"] = _completion_content_state(cast("dict[str, Any]", supplied_message))
    return observation


class OperatorModelBroker:
    """Serialize one bounded call without retries, proxies or lifecycle effects."""

    def __init__(
        self,
        profile: OperatorConversationProfile,
        *,
        endpoint: str = MODEL_ENDPOINT,
        transport: httpx2.AsyncBaseTransport | None = None,
        trace: TraceSink | None = None,
        api_key: str | None = None,
    ) -> None:
        """Bind transport to a frozen profile without opening any network connection."""
        self.profile = profile
        self.endpoint = validate_endpoint(endpoint)
        self._local = is_loopback_endpoint(self.endpoint)
        self._api_key = validate_api_key(api_key) if api_key is not None else None
        self.transport = transport
        self._busy = False
        self.trace = TraceEmitter("host", trace)
        self._active_request: OperatorModelRequest | None = None
        self._completion_metadata: dict[str, str] = {}

    def _observe(self, name: TraceName, **fields: Any) -> None:
        request = self._active_request
        binding = request.correlation.model_dump(exclude_none=True) if request and request.correlation else {}
        self.trace.record(name, call_id=request.call_id if request else None, **binding, **fields)

    async def _request(
        self,
        client: httpx2.AsyncClient,
        method: str,
        route: str,
        body: bytes | None = None,
        *,
        authorize: Callable[[], None] | None = None,
    ) -> Any:
        if authorize is not None:
            authorize()
        extensions = {"lychd_research_authorize": authorize} if authorize is not None else None
        started, status, size, outcome = time.monotonic(), None, 0, "error"
        operation = {"/health": "health", "/v1/models": "inventory", "/v1/chat/completions": "completion"}[route]
        try:
            async with client.stream(method, self.endpoint + route, content=body, extensions=extensions) as response:
                status = response.status_code
                response.raise_for_status()
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    msg = "model_response_encoding"
                    raise ValueError(msg)
                raw = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    raw.extend(chunk)
                    size = len(raw)
                    if size > MAX_MODEL_PAYLOAD_BYTES:
                        msg = "model_response_limit"
                        raise ValueError(msg)
                result = strict_json(bytes(raw)) if raw else None
                outcome = "ok"
                return result
        finally:
            self._observe(
                "model_http",
                status=outcome,
                operation=operation,
                http_status=status,
                bytes_count=size,
                duration_ms=min(86_400_000, int((time.monotonic() - started) * 1000)),
            )

    async def _probe(self, client: httpx2.AsyncClient) -> str:
        # A remote OpenAI-compatible API has no standard /health route; its inventory is the probe.
        if self._local:
            await self._request(client, "GET", "/health")
        value = _object(await self._request(client, "GET", "/v1/models"), "model_inventory")
        entries = _array(value.get("data"), "model_inventory")
        if len(entries) > (MAX_MODEL_IDS if self._local else MAX_REMOTE_MODEL_IDS):
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
        if len(ids) > MAX_MODEL_IDS:
            # A gateway catalogue can exceed the wire bound; the worker needs only its own model.
            ids = (self.profile.model_id,)
        return canonical_json(OperatorModelProbe(healthy=True, model_ids=ids).model_dump(mode="json"))

    async def _generate(
        self, client: httpx2.AsyncClient, payload: str, *, authorize: Callable[[], None] | None = None
    ) -> str:
        body = canonical_json(validate_generation_payload(self.profile, payload)).encode()
        if len(body) > MAX_MODEL_PAYLOAD_BYTES:
            msg = "model_request_limit"
            raise ValueError(msg)
        value = _object(
            await self._request(client, "POST", "/v1/chat/completions", body, authorize=authorize), "model_completion"
        )
        self._completion_metadata = _completion_observation(value)
        if not self.profile.serves(value.get("model")):
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

    async def handle(
        self, request: OperatorModelRequest, *, authorize: Callable[[], None] | None = None
    ) -> OperatorModelResponse:
        """Finish or cancel the HTTP context before releasing this one-call slot."""
        if self._busy or request.binding_digest != self.profile.digest:
            msg = "model_binding"
            raise ValueError(msg)
        self._busy = True
        self._active_request = request
        self._completion_metadata = {}
        started = time.monotonic()
        result: OperatorModelResponse | None = None
        self._observe("model_call", status="started", operation=request.operation)
        budget = min(5, self.profile.timeout_seconds) if request.operation == "probe" else self.profile.timeout_seconds
        try:
            async with (
                asyncio.timeout(budget),
                create_async_http_client(
                    transport=self.transport,
                    timeout=httpx2.Timeout(budget),
                    headers={
                        "Content-Type": "application/json",
                        "Accept-Encoding": "identity",
                        **({"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}),
                    },
                ) as client,
            ):
                payload = await (
                    self._probe(client)
                    if request.operation == "probe"
                    else self._generate(client, request.payload_json, authorize=authorize)
                )
            if authorize is not None:
                authorize()
            result = OperatorModelResponse(
                call_id=request.call_id, binding_digest=request.binding_digest, status="ok", payload_json=payload
            )
            return result  # noqa: TRY300 - the finally observer shares this guarded result boundary
        except (TimeoutError, httpx2.TimeoutException):
            result = OperatorModelResponse(
                call_id=request.call_id,
                binding_digest=request.binding_digest,
                status="unavailable",
                reason="model_timeout",
            )
            return result
        except (httpx2.HTTPError, LookupError):
            result = OperatorModelResponse(
                call_id=request.call_id,
                binding_digest=request.binding_digest,
                status="unavailable",
                reason="model_unavailable",
            )
            return result
        except (ValueError, TypeError, KeyError):
            result = OperatorModelResponse(
                call_id=request.call_id,
                binding_digest=request.binding_digest,
                status="error",
                reason="model_protocol",
            )
            return result
        finally:
            self._observe(
                "model_call",
                status=result.status if result else "cancelled",
                operation=request.operation,
                code=result.reason if result else None,
                duration_ms=min(86_400_000, int((time.monotonic() - started) * 1000)),
                **self._completion_metadata,
            )
            self._completion_metadata = {}
            self._active_request = None
            self._busy = False
