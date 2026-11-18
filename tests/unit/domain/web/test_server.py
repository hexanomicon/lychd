from __future__ import annotations

# The launcher deliberately bridges locked Granian/asyncio lifecycle seams.
# pyright: reportPrivateUsage=false
import asyncio
import contextvars
import os
import signal
from collections.abc import Generator
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
from granian.constants import HTTPModes, Interfaces, TaskImpl
from litestar import Litestar, Request, Response, get
from litestar.background_tasks import BackgroundTask
from litestar.plugins import CLIPlugin

from lychd.interface import server
from lychd.interface.server_policy import ServerRuntimePolicyError

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar.types import ASGIApp, HTTPRequestEvent, Message, Scope
    from pytest_mock import MockerFixture

_CAGED_ADDRESS = "0.0.0.0"  # noqa: S104 -- fixed image profile; tests never open a socket


class _Transport:
    def __init__(self, application: ASGIApp, **configuration: Any) -> None:
        self.application = application
        self.configuration = configuration
        self.started = asyncio.Event()
        self.stopping = asyncio.Event()
        self.retired = asyncio.Event()
        self.serve_calls = 0

    async def serve(self) -> None:
        self.serve_calls += 1
        self.started.set()
        await self.stopping.wait()
        self.retired.set()

    def stop(self) -> None:
        self.stopping.set()


class _ServerHook(CLIPlugin):
    def __init__(self, events: list[str]) -> None:
        self.events = events

    @contextmanager
    def server_lifespan(self, app: Litestar) -> Generator[None]:
        _ = app
        self.events.append("sync-start")
        try:
            yield
        finally:
            self.events.append("sync-close")


def _transport_factory(monkeypatch: pytest.MonkeyPatch) -> list[_Transport]:
    transports: list[_Transport] = []

    def create(application: ASGIApp, **configuration: Any) -> _Transport:
        transport = _Transport(application, **configuration)
        transports.append(transport)
        return transport

    monkeypatch.setattr(server, "_EmbeddedServer", create)
    return transports


async def _started_transport(transports: list[_Transport]) -> _Transport:
    await asyncio.sleep(0)
    assert transports
    transport = transports[0]
    await transport.started.wait()
    return transport


def _signal(signum: signal.Signals = signal.SIGTERM) -> None:
    loop = asyncio.get_running_loop()
    handles = cast("dict[int, asyncio.Handle]", loop._signal_handlers)  # type: ignore[attr-defined]
    handles[signum]._run()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["container", "native"])
async def test_one_sync_and_async_lifespan_wrap_fixed_transport(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    monkeypatch.setenv("LYCHD_VESSEL_MODE", mode)
    events: list[str] = []

    @asynccontextmanager
    async def lifespan(app: Litestar) -> AsyncGenerator[None]:
        events.append("app-start")
        yield
        assert transports[0].retired.is_set()
        events.append("app-close")

    app = Litestar(lifespan=[lifespan], plugins=[_ServerHook(events)])
    transports = _transport_factory(monkeypatch)
    task = asyncio.create_task(server.serve_application(app, host="::1", port=7134))
    transport = await _started_transport(transports)
    assert events == ["sync-start", "app-start"]
    assert transport.configuration == {
        "address": "::1",
        "port": 7134,
        "interface": Interfaces.ASGINL,
        "factory": False,
        "runtime_threads": 1,
        "runtime_blocking_threads": 1,
        "blocking_threads": 1,
        "task_impl": TaskImpl.asyncio,
        "http": HTTPModes.auto,
        "websockets": True,
        "backlog": 1024,
    }
    if mode == "native":
        app.state.native_request_stop()
    else:
        assert getattr(app.state, "native_request_stop", None) is None
        _signal()
    await task
    assert events == ["sync-start", "app-start", "app-close", "sync-close"]
    assert transport.serve_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["startup", "closure"])
async def test_required_lifespan_failure_propagates_and_restores_signals(
    monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    events: list[str] = []
    original = {signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)}

    @asynccontextmanager
    async def lifespan(app: Litestar) -> AsyncGenerator[None]:
        try:
            if phase == "startup":
                message = "required startup failed"
                raise RuntimeError(message)
            yield
        finally:
            events.append("app-close")
            if phase == "closure":
                message = "required closure failed"
                raise RuntimeError(message)

    app = Litestar(lifespan=[lifespan], plugins=[_ServerHook(events)])
    transports = _transport_factory(monkeypatch)
    task = asyncio.create_task(server.serve_application(app, host="127.0.0.1", port=7134))
    if phase == "closure":
        await _started_transport(transports)
        _signal(signal.SIGINT)
    with pytest.RaisesGroup(pytest.RaisesExc(RuntimeError, match=f"required {phase} failed")):
        await task
    assert events == ["sync-start", "app-close", "sync-close"]
    assert {signum: signal.getsignal(signum) for signum in original} == original
    assert transports[0].serve_calls == (phase == "closure")


