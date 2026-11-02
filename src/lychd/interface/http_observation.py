"""Observe SDK HTTP header dispatch through aiohttp's public tracing signals.

One logical request can dispatch multiple attempts through persistent-connection
retry or redirect. Header dispatch follows connection acquisition but precedes
serialization and socket write; it does not prove bytes reached the peer. Failures
before that boundary emit no transport attempt. Response completion covers only
headers, not body consumption, effect settlement, or WebSocket frames.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from types import SimpleNamespace

import aiohttp

from lychd.interface.observation import ObservedOperation, OperationObserver


class _TraceContext(SimpleNamespace):
    def __init__(self, *, trace_request_ctx: object = None) -> None:
        """Discard caller metadata and retain only local logical/attempt identities."""
        del trace_request_ctx
        super().__init__()
        self.logical: ObservedOperation | None = None
        self.attempt: ObservedOperation | None = None


def _operation_name(method: str) -> str:
    value = method.lower()
    return f"http.{value}" if value in {"get", "post", "put", "patch", "delete", "head", "options"} else "http.other"


class _HttpObserver:
    """Bind one driver's callbacks and a private copy of its safe destination map."""

    def __init__(self, observer: OperationObserver, targets: Mapping[str, str] | None) -> None:
        """Retain only the observer and configured host-to-component mapping."""
        self.observer = observer
        self.targets = dict(targets or {})

    async def _start(
        self, _session: aiohttp.ClientSession, context: SimpleNamespace, params: aiohttp.TraceRequestStartParams
    ) -> None:
        if not isinstance(context, _TraceContext):
            return
        try:
            context.logical = self.observer.operation(_operation_name(params.method))
        except (Exception, asyncio.CancelledError):  # noqa: BLE001 - SDK observers cannot alter traffic
            return

    async def _headers(
        self, _session: aiohttp.ClientSession, context: SimpleNamespace, params: aiohttp.TraceRequestHeadersSentParams
    ) -> None:
        if not isinstance(context, _TraceContext) or context.logical is None:
            return
        try:
            if context.attempt is not None:
                # aiohttp may retry internally without issuing a finish or another request-start.
                context.attempt.finish("unknown", error="unknown")
            target = self.targets.get(params.url.host or "", self.observer.target)
            context.attempt = context.logical.next_attempt(name=_operation_name(params.method), target=target)
            context.attempt.start()
        except (Exception, asyncio.CancelledError):  # noqa: BLE001 - SDK observers cannot alter traffic
            return

    async def _response(
        self,
        _session: aiohttp.ClientSession,
        context: SimpleNamespace,
        params: aiohttp.TraceRequestEndParams | aiohttp.TraceRequestRedirectParams,
    ) -> None:
        if not isinstance(context, _TraceContext):
            return
        try:
            if context.attempt is not None:
                context.attempt.http_status = params.response.status
                # Every HTTP response, including 403 or 101, completes this transport boundary.
                # Application rejection and journal/effect outcome retain separate owners.
                context.attempt.finish("succeeded")
                context.attempt = None
        except (Exception, asyncio.CancelledError):  # noqa: BLE001 - SDK observers cannot alter traffic
            return

    async def _exception(
        self, _session: aiohttp.ClientSession, context: SimpleNamespace, params: aiohttp.TraceRequestExceptionParams
    ) -> None:
        if not isinstance(context, _TraceContext):
            return
        try:
            if context.attempt is not None:
                cancelled = isinstance(params.exception, asyncio.CancelledError)
                context.attempt.finish(
                    "cancelled" if cancelled else "failed",
                    error="cancelled"
                    if cancelled
                    else "timeout"
                    if isinstance(params.exception, TimeoutError)
                    else "transport",
                )
                context.attempt = None
        except (Exception, asyncio.CancelledError):  # noqa: BLE001 - SDK observers cannot alter traffic
            return

    def configure(self) -> aiohttp.TraceConfig:
        """Connect only supported public signals, retaining callbacks through their config."""
        trace = aiohttp.TraceConfig(trace_config_ctx_factory=_TraceContext)
        trace.on_request_start.append(self._start)
        trace.on_request_headers_sent.append(self._headers)
        trace.on_request_end.append(self._response)
        trace.on_request_redirect.append(self._response)
        trace.on_request_exception.append(self._exception)
        return trace


def http_trace(observer: OperationObserver, *, targets: Mapping[str, str] | None = None) -> aiohttp.TraceConfig:
    """Bind logical requests and each observed header dispatch without capturing URLs."""
    return _HttpObserver(observer, targets).configure()
