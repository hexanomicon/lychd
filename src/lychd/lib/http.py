"""Shared HTTP client construction and the animation control-plane JSON helper.

Adapters own destinations, credentials, protocol semantics and client lifetime.
The factories supply one nonambient HTTP/HTTPS policy without a global session.
``request_json`` retains its narrow control-plane normalization; ``run_sync``
bridges the still-synchronous registry to async probe primitives.
"""

from __future__ import annotations

import asyncio
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, cast

import certifi
import httpx2

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine, Mapping, Sequence

DEFAULT_TIMEOUT_SECONDS = 5.0
_HTTP_STATUS_BAD_REQUEST = 400


def create_http_ssl_context() -> ssl.SSLContext:
    """Use maintained public roots without ambient CA or key-log configuration."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if sys.version_info >= (3, 13):  # noqa: UP036 - the declared Python 3.12 keeps its stdlib TLS defaults
        context.verify_flags |= ssl.VERIFY_X509_STRICT | ssl.VERIFY_X509_PARTIAL_CHAIN
    context.load_verify_locations(cafile=certifi.where())
    return context


def _pool_limits(limits: httpx2.Limits | None) -> httpx2.Limits:
    # Limits() is unbounded; preserve the pinned client's actual 100/20 defaults.
    return limits if limits is not None else httpx2.Limits(max_connections=100, max_keepalive_connections=20)


def create_async_http_transport(*, limits: httpx2.Limits | None = None) -> httpx2.AsyncHTTPTransport:
    """Create an owned HTTP/HTTPS transport with verified TLS and no retries."""
    return httpx2.AsyncHTTPTransport(
        verify=create_http_ssl_context(),
        trust_env=False,
        retries=0,
        limits=_pool_limits(limits),
    )


def create_async_http_client(
    *,
    timeout: float | httpx2.Timeout,
    limits: httpx2.Limits | None = None,
    transport: httpx2.AsyncBaseTransport | None = None,
    base_url: str = "",
    headers: Mapping[str, str] | None = None,
    request_hooks: Sequence[Callable[[httpx2.Request], Awaitable[None]]] = (),
) -> httpx2.AsyncClient:
    """Create a caller-owned client without ambient routing or redirects.

    The default network transport verifies maintained public roots, uses zero
    connection retries, and receives the supplied pool limits. A custom transport
    owns its wire policy and limits; entering/closing the client enters/closes
    that transport. No request or authorization occurs during construction.
    """
    return httpx2.AsyncClient(
        verify=create_http_ssl_context(),
        trust_env=False,
        follow_redirects=False,
        timeout=timeout,
        limits=_pool_limits(limits),
        transport=transport,
        base_url=base_url,
        headers=headers,
        event_hooks={"request": list(request_hooks)},
    )


class HttpJsonError(RuntimeError):
    """Raised when an async JSON HTTP request fails or returns a non-JSON body."""

    def __init__(self, message: str, *, status: int | None = None, transport: bool = False) -> None:
        """Store status and whether the request failed before a valid HTTP response."""
        super().__init__(message)
        self.status = status
        self.transport = transport


async def request_json(
    method: str,
    url: str,
    *,
    query: Mapping[str, str] | None = None,
    payload: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,  # noqa: ASYNC109 - httpx2 owns the request timeout natively
) -> dict[str, object]:
    """Issue a direct, non-redirecting JSON request and normalize its response.

    Lists are wrapped as ``{"data": [...]}``; empty bodies become ``{}``. Raises
    ``HttpJsonError`` on transport failure, HTTP status >= 400, or invalid JSON —
    preserving the ``"{method} {path} failed ..."`` message discipline the
    llama.cpp control plane relied on with ``urlopen``.
    """
    request_headers = dict(headers or {})
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")

    try:
        async with create_async_http_client(timeout=timeout) as client:
            response = await client.request(
                method,
                url,
                params=dict(query) if query else None,
                json=dict(payload) if payload is not None else None,
                headers=request_headers,
            )
    except httpx2.HTTPError as exc:
        msg = f"{method} {url} failed: {exc}"
        raise HttpJsonError(msg, transport=True) from exc

    if response.status_code >= _HTTP_STATUS_BAD_REQUEST:
        body = response.text[:200]
        msg = f"{method} {url} failed with status {response.status_code}: {body}"
        raise HttpJsonError(msg, status=response.status_code)

    text = response.text
    if not text.strip():
        return {}

    try:
        parsed: object = response.json()
    except ValueError as exc:
        msg = f"{method} {url} returned invalid JSON: {text[:120]}"
        raise HttpJsonError(msg) from exc

    if isinstance(parsed, dict):
        mapping = cast("dict[object, object]", parsed)
        return {str(key): value for key, value in mapping.items()}
    if isinstance(parsed, list):
        return {"data": cast("list[object]", parsed)}
    msg = f"{method} {url} returned unsupported payload type: {type(parsed)}"
    raise HttpJsonError(msg)


def run_sync[T](coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine from synchronous registry code, including under an active loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "HttpJsonError",
    "create_async_http_client",
    "create_async_http_transport",
    "create_http_ssl_context",
    "request_json",
    "run_sync",
]
