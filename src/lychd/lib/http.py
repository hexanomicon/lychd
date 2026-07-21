"""Async HTTP helpers shared by animation control planes and probes.

This module homes the single async JSON transport used by the llama.cpp control
plane and the OpenAI-compatible reachability probe (A3-U3: kills the blocking
stdlib ``urlopen`` calls). It also provides ``run_sync`` — a small,
transitional bridge that lets the still-synchronous registry surface (consumed
by the Dispatcher/OrchestratorManager) drive the new async primitives until the
agents builder migrates those call sites to ``await``.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, cast

import httpx

if TYPE_CHECKING:
    from collections.abc import Coroutine, Mapping

DEFAULT_TIMEOUT_SECONDS = 5.0
_HTTP_STATUS_BAD_REQUEST = 400


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
    timeout: float = DEFAULT_TIMEOUT_SECONDS,  # noqa: ASYNC109 - httpx owns the request timeout natively
    allow_null: bool = False,
) -> dict[str, object]:
    """Issue an async JSON request and normalize the response into a dict.

    Lists are wrapped as ``{"data": [...]}``; empty bodies become ``{}``. Raises
    ``HttpJsonError`` on transport failure, HTTP status >= 400, or invalid JSON —
    preserving the ``"{method} {path} failed ..."`` message discipline the
    llama.cpp control plane relied on with ``urlopen``.
    """
    request_headers = dict(headers or {})
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                url,
                params=dict(query) if query else None,
                json=dict(payload) if payload is not None else None,
                headers=request_headers,
            )
    except httpx.HTTPError as exc:
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
    if parsed is None and allow_null:
        return {}

    msg = f"{method} {url} returned unsupported payload type: {type(parsed)}"
    raise HttpJsonError(msg)


def run_sync[T](coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine to completion from synchronous code.

    When no event loop is running (startup thread, CLI, tests) this uses
    ``asyncio.run``. When a loop is already running (a synchronous registry
    method invoked from an async Dispatcher/Orchestrator path) the coroutine is
    executed on a dedicated worker-thread loop so the call still returns a value
    without ``asyncio.run`` complaining about a running loop. This is the
    transitional shim flagged in the platform contract; it blocks the caller for
    the duration of the request exactly as the old ``urlopen`` code did.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


__all__ = ["DEFAULT_TIMEOUT_SECONDS", "HttpJsonError", "request_json", "run_sync"]