@pytest.mark.asyncio
async def test_previous_asyncio_signal_callback_keeps_arguments_and_context(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = asyncio.get_running_loop()
    original = signal.getsignal(signal.SIGTERM)
    context = contextvars.ContextVar("launcher_signal_test", default="outside")
    observed: list[tuple[str, str]] = []

    def previous(argument: str) -> None:
        observed.append((argument, context.get()))

    token = context.set("registered")
    loop.add_signal_handler(signal.SIGTERM, previous, "argument")
    context.reset(token)
    try:
        transports = _transport_factory(monkeypatch)
        task = asyncio.create_task(server.serve_application(Litestar(), host="127.0.0.1", port=7134))
        await _started_transport(transports)
        _signal()
        await task
        assert observed == []
        _signal()
        assert observed == [("argument", "registered")]
    finally:
        loop.remove_signal_handler(signal.SIGTERM)
        signal.signal(signal.SIGTERM, original)


@pytest.mark.asyncio
async def test_stop_during_startup_cancels_once_and_never_starts_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    startup = asyncio.Event()
    closing = asyncio.Event()
    allow_close = asyncio.Event()
    events: list[str] = []

    @asynccontextmanager
    async def lifespan(app: Litestar) -> AsyncGenerator[None]:
        try:
            startup.set()
            await asyncio.Event().wait()
            yield
        finally:
            closing.set()
            await allow_close.wait()
            events.append("app-close")

    transports = _transport_factory(monkeypatch)
    app = Litestar(lifespan=[lifespan], plugins=[_ServerHook(events)])
    task = asyncio.create_task(server.serve_application(app, host="127.0.0.1", port=7134))
    await startup.wait()
    _signal()
    await closing.wait()
    _signal()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    allow_close.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert transports[0].serve_calls == 0
    assert events == ["sync-start", "app-close", "sync-close"]


def _scope(kind: str = "http") -> Scope:
    return cast(
        "Scope",
        {
            "type": kind,
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/probe",
            "raw_path": b"/%70robe",
            "query_string": b"",
            "root_path": "",
            "headers": [],
            "server": ("127.0.0.1", 7134),
            "client": ("127.0.0.1", 1234),
        },
    )


async def _receive() -> HTTPRequestEvent:
    return {"type": "http.request", "body": b"", "more_body": False}


def _request_stop(task: asyncio.Task[None], kind: str) -> None:
    if kind == "signal":
        _signal()
    else:
        task.cancel()


async def _assert_retired_admission(transport: _Transport) -> None:
    messages: list[Message] = []

    async def send(message: Message) -> None:
        messages.append(message)

    await transport.application(_scope(), _receive, send)
    await transport.application(_scope("websocket"), _receive, send)
    assert messages[0]["type"] == "http.response.start"
    assert messages[0].get("status") == 503
    assert messages[-1] == {"type": "websocket.close", "code": 1012}


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["response", "background"])
@pytest.mark.parametrize("stop", ["signal", "cancellation"])
async def test_requests_including_post_response_work_retire_before_app_close(
    monkeypatch: pytest.MonkeyPatch, phase: str, stop: str
) -> None:
    in_flight = asyncio.Event()
    release_request = asyncio.Event()
    app_closed = asyncio.Event()
    events: list[str] = []
    messages: list[Message] = []
    invocations = 0

    async def pending_work() -> None:
        in_flight.set()
        await release_request.wait()
        assert not app_closed.is_set()
        events.append("request-retired")

    @get("/probe")
    async def route(request: Request[Any, Any, Any]) -> Response[dict[str, str]]:
        nonlocal invocations
        invocations += 1
        if phase == "response":
            await pending_work()
        return Response(
            {"raw": request.scope["raw_path"].decode()},
            background=BackgroundTask(pending_work) if phase == "background" else None,
        )

    @asynccontextmanager
    async def lifespan(app: Litestar) -> AsyncGenerator[None]:
        yield
        events.append("app-close")
        app_closed.set()

    async def send(message: Message) -> None:
        messages.append(message)

    app = Litestar([route], lifespan=[lifespan])
    transports = _transport_factory(monkeypatch)
    task = asyncio.create_task(server.serve_application(app, host="127.0.0.1", port=7134))
    transport = await _started_transport(transports)

    async def invoke_request() -> None:
        await transport.application(_scope(), _receive, send)

    request_task = asyncio.create_task(invoke_request())
    await in_flight.wait()
    assert bool(messages) == (phase == "background")
    _request_stop(task, stop)
    await transport.retired.wait()
    for _ in range(2):
        _request_stop(task, stop)
        await asyncio.sleep(0)
    assert not task.done()
    assert not app_closed.is_set()

    await _assert_retired_admission(transport)
    assert invocations == 1
    release_request.set()
    await request_task
    if stop == "cancellation":
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        await task
    assert events == ["request-retired", "app-close"]
    assert b"/%70robe" in b"".join(message.get("body", b"") for message in messages)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["startup", "worker", "retirement", "unexpected-exit", "none"])
