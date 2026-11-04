"""Exercise real client routing without allowing either route to open a socket."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal, cast

import httpx
import httpx2
import pytest
import respx

from lychd.extensions.builtin.animator.exllamav3.control_plane import (
    TabbyAPIControlPlane,
    TabbyAPIControlPlaneError,
)

if TYPE_CHECKING:
    from pathlib import Path

_BASE_URL = "http://127.0.0.1:5000/v1"
_ADMIN_KEY = "control-plane-test-key-0000000001"


def response(request: httpx2.Request) -> httpx2.Response:
    if request.url.path == "/health":
        return httpx2.Response(200, json={"status": "healthy"})
    if request.url.path == "/v1/models":
        return httpx2.Response(200, json={"data": [{"id": "test-model"}]})
    if request.url.path == "/v1/model":
        return httpx2.Response(200, json={"id": "test-model"})
    assert request.url.path == "/v1/model/load"
    return httpx2.Response(
        200,
        text='data: {"model_type":"model","module":1,"modules":1,"status":"finished"}\n\n',
        headers={"content-type": "text/event-stream"},
    )


@pytest.mark.parametrize("operation", ["json", "stream"])
@pytest.mark.parametrize("proxy_env", ["HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"])
@pytest.mark.asyncio
async def test_control_plane_never_routes_admin_credential_through_ambient_proxy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    operation: Literal["json", "stream"],
    proxy_env: str,
) -> None:
    direct: list[httpx2.Request] = []
    proxied: list[httpx2.Request] = []
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    monkeypatch.setenv(proxy_env, "http://unapproved-proxy.invalid:8888")
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(tmp_path))
    (tmp_path / "tabby_test_auth").write_text(
        f'{{"api_key":"data-plane-test-key-00000000000001","admin_key":"{_ADMIN_KEY}"}}',
        encoding="utf-8",
    )

    def direct_response(request: httpx2.Request) -> httpx2.Response:
        direct.append(request)
        return response(request)

    def proxy_response(request: httpx2.Request) -> httpx2.Response:
        proxied.append(request)
        return response(request)

    def direct_transport(*args: object, **kwargs: object) -> httpx2.MockTransport:
        return httpx2.MockTransport(direct_response)

    def proxy_transport(*args: object, **kwargs: object) -> httpx2.MockTransport:
        return httpx2.MockTransport(proxy_response)

    # Keep the client's real environment parsing and route selection. Replacing
    # both transport factories prevents sockets without masking proxy selection,
    # unlike passing transport=MockTransport, which disables environment proxies.
    monkeypatch.setattr(httpx2.AsyncClient, "_init_transport", direct_transport)
    monkeypatch.setattr(httpx2.AsyncClient, "_init_proxy_transport", proxy_transport)
    control = TabbyAPIControlPlane()
    control.register_runtime(_BASE_URL, "tabby_test_auth")
    if operation == "json":
        lifecycle = await control.inspect(base_url=_BASE_URL)
        assert lifecycle.active_model == "test-model"
    else:
        assert await control.load_model(_BASE_URL, "test-model") is True
        load = next(iter(control._loads.values()))  # pyright: ignore[reportPrivateUsage]
        assert load.task is not None
        await asyncio.wait_for(load.task, timeout=1.0)
        assert load.stream_finished is True
    assert proxied == []
    assert len(direct) == (3 if operation == "json" else 1)
    assert all(request.headers["Authorization"] == f"Bearer {_ADMIN_KEY}" for request in direct)


@pytest.mark.parametrize("operation", ["json", "stream"])
@pytest.mark.parametrize("status", [307, 308])
@pytest.mark.asyncio
async def test_control_plane_refuses_redirect_without_forwarding_admin_credential(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    operation: Literal["json", "stream"],
    status: int,
) -> None:
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(tmp_path))
    (tmp_path / "tabby_test_auth").write_text(
        f'{{"api_key":"data-plane-test-key-00000000000001","admin_key":"{_ADMIN_KEY}"}}',
        encoding="utf-8",
    )
    control = TabbyAPIControlPlane()
    control.register_runtime(_BASE_URL, "tabby_test_auth")
    target = "https://unapproved-provider.invalid/capture"
    with respx.mock(assert_all_called=False, using="httpcore2") as router:
        rejected = router.route(url=target).mock(return_value=httpx.Response(200, json={}))
        url = "http://127.0.0.1:5000/health" if operation == "json" else f"{_BASE_URL}/model/load"
        original = router.route(url=url).mock(
            return_value=httpx.Response(status, text="redirect refused", headers={"Location": target})
        )
        request = (
            control.inspect(base_url=_BASE_URL) if operation == "json" else control.load_model(_BASE_URL, "test-model")
        )
        with pytest.raises(TabbyAPIControlPlaneError):
            await request
    assert original.call_count == 1
    assert rejected.call_count == 0
    sent = cast("httpx.Request", original.calls[0].request)
    assert sent.headers["Authorization"] == f"Bearer {_ADMIN_KEY}"
