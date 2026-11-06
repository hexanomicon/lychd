"""Closed HTTP transport through one existing rootless Podman model container.

This host adapter neither constructs Core nor starts, stops or reconfigures the
model. Its fixed container helper receives bounded request data on stdin only.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from collections.abc import Awaitable, Callable
from contextlib import suppress
from http import HTTPStatus
from typing import Any, NoReturn, cast

import httpx2

MAX_BODY_BYTES = 1_048_576
MAX_FRAME_BYTES = 2_097_152
PROCESS_TIMEOUT_SECONDS = 300
TERMINATE_TIMEOUT_SECONDS = 2
_MODEL_PORT = 28000
_MAX_HTTP_STATUS = 599
_ROUTES = {("GET", b"/health"), ("GET", b"/v1/models"), ("POST", b"/v1/chat/completions")}
_HEADERS = frozenset(
    {
        "host",
        "accept",
        "accept-encoding",
        "user-agent",
        "connection",
        "content-type",
        "content-length",
        "transfer-encoding",
    }
)

# The argv contains only this constant program. Neither its origin nor headers
# are supplied by the caller; Python isolation and ProxyHandler exclude ambient
# Python and HTTP proxy configuration inside the existing container.
_HELPER = r"""
import base64
import json
import sys
import urllib.error
import urllib.request

BODY_LIMIT = 1048576
FRAME_LIMIT = 2097152

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result

