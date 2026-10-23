from __future__ import annotations

import asyncio

# pyright: reportPrivateUsage=false
import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol, cast

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from http_message_signatures import algorithms
from http_message_signatures.resolvers import HTTPSignatureKeyResolver
from http_message_signatures.signatures import HTTPMessageSigner, HTTPMessageVerifier

from lychd.domain.intercom.codec import send_params
from lychd.domain.intercom.transport import IntercomEndpoint, IntercomError, IntercomHandoff, PreparedRequest
from lychd.domain.scout.transport import NetworkHandoff, NetworkTarget
from lychd.system.services import intercom_http
from lychd.system.services.intercom_http import (
    EXTENSION_URI,
    REQUEST_TAG,
    RESPONSE_COMPONENTS,
    RESPONSE_TAG,
    BoundedIntercomHTTP,
    content_digest,
    prepare_request,
    verify_response,
)


class _Signer(Protocol):
    def sign(
        self,
        message: object,
        *,
        key_id: str,
        nonce: str,
        tag: str,
        created: datetime,
        expires: datetime,
        covered_component_ids: Sequence[str],
        label: str,
    ) -> None: ...


class _Verifier(Protocol):
    def verify(self, message: object, *, expect_tag: str) -> list[object]: ...


class _Key(HTTPSignatureKeyResolver):
    def __init__(self, private: bytes, public: bytes) -> None:
        self.private, self.public = private, public

    def resolve_private_key(self, key_id: str) -> bytes:
        del key_id
        return self.private

    def resolve_public_key(self, key_id: str) -> bytes:
        del key_id
        return self.public


@dataclass
class _Response:
    url: str
    headers: dict[str, str]
    status_code: int = 200


@dataclass
class _Request:
    url: str
    headers: dict[str, str]
    method: str = "POST"


def _key() -> _Key:
    key = Ed25519PrivateKey.generate()
    return _Key(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
        key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo),
    )


@pytest.fixture
def keys() -> tuple[_Key, _Key]:
    return _key(), _key()


def _prepared(key: _Key) -> PreparedRequest:
    return prepare_request(
        method="SendMessage",
        local_task_id="local-1",
        attempt_id="attempt-1",
        peer_id="peer-1",
        workload_id="workload-1",
        task_schema="public-echo@1",
        endpoint="https://peer.test:8443/a2a",
        params=send_params("public text", "message-1"),
        signing_key=key.private,
        key_id="workload-key-1",
    )


def _reply(
    prepared: PreparedRequest,
    peer: _Key,
    *,
    components: Sequence[str] = RESPONSE_COMPONENTS,
    tag: str = RESPONSE_TAG,
    key_id: str = "peer-key-1",
    age: int = 0,
    lifetime: int = 30,
    extra: dict[str, str] | None = None,
) -> tuple[list[tuple[str, str]], bytes]:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": prepared.local_task_id,
            "result": {
                "task": {
                    "id": "receiver-task",
                    "contextId": "receiver-context",
                    "status": {"state": "TASK_STATE_SUBMITTED"},
                }
            },
        }
    ).encode()
    headers = {
        "content-type": "application/json",
        "content-digest": content_digest(body),
        "content-length": str(len(body)),
        "a2a-version": "1.0",
        "a2a-extensions": EXTENSION_URI,
        "x-lychd-sender": prepared.peer_id,
        "x-lychd-recipient": prepared.workload_id,
        "x-lychd-task-schema": prepared.task_schema,
        "x-lychd-task-id": prepared.local_task_id,
        "x-lychd-attempt-id": prepared.attempt_id,
        "x-lychd-request-uri": prepared.request_uri,
        "x-lychd-request-digest": prepared.digest,
        "x-lychd-request-nonce": prepared.nonce,
    }
    headers.update(extra or {})
    now = datetime.now(UTC) + timedelta(seconds=age)
    signer = cast("_Signer", HTTPMessageSigner(signature_algorithm=algorithms.ED25519, key_resolver=peer))  # pyright: ignore[reportPrivateImportUsage]
    signer.sign(
        _Response(prepared.request_uri, headers),
        key_id=key_id,
        nonce="b" * 32,
        tag=tag,
        created=now,
        expires=now + timedelta(seconds=lifetime),
        covered_component_ids=components,
        label="lychd",
    )
    return list(headers.items()), body


def test_actual_ed25519_package_verifies_request_and_distinct_peer_reply(keys: tuple[_Key, _Key]) -> None:
    workload, peer = keys
    prepared = _prepared(workload)
    verifier = cast("_Verifier", HTTPMessageVerifier(signature_algorithm=algorithms.ED25519, key_resolver=workload))  # pyright: ignore[reportPrivateImportUsage]
    assert len(verifier.verify(_Request(prepared.request_uri, dict(prepared.headers)), expect_tag=REQUEST_TAG)) == 1
    fields, body = _reply(prepared, peer)
    result = verify_response(prepared, 200, fields, body, peer.public, "peer-key-1")
    assert result.foreign_task_id == "receiver-task"
    assert result.context_id == "receiver-context"
    assert result.terminal is False
    assert prepared.wire.endswith(prepared.body)
    assert b"Authorization" not in prepared.wire
    assert prepared.body not in repr(prepared).encode()
    with pytest.raises(IntercomError):
        verify_response(prepared, 200, fields, body, workload.public, "peer-key-1")


