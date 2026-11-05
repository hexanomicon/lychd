"""Exercise shared construction through real clients and their transport seam."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import httpcore2
import httpx2
import pytest
from httpcore2._backends.auto import AutoBackend

from lychd.lib.http import create_async_http_client, create_async_http_transport

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.mark.asyncio
async def test_client_retains_binding_hooks_timeout_streaming_and_owned_close() -> None:
    requests: list[httpx2.Request] = []
    closed = False

    class Body(httpx2.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b"first"
            yield b"second"

    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            return httpx2.Response(307, headers={"Location": "http://other.invalid/"}, stream=Body())

        async def aclose(self) -> None:
            nonlocal closed
            closed = True

    async def hook(request: httpx2.Request) -> None:
        request.headers["X-Request-Hook"] = "observed"

    client = create_async_http_client(
        timeout=httpx2.Timeout(connect=1, read=None, write=2, pool=3),
        base_url="http://owned.invalid/v1/",
        headers={"Authorization": "Bearer synthetic-binding"},
        transport=Transport(),
        request_hooks=[hook],
    )
    assert requests == []
    assert not closed
    async with client, client.stream("POST", "action", content=b"payload") as response:
        assert response.status_code == 307
        assert [part async for part in response.aiter_bytes()] == [b"first", b"second"]
        assert not closed
    assert closed
    assert client.is_closed
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "http://owned.invalid/v1/action"
    assert request.headers["Authorization"] == "Bearer synthetic-binding"
    assert request.headers["X-Request-Hook"] == "observed"
    assert request.content == b"payload"
    assert request.extensions["timeout"] == {"connect": 1, "read": None, "write": 2, "pool": 3}


@pytest.mark.parametrize("explicit_transport", [False, True])
@pytest.mark.parametrize(
    ("limits", "expected"),
    [
        (None, (100, 20, 5.0)),
        (httpx2.Limits(max_connections=3, max_keepalive_connections=1, keepalive_expiry=0.5), (3, 1, 0.5)),
    ],
)
@pytest.mark.asyncio
async def test_default_pool_bounds_and_explicit_limits_are_preserved(
    *, explicit_transport: bool, limits: httpx2.Limits | None, expected: tuple[int, int, float]
) -> None:
    transport = create_async_http_transport(limits=limits) if explicit_transport else None
    async with create_async_http_client(timeout=1, limits=limits, transport=transport) as client:
        # The pinned library exposes effective pool limits only on its transport.
        network = cast("httpx2.AsyncHTTPTransport", client._transport)  # pyright: ignore[reportPrivateUsage]
        pool = network._pool  # pyright: ignore[reportPrivateUsage]
        assert (
            pool._max_connections,  # pyright: ignore[reportPrivateUsage]
            pool._max_keepalive_connections,  # pyright: ignore[reportPrivateUsage]
            pool._keepalive_expiry,  # pyright: ignore[reportPrivateUsage]
        ) == expected


@pytest.mark.parametrize("explicit_transport", [False, True])
@pytest.mark.asyncio
async def test_default_network_transport_never_retries_connection_failure(
    monkeypatch: pytest.MonkeyPatch, *, explicit_transport: bool
) -> None:
    attempts = 0

    async def refuse_connection(*args: object, **kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        msg = "synthetic connection failure"
        raise httpcore2.ConnectError(msg)

    monkeypatch.setattr(AutoBackend, "connect_tcp", refuse_connection)
    transport = create_async_http_transport() if explicit_transport else None
    async with create_async_http_client(timeout=1, transport=transport) as client:
        with pytest.raises(httpx2.ConnectError, match="synthetic connection failure"):
            await client.get("http://owned.invalid/")
    assert attempts == 1
