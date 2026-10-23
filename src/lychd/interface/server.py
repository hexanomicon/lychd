"""Owned production entrypoints and one failure-propagating application lifespan."""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING, Any, Literal, cast

from granian.constants import HTTPModes, Interfaces, TaskImpl
from granian.server.embed import Server

from lychd.interface.server_policy import (
    ServerRuntimePolicyError,
    evaluate_server_runtime_policy,
    validate_server_environment,
)

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.types import Receive, Scope, Send

    from lychd.interface.api.lifecycle import StopAdmissionState

_SIGNALS = (signal.SIGINT, signal.SIGTERM)
_CAGED_HOST = "0.0.0.0"  # noqa: S104 -- fixed internal listener behind managed loopback publication
_CAGED_PORT = 8000


class _EmbeddedServer(Server):
    """Close the locked embedded worker on every exit and expose abnormal retirement."""

    _retire: Callable[[], None] | None = None

    async def _serve(self, spawn_target: Callable[..., Any], target_loader: Callable[[], Any]) -> None:
        # Granian 2.8.2's embedded _serve skips shutdown on exceptions and treats
        # interrupt_children as a successful return. Keep this seam deliberately
        # limited to that method; spawning and connection drain remain Granian's.
        target = target_loader()
        try:
            self.startup(spawn_target, target)  # pyright: ignore[reportUnknownMemberType]
            await self._serve_loop(spawn_target, target)  # pyright: ignore[reportUnknownMemberType]
        finally:
            if self._retire is not None:
                self._retire()
            await self.shutdown()
        if self.interrupt_children:  # pyright: ignore[reportUnknownMemberType]
            message = "The HTTP worker terminated unexpectedly."
            raise RuntimeError(message)


@contextmanager
def _preserve_signal_handlers(loop: asyncio.AbstractEventLoop) -> Generator[None]:
    # asyncio has no public getter for an existing loop signal callback. Preserve
    # its Handle callback/arguments/context before add_signal_handler cancels it.
    # This is the sole standard-asyncio private seam, covered by restoration tests.
    previous_handlers = {signum: signal.getsignal(signum) for signum in _SIGNALS}
    handles = cast("dict[int, asyncio.Handle]", getattr(loop, "_signal_handlers", {}))
    previous_callbacks: dict[signal.Signals, Callable[[], None]] = {}
    for signum in _SIGNALS:
        if (handle := handles.get(signum)) is not None:
            callback = handle._callback  # noqa: SLF001
            arguments = handle._args  # noqa: SLF001
            previous_callbacks[signum] = partial(handle.get_context().run, callback, *arguments)
    try:
        yield
    finally:
        for signum in _SIGNALS:
            loop.remove_signal_handler(signum)
            if (previous_callback := previous_callbacks.get(signum)) is not None:
                loop.add_signal_handler(signum, previous_callback)
            else:
                signal.signal(signum, previous_handlers[signum])


async def _await_lifespan(lifecycle: asyncio.Task[None], request_stop: Callable[[], None]) -> None:
    cancelled: asyncio.CancelledError | None = None
    while not lifecycle.done():
        try:
            await asyncio.shield(lifecycle)
        except asyncio.CancelledError as exc:
            if lifecycle.cancelled():
                raise
            cancelled = exc
            request_stop()
    lifecycle.result()
    if cancelled is not None:
        raise cancelled


async def _refuse_retired_callback(scope: Scope, send: Send) -> None:
    if scope["type"] == "http":
        await send({"type": "http.response.start", "status": 503, "headers": [(b"connection", b"close")]})
        await send({"type": "http.response.body", "body": b""})
    elif scope["type"] == "websocket":
        await send({"type": "websocket.close", "code": 1012})


def _withdraw_admission(admission: StopAdmissionState | None) -> None:
    if admission is not None:
        admission.withdraw()


