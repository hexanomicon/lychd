"""One-shot bounded HTTPS over an explicitly selected Tether service."""

# One finite parser owns refusal normalization and stream closure.
# ruff: noqa: TRY301

from __future__ import annotations

import asyncio
import math
import time
from pathlib import Path
from typing import TYPE_CHECKING, cast

import h11
import httpx2

from lychd.domain.scout.transport import FetchCode, FetchError, NetworkHandoff, NetworkTarget
from lychd.domain.tether.models import TetherSelection
from lychd.system.services.scout_socket import PinnedTlsStream
from lychd.system.services.tether.connector import TetherConnector

if TYPE_CHECKING:
    from collections.abc import Callable

_MAX_REQUEST = 64 * 1024
_MAX_RESPONSE = 4 * 1024 * 1024
_MAX_HEAD = 16 * 1024
_MAX_SECONDS = 30.0
_MAX_FIELDS = 64
_REDIRECT_MIN = 300
_REDIRECT_MAX = 400


class _ServiceGate:
    def __init__(self, current: Callable[[], None]) -> None:
        self.current = current

    def handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:
        self.current()
        if handoff.target.role != "origin":
            raise FetchError(FetchCode.CONFIG)
        # This transport supplies reachability only. The service caller owns its
        # request and credentials; the connector checks current route admission.
        return action()


