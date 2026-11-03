"""One generic observation seam works for unrelated transport drivers."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import aiohttp
import pytest
from multidict import CIMultiDict
from pydantic import ValidationError
from yarl import URL

from lychd.interface.http_observation import http_trace
from lychd.interface.observation import (
    OperationObservation,
    OperationObserver,
    observation_bytes,
    observation_context,
)


@pytest.mark.parametrize("driver", ["mail.smtp", "image.render"])
def test_differently_named_drivers_preserve_attempts_and_explicit_context(driver: str) -> None:
    events: list[OperationObservation] = []
    observer = OperationObserver(
        generation=str(uuid4()), producer_id=driver, source=driver, target="fixture.endpoint", sink=events.append
    )
    run_id, request_id = str(uuid4()), str(uuid4())
    with observation_context(run_id=run_id, request_id=request_id):
        first = observer.operation("send")
        first.start()
        first.http_status = 202
        first.finish("succeeded")
        first.settle("unknown")
        second = observer.operation("send")
        second.start()
        second.finish("failed", error="timeout")
    background = observer.operation("probe")
    background.start()
    assert first.attempt_id != second.attempt_id
    assert all(event.run_id == run_id and event.request_id == request_id for event in events[:-1])
    assert events[-1].run_id is None
    assert [event.seq for event in events] == list(range(1, len(events) + 1))
    assert events[1].effect_outcome is None
    assert events[2].effect_outcome == "unknown"
    assert events[2].http_status == 202
    assert b"payload" not in observation_bytes(events[0])


@pytest.mark.parametrize("failure", [RuntimeError, asyncio.CancelledError])
def test_observer_failure_does_not_cancel_work(failure: type[BaseException]) -> None:
    def sink(_event: OperationObservation) -> None:
        raise failure

    observer = OperationObserver(
        generation=str(uuid4()),
        producer_id="fixture.driver",
        source="fixture.driver",
        target="fixture.endpoint",
        sink=sink,
    )
    operation = observer.operation("lookup")
    operation.start()
    operation.finish("succeeded")
    operation.settle("succeeded")
    assert observer.sequence == 3


@pytest.mark.asyncio
async def test_public_sdk_trace_hooks_record_each_request_without_private_urls() -> None:
    events: list[OperationObservation] = []
    observer = OperationObserver(
        generation=str(uuid4()),
        producer_id="fixture.sdk",
        source="fixture.sdk",
        target="fixture.api",
        sink=events.append,
    )
    trace = http_trace(observer, targets={"known.example": "fixture.known"})
    trace.freeze()
    secret_url = URL("https://private.invalid/webhooks/token?secret=canary")
    session = cast("aiohttp.ClientSession", SimpleNamespace())
    # Public signals are invoked exactly as aiohttp invokes them; no request is sent.
    for status in (429, 403, 200, 101):
        context = trace.trace_config_ctx()
        await trace.on_request_start.send(
            session, context, aiohttp.TraceRequestStartParams("POST", secret_url, CIMultiDict())
        )
        await trace.on_request_headers_sent.send(
            session, context, aiohttp.TraceRequestHeadersSentParams("POST", secret_url, CIMultiDict())
        )
        response = cast("aiohttp.ClientResponse", SimpleNamespace(status=status))
        await trace.on_request_end.send(
            session, context, aiohttp.TraceRequestEndParams("POST", secret_url, CIMultiDict(), response)
        )
    assert len({event.attempt_id for event in events}) == 4
    assert [event.http_status for event in events if event.activity_kind == "transport_result"] == [429, 403, 200, 101]
    assert all(event.run_id is None for event in events)
    assert all(event.target == "fixture.api" for event in events)
    context = trace.trace_config_ctx()
    await trace.on_request_start.send(
        session, context, aiohttp.TraceRequestStartParams("GET", URL("https://known.example/secret"), CIMultiDict())
    )
    await trace.on_request_headers_sent.send(
        session,
        context,
        aiohttp.TraceRequestHeadersSentParams("GET", URL("https://known.example/secret"), CIMultiDict()),
    )
    assert events[-1].target == "fixture.known"
    encoded = b"".join(observation_bytes(event) for event in events)
    assert b"private.invalid" not in encoded
    assert b"canary" not in encoded
    assert b"webhooks" not in encoded


def test_wire_sequence_refuses_values_that_browser_cannot_represent_exactly() -> None:
    with pytest.raises(ValidationError):
        OperationObservation(
            generation=str(uuid4()),
            producer_id="fixture.driver",
            operation_id=str(uuid4()),
            attempt_id=str(uuid4()),
            seq=2**53,
            source="fixture.driver",
            target="fixture.endpoint",
            operation="probe",
            activity_kind="transport_attempt",
            phase="started",
        )


@pytest.mark.asyncio
async def test_hidden_sdk_retry_gets_distinct_attempts_with_one_logical_operation() -> None:
    events: list[OperationObservation] = []
    observer = OperationObserver(
        generation=str(uuid4()),
        producer_id="fixture.sdk",
        source="fixture.sdk",
        target="fixture.api",
        sink=events.append,
    )
    trace = http_trace(observer)
    trace.freeze()
    session = cast("aiohttp.ClientSession", SimpleNamespace())
    url = URL("https://fixture.invalid/private")
    context = trace.trace_config_ctx()
    await trace.on_request_start.send(session, context, aiohttp.TraceRequestStartParams("GET", url, CIMultiDict()))
    assert not events
    for _ in range(2):
        await trace.on_request_headers_sent.send(
            session, context, aiohttp.TraceRequestHeadersSentParams("GET", url, CIMultiDict())
        )
    response = cast("aiohttp.ClientResponse", SimpleNamespace(status=200))
    await trace.on_request_end.send(
        session, context, aiohttp.TraceRequestEndParams("GET", url, CIMultiDict(), response)
    )
    assert [event.phase for event in events] == ["started", "unknown", "started", "succeeded"]
    assert len({event.operation_id for event in events}) == 1
    assert events[0].attempt_id == events[1].attempt_id
    assert events[2].attempt_id == events[3].attempt_id
    assert events[0].attempt_id != events[2].attempt_id
    assert events[1].http_status is None
    assert all(event.effect_outcome is None for event in events)


@pytest.mark.asyncio
async def test_sdk_preheader_failure_does_not_fabricate_dispatch() -> None:
    events: list[OperationObservation] = []
    observer = OperationObserver(
        generation=str(uuid4()),
        producer_id="fixture.sdk",
        source="fixture.sdk",
        target="fixture.api",
        sink=events.append,
    )
    trace = http_trace(observer)
    trace.freeze()
    session = cast("aiohttp.ClientSession", SimpleNamespace())
    url = URL("https://fixture.invalid/private")
    context = trace.trace_config_ctx()
    await trace.on_request_start.send(session, context, aiohttp.TraceRequestStartParams("GET", url, CIMultiDict()))
    await trace.on_request_exception.send(
        session, context, aiohttp.TraceRequestExceptionParams("GET", url, CIMultiDict(), TimeoutError())
    )
    assert not events


@pytest.mark.asyncio
async def test_aiohttp_persistent_connection_retry_observes_both_header_dispatches() -> None:
    events: list[OperationObservation] = []
    observer = OperationObserver(
        generation=str(uuid4()),
        producer_id="fixture.sdk",
        source="fixture.sdk",
        target="fixture.loopback",
        sink=events.append,
    )
    requests = 0
    handlers: set[asyncio.Task[object]] = set()

    async def serve(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        nonlocal requests
        task = asyncio.current_task()
        assert task is not None
        handlers.add(task)
        try:
            with suppress(asyncio.IncompleteReadError, ConnectionResetError):
                while True:
                    await reader.readuntil(b"\r\n\r\n")
                    requests += 1
                    if requests == 2:
                        # Drop the reused connection after receiving the second request.
                        return
                    writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: keep-alive\r\n\r\nok")
                    await writer.drain()
        finally:
            writer.close()
            with suppress(ConnectionResetError):
                await writer.wait_closed()
            handlers.discard(task)

    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    try:
        port = int(server.sockets[0].getsockname()[1])
        async with aiohttp.ClientSession(trace_configs=[http_trace(observer)]) as session:
            async with asyncio.timeout(5):
                async with session.get(f"http://127.0.0.1:{port}/warm") as first:
                    assert await first.read() == b"ok"
                events.clear()
                async with session.get(f"http://127.0.0.1:{port}/retry") as second:
                    assert await second.read() == b"ok"
        assert requests == 3
        assert [event.phase for event in events] == ["started", "unknown", "started", "succeeded"]
        assert len({event.operation_id for event in events}) == 1
        assert len({event.attempt_id for event in events}) == 2
        assert events[-1].http_status == 200
    finally:
        server.close()
        await server.wait_closed()
        if handlers:
            await asyncio.wait_for(asyncio.gather(*handlers), timeout=5)