@pytest.mark.parametrize(
    "mutation",
    ["body", "digest", "signature", "duplicate", "encoding", "extra-profile", "second-signature", "component-param"],
)
def test_signed_reply_rejects_tampering_and_ambiguous_critical_headers(keys: tuple[_Key, _Key], mutation: str) -> None:
    workload, peer = keys
    prepared = _prepared(workload)
    fields, body = _reply(prepared, peer)
    if mutation == "body":
        body += b" "
    elif mutation == "duplicate":
        fields.append(("Content-Digest", content_digest(body)))
    elif mutation == "encoding":
        fields.append(("Content-Encoding", "identity"))
    elif mutation == "extra-profile":
        fields.append(("x-lychd-authority", "admin"))
    else:
        name = (
            "content-digest" if mutation == "digest" else "Signature" if mutation == "signature" else "Signature-Input"
        )
        old = dict(fields)[name]
        value = (
            content_digest(b"changed")
            if mutation == "digest"
            else old[:-1] + "A"
            if mutation == "signature"
            else old + ", other=()"
            if mutation == "second-signature"
            else old.replace('"@status"', '"@status";req')
        )
        fields = [(k, value if k == name else v) for k, v in fields]
    with pytest.raises(IntercomError):
        verify_response(prepared, 200, fields, body, peer.public, "peer-key-1")


@pytest.mark.parametrize(
    "change",
    [
        "coverage",
        "tag",
        "key-id",
        "future",
        "expired",
        "too-long",
        "sender",
        "audience",
        "request-uri",
        "request-digest",
        "request-nonce",
        "attempt",
        "schema",
        "version",
        "extension",
    ],
)
def test_even_valid_signature_must_match_exact_profile_and_pending_request(
    keys: tuple[_Key, _Key], change: str
) -> None:
    workload, peer = keys
    prepared = _prepared(workload)
    extras = {
        "sender": {"x-lychd-sender": "wrong-peer"},
        "audience": {"x-lychd-recipient": "wrong-workload"},
        "request-uri": {"x-lychd-request-uri": "https://elsewhere.test/a2a"},
        "request-digest": {"x-lychd-request-digest": content_digest(b"elsewhere")},
        "request-nonce": {"x-lychd-request-nonce": "f" * 32},
        "attempt": {"x-lychd-attempt-id": "attempt-2"},
        "schema": {"x-lychd-task-schema": "other@1"},
        "version": {"a2a-version": "0.3"},
        "extension": {"a2a-extensions": "https://example.test/downgrade"},
    }
    fields, body = _reply(
        prepared,
        peer,
        components=RESPONSE_COMPONENTS[:-1] if change == "coverage" else RESPONSE_COMPONENTS,
        tag=REQUEST_TAG if change == "tag" else RESPONSE_TAG,
        key_id="other-key" if change == "key-id" else "peer-key-1",
        age=10 if change == "future" else -60 if change == "expired" else 0,
        lifetime=31 if change == "too-long" else 30,
        extra=extras.get(change),
    )
    with pytest.raises(IntercomError):
        verify_response(prepared, 200, fields, body, peer.public, "peer-key-1")


def test_physical_wrappers_change_while_semantic_body_remains_exact(keys: tuple[_Key, _Key]) -> None:
    first = _prepared(keys[0])
    second = _prepared(keys[0])
    assert first.body == second.body
    assert first.nonce != second.nonce
    assert first.wire != second.wire
    assert len(first.wire) <= 65536
    assert first.wire.index(b"\r\n\r\n") + 4 <= 8192


class _Gate:
    def __init__(self) -> None:
        self.handoffs: list[IntercomHandoff] = []

    def handoff(self, handoff: IntercomHandoff, action: Callable[[], int]) -> int:
        self.handoffs.append(handoff)
        return action()


def test_socket_bridge_preserves_complete_plaintext_and_uses_only_intercom_gate(keys: tuple[_Key, _Key]) -> None:
    endpoint = IntercomEndpoint("127.0.0.1", "peer.test", 8443, "/a2a", Path("/explicit-ca.pem"))
    prepared = _prepared(keys[0])
    gate = _Gate()
    bridge = intercom_http._SocketGate(endpoint, prepared, gate)
    target = NetworkTarget(endpoint.address, endpoint.port, endpoint.hostname, "origin")
    assert bridge.handoff(NetworkHandoff(target, "http", b"ciphertext", prepared.wire), lambda: 7) == 7
    assert gate.handoffs[0].application_bytes is prepared.wire
    assert gate.handoffs[0].target is endpoint
    with pytest.raises(IntercomError):
        bridge.handoff(NetworkHandoff(target, "dns", b"query", None), lambda: 7)
    with pytest.raises(IntercomError):
        bridge.handoff(NetworkHandoff(target, "http", b"ciphertext", b"changed"), lambda: 7)