class TetherHTTPTransport(httpx2.AsyncBaseTransport):
    """Exact HTTPS origin, fixed caller and selection, no retries or retained pool.

    Use with the shared create_async_http_client factory. Each request resolves
    current admission and verifies TLS again. No ambient DNS or proxy is used.
    """

    def __init__(
        self,
        *,
        connector: TetherConnector,
        selection: TetherSelection,
        application_identity_ref: str,
        ca_file: Path,
    ) -> None:
        """Bind one trusted caller, application identity and attachment selection."""
        self.connector = connector
        self.selection = selection
        self.application_identity_ref = application_identity_ref
        self.ca_file = ca_file
        self._closed = False
        self._streams: set[PinnedTlsStream] = set()

    def _admit(self) -> None:
        if self._closed:
            raise FetchError(FetchCode.EGRESS)

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Enforce one absolute deadline, including request body consumption."""
        try:
            async with asyncio.timeout(_request_seconds(request)):
                return await self._exchange(request)
        except TimeoutError:
            message = "Tether deadline expired."
            raise httpx2.TimeoutException(message, request=request) from None

    async def _exchange(self, request: httpx2.Request) -> httpx2.Response:  # noqa: C901, PLR0912, PLR0915 - finite parser with owned closure
        """Buffer only finite messages; close the selected stream on every outcome."""
        stream = None
        try:
            if self._closed:
                raise FetchError(FetchCode.CONFIG)
            route = self.connector.resolve(self.selection)
            if (
                request.url.scheme != "https"
                or request.url.host != route.hostname
                or (request.url.port or 443) != route.port
                or request.url.userinfo
                or request.url.fragment
                or request.headers.get("host") != request.url.netloc.decode("ascii")
                or "transfer-encoding" in request.headers
                or "proxy-authorization" in request.headers
            ):
                raise FetchError(FetchCode.DESTINATION)
            if not isinstance(request.stream, httpx2.AsyncByteStream):
                raise FetchError(FetchCode.CONFIG)
            body = bytearray()
            async for chunk in request.stream:
                body.extend(chunk)
                if len(body) > _MAX_REQUEST:
                    raise FetchError(FetchCode.LIMIT)
            headers = [
                (k, v)
                for k, v in request.headers.raw
                if k.lower() not in {b"connection", b"content-length", b"accept-encoding"}
            ]
            headers.extend(
                [
                    (b"accept-encoding", b"identity"),
                    (b"connection", b"close"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ]
            )
            connection = h11.Connection(h11.CLIENT, max_incomplete_event_size=_MAX_HEAD)
            head = connection.send(h11.Request(method=request.method, target=request.url.raw_path, headers=headers))
            wire = head + connection.send(h11.Data(data=bytes(body))) + connection.send(h11.EndOfMessage())
            if len(head) > _MAX_HEAD or len(wire) > _MAX_REQUEST:
                raise FetchError(FetchCode.LIMIT)
            stream = await self.connector.open_tls(
                self.selection,
                target=NetworkTarget(route.address, route.port, route.hostname, "origin"),
                application_identity_ref=self.application_identity_ref,
                gate=_ServiceGate(self._admit),
                deadline=time.monotonic() + _MAX_SECONDS,
                ca_file=self.ca_file,
            )
            if self._closed:
                raise FetchError(FetchCode.CONFIG)
            self._streams.add(stream)
            await stream.send(wire)
            response: h11.Response | None = None
            content = bytearray()
            received = 0
            raw_head = bytearray()
            while True:
                self.connector.current(route)
                data = await stream.receive()
                received += len(data)
                if received > _MAX_RESPONSE + _MAX_HEAD:
                    raise FetchError(FetchCode.LIMIT)
                if response is None:
                    raw_head.extend(data)
                    marker = raw_head.find(b"\r\n\r\n")
                    if (marker < 0 and len(raw_head) > _MAX_HEAD) or marker + 4 > _MAX_HEAD:
                        raise FetchError(FetchCode.LIMIT)
                    if marker >= 0:
                        names = [
                            line.partition(b":")[0].lower() for line in bytes(raw_head[:marker]).split(b"\r\n")[1:]
                        ]
                        if len(names) != len(set(names)) or b"content-encoding" in names:
                            raise FetchError(FetchCode.PROTOCOL)
                        raw_head.clear()
                connection.receive_data(data)
                while True:
                    event = connection.next_event()
                    if event is h11.NEED_DATA:
                        break
                    if isinstance(event, h11.Response):
                        if (
                            response is not None
                            or len(event.headers) > _MAX_FIELDS
                            or _REDIRECT_MIN <= event.status_code < _REDIRECT_MAX
                        ):
                            raise FetchError(FetchCode.PROTOCOL)
                        response = event
                    elif isinstance(event, h11.Data):
                        content.extend(event.data)
                        if len(content) > _MAX_RESPONSE:
                            raise FetchError(FetchCode.LIMIT)
                    elif isinstance(event, h11.EndOfMessage):
                        if response is None or event.headers or connection.trailing_data[0]:
                            raise FetchError(FetchCode.PROTOCOL)
                        self.connector.current(route)
                        return httpx2.Response(
                            response.status_code, headers=list(response.headers), content=bytes(content)
                        )
                    else:
                        raise FetchError(FetchCode.PROTOCOL)
                if not data:
                    raise FetchError(FetchCode.PROTOCOL)
        except (FetchError, OSError, ValueError, h11.ProtocolError):
            message = "Tether service request refused."
            raise httpx2.TransportError(message, request=request) from None
        finally:
            if stream is not None:
                self._streams.discard(stream)
                stream.close()

    async def aclose(self) -> None:
        """Permanently refuse future requests; each exchange owns its connection."""
        self._closed = True
        for stream in tuple(self._streams):
            stream.close()
        self._streams.clear()


def _request_seconds(request: httpx2.Request) -> float:
    """Apply the caller's tighter timeout within the transport's absolute ceiling."""
    configured: object = request.extensions.get("timeout", {})
    if not isinstance(configured, dict):
        message = "Invalid Tether request timeout."
        raise httpx2.TransportError(message, request=request)
    seconds = _MAX_SECONDS
    for value in cast("dict[object, object]", configured).values():
        if value is None:
            continue
        if type(value) not in {int, float}:
            message = "Invalid Tether request timeout."
            raise httpx2.TransportError(message, request=request)
        numeric = cast("int | float", value)
        if not math.isfinite(numeric) or numeric <= 0:
            message = "Invalid Tether request timeout."
            raise httpx2.TransportError(message, request=request)
        seconds = min(seconds, float(numeric))
    return seconds
