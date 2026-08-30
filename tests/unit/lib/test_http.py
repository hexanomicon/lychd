"""Async JSON transport and its synchronous registry bridge."""

from __future__ import annotations

import httpx
import pytest
import respx

from lychd.lib.http import HttpJsonError, request_json


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