def test_expired_request_cannot_handoff_even_after_tls_wait(
    keys: tuple[_Key, _Key], monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepared(keys[0])
    endpoint = IntercomEndpoint("127.0.0.1", "peer.test", 8443, "/a2a", Path("/explicit-ca.pem"))
    gate = _Gate()
    bridge = intercom_http._SocketGate(endpoint, prepared, gate)
    expired = time.time() + 31
    monkeypatch.setattr(intercom_http.time, "time", lambda: expired)
    with pytest.raises(IntercomError):
        bridge.handoff(
            NetworkHandoff(
                NetworkTarget(endpoint.address, endpoint.port, endpoint.hostname, "origin"), "tls", b"ciphertext", None
            ),
            lambda: 7,
        )
    assert gate.handoffs == []


@pytest.mark.asyncio
async def test_transport_refuses_missing_gate_wrong_endpoint_and_deadline_before_contact(
    keys: tuple[_Key, _Key], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("transport contacted a target before validation")

    monkeypatch.setattr(intercom_http, "open_pinned_tls", forbidden)
    endpoint = IntercomEndpoint("127.0.0.1", "peer.test", 8443, "/a2a", Path("/explicit-ca.pem"))
    prepared = _prepared(keys[0])
    for changed, deadline in (
        (endpoint, time.monotonic() + 31),
        (replace(endpoint, path="/other"), time.monotonic() + 10),
    ):
        with pytest.raises(IntercomError):
            await BoundedIntercomHTTP().exchange(changed, prepared, gate=_Gate(), deadline=deadline)


@pytest.mark.parametrize(
    "head",
    [
        b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Length: 1\r\n\r\n",
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n",
        b"HTTP/1.1 302 Found\r\nContent-Length: 0\r\n\r\n",
    ],
)
def test_raw_header_preflight_refuses_h11_normalization_and_redirect(head: bytes) -> None:
    with pytest.raises(IntercomError):
        intercom_http._raw_head(head)


class _OctetStream:
    """Unit-only octet source; not an HTTP endpoint or interoperability witness."""

    def __init__(self, chunks: list[bytes], *, cancel: bool = False) -> None:
        self.chunks, self.cancel = chunks, cancel
        self.closed = False
        self.sent: list[bytes] = []

    async def send(self, body: bytes) -> None:
        self.sent.append(body)

    async def receive(self) -> bytes:
        if self.cancel:
            raise asyncio.CancelledError
        return self.chunks.pop(0) if self.chunks else b""

    def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", ["complete", "split", "duplicate", "oversized", "encoding", "cancel", "truncated", "trailing"]
)
async def test_bounded_octet_parser_one_send_and_unconditional_close(
    keys: tuple[_Key, _Key], monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    prepared = _prepared(keys[0])
    fields, body = _reply(prepared, keys[1])
    if case == "duplicate":
        fields.append(("Content-Length", str(len(body))))
    if case == "oversized":
        fields = [(k, "65537" if k == "content-length" else v) for k, v in fields]
    if case == "encoding":
        fields.append(("Content-Encoding", "gzip"))
    raw = (
        b"HTTP/1.1 200 OK\r\n" + b"".join(k.encode() + b": " + v.encode() + b"\r\n" for k, v in fields) + b"\r\n" + body
    )
    if case == "truncated":
        raw = raw[:-1]
    if case == "trailing":
        raw += b"extra"
    stream = _OctetStream([raw[:17], raw[17:311], raw[311:]] if case == "split" else [raw], cancel=case == "cancel")
    calls = 0

    async def opened(*args: object, **kwargs: object) -> _OctetStream:
        nonlocal calls
        calls += 1
        return stream

    monkeypatch.setattr(intercom_http, "open_pinned_tls", opened)
    endpoint = IntercomEndpoint("127.0.0.1", "peer.test", 8443, "/a2a", Path("/explicit-ca.pem"))
    if case in {"complete", "split"}:
        result = await BoundedIntercomHTTP().exchange(endpoint, prepared, gate=_Gate(), deadline=time.monotonic() + 5)
        assert result.body == body
        assert (
            verify_response(
                prepared, result.status, result.headers, result.body, keys[1].public, "peer-key-1"
            ).foreign_task_id
            == "receiver-task"
        )
    else:
        with pytest.raises(asyncio.CancelledError if case == "cancel" else IntercomError):
            await BoundedIntercomHTTP().exchange(endpoint, prepared, gate=_Gate(), deadline=time.monotonic() + 5)
    assert calls == 1
    assert stream.sent == [prepared.wire]
    assert stream.closed
