"""Closed Podman model transport: mocked processes, no daemon or network."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator
from typing import Any, cast
from unittest.mock import AsyncMock

import httpx
import pytest
from scripts import reach_podman_model as podman


def frame(body: bytes = b'{"status":"ok"}', status: Any = 200, **extra: Any) -> bytes:
    return json.dumps({"status": status, "body": base64.b64encode(body).decode(), **extra}).encode()


class Process:
    def __init__(
        self, output: bytes | None = None, *, returncode: int = 0, error: Exception | None = None, block: bool = False
    ) -> None:
        self.output = frame() if output is None else output
        self.returncode: int | None = None if block or error is not None else returncode
        self.error = error
        self.block = block
        self.input: bytes | None = None
        self.entered, self.settled = asyncio.Event(), asyncio.Event()
        self.terminated = self.killed = False
        self.wait_calls = 0
        self.wait_timeout_once = False

    async def communicate(self, input_bytes: bytes | None = None) -> tuple[bytes, bytes]:
        self.input = input_bytes
        self.entered.set()
        try:
            if self.error is not None:
                error, self.error = self.error, None
                raise error
            if self.block:
                await asyncio.Event().wait()
            return self.output, b""
        finally:
            self.settled.set()

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    async def wait(self) -> int:
        self.wait_calls += 1
        if self.wait_timeout_once and self.wait_calls == 1:
            message = "private process diagnostic"
            raise TimeoutError(message)
        return self.returncode or 0


@pytest.mark.parametrize(
    ("method", "path"), [("GET", "/health"), ("GET", "/v1/models"), ("POST", "/v1/chat/completions")]
)
@pytest.mark.asyncio
async def test_only_closed_argv_and_bounded_stdin_carry_request(
    monkeypatch: pytest.MonkeyPatch, method: str, path: str
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://private-proxy.invalid")
    monkeypatch.setenv("NADIR_PROCESS_TEST_SECRET", "private inherited credential")
    environment = {"HOME": "/fixture/home", "XDG_RUNTIME_DIR": "/fixture/runtime", "PATH": "/bin", "LANG": "C"}
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    processes = [Process(), Process()]
    factory = AsyncMock(side_effect=processes)
    transport = podman.PodmanModelTransport(process_factory=factory)
    body = b'{"messages":[{"content":"private prompt"}]}' if method == "POST" else b""
    contents = (body, b"x" * podman.MAX_BODY_BYTES if method == "POST" else b"")
    for process, content in zip(processes, contents, strict=True):
        request = httpx.Request(method, f"http://127.0.0.1:28000{path}", content=content)
        response = await transport.handle_async_request(request)
        assert response.status_code == 200
        assert response.content == b'{"status":"ok"}'
        assert process.input is not None
        assert len(process.input) <= podman.MAX_FRAME_BYTES
        packet = json.loads(process.input)
        assert set(packet) == {"method", "path", "body"}
        assert packet["method"] == method
        assert packet["path"] == path
        assert base64.b64decode(packet["body"], validate=True) == content
    first, second = factory.await_args_list
    assert first.args == second.args
    assert first.args[:7] == ("podman", "exec", "--interactive", "lychd-night-qwen38", "python3", "-I", "-c")
    assert len(first.args) == 8
    assert isinstance(first.args[7], str)
    for call in factory.await_args_list:
        assert call.kwargs["stdin"] == asyncio.subprocess.PIPE
        assert call.kwargs["stdout"] == asyncio.subprocess.PIPE
        assert call.kwargs["stderr"] == asyncio.subprocess.DEVNULL
        assert set(call.kwargs["env"]) <= {"HOME", "XDG_RUNTIME_DIR", "PATH", "LANG"}
        assert "private" not in repr((call.args, call.kwargs["env"]))
        assert 0 < call.kwargs["limit"] <= podman.MAX_FRAME_BYTES + 1


@pytest.mark.parametrize(
    ("method", "url", "headers", "body"),
    [
        ("PUT", "http://127.0.0.1:28000/health", {}, b""),
        ("POST", "http://127.0.0.1:28000/health", {}, b""),
        ("GET", "http://127.0.0.1:28000/v1/chat/completions", {}, b""),
        ("GET", "http://127.0.0.1:28000/other", {}, b""),
        ("GET", "https://127.0.0.1:28000/health", {}, b""),
        ("GET", "http://localhost:28000/health", {}, b""),
        ("GET", "http://127.0.0.1:28001/health", {}, b""),
        ("GET", "http://user:password@127.0.0.1:28000/health", {}, b""),
        ("GET", "http://127.0.0.1:28000/health?private=1", {}, b""),
        ("GET", "http://127.0.0.1:28000/health#private", {}, b""),
        ("GET", "http://127.0.0.1:28000/health", {"Authorization": "private"}, b""),
        ("GET", "http://127.0.0.1:28000/health", {"Proxy-Authorization": "private"}, b""),
        ("GET", "http://127.0.0.1:28000/health", {"Cookie": "private"}, b""),
        ("GET", "http://127.0.0.1:28000/health", {"X-API-Key": "private"}, b""),
        ("GET", "http://127.0.0.1:28000/health", {"X-Unadmitted": "private"}, b""),
        ("GET", "http://127.0.0.1:28000/health", {}, b"private"),
        ("POST", "http://127.0.0.1:28000/v1/chat/completions", {}, b"x" * 49_153),
    ],
)
@pytest.mark.asyncio
async def test_unadmitted_request_never_starts_process(
    method: str, url: str, headers: dict[str, str], body: bytes
) -> None:
    factory = AsyncMock()
    request = httpx.Request(method, url, headers=headers, content=body)
    with pytest.raises(httpx.TransportError, match=r"^model_podman_request$"):
        await podman.PodmanModelTransport(process_factory=factory).handle_async_request(request)
    factory.assert_not_awaited()


@pytest.mark.asyncio
async def test_streamed_request_stops_at_cumulative_limit_before_spawn() -> None:
    consumed: list[int] = []

    async def chunks() -> AsyncIterator[bytes]:
        for index, chunk in enumerate((b"x" * podman.MAX_BODY_BYTES, b"x", b"unread")):
            consumed.append(index)
            yield chunk

    factory = AsyncMock()
    request = httpx.Request("POST", "http://127.0.0.1:28000/v1/chat/completions", content=chunks())
    with pytest.raises(httpx.TransportError, match=r"^model_podman_request$"):
        await podman.PodmanModelTransport(process_factory=factory).handle_async_request(request)
    assert consumed == [0, 1]
    factory.assert_not_awaited()


@pytest.mark.parametrize(
    "output",
    [
        b"private malformed output",
        b'{"status":200,"body":""} trailing private data',
        b'{"status":200,"status":201,"body":""}',
        b'{"status":200,"body":"private invalid base64!"}',
        b'{"status":200,"body":null}',
        b'{"status":200}',
        frame(extra="private"),
        frame(status=True),
        frame(status=99),
        frame(status=600),
        frame(status=302),
        frame(body=b"x" * 49_153),
        b" " * 66_049,
    ],
)
@pytest.mark.asyncio
async def test_untrusted_response_is_bounded_and_has_content_free_errors(output: bytes) -> None:
    process = Process(output)
    factory = AsyncMock(return_value=process)
    with pytest.raises(httpx.TransportError, match=r"^model_podman_protocol$"):
        await podman.PodmanModelTransport(process_factory=factory).handle_async_request(
            httpx.Request("GET", "http://127.0.0.1:28000/health")
        )
    factory.assert_awaited_once()


@pytest.mark.asyncio
async def test_binary_response_at_exact_body_limit_preserves_status() -> None:
    content = b"\x00\xff" * (podman.MAX_BODY_BYTES // 2)
    factory = AsyncMock(return_value=Process(frame(content, status=503)))
    response = await podman.PodmanModelTransport(process_factory=factory).handle_async_request(
        httpx.Request("GET", "http://127.0.0.1:28000/health")
    )
    assert response.status_code == 503
    assert response.content == content


@pytest.mark.parametrize("failure", ["start", "io", "exit"])
@pytest.mark.asyncio
async def test_process_failure_does_not_expose_diagnostics_or_retry(failure: str) -> None:
    process = Process(returncode=7 if failure == "exit" else 0, error=OSError("private") if failure == "io" else None)
    factory = AsyncMock(side_effect=OSError("private")) if failure == "start" else AsyncMock(return_value=process)
    expected = "model_podman_start" if failure == "start" else "model_podman_failed"
    with pytest.raises(httpx.TransportError, match=rf"^{expected}$"):
        await podman.PodmanModelTransport(process_factory=factory).handle_async_request(
            httpx.Request("GET", "http://127.0.0.1:28000/health")
        )
    factory.assert_awaited_once()


@pytest.mark.asyncio
async def test_timeout_terminates_and_joins_process_before_content_free_error() -> None:
    process = Process(error=TimeoutError("private process diagnostic"))
    with pytest.raises(httpx.ReadTimeout, match=r"^model_podman_timeout$"):
        await podman.PodmanModelTransport(process_factory=AsyncMock(return_value=process)).handle_async_request(
            httpx.Request("GET", "http://127.0.0.1:28000/health")
        )
    assert process.terminated
    assert process.wait_calls >= 1
    assert process.settled.is_set()


@pytest.mark.parametrize("grace_expires", [False, True])
@pytest.mark.asyncio
async def test_cancellation_joins_process_and_escalates_expired_grace(*, grace_expires: bool) -> None:
    process = Process(block=True)
    process.wait_timeout_once = grace_expires
    transport = podman.PodmanModelTransport(process_factory=AsyncMock(return_value=process))
    task = asyncio.create_task(transport.handle_async_request(httpx.Request("GET", "http://127.0.0.1:28000/health")))
    await process.entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert process.terminated
    assert process.settled.is_set()
    assert process.killed is grace_expires
    assert process.wait_calls == (2 if grace_expires else 1)


@pytest.mark.asyncio
async def test_cancellation_during_spawn_settles_new_process_before_returning() -> None:
    process = Process()
    process.returncode = None
    entered, released = asyncio.Event(), asyncio.Event()

    async def spawn(*_args: str, **_kwargs: Any) -> asyncio.subprocess.Process:
        entered.set()
        await released.wait()
        return cast("asyncio.subprocess.Process", process)

    transport = podman.PodmanModelTransport(process_factory=spawn)
    task = asyncio.create_task(transport.handle_async_request(httpx.Request("GET", "http://127.0.0.1:28000/health")))
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    released.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert process.terminated
    assert process.wait_calls == 1


@pytest.mark.asyncio
async def test_authority_revoked_during_spawn_never_hands_payload_to_helper() -> None:
    process = Process()
    process.returncode = None
    entered, released = asyncio.Event(), asyncio.Event()
    current = True
    checks: list[bool] = []
    spawns = 0

    async def spawn(*_args: str, **_kwargs: Any) -> asyncio.subprocess.Process:
        nonlocal spawns
        spawns += 1
        entered.set()
        await released.wait()
        return cast("asyncio.subprocess.Process", process)

    def authorize() -> None:
        checks.append(current)
        if not current:
            message = "research_consume"
            raise ValueError(message)

    transport = podman.PodmanModelTransport(process_factory=spawn)
    request = httpx.Request(
        "POST",
        "http://127.0.0.1:28000/v1/chat/completions",
        content=b'{"messages":[{"content":"admitted public-source excerpt"}]}',
        extensions={"lychd_research_authorize": authorize},
    )
    task = asyncio.create_task(transport.handle_async_request(request))
    async with asyncio.timeout(3):
        await entered.wait()
        current = False
        released.set()
        with pytest.raises(ValueError, match=r"^research_consume$"):
            await task
    assert checks
    assert checks[-1] is False
    assert spawns == 1
    assert process.input is None
    assert not process.entered.is_set()
    assert process.terminated
    assert process.wait_calls == 1
    assert process.returncode is not None


@pytest.mark.asyncio
async def test_repeated_cancellation_waits_for_late_spawn_and_owned_reaping() -> None:
    spawn_entered, release_spawn = asyncio.Event(), asyncio.Event()
    reap_entered, release_reap, reaped = asyncio.Event(), asyncio.Event(), asyncio.Event()
    spawn_cancelled = False

    class DelayedReapingProcess(Process):
        async def wait(self) -> int:
            self.wait_calls += 1
            reap_entered.set()
            await release_reap.wait()
            reaped.set()
            return self.returncode or 0

    process = DelayedReapingProcess()
    process.returncode = None

    async def spawn(*_args: str, **_kwargs: Any) -> asyncio.subprocess.Process:
        nonlocal spawn_cancelled
        spawn_entered.set()
        try:
            await release_spawn.wait()
        except asyncio.CancelledError:
            spawn_cancelled = True
            raise
        return cast("asyncio.subprocess.Process", process)

    transport = podman.PodmanModelTransport(process_factory=spawn)
    task = asyncio.create_task(transport.handle_async_request(httpx.Request("GET", "http://127.0.0.1:28000/health")))
    async with asyncio.timeout(3):
        await spawn_entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        assert not spawn_cancelled
        release_spawn.set()
        await reap_entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        assert not reaped.is_set()
        release_reap.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert not spawn_cancelled
    assert process.input is None
    assert process.terminated
    assert reaped.is_set()
    assert process.wait_calls == 1
