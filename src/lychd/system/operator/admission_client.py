"""Inert stop admission: five-second exchange, then two one-second close budgets.

The credential loader retains its existing host-adapter bounds. HTTP transports
must cooperate with cancellation; cleanup uncertainty refuses the operation.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import httpx

from lychd.config.constants import STOP_ADMISSION_PATH
from lychd.system.operator.admission import (
    MAX_ADMISSION_BODY_BYTES,
    StopAdmissionProtocol,
)
from lychd.system.operator.models import OperatorAuthorityError

if TYPE_CHECKING:
    from collections.abc import Callable

    from lychd.system.services.local_access import LocalAccess

_EXCHANGE_TIMEOUT_SECONDS = 5.0
_CLEANUP_TIMEOUT_SECONDS = 1.0
_MAX_PORT = 65535
_REFUSAL = "Local stop admission could not be authenticated; no host action was taken."


class StopAdmissionClient:
    """Authenticate one fresh local request and its corresponding inert reply."""

    def __init__(
        self,
        *,
        access_loader: Callable[[], LocalAccess] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Keep credential retrieval lazy and allow an isolated HTTP transport."""
        self._access_loader = access_loader
        self._transport = transport

    def admit(self, binding_generation: str) -> None:
        """Load the credential, then bound the whole exchange and conceal all failure data."""
        try:
            access = self._load_access()
            asyncio.run(self._admit(binding_generation, access))
        except Exception:  # noqa: BLE001 - transport/configuration errors must never expose credentials
            raise OperatorAuthorityError(_REFUSAL) from None

    async def _admit(self, binding_generation: str, access: LocalAccess) -> None:
        port = urlsplit(access.url).port
        if port is None or not 0 < port <= _MAX_PORT or access.url != f"http://127.0.0.1:{port}/":
            raise ValueError(_REFUSAL)
        protocol = StopAdmissionProtocol(access.password.get_secret_value())
        request = protocol.request(f"http://127.0.0.1:{port}{STOP_ADMISSION_PATH}", binding_generation)
        request.headers["Accept-Encoding"] = "identity"
        client = httpx.AsyncClient(
            trust_env=False,
            follow_redirects=False,
            auth=None,
            timeout=_EXCHANGE_TIMEOUT_SECONDS,
            transport=self._transport,
        )
        response = None
        exchange_failed = True
        try:
            async with asyncio.timeout(_EXCHANGE_TIMEOUT_SECONDS):
                response = await client.send(request, stream=True)
                if response.headers.get("content-encoding", "identity") != "identity":
                    raise ValueError(_REFUSAL)
                body = bytearray()
                async for chunk in response.aiter_raw():
                    if len(body) + len(chunk) > MAX_ADMISSION_BODY_BYTES:
                        raise ValueError(_REFUSAL)
                    body.extend(chunk)
                reply = httpx.Response(
                    response.status_code,
                    headers=response.headers.raw,
                    content=bytes(body),
                    request=request,
                )
                protocol.verify_reply(request, reply)
            exchange_failed = False
        finally:
            await self._close_http(response, client, exchange_failed=exchange_failed)

    @staticmethod
    async def _close_http(response: httpx.Response | None, client: httpx.AsyncClient, *, exchange_failed: bool) -> None:
        """Attempt both closes under independent deadlines, preserving primary failure."""
        cleanup_error: BaseException | None = None
        try:
            if response is not None:
                try:
                    async with asyncio.timeout(_CLEANUP_TIMEOUT_SECONDS):
                        await response.aclose()
                except BaseException as exc:  # noqa: BLE001 - client close must still be attempted
                    cleanup_error = exc
        finally:
            try:
                async with asyncio.timeout(_CLEANUP_TIMEOUT_SECONDS):
                    await client.aclose()
            except BaseException as exc:  # noqa: BLE001 - preserve cancellation over ordinary cleanup failure
                if cleanup_error is None or isinstance(exc, asyncio.CancelledError):
                    cleanup_error = exc
        if isinstance(cleanup_error, asyncio.CancelledError) or (cleanup_error is not None and not exchange_failed):
            raise cleanup_error

    def _load_access(self) -> LocalAccess:
        if self._access_loader is not None:
            return self._access_loader()
        from lychd.system.services.local_access import load_local_access

        return load_local_access()
