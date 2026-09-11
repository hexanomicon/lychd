"""HTTP stream budgets reject before headers and settle even before iteration."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import ExitStack
from typing import TYPE_CHECKING, Any

import pytest
from litestar.response import ServerSentEventMessage
from litestar.testing import RequestFactory

from lychd.agents.router import Intent
from lychd.domain.cortex.events import InProcessEventBus, RunStreamLimitError
from lychd.domain.cortex.runs import RunStatus
from lychd.interface.web.bridge_stream import BoundedRunEventStream

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient
    from litestar.types import HTTPDisconnectEvent, Message


def test_stream_budgets_bound_one_run_and_the_whole_process() -> None:
    bus = InProcessEventBus(max_http_streams=2, max_http_streams_per_run=1)
    with bus.reserve_http_stream("first"):
        with pytest.raises(RunStreamLimitError), bus.reserve_http_stream("first"):
            pytest.fail("Per-Run stream cap was bypassed.")
        with bus.reserve_http_stream("second"), pytest.raises(RunStreamLimitError), bus.reserve_http_stream("third"):
            pytest.fail("Global stream cap was bypassed.")
    with bus.reserve_http_stream("first"), bus.reserve_http_stream("second"):
        pass


@pytest.mark.parametrize("failure", [OSError, asyncio.CancelledError])
@pytest.mark.asyncio
async def test_stream_capacity_releases_when_headers_fail_before_generator_starts(
    failure: type[BaseException],
) -> None:
    bus = InProcessEventBus(max_http_streams=1, max_http_streams_per_run=1)
    started = False

    async def events() -> AsyncIterator[ServerSentEventMessage]:
        nonlocal started
        started = True
        yield ServerSentEventMessage(data="visible")

    request = RequestFactory().get("/api/v1/bridge/runs/run/events")
    response = BoundedRunEventStream(events(), bus=bus, run_id="run").to_asgi_response(None, request)

    async def send(_message: Message) -> None:
        raise failure

    async def receive() -> HTTPDisconnectEvent:
        return {"type": "http.disconnect"}

    with pytest.raises(failure):
        await response(request.scope, receive, send)

    assert not started
    with bus.reserve_http_stream("run"):
        pass


def test_stream_limit_is_an_http_refusal_with_retry_after(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    async def seed() -> Any:
        session = await fake_services.bridge_sessions.create_session()
        run = await fake_services.ledger.create(
            Intent(session_id=session.id, run_id="bounded-stream", prompt="hello", source="bridge"),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )
        await fake_services.ledger.set_status(run.run_id, RunStatus.RUNNING)
        await fake_services.ledger.set_status(run.run_id, RunStatus.DONE)
        return run

    run = asyncio.run(seed())
    with ExitStack() as stack:
        for _ in range(4):
            stack.enter_context(fake_services.bus.reserve_http_stream(run.run_id))
        response = altar_client.get(f"/api/v1/bridge/runs/{run.run_id}/events")
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "5"
        assert response.headers["content-type"].startswith("application/json")
    assert altar_client.get(f"/api/v1/bridge/runs/{run.run_id}/events").status_code == 200