async def test_locked_embedded_seam_always_shuts_down_and_rejects_abnormal_worker(
    mocker: MockerFixture, failure: str
) -> None:
    embedded = object.__new__(server._EmbeddedServer)
    embedded.interrupt_children = [0] if failure == "unexpected-exit" else []
    startup = mocker.patch.object(
        embedded, "startup", side_effect=RuntimeError("startup failed") if failure == "startup" else None
    )
    serve_loop = mocker.patch.object(
        embedded,
        "_serve_loop",
        new=AsyncMock(side_effect=RuntimeError("worker failed") if failure == "worker" else None),
    )
    shutdown = mocker.patch.object(
        embedded,
        "shutdown",
        new=AsyncMock(side_effect=RuntimeError("retirement failed") if failure == "retirement" else None),
    )
    spawn = Mock()
    loader = Mock(return_value=object())
    if failure == "none":
        await embedded._serve(spawn, loader)
    else:
        with pytest.raises(RuntimeError, match="unexpectedly" if failure == "unexpected-exit" else "failed"):
            await embedded._serve(spawn, loader)
    startup.assert_called_once_with(spawn, loader.return_value)
    assert serve_loop.await_count == (failure != "startup")
    shutdown.assert_awaited_once_with()


@pytest.mark.parametrize("failure", [None, "factory", "close"])
def test_production_runner_constructs_once_and_restores_actual_listener_environment(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, failure: str | None
) -> None:
    monkeypatch.setenv("LITESTAR_HOST", "::1")
    monkeypatch.setenv("LITESTAR_PORT", "7134")
    monkeypatch.delenv("GRANIAN_HOST", raising=False)
    monkeypatch.delenv("GRANIAN_PORT", raising=False)
    keys = ("LITESTAR_HOST", "LITESTAR_PORT", "GRANIAN_HOST", "GRANIAN_PORT")
    previous = {key: os.environ.get(key) for key in keys}
    observed: list[tuple[str, int]] = []
    app = Litestar()

    def factory() -> Litestar:
        assert os.environ["LITESTAR_HOST"] == os.environ["GRANIAN_HOST"] == _CAGED_ADDRESS
        assert os.environ["LITESTAR_PORT"] == os.environ["GRANIAN_PORT"] == "8000"
        if failure == "factory":
            message = "factory failed"
            raise RuntimeError(message)
        return app

    async def serve(application: Litestar, *, host: str, port: int) -> None:
        assert application is app
        assert isinstance(asyncio.get_running_loop(), asyncio.SelectorEventLoop)
        observed.append((host, port))
        if failure == "close":
            message = "close failed"
            raise RuntimeError(message)

    create_app = mocker.patch("lychd.app.create_app", side_effect=factory)
    monkeypatch.setattr(server, "serve_application", serve)
    if failure is None:
        server.run_production_server()
    else:
        with pytest.raises(RuntimeError, match=f"{failure} failed"):
            server.run_production_server()
    create_app.assert_called_once_with()
    assert observed == ([] if failure == "factory" else [(_CAGED_ADDRESS, 8000)])
    assert {key: os.environ.get(key) for key in keys} == previous


@pytest.mark.parametrize("key", ["GRANIAN_WORKERS", "GRANIAN_RELOAD", "GRANIAN_UDS", "GRANIAN_METRICS_ENABLED"])
def test_production_runner_rejects_unsafe_environment_before_factory(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, key: str
) -> None:
    monkeypatch.setenv(key, "2")
    create_app = mocker.patch("lychd.app.create_app")
    with pytest.raises(ServerRuntimePolicyError):
        server.run_production_server()
    create_app.assert_not_called()


@pytest.mark.parametrize("arguments", [[], ["--host", _CAGED_ADDRESS], ["--caged", "--port", "8001"], ["--cage"]])
def test_module_adapter_has_only_explicit_caged_profile(mocker: MockerFixture, arguments: list[str]) -> None:
    run = mocker.patch.object(server, "run_production_server")
    with pytest.raises(SystemExit) as exc:
        server.main(arguments)
    assert exc.value.code == 2
    run.assert_not_called()


def test_module_adapter_selects_fixed_caged_listener(mocker: MockerFixture) -> None:
    run = mocker.patch.object(server, "run_production_server")
    server.main(["--caged"])
    run.assert_called_once_with()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["startup", "worker", "unexpected-exit"])
async def test_worker_retirement_precedes_embedded_shutdown_await(mocker: MockerFixture, failure: str) -> None:
    retired = False
    embedded = object.__new__(server._EmbeddedServer)
    embedded.interrupt_children = [0] if failure == "unexpected-exit" else []

    def retire() -> None:
        nonlocal retired
        retired = True

    embedded._retire = retire
    mocker.patch.object(
        embedded, "startup", side_effect=RuntimeError("startup failed") if failure == "startup" else None
    )
    mocker.patch.object(
        embedded,
        "_serve_loop",
        new=AsyncMock(side_effect=RuntimeError("worker failed") if failure == "worker" else None),
    )

    async def shutdown() -> None:
        assert retired

    shutdown_mock = mocker.patch.object(embedded, "shutdown", side_effect=shutdown)
    with pytest.raises(RuntimeError, match="unexpectedly" if failure == "unexpected-exit" else "failed"):
        await embedded._serve(Mock(), Mock(return_value=object()))
    shutdown_mock.assert_awaited_once_with()
