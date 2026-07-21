"""A3-U3: async JSON transport + the sync bridge (``lychd.lib.http``)."""

from __future__ import annotations

import pytest

from lychd.lib.http import HttpJsonError, request_json, run_sync

# respx is the project's httpx mocking tool (see dossier). Skip cleanly if the
# dev extra is not installed rather than erroring the whole session.
respx = pytest.importorskip("respx")
import httpx  # noqa: E402


@pytest.mark.asyncio
async def test_request_json_returns_object_body() -> None:
    with respx.mock:
        respx.get("http://host/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        body = await request_json("GET", "http://host/health")
    assert body == {"status": "ok"}


@pytest.mark.asyncio
async def test_request_json_wraps_list_body_as_data() -> None:
    with respx.mock:
        respx.get("http://host/models").mock(return_value=httpx.Response(200, json=[{"id": "a"}]))
        body = await request_json("GET", "http://host/models")
    assert body == {"data": [{"id": "a"}]}


@pytest.mark.asyncio
async def test_request_json_raises_on_http_error_with_status() -> None:
    with respx.mock:
        respx.get("http://host/health").mock(return_value=httpx.Response(503, text="Loading model"))
        with pytest.raises(HttpJsonError) as exc:
            await request_json("GET", "http://host/health")
    assert exc.value.status == 503


@pytest.mark.asyncio
async def test_request_json_raises_on_transport_error() -> None:
    with respx.mock:
        respx.get("http://host/health").mock(side_effect=httpx.ConnectError("boom"))
        with pytest.raises(HttpJsonError):
            await request_json("GET", "http://host/health")


@pytest.mark.asyncio
async def test_request_json_empty_body_is_empty_dict() -> None:
    with respx.mock:
        respx.post("http://host/models/load").mock(return_value=httpx.Response(200, text=""))
        body = await request_json("POST", "http://host/models/load", payload={"model": "x"})
    assert body == {}


@pytest.mark.asyncio
async def test_request_json_rejects_null_by_default() -> None:
    with respx.mock:
        respx.post("http://host/model/unload").mock(
            return_value=httpx.Response(200, text="null", headers={"content-type": "application/json"})
        )
        with pytest.raises(HttpJsonError, match="unsupported payload type"):
            await request_json("POST", "http://host/model/unload")


@pytest.mark.asyncio
async def test_request_json_accepts_null_only_when_explicit() -> None:
    with respx.mock:
        respx.post("http://host/model/unload").mock(
            return_value=httpx.Response(200, text="null", headers={"content-type": "application/json"})
        )
        body = await request_json("POST", "http://host/model/unload", allow_null=True)
    assert body == {}


def test_run_sync_without_running_loop() -> None:
    async def coro() -> int:
        return 21

    assert run_sync(coro()) == 21


@pytest.mark.asyncio
async def test_run_sync_from_within_running_loop() -> None:
    async def coro() -> str:
        return "bridged"

    # Called from inside a running event loop: run_sync must offload to a worker
    # thread instead of raising "asyncio.run() cannot be called from a running loop".
    assert run_sync(coro()) == "bridged"
