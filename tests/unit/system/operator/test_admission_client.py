from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import httpx
import pytest
from http_message_signatures import algorithms
from http_message_signatures.http_sfv.dictionary import Dictionary
from http_message_signatures.resolvers import HTTPSignatureKeyResolver
from http_message_signatures.signatures import HTTPMessageSigner
from pydantic import SecretStr

from lychd.config.constants import STOP_ADMISSION_PATH
from lychd.system.operator.admission import StopAdmissionProtocol
from lychd.system.operator.admission_client import StopAdmissionClient
from lychd.system.operator.models import OperatorAuthorityError
from lychd.system.services.local_access import LocalAccess

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pytest_mock import MockerFixture

_PASSWORD = "dedicated-local-operator-password-for-tests"  # noqa: S105 - isolated fixture credential
_GENERATION = "a" * 64


class _LegacyKeys(HTTPSignatureKeyResolver):
    def resolve_private_key(self, key_id: str) -> bytes:
        assert key_id == "lychd-local-operator@1"
        return _PASSWORD.encode("ascii")

    def resolve_public_key(self, key_id: str) -> bytes:
        return self.resolve_private_key(key_id)


class _Body(httpx.AsyncByteStream):
    def __init__(self, *chunks: bytes, delay: float = 0) -> None:
        self._chunks = chunks
        self._delay = delay

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            await asyncio.sleep(self._delay)
            yield chunk


class _ClosingBody(httpx.AsyncByteStream):
    def __init__(self, *, block_read: bool, block_close: bool) -> None:
        self.content = b""
        self.read_started = asyncio.Event()
        self.close_started = False
        self.close_cancelled = False
        self._block_read = block_read
        self._block_close = block_close

    async def __aiter__(self) -> AsyncIterator[bytes]:
        self.read_started.set()
        if self._block_read:
            await asyncio.Event().wait()
        yield self.content

    async def aclose(self) -> None:
        self.close_started = True
        if self._block_close:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.close_cancelled = True
                raise


class _ClosingTransport(httpx.MockTransport):
    def __init__(self, *, block_read: bool, block_stream_close: bool, block_transport_close: bool) -> None:
        self.body = _ClosingBody(block_read=block_read, block_close=block_stream_close)
        self.close_started = False
        self.close_cancelled = False
        self._block_transport_close = block_transport_close
        super().__init__(self._reply)

    def _reply(self, request: httpx.Request) -> httpx.Response:
        reply = StopAdmissionProtocol(_PASSWORD).admit(request)
        self.body.content = reply.content
        return httpx.Response(reply.status_code, headers=reply.headers.raw, stream=self.body)

    async def aclose(self) -> None:
        self.close_started = True
        if self._block_transport_close:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.close_cancelled = True
                raise


def _access(url: str = "http://127.0.0.1:8200/") -> LocalAccess:
    return LocalAccess(url=url, password=SecretStr(_PASSWORD))


def _reply(request: httpx.Request) -> httpx.Response:
    reply = StopAdmissionProtocol(_PASSWORD).admit(request)
    return httpx.Response(reply.status_code, headers=reply.headers.raw, stream=_Body(reply.content))


def test_exchange_authenticates_exact_literal_loopback_request_without_basic() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url == f"http://127.0.0.1:8200{STOP_ADMISSION_PATH}"
        assert request.method == "POST"
        assert "authorization" not in request.headers
        assert request.headers["accept-encoding"] == "identity"
        assert _PASSWORD.encode() not in request.content
        return _reply(request)

    client = StopAdmissionClient(access_loader=_access, transport=httpx.MockTransport(handle))
    client.admit(_GENERATION)
    client.admit(_GENERATION)

    assert len(requests) == 2
    assert requests[0].content != requests[1].content


def test_old_servers_authentic_version_one_reply_cannot_authorize_client() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        assert body["version"] == 2
        assert body["launcher_profile"] == "native-owned-lifespan@1"
        reply = httpx.Response(
            200,
            json={
                "version": 1,
                "request_nonce": body["nonce"],
                "operation": body["operation"],
                "binding_generation": body["binding_generation"],
                "request_method": request.method,
                "request_uri": str(request.url),
                "request_content_digest": request.headers["content-digest"],
                "decision": "admit",
            },
            request=request,
        )
        reply.headers["content-digest"] = str(Dictionary({"sha-256": hashlib.sha256(reply.content).digest()}))
        signer = HTTPMessageSigner(
            signature_algorithm=algorithms.HMAC_SHA256,  # pyright: ignore[reportPrivateImportUsage]
            key_resolver=_LegacyKeys(),
        )
        now = datetime.now(UTC)
        signer.sign(  # pyright: ignore[reportUnknownMemberType]
            reply,
            key_id="lychd-local-operator@1",
            nonce=body["nonce"],
            tag="lychd-system-stop-reply@1",
            created=now,
            expires=now + timedelta(seconds=30),
            covered_component_ids=("@status", "content-type", "content-digest"),
        )
        return httpx.Response(reply.status_code, headers=reply.headers.raw, stream=_Body(reply.content))

    client = StopAdmissionClient(access_loader=_access, transport=httpx.MockTransport(handle))
    with pytest.raises(OperatorAuthorityError, match="no host action was taken"):
        client.admit(_GENERATION)
    assert len(requests) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8200/",
        "http://localhost:8200/",
        "http://127.1:8200/",
        "http://[::1]:8200/",
        "http://127.0.0.1:8200/extra",
        "http://127.0.0.1:8200/?query=1",
        "http://127.0.0.1:8200/#fragment",
        "http://magus:password@127.0.0.1:8200/",
        "http://127.0.0.1/",
    ],
)
def test_untrusted_address_refuses_before_network(url: str) -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _reply(request)

    client = StopAdmissionClient(access_loader=lambda: _access(url), transport=httpx.MockTransport(handle))

    with pytest.raises(OperatorAuthorityError, match="no host action was taken"):
        client.admit(_GENERATION)

    assert requests == []


