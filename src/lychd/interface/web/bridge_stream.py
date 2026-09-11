"""HTTP-lifetime reservations for bounded Bridge event streams."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.exceptions import HTTPException
from litestar.response import ServerSentEvent
from litestar.response.base import ASGIResponse
from litestar.status_codes import HTTP_429_TOO_MANY_REQUESTS

from lychd.domain.cortex.events import InProcessEventBus, RunStreamLimitError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar.response import ServerSentEventMessage
    from litestar.types import Receive, Scope, Send


class _ReservedStreamResponse(ASGIResponse):
    """Acquire before headers and release independently of generator startup."""

    def __init__(self, response: ASGIResponse, *, bus: InProcessEventBus, run_id: str) -> None:
        """Retain the configured response and its process-local reservation owner."""
        super().__init__()
        self._response = response
        self._bus = bus
        self._run_id = run_id

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            with self._bus.reserve_http_stream(self._run_id):
                await self._response(scope, receive, send)
        except RunStreamLimitError as exc:
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
                headers={"Retry-After": "5"},
            ) from exc


class BoundedRunEventStream(ServerSentEvent):
    """Keep Litestar's SSE encoding while reserving its complete ASGI lifetime."""

    def __init__(self, content: AsyncIterator[ServerSentEventMessage], *, bus: InProcessEventBus, run_id: str) -> None:
        """Bind semantic events to the Run whose HTTP stream capacity they consume."""
        super().__init__(content)
        self._bus = bus
        self._run_id = run_id

    def to_asgi_response(self, *args: Any, **kwargs: Any) -> ASGIResponse:
        """Wrap the fully configured response without duplicating Litestar options."""
        # Litestar annotates the inherited Request without its generic arguments.
        response = super().to_asgi_response(*args, **kwargs)  # pyright: ignore[reportUnknownMemberType]
        return _ReservedStreamResponse(response, bus=self._bus, run_id=self._run_id)