async def serve_application(app: Litestar, *, host: str, port: int) -> None:
    """Retire HTTP callbacks before closing the single explicit application lifespan.

    Signals request graceful retirement. Caller cancellation also requests stop,
    then waits for retirement and closure before propagating. Further cancellation
    cannot interrupt that cleanup; the service manager retains its outer deadline.
    """
    from litestar.cli.commands.core import _server_lifespan  # pyright: ignore[reportPrivateUsage]

    loop = asyncio.get_running_loop()
    active_callbacks = 0
    callbacks_retired = asyncio.Event()
    callbacks_retired.set()
    stopping = started = startup_cancelled = False
    lifecycle: asyncio.Task[None] | None = None
    admission = cast("StopAdmissionState | None", getattr(app.state, "stop_admission", None))

    async def application(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal active_callbacks
        if stopping:
            await _refuse_retired_callback(scope, send)
            return
        active_callbacks += 1
        callbacks_retired.clear()
        try:
            # Preserve the exact scope, including raw_path. Granian's connection
            # drain can finish before an ASGI callable's post-response work.
            await app(scope, receive, send)
        finally:
            active_callbacks -= 1
            if not active_callbacks:
                callbacks_retired.set()

    server = _EmbeddedServer(
        application,
        address=host,
        port=port,
        interface=Interfaces.ASGINL,
        factory=False,
        runtime_threads=1,
        runtime_blocking_threads=1,
        blocking_threads=1,
        task_impl=TaskImpl.asyncio,
        http=HTTPModes.auto,
        websockets=True,
        backlog=1024,
    )

    def request_stop() -> None:
        nonlocal stopping, startup_cancelled
        stopping = True
        _withdraw_admission(admission)
        server.stop()
        if lifecycle is not None and not started and not startup_cancelled:
            startup_cancelled = True
            lifecycle.cancel()

    server._retire = request_stop  # noqa: SLF001 # pyright: ignore[reportPrivateUsage] - before Granian's shutdown await

    async def run_lifespan() -> None:
        nonlocal started
        if stopping:
            message = "Application startup was interrupted."
            raise RuntimeError(message)
        async with app.lifespan():
            started = True
            try:
                if not stopping:
                    await server.serve()
            finally:
                request_stop()
                await callbacks_retired.wait()

    with _preserve_signal_handlers(loop), _server_lifespan(app):
        for signum in _SIGNALS:
            loop.add_signal_handler(signum, request_stop)
        lifecycle = asyncio.create_task(run_lifespan(), name="lychd-server-lifespan")
        await _await_lifespan(lifecycle, request_stop)


def run_production_server(
    *,
    host: str,
    port: int,
    debug: bool = False,
    pdb: bool = False,
    _profile: Literal["native", "caged"] = "native",
) -> None:
    """Construct one captured app; only the fixed native entrypoint arms admission."""
    validate_server_environment(os.environ)
    if _profile == "native":
        evaluate_server_runtime_policy(environment={}, server_arguments=("--host", host, "--port", str(port)))
    elif _profile != "caged" or (host, port) != (_CAGED_HOST, _CAGED_PORT):
        message = "The managed image requires its fixed internal listener."
        raise ServerRuntimePolicyError(message)
    from lychd.app import create_app

    exports = {"LITESTAR_HOST": host, "GRANIAN_HOST": host, "LITESTAR_PORT": str(port), "GRANIAN_PORT": str(port)}
    previous = {key: os.environ.get(key) for key in exports}
    admission: StopAdmissionState | None = None
    try:
        os.environ.update(exports)
        app = create_app()
        admission = cast("StopAdmissionState | None", getattr(app.state, "stop_admission", None))
        if admission is not None and _profile == "native":
            admission.arm_native_launcher()
        if debug:
            app.debug = True
        if pdb:
            app.pdb_on_exception = True
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(serve_application(app, host=host, port=port))
    finally:
        _withdraw_admission(admission)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main(arguments: Sequence[str] | None = None) -> None:
    """Select only the managed image's fixed internal TCP listener."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--caged", action="store_true", required=True, help="Run the managed image listener")
    parser.parse_args(arguments)
    try:
        run_production_server(host=_CAGED_HOST, port=_CAGED_PORT, _profile="caged")
    except ServerRuntimePolicyError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
