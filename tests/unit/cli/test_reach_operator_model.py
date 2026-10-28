"""Closed host transport and pipe routing, with no live model or container daemon."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import httpx
import pytest
from scripts import reach_operator as operator
from scripts.reach_model_broker import OperatorModelBroker, validate_endpoint

from lychd.compositions.reach.operator_model_wire import (
    MAX_MODEL_PAYLOAD_BYTES,
    OperatorConversationProfile,
    OperatorModelRequest,
    canonical_json,
)


def profile() -> OperatorConversationProfile:
    return OperatorConversationProfile(persona_name="Fixture", persona_instructions="Answer plainly.")


def request(operation: Literal["probe", "generate"] = "generate", **changes: Any) -> OperatorModelRequest:
    selected = profile()
    body: dict[str, Any] = {
        "model": selected.model_id,
        "messages": [{"role": "system", "content": "Answer plainly."}, {"role": "user", "content": "Hello"}],
        "max_tokens": selected.max_tokens,
        "temperature": selected.temperature,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    body.update(changes)
    return OperatorModelRequest(
        call_id=str(uuid4()),
        binding_digest=selected.digest,
        operation=operation,
        payload_json="{}" if operation == "probe" else canonical_json(body),
    )


def completion(**changes: Any) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": "Hello back"}
    message.update(changes)
    return {"model": "Qwen3.8-27B", "choices": [{"message": message, "finish_reason": "stop"}]}


@pytest.mark.asyncio
async def test_fresh_probe_exact_model_and_one_closed_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://foreign.invalid")
    observed: list[httpx.Request] = []

    def handle(value: httpx.Request) -> httpx.Response:
        observed.append(value)
        assert str(value.url).startswith("http://127.0.0.1:28000/")
        assert "authorization" not in value.headers
        if value.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if value.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "Qwen3.8-27B"}]})
        assert value.method == "POST"
        assert value.url.path == "/v1/chat/completions"
        body = json.loads(value.content)
        assert set(body) == {"model", "messages", "max_tokens", "temperature", "stream", "chat_template_kwargs"}
        assert body["chat_template_kwargs"] == {"enable_thinking": False}
        return httpx.Response(200, json=completion())

    broker = OperatorModelBroker(profile(), transport=httpx.MockTransport(handle))
    for _ in range(2):
        result = await broker.handle(request("probe"))
        assert result.status == "ok"
        assert json.loads(result.payload_json) == {"healthy": True, "model_ids": ["Qwen3.8-27B"]}
    result = await broker.handle(request())
    assert result.status == "ok"
    assert json.loads(result.payload_json)["choices"][0]["message"]["content"] == "Hello back"
    assert [item.url.path for item in observed] == [
        "/health",
        "/v1/models",
        "/health",
        "/v1/models",
        "/v1/chat/completions",
    ]


@pytest.mark.parametrize(
    "changes", [{"model": "other"}, {"tools": []}, {"headers": {"X-Test": "bad"}}, {"max_tokens": 2048}]
)
@pytest.mark.asyncio
async def test_forbidden_generation_fields_never_reach_http(changes: dict[str, Any]) -> None:
    def handle(_value: httpx.Request) -> httpx.Response:
        pytest.fail("Unadmitted payload reached HTTP")

    broker = OperatorModelBroker(profile(), transport=httpx.MockTransport(handle))
    result = await broker.handle(request(**changes))
    assert result.status == "error"
    assert result.reason == "model_protocol"
    assert result.payload_json == "{}"


@pytest.mark.parametrize("scenario", ["redirect", "wrong_model", "oversized", "tool_calls", "timeout"])
@pytest.mark.asyncio
async def test_foreign_failure_is_bounded_content_free_and_never_retried(scenario: str) -> None:
    calls = 0

    def handle(value: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if scenario == "redirect":
            return httpx.Response(307, headers={"Location": "http://foreign.invalid"})
        if scenario == "timeout":
            message = "private foreign diagnostic"
            raise httpx.ReadTimeout(message, request=value)
        if scenario == "oversized":
            return httpx.Response(200, content=b"x" * (MAX_MODEL_PAYLOAD_BYTES + 1))
        body = completion(tool_calls=[{"function": {"name": "unsafe"}}]) if scenario == "tool_calls" else completion()
        if scenario == "wrong_model":
            body["model"] = "other"
        return httpx.Response(200, json=body)

    result = await OperatorModelBroker(profile(), transport=httpx.MockTransport(handle)).handle(request())
    assert calls == 1
    assert result.status in {"unavailable", "error"}
    assert result.payload_json == "{}"
    assert "private" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_cancellation_joins_http_and_releases_single_outstanding_slot() -> None:
    entered, settled = asyncio.Event(), asyncio.Event()

    async def handle(_value: httpx.Request) -> httpx.Response:
        if settled.is_set():
            return httpx.Response(200, json=completion())
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            settled.set()
        return httpx.Response(200, json=completion())

    broker = OperatorModelBroker(profile(), transport=httpx.MockTransport(handle))
    task = asyncio.create_task(broker.handle(request()))
    await entered.wait()
    with pytest.raises(ValueError, match="model_binding"):
        await broker.handle(request())
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert settled.is_set()
    resumed = await broker.handle(request())
    assert resumed.status == "ok"


@pytest.mark.parametrize(("operation", "profile_timeout", "expected_budget"), [("generate", 5, 5), ("probe", 60, 5)])
@pytest.mark.asyncio
async def test_profile_deadline_and_probe_cap_retire_http_before_response(
    monkeypatch: pytest.MonkeyPatch,
    operation: Literal["probe", "generate"],
    profile_timeout: int,
    expected_budget: int,
) -> None:
    observed: list[int] = []
    settled = asyncio.Event()
    original_timeout = asyncio.timeout

    @asynccontextmanager
    async def immediate_timeout(delay: int) -> AsyncGenerator[None]:
        observed.append(delay)
        async with original_timeout(0):
            yield

    async def handle(value: httpx.Request) -> httpx.Response:
        assert value.extensions["timeout"] == dict.fromkeys(("connect", "read", "write", "pool"), expected_budget)
        try:
            await asyncio.Event().wait()
        finally:
            settled.set()
        return httpx.Response(200, json=completion())

    selected = profile().model_copy(update={"timeout_seconds": profile_timeout})
    frame = request(operation).model_copy(update={"binding_digest": selected.digest})
    monkeypatch.setattr("scripts.reach_model_broker.asyncio.timeout", immediate_timeout)
    response = await OperatorModelBroker(selected, transport=httpx.MockTransport(handle)).handle(frame)
    assert observed == [expected_budget]
    assert settled.is_set()
    assert response.status == "unavailable"
    assert response.reason == "model_timeout"


class Writer:
    def __init__(self) -> None:
        self.raw = bytearray()

    def write(self, raw: bytes) -> None:
        self.raw.extend(raw)

    async def drain(self) -> None:
        return


@pytest.mark.asyncio
async def test_multiplexer_keeps_model_payload_off_discord_pipe_and_refuses_unknown_frames() -> None:
    model_call = request()
    reader = asyncio.StreamReader(limit=operator.WIRE_LIMIT)
    reader.feed_data(b'{"kind":"ready"}\n' + model_call.model_dump_json().encode() + b'\n{"kind":"result"}\n')
    reader.feed_eof()
    edge, core = Writer(), Writer()
    broker = OperatorModelBroker(
        profile(), transport=httpx.MockTransport(lambda _value: httpx.Response(200, json=completion()))
    )
    await operator.model_relay(reader, edge, core, broker)  # type: ignore[arg-type] - write-only pipe fixtures
    assert edge.raw == b'{"kind":"ready"}\n{"kind":"result"}\n'
    response = json.loads(core.raw)
    assert response["kind"] == "model_response"
    assert response["call_id"] == model_call.call_id
    reader = asyncio.StreamReader()
    reader.feed_data(b'{"kind":"execute"}\n')
    reader.feed_eof()
    with pytest.raises(ValueError, match="operator_core_frame"):
        await operator.model_relay(reader, edge, core, broker)  # type: ignore[arg-type] - write-only pipe fixtures


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://localhost:28000",
        "http://127.0.0.1:28000/",
        "http://127.0.0.1:28000?q=1",
        "https://127.0.0.1:28000",
        "http://user:pass@127.0.0.1:28000",
    ],
)
def test_endpoint_is_one_literal_fixed_road(endpoint: str) -> None:
    with pytest.raises(ValueError, match="model_endpoint"):
        validate_endpoint(endpoint)


def test_profile_is_frozen_worker_only_and_publication_mount_is_edge_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.unit.cli.test_reach_operator import files

    policy, token, images, state = files(tmp_path)
    selected = tmp_path / "conversation.json"
    operator.write_private(selected, profile().model_dump_json().encode())
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "manifest.json").write_text("{}")
    publications = tmp_path / "publications"
    observed: list[list[str]] = []
    original = operator.read_regular

    def read(path: Path, limit: int, *, private: bool = False) -> bytes:
        assert path != token
        return original(path, limit, private=private)

    async def supervise(
        _engine: str,
        commands: tuple[list[str], list[str]],
        _ids: tuple[Path, Path],
        *,
        broker: OperatorModelBroker,
    ) -> int:
        observed.extend(commands)
        core, edge = commands
        mount = next(item for item in core if ":/run/reach/conversation.json:ro" in item)
        frozen = Path(mount.split(":", 1)[0])
        assert frozen != selected
        assert await asyncio.to_thread(frozen.read_bytes) == profile().model_dump_json().encode()
        metadata = await asyncio.to_thread(frozen.stat)
        assert metadata.st_mode & 0o777 == 0o600
        assert broker.profile.digest == profile().digest
        assert str(selected) not in " ".join(core + edge)
        assert "conversation.json" not in " ".join(edge)
        return 0

    monkeypatch.setattr(operator, "read_regular", read)
    monkeypatch.setattr(operator, "supervise", supervise)
    args = operator.parser().parse_args(
        [
            "run",
            "--policy",
            str(policy),
            "--token-file",
            str(token),
            "--images",
            str(images),
            "--state-dir",
            str(state),
            "--corpus-dir",
            str(corpus),
            "--conversation-profile",
            str(selected),
            "--publications-dir",
            str(publications),
            "--publication-channel",
            "104",
            "--command-name",
            "nadir",
        ]
    )
    assert operator.run_containers(args) == 0
    core, edge = observed
    assert "--network=none" in core
    assert "--conversation-profile" in core
    assert "--conversation" in edge
    assert str(publications) not in " ".join(core)
    assert f"{publications}:/state/publications:rw,Z" in edge
    assert "--publication-channel" in edge
    assert edge[edge.index("--command-name") + 1] == "nadir"


@pytest.mark.parametrize(
    "frame", [b'{"kind":"model_response"}\n', b'{"kind":"model_request"}\n', b'{"kind":"request"}\n']
)
@pytest.mark.asyncio
async def test_conversation_edge_cannot_inject_model_frames_or_invalid_requests(frame: bytes) -> None:
    reader = asyncio.StreamReader(limit=operator.WIRE_LIMIT)
    reader.feed_data(frame)
    reader.feed_eof()
    core = Writer()
    with pytest.raises(ValueError, match="validation error"):
        await operator.relay(reader, core, requests_only=True)  # type: ignore[arg-type] - write-only pipe fixture
    assert core.raw == b""