def test_complete_exchange_deadline_covers_slow_response_body(mocker: MockerFixture) -> None:
    mocker.patch("lychd.system.operator.admission_client._EXCHANGE_TIMEOUT_SECONDS", 0.025)

    def handle(request: httpx.Request) -> httpx.Response:
        reply = StopAdmissionProtocol(_PASSWORD).admit(request)
        return httpx.Response(reply.status_code, headers=reply.headers.raw, stream=_Body(reply.content, delay=1))

    client = StopAdmissionClient(access_loader=_access, transport=httpx.MockTransport(handle))
    start = time.monotonic()

    with pytest.raises(OperatorAuthorityError):
        client.admit(_GENERATION)

    assert time.monotonic() - start < 0.5


@pytest.mark.parametrize("failure", ["exchange-and-both-closes", "transport-close-after-valid-ack"])
def test_cleanup_has_independent_budgets_and_refuses_uncertainty(mocker: MockerFixture, failure: str) -> None:
    mocker.patch("lychd.system.operator.admission_client._EXCHANGE_TIMEOUT_SECONDS", 0.025)
    mocker.patch("lychd.system.operator.admission_client._CLEANUP_TIMEOUT_SECONDS", 0.025)
    interrupted_exchange = failure == "exchange-and-both-closes"
    transport = _ClosingTransport(
        block_read=interrupted_exchange,
        block_stream_close=interrupted_exchange,
        block_transport_close=True,
    )
    client = StopAdmissionClient(access_loader=_access, transport=transport)
    start = time.monotonic()

    with pytest.raises(OperatorAuthorityError, match="no host action was taken"):
        client.admit(_GENERATION)

    assert time.monotonic() - start < 0.5
    assert transport.body.close_started
    assert transport.body.close_cancelled is interrupted_exchange
    assert transport.close_started
    assert transport.close_cancelled


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["exchange-timeout", "transport-close-timeout", "caller-cancellation"])
async def test_cleanup_timeouts_leave_no_pending_tasks_and_preserve_cancellation(
    mocker: MockerFixture, failure: str
) -> None:
    mocker.patch("lychd.system.operator.admission_client._EXCHANGE_TIMEOUT_SECONDS", 0.025)
    mocker.patch("lychd.system.operator.admission_client._CLEANUP_TIMEOUT_SECONDS", 0.025)
    interrupted_exchange = failure != "transport-close-timeout"
    transport = _ClosingTransport(
        block_read=interrupted_exchange,
        block_stream_close=interrupted_exchange,
        block_transport_close=True,
    )
    client = StopAdmissionClient(access_loader=_access, transport=transport)
    before = asyncio.all_tasks()
    task = asyncio.create_task(client._admit(_GENERATION, _access()))  # pyright: ignore[reportPrivateUsage]
    if failure == "caller-cancellation":
        await transport.body.read_started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        with pytest.raises(TimeoutError):
            await task

    assert transport.body.close_started
    assert transport.body.close_cancelled is interrupted_exchange
    assert transport.close_started
    assert transport.close_cancelled
    assert asyncio.all_tasks() == before


@pytest.mark.parametrize("failure", ["oversize", "redirect", "encoding", "tampered"])
def test_unverified_or_unbounded_reply_refuses(failure: str) -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        reply = StopAdmissionProtocol(_PASSWORD).admit(request)
        headers = list(reply.headers.raw)
        body = reply.content
        status = reply.status_code
        if failure == "oversize":
            body = b"x" * 4097
        elif failure == "redirect":
            status = 307
            headers.append((b"location", b"http://127.0.0.1:8300/"))
        elif failure == "encoding":
            headers.append((b"content-encoding", b"gzip"))
        else:
            body = b"{}"
        return httpx.Response(status, headers=headers, stream=_Body(body))

    client = StopAdmissionClient(access_loader=_access, transport=httpx.MockTransport(handle))

    with pytest.raises(OperatorAuthorityError):
        client.admit(_GENERATION)

    assert len(requests) == 1


def test_errors_hide_loader_and_transport_credentials() -> None:
    def load() -> LocalAccess:
        raise ValueError(_PASSWORD)

    client = StopAdmissionClient(access_loader=load)

    with pytest.raises(OperatorAuthorityError) as caught:
        client.admit(_GENERATION)

    assert _PASSWORD not in str(caught.value)
    assert caught.value.__suppress_context__


def test_transport_exception_cannot_reveal_credentials() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(_PASSWORD, request=request)

    client = StopAdmissionClient(access_loader=_access, transport=httpx.MockTransport(handle))

    with pytest.raises(OperatorAuthorityError) as caught:
        client.admit(_GENERATION)

    assert _PASSWORD not in str(caught.value)
    assert caught.value.__suppress_context__


def test_credential_loading_is_lazy() -> None:
    calls: list[str] = []

    def load() -> LocalAccess:
        calls.append("load")
        return _access()

    client = StopAdmissionClient(access_loader=load, transport=httpx.MockTransport(_reply))
    assert calls == []

    client.admit(_GENERATION)

    assert calls == ["load"]


def test_client_disables_environment_proxies_and_redirects(mocker: MockerFixture) -> None:
    factory = mocker.spy(httpx, "AsyncClient")
    client = StopAdmissionClient(access_loader=_access, transport=httpx.MockTransport(_reply))

    client.admit(_GENERATION)

    assert factory.call_args.kwargs["trust_env"] is False
    assert factory.call_args.kwargs["follow_redirects"] is False
    assert factory.call_args.kwargs["auth"] is None
