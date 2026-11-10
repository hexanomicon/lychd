"""Explicit Tether selection and failure-closed consumer tests."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
import json
import os
import stat
import time
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import httpx2
import pytest

from lychd.domain.scout.transport import FetchError, NetworkHandoff, NetworkTarget
from lychd.domain.tether.models import TetherRoute, TetherSelection
from lychd.system.services.tether.connector import TetherConnector
from lychd.system.services.tether.transport import TetherHTTPTransport


class _Gate:
    def handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:
        del handoff
        return action()


def _route(**updates: object) -> TetherRoute:
    return TetherRoute.model_validate(
        {
            "selection": {"remote_lich_id": "remote", "attachment_id": "road", "generation": 1, "service_id": "api"},
            "installation_epoch": "a" * 32,
            "policy_digest": "b" * 64,
            "socket_path": "/run/lychd-tether/" + "c" * 16 + "/" + "d" * 32 + ".sock",
            "hostname": "peer.test",
            "address": "10.44.0.1",
            "port": 8443,
            "application_identity_ref": "peer-1",
            "allowed_callers": ["intercom"],
            "unit_name": "lychd-tether-road.service",
            **updates,
        }
    )


def test_catalog_never_selects_overlapping_address() -> None:
    route = _route()
    other = _route(
        selection={"remote_lich_id": "other", "attachment_id": "other", "generation": 1, "service_id": "api"}
    )
    connector = TetherConnector(catalog=lambda: (route, other), installation_epoch="a" * 32, caller="intercom")
    assert connector.resolve(route.selection) == route
    missing = TetherSelection(remote_lich_id="missing", attachment_id="road", generation=1, service_id="api")
    with pytest.raises(FetchError):
        connector.resolve(missing)


@pytest.mark.parametrize(("epoch", "caller"), [("e" * 32, "intercom"), ("a" * 32, "unadmitted")])
def test_catalog_requires_current_epoch_and_caller(epoch: str, caller: str) -> None:
    route = _route()
    connector = TetherConnector(catalog=lambda: (route,), installation_epoch=epoch, caller=caller)
    with pytest.raises(FetchError):
        connector.resolve(route.selection)


def test_catalog_revocation_and_policy_change_fence_existing_route() -> None:
    route = _route()
    rows = [route]
    connector = TetherConnector(catalog=lambda: tuple(rows), installation_epoch="a" * 32, caller="intercom")
    connector.current(route)
    rows[:] = [_route(policy_digest="f" * 64)]
    with pytest.raises(FetchError):
        connector.current(route)
    rows.clear()
    with pytest.raises(FetchError):
        connector.current(route)


@pytest.mark.asyncio
async def test_application_identity_refused_before_socket() -> None:
    route = _route()
    connector = TetherConnector(catalog=lambda: (route,), installation_epoch="a" * 32, caller="intercom")
    with pytest.raises(FetchError):
        await connector.open_tls(
            route.selection,
            target=NetworkTarget(route.address, route.port, route.hostname, "origin"),
            application_identity_ref="wrong-peer",
            gate=_Gate(),
            deadline=time.monotonic() + 5,
            ca_file=Path("/unused"),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["https://other.test:8443/", "http://peer.test:8443/", "https://peer.test:443/"])
async def test_http_origin_cannot_redirect_selected_service(url: str) -> None:
    route = _route()
    connector = TetherConnector(catalog=lambda: (route,), installation_epoch="a" * 32, caller="intercom")
    transport = TetherHTTPTransport(
        connector=connector, selection=route.selection, application_identity_ref="peer-1", ca_file=Path("/unused")
    )
    with pytest.raises(httpx2.TransportError):
        await transport.handle_async_request(httpx2.Request("GET", url))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "chunks",
    [
        (b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok",),
        (b"HTTP/1.1 200 OK\r\nContent-Le", b"ngth: 2\r\n\r\nok"),
    ],
)
async def test_http_uses_selected_stream_and_closes_it(
    chunks: tuple[bytes, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    route = _route()
    connector = TetherConnector(catalog=lambda: (route,), installation_epoch="a" * 32, caller="intercom")
    sent: list[bytes] = []
    closed: list[bool] = []
    received = iter(chunks)

    class Stream:
        async def send(self, data: bytes) -> None:
            sent.append(data)

        async def receive(self) -> bytes:
            return next(received)

        def close(self) -> None:
            closed.append(True)

    async def open_tls(selection: TetherSelection, **kwargs: object) -> Stream:
        assert selection == route.selection
        assert kwargs["application_identity_ref"] == "peer-1"
        assert kwargs["target"] == NetworkTarget(route.address, route.port, route.hostname, "origin")
        return Stream()

    monkeypatch.setattr(connector, "open_tls", open_tls)
    transport = TetherHTTPTransport(
        connector=connector, selection=route.selection, application_identity_ref="peer-1", ca_file=Path("/unused")
    )
    response = await transport.handle_async_request(httpx2.Request("GET", "https://peer.test:8443/health"))
    assert response.content == b"ok"
    assert sent[0].startswith(b"GET /health HTTP/1.1\r\n")
    assert closed == [True]
    await transport.aclose()
    with pytest.raises(httpx2.TransportError):
        await transport.handle_async_request(httpx2.Request("GET", "https://peer.test:8443/health"))


def test_intercom_endpoint_old_records_direct_explicit_routes_closed() -> None:
    from lychd.domain.codex.peer import PeerAuthorityError
    from lychd.system.services.intercom import _endpoint

    record = {"address": "10.44.0.1", "hostname": "peer.test", "port": 8443, "path": "/a2a", "ca_file": "/ca.pem"}
    endpoint, _ = _endpoint(record)
    assert endpoint.tether is None
    endpoint, _ = _endpoint({**record, "tether": _route().selection.model_dump()})
    assert endpoint.tether == _route().selection
    for malformed in (None, {}, {**_route().selection.model_dump(), "socket_path": "/arbitrary"}):
        with pytest.raises(PeerAuthorityError):
            _endpoint({**record, "tether": malformed})


def _catalog(path: Path, route: TetherRoute, *, epoch: str = "a" * 32) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "lychd.tether.catalog",
                "version": 1,
                "installation_epoch": epoch,
                "routes": [route.model_dump(mode="json")],
            }
        )
    )
    path.chmod(0o600)


def test_catalog_epoch_is_pinned_and_truncation_is_closed(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    route = _route()
    _catalog(path, route)
    connector = TetherConnector.from_catalog(caller="intercom", catalog_path=path)
    assert connector.resolve(route.selection) == route
    _catalog(path, _route(installation_epoch="e" * 32), epoch="e" * 32)
    with pytest.raises(FetchError):
        connector.resolve(route.selection)
    path.write_bytes(b'{"schema":')
    with pytest.raises(FetchError):
        connector.resolve(route.selection)


def test_catalog_refuses_symlink_and_loose_permissions(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    _catalog(path, _route())
    alias = tmp_path / "alias.json"
    alias.symlink_to(path)
    with pytest.raises(FetchError):
        TetherConnector.from_catalog(caller="intercom", catalog_path=alias)
    path.chmod(0o644)
    with pytest.raises(FetchError):
        TetherConnector.from_catalog(caller="intercom", catalog_path=path)


@pytest.mark.asyncio
async def test_http_cancellation_closes_active_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    route = _route()
    connector = TetherConnector(catalog=lambda: (route,), installation_epoch="a" * 32, caller="intercom")
    receiving = asyncio.Event()
    closed: list[bool] = []

    class Stream:
        async def send(self, data: bytes) -> None:
            del data

        async def receive(self) -> bytes:
            receiving.set()
            await asyncio.Future()
            return b""

        def close(self) -> None:
            closed.append(True)

    async def open_tls(*args: object, **kwargs: object) -> Stream:
        del args, kwargs
        return Stream()

    monkeypatch.setattr(connector, "open_tls", open_tls)
    transport = TetherHTTPTransport(
        connector=connector, selection=route.selection, application_identity_ref="peer-1", ca_file=Path("/unused")
    )
    task = asyncio.create_task(transport.handle_async_request(httpx2.Request("GET", "https://peer.test:8443/")))
    await receiving.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed == [True]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "wire",
    [
        b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nshort",
        b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nContent-Length: 2\r\n\r\nok",
        b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nextra",
        b"HTTP/1.1 302 Found\r\nLocation: https://peer.test:8443/other\r\nContent-Length: 0\r\n\r\n",
    ],
)
async def test_http_refuses_ambiguous_truncated_and_redirect_response(
    wire: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    route = _route()
    connector = TetherConnector(catalog=lambda: (route,), installation_epoch="a" * 32, caller="intercom")
    chunks = iter((wire, b""))
    closed: list[bool] = []

    class Stream:
        async def send(self, data: bytes) -> None:
            del data

        async def receive(self) -> bytes:
            return next(chunks)

        def close(self) -> None:
            closed.append(True)

    async def open_tls(*args: object, **kwargs: object) -> Stream:
        del args, kwargs
        return Stream()

    monkeypatch.setattr(connector, "open_tls", open_tls)
    transport = TetherHTTPTransport(
        connector=connector, selection=route.selection, application_identity_ref="peer-1", ca_file=Path("/unused")
    )
    with pytest.raises(httpx2.TransportError):
        await transport.handle_async_request(httpx2.Request("GET", "https://peer.test:8443/"))
    assert closed == [True]


@pytest.mark.parametrize(
    ("level", "mode", "owner_delta", "kind"),
    [
        ("root", 0o755, 0, stat.S_IFDIR),
        ("network", 0o770, 0, stat.S_IFDIR),
        ("socket", 0o660, 0, stat.S_IFSOCK),
        ("socket", 0o600, 1, stat.S_IFSOCK),
        ("network", 0o700, 0, stat.S_IFLNK),
        ("socket", 0o600, 0, stat.S_IFREG),
    ],
)
def test_broker_socket_requires_exact_owned_private_metadata(
    level: str, mode: int, owner_delta: int, kind: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = Path(_route().socket_path)
    uid = os.getuid()
    paths = {"root": path.parent.parent, "network": path.parent, "socket": path}
    metadata = {
        paths["root"]: SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=uid),
        paths["network"]: SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=uid),
        paths["socket"]: SimpleNamespace(st_mode=stat.S_IFSOCK | 0o600, st_uid=uid),
    }

    def statvfs(_path: Path) -> SimpleNamespace:
        return SimpleNamespace(f_flag=os.ST_RDONLY)

    def lstat(observed: Path) -> SimpleNamespace:
        return metadata[observed]

    monkeypatch.setattr(os, "statvfs", statvfs)
    monkeypatch.setattr(Path, "lstat", lstat)
    TetherConnector._check_socket(path)
    metadata[paths[level]] = SimpleNamespace(st_mode=kind | mode, st_uid=uid + owner_delta)
    with pytest.raises(FetchError):
        TetherConnector._check_socket(path)


@pytest.mark.asyncio
async def test_shared_http_factory_sends_only_identity_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.lib.http import create_async_http_client

    route = _route()
    connector = TetherConnector(catalog=lambda: (route,), installation_epoch="a" * 32, caller="intercom")
    sent: list[bytes] = []

    class Stream:
        async def send(self, data: bytes) -> None:
            sent.append(data)

        async def receive(self) -> bytes:
            return b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"

        def close(self) -> None:
            pass

    async def open_tls(*args: object, **kwargs: object) -> Stream:
        del args, kwargs
        return Stream()

    monkeypatch.setattr(connector, "open_tls", open_tls)
    transport = TetherHTTPTransport(
        connector=connector,
        selection=route.selection,
        application_identity_ref="peer-1",
        ca_file=Path("/unused"),
    )
    async with create_async_http_client(timeout=5, transport=transport) as client:
        response = await client.get("https://peer.test:8443/health")
    assert response.content == b"ok"
    headers = sent[0].split(b"\r\n\r\n", 1)[0].lower().split(b"\r\n")
    assert [line for line in headers if line.startswith(b"accept-encoding:")] == [b"accept-encoding: identity"]


def test_broker_socket_refuses_a_writable_consumer_mount(monkeypatch: pytest.MonkeyPatch) -> None:
    def statvfs(_path: Path) -> SimpleNamespace:
        return SimpleNamespace(f_flag=0)

    monkeypatch.setattr(os, "statvfs", statvfs)
    with pytest.raises(FetchError):
        TetherConnector._check_socket(Path(_route().socket_path))


def test_catalog_duplicate_selection_remains_refused(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    _catalog(path, _route())
    document = json.loads(path.read_text())
    document["routes"].append(document["routes"][0])
    path.write_text(json.dumps(document))
    with pytest.raises(FetchError):
        TetherConnector.from_catalog(caller="intercom", catalog_path=path)


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout_value", [[], {"read": True}, {"read": "5"}, {"read": float("nan")}, {"read": 0}])
async def test_http_malformed_timeout_is_refused_before_open(
    timeout_value: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    route = _route()
    connector = TetherConnector(catalog=lambda: (route,), installation_epoch="a" * 32, caller="intercom")

    async def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("Malformed timeout must refuse before connection")

    monkeypatch.setattr(connector, "open_tls", forbidden)
    transport = TetherHTTPTransport(
        connector=connector, selection=route.selection, application_identity_ref="peer-1", ca_file=Path("/unused")
    )
    request = httpx2.Request("GET", "https://peer.test:8443/", extensions={"timeout": timeout_value})
    with pytest.raises(httpx2.TransportError):
        await transport.handle_async_request(request)


@pytest.mark.asyncio
async def test_http_sync_only_body_is_refused_before_open(monkeypatch: pytest.MonkeyPatch) -> None:
    route = _route()
    connector = TetherConnector(catalog=lambda: (route,), installation_epoch="a" * 32, caller="intercom")

    async def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("Sync request body must refuse before connection")

    monkeypatch.setattr(connector, "open_tls", forbidden)
    transport = TetherHTTPTransport(
        connector=connector, selection=route.selection, application_identity_ref="peer-1", ca_file=Path("/unused")
    )
    request = httpx2.Request("POST", "https://peer.test:8443/", stream=httpx2.SyncByteStream())
    with pytest.raises(httpx2.TransportError):
        await transport.handle_async_request(request)