try:
    raw = sys.stdin.buffer.read(FRAME_LIMIT + 1)
    if len(raw) > FRAME_LIMIT:
        raise ValueError()
    value = json.loads(raw, object_pairs_hook=unique)
    if type(value) is not dict or set(value) != {"method", "path", "body"}:
        raise ValueError()
    method, path = value["method"], value["path"]
    if (method, path) not in {
        ("GET", "/health"), ("GET", "/v1/models"), ("POST", "/v1/chat/completions")
    } or type(value["body"]) is not str:
        raise ValueError()
    body = base64.b64decode(value["body"], validate=True)
    if len(body) > BODY_LIMIT or (method == "GET" and body):
        raise ValueError()
    request = urllib.request.Request(
        "http://127.0.0.1:28000" + path,
        data=body if method == "POST" else None,
        method=method,
        headers={"Content-Type": "application/json", "Accept-Encoding": "identity"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        response = opener.open(request, timeout=300)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            raise ValueError()
        status = response.getcode()
        body = response.read(BODY_LIMIT + 1)
    if type(status) is not int or not 100 <= status <= 599 or len(body) > BODY_LIMIT:
        raise ValueError()
    output = json.dumps(
        {"status": status, "body": base64.b64encode(body).decode("ascii")},
        separators=(",", ":"),
    ).encode("ascii")
    if len(output) > FRAME_LIMIT:
        raise ValueError()
    sys.stdout.buffer.write(output)
    sys.stdout.buffer.flush()
except Exception:
    sys.exit(1)
"""
_ARGV = ("podman", "exec", "--interactive", "lychd-night-qwen38", "python3", "-I", "-c", _HELPER)


def _fail(code: str, request: httpx2.Request) -> NoReturn:
    raise httpx2.TransportError(code, request=request) from None


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


async def _retire(process: asyncio.subprocess.Process) -> None:
    """Settle the one exec client, escalating only from terminate to kill."""
    if process.returncode is None:
        with suppress(ProcessLookupError):
            process.terminate()
    try:
        async with asyncio.timeout(TERMINATE_TIMEOUT_SECONDS):
            await process.wait()
    except TimeoutError:
        with suppress(ProcessLookupError):
            process.kill()
        await process.wait()


async def _settle(
    started: asyncio.Future[asyncio.subprocess.Process] | None, process: asyncio.subprocess.Process | None
) -> None:
    """Obtain a pending spawn's handle before settling that exec client."""

    async def cleanup() -> None:
        selected = process
        if selected is None and started is not None:
            with suppress(OSError):
                selected = await asyncio.shield(started)
        if selected is not None:
            await _retire(selected)

    task = asyncio.create_task(cleanup())
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    task.result()
    if cancelled:
        raise asyncio.CancelledError


async def _request_frame(request: httpx2.Request) -> bytes:
    url = request.url
    if (
        url.scheme != "http"
        or url.raw_host != b"127.0.0.1"
        or url.port != _MODEL_PORT
        or url.userinfo
        or url.query
        or url.fragment
        or (request.method, url.raw_path) not in _ROUTES
        or any(name not in _HEADERS for name in request.headers)
    ):
        _fail("model_podman_request", request)
    body = bytearray()
    try:
        if not isinstance(request.stream, httpx2.AsyncByteStream):
            _fail("model_podman_request", request)
        async for chunk in request.stream:
            if len(chunk) > MAX_BODY_BYTES - len(body):
                _fail("model_podman_request", request)
            body.extend(chunk)
    except (OSError, ValueError, TypeError, httpx2.StreamError):
        _fail("model_podman_request", request)
    if request.method == "GET" and body:
        _fail("model_podman_request", request)
    frame = json.dumps(
        {"method": request.method, "path": url.path, "body": base64.b64encode(body).decode("ascii")},
        separators=(",", ":"),
    ).encode("ascii")
    if len(frame) > MAX_FRAME_BYTES:
        _fail("model_podman_request", request)
    return frame


def _decode_response(output: bytes) -> tuple[int, bytes]:
    if type(output) is not bytes or len(output) > MAX_FRAME_BYTES:
        raise ValueError
    raw_value = json.loads(output, object_pairs_hook=_unique)
    if not isinstance(raw_value, dict):
        raise TypeError
    value = cast("dict[str, Any]", raw_value)
    if set(value) != {"status", "body"}:
        raise ValueError
    status = value["status"]
    if (
        type(status) is not int
        or not HTTPStatus.CONTINUE <= status <= _MAX_HTTP_STATUS
        or HTTPStatus.MULTIPLE_CHOICES <= status < HTTPStatus.BAD_REQUEST
    ):
        raise ValueError
    if type(value["body"]) is not str:
        raise ValueError
    content = base64.b64decode(value["body"], validate=True)
    if len(content) > MAX_BODY_BYTES:
        raise ValueError
    return status, content


def _authorize_payload(request: httpx2.Request) -> None:
    authorize = request.extensions.get("lychd_research_authorize")
    if authorize is not None:
        if not callable(authorize):
            msg = "model_authorization"
            raise ValueError(msg)
        authorize()


class PodmanModelTransport(httpx2.AsyncBaseTransport):
    """Admit the broker's fixed HTTP dialect through a bounded exec helper."""

    def __init__(
        self,
        *,
        process_factory: Callable[..., Awaitable[asyncio.subprocess.Process]] | None = None,
    ) -> None:
        """Bind the fixed executor without starting a process or network call."""
        self._process_factory = process_factory or asyncio.create_subprocess_exec

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Return one response without retries, redirects or forwarded headers."""
        frame = await _request_frame(request)
        environment = {
            name: os.environ[name] for name in ("HOME", "XDG_RUNTIME_DIR", "PATH", "LANG") if name in os.environ
        }
        process = None
        started = None
        try:
            async with asyncio.timeout(PROCESS_TIMEOUT_SECONDS):
                started = asyncio.ensure_future(
                    self._process_factory(
                        *_ARGV,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.DEVNULL,
                        env=environment,
                        limit=MAX_FRAME_BYTES + 1,
                    )
                )
                process = await asyncio.shield(started)
                _authorize_payload(request)
                output, _ = await process.communicate(frame)
        except ValueError:
            await _settle(started, process)
            raise
        except asyncio.CancelledError:
            await _settle(started, process)
            raise
        except TimeoutError:
            await _settle(started, process)
            code = "model_podman_timeout"
            raise httpx2.ReadTimeout(code, request=request) from None
        except OSError:
            await _settle(started, process)
            _fail("model_podman_start" if process is None else "model_podman_failed", request)
        if process.returncode != 0:
            _fail("model_podman_failed", request)
        try:
            status, content = _decode_response(output)
        except (ValueError, TypeError):
            _fail("model_podman_protocol", request)
        return httpx2.Response(status, content=content, headers={"Content-Type": "application/json"}, request=request)
