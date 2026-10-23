"""Byte-bound RFC9421 Ed25519 and one-shot pinned HTTPS for Intercom.

The installed signature implementation signs and verifies actual RFC signature
bases. This consumer independently enforces exact coverage, freshness, body
digests and request correlation. Socket reuse imports mechanics only: the
mandatory Intercom gate supplies all effect-time policy and durable capacity.
"""

from __future__ import annotations

import hashlib
import math
import re
import secrets
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from typing import Literal, Protocol, cast
from urllib.parse import urlsplit

import h11
from http_message_signatures import algorithms
from http_message_signatures.http_sfv.dictionary import Dictionary
from http_message_signatures.http_sfv.item import InnerList, Item
from http_message_signatures.resolvers import HTTPSignatureKeyResolver
from http_message_signatures.signatures import HTTPMessageSigner, HTTPMessageVerifier

from lychd.domain.intercom.codec import decode_response, encode_request, visible_id
from lychd.domain.intercom.transport import (
    MAX_HEADER_BYTES,
    MAX_HEADER_FIELDS,
    MAX_OPERATION_SECONDS,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BODY_BYTES,
    IntercomCode,
    IntercomEndpoint,
    IntercomError,
    IntercomGate,
    IntercomHandoff,
    PreparedRequest,
    RawResponse,
    TaskMethod,
    TaskObservation,
)
from lychd.domain.scout.transport import FetchCode, FetchError, NetworkHandoff, NetworkTarget
from lychd.system.services.scout_socket import open_pinned_tls

EXTENSION_URI = "https://github.com/hexanomicon/lychd/blob/main/docs/adr/26-a2a.md#peer-task-jsonrpc-1"
SIGNATURE_LABEL = "lychd"
REQUEST_TAG = "lychd-peer-task-request@1"
RESPONSE_TAG = "lychd-peer-task-response@1"
REQUEST_COMPONENTS = (
    "@method",
    "@target-uri",
    "content-type",
    "content-digest",
    "a2a-version",
    "a2a-extensions",
    "x-lychd-sender",
    "x-lychd-recipient",
    "x-lychd-task-schema",
    "x-lychd-task-id",
    "x-lychd-attempt-id",
)
RESPONSE_COMPONENTS = (
    "@status",
    "content-type",
    "content-digest",
    "a2a-version",
    "a2a-extensions",
    "x-lychd-sender",
    "x-lychd-recipient",
    "x-lychd-task-schema",
    "x-lychd-task-id",
    "x-lychd-attempt-id",
    "x-lychd-request-uri",
    "x-lychd-request-digest",
    "x-lychd-request-nonce",
)
_PARAMETERS = {"created", "keyid", "alg", "expires", "nonce", "tag"}
_NONCE = re.compile(r"[0-9a-f]{32}")
_FIELD = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
_MAX_URI_BYTES = 2048
_MAX_VALUE_BYTES = 4096
_ED25519_SIGNATURE_BYTES = 64
_OK_STATUS = 200
_HTTPS_PORT = 443
_MAX_PORT = 65535
_ASCII_SPACE = 32
_ASCII_VISIBLE_FIRST = 33
_ASCII_VISIBLE_LAST = 126
_MAX_LENGTH_DIGITS = 6


@dataclass(slots=True)
class _RequestMessage:
    url: str
    headers: dict[str, str]
    method: str = "POST"


@dataclass(slots=True)
class _ResponseMessage:
    url: str
    headers: dict[str, str]
    status_code: int


class _Signer(Protocol):
    def sign(
        self,
        message: _RequestMessage,
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
    def verify(self, message: _ResponseMessage, *, expect_tag: str, max_age: timedelta) -> list[object]: ...


class _SigningKey(HTTPSignatureKeyResolver):
    def __init__(self, key_id: str, key: bytes) -> None:
        self.key_id, self.key = key_id, key

    def resolve_private_key(self, key_id: str) -> bytes:
        if key_id != self.key_id:
            raise IntercomError(IntercomCode.AUTHENTICATION)
        return self.key


class _PeerKey(HTTPSignatureKeyResolver):
    def __init__(self, key_id: str, key: bytes) -> None:
        self.key_id, self.key = key_id, key

    def resolve_public_key(self, key_id: str) -> bytes:
        if key_id != self.key_id:
            raise IntercomError(IntercomCode.AUTHENTICATION)
        return self.key


def content_digest(body: bytes) -> str:
    """Return RFC9530 sha-256 over actual message content, before JSON parsing."""
    return str(Dictionary({"sha-256": hashlib.sha256(body).digest()}))


def _uri(uri: str) -> tuple[str, str]:
    try:
        parsed = urlsplit(uri)
        port = parsed.port
        if (
            not uri.isascii()
            or not 0 < len(uri) <= _MAX_URI_BYTES
            or any(ord(char) < _ASCII_VISIBLE_FIRST or ord(char) > _ASCII_VISIBLE_LAST for char in uri)
            or parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or parsed.query
            or not parsed.path.startswith("/")
            or "\\" in uri
            or (port is not None and not 1 <= port <= _MAX_PORT)
        ):
            raise IntercomError(IntercomCode.CONFIG)
    except ValueError:
        raise IntercomError(IntercomCode.CONFIG) from None
    return parsed.netloc, parsed.path


def _headers(fields: Sequence[tuple[str, str]], body: bytes) -> dict[str, str]:
    if len(fields) > MAX_HEADER_FIELDS or sum(len(k) + len(v) + 4 for k, v in fields) + 2 > MAX_HEADER_BYTES:
        raise IntercomError(IntercomCode.LIMIT)
    result: dict[str, str] = {}
    allowed_profile = set(REQUEST_COMPONENTS + RESPONSE_COMPONENTS)
    for key, value in fields:
        if (
            type(key) is not str
            or type(value) is not str
            or _FIELD.fullmatch(key) is None
            or len(value) > _MAX_VALUE_BYTES
            or any(not _ASCII_SPACE <= ord(char) <= _ASCII_VISIBLE_LAST for char in value)
        ):
            raise IntercomError(IntercomCode.PROTOCOL)
        name = key.lower()
        if (
            name in result
            or (name.startswith("x-lychd-") and name not in allowed_profile)
            or (name.startswith("a2a-") and name not in {"a2a-version", "a2a-extensions"})
        ):
            raise IntercomError(IntercomCode.PROTOCOL)
        result[name] = value
    if (
        any(
            name in result for name in ("content-encoding", "transfer-encoding", "authorization", "proxy-authorization")
        )
        or result.get("content-type") != "application/json"
        or result.get("content-digest") != content_digest(body)
        or result.get("a2a-version") != "1.0"
        or result.get("a2a-extensions") != EXTENSION_URI
        or ("content-length" in result and result["content-length"] != str(len(body)))
    ):
        raise IntercomError(IntercomCode.AUTHENTICATION)
    return result


def _signature(
    headers: dict[str, str],
    *,
    key_id: str,
    tag: str,
    components: tuple[str, ...],
) -> str:
    try:  # Package parsing and consumer checks share one diagnostic quarantine.
        fields: dict[str, Dictionary] = {}
        for name in ("signature", "signature-input"):
            raw = headers[name]
            node = Dictionary()
            node.parse(raw.encode("ascii"))
            if set(node) != {SIGNATURE_LABEL} or str(node) != raw:
                raise IntercomError(IntercomCode.AUTHENTICATION)  # noqa: TRY301
            fields[name] = node
        signature = cast("Item | InnerList", fields["signature"][SIGNATURE_LABEL])
        inputs = cast("Item | InnerList", fields["signature-input"][SIGNATURE_LABEL])
        if (
            not isinstance(signature, Item)
            or signature.params
            or not isinstance(signature.value, bytes)
            or len(signature.value) != _ED25519_SIGNATURE_BYTES
            or not isinstance(inputs, InnerList)
            or set(inputs.params) != _PARAMETERS
            or tuple(str(item.value) for item in cast("list[Item]", list(inputs))) != components
            or any(item.params for item in cast("list[Item]", list(inputs)))
            or any(type(item.value) is not str for item in cast("list[Item]", list(inputs)))
        ):
            raise IntercomError(IntercomCode.AUTHENTICATION)  # noqa: TRY301
        params = cast("dict[str, object]", inputs.params)
        created, expires, nonce = params["created"], params["expires"], params["nonce"]
        now = time.time()
        if (
            type(created) is not int
            or type(expires) is not int
            or not created <= now < expires
            or not 0 < expires - created <= MAX_OPERATION_SECONDS
            or any(type(params[name]) is not str for name in ("alg", "keyid", "tag", "nonce"))
            or params["alg"] != "ed25519"
            or params["keyid"] != key_id
            or params["tag"] != tag
            or not isinstance(nonce, str)
            or _NONCE.fullmatch(nonce) is None
        ):
            raise IntercomError(IntercomCode.AUTHENTICATION)  # noqa: TRY301
    except Exception:  # noqa: BLE001 - Never export package diagnostics or foreign structured fields.
        raise IntercomError(IntercomCode.AUTHENTICATION) from None
    return nonce


def _serialize(uri: str, fields: Sequence[tuple[str, str]], body: bytes) -> bytes:
    authority, path = _uri(uri)
    headers = _headers(fields, body)
    if (
        headers.get("host") != authority
        or headers.get("content-length") != str(len(body))
        or headers.get("connection") != "close"
    ):
        raise IntercomError(IntercomCode.PROTOCOL)
    connection = h11.Connection(h11.CLIENT)
    try:
        head = connection.send(
            h11.Request(
                method=b"POST",
                target=path.encode("ascii"),
                headers=[(k.encode("ascii"), v.encode("ascii")) for k, v in fields],
            )
        )
        wire = head + connection.send(h11.Data(data=body)) + connection.send(h11.EndOfMessage())
    except h11.LocalProtocolError:
        raise IntercomError(IntercomCode.PROTOCOL) from None
    if len(head) > MAX_HEADER_BYTES or len(wire) > MAX_REQUEST_BYTES:
        raise IntercomError(IntercomCode.LIMIT)
    return wire


def prepare_request(
    *,
    method: TaskMethod,
    local_task_id: str,
    attempt_id: str,
    peer_id: str,
    workload_id: str,
    task_schema: str,
    endpoint: str,
    params: dict[str, object],
    signing_key: bytes,
    key_id: str,
    expected_context_id: str | None = None,
) -> PreparedRequest:
    """Seal one fresh physical wrapper before the host's exact egress decision."""
    for identity in (local_task_id, attempt_id, peer_id, workload_id, task_schema, key_id):
        visible_id(identity)
    if expected_context_id is not None:
        visible_id(expected_context_id)
    authority, _ = _uri(endpoint)
    body = encode_request(method, local_task_id, params)
    nonce = secrets.token_hex(16)
    headers = {
        "host": authority,
        "content-type": "application/json",
        "content-digest": content_digest(body),
        "content-length": str(len(body)),
        "connection": "close",
        "a2a-version": "1.0",
        "a2a-extensions": EXTENSION_URI,
        "x-lychd-sender": workload_id,
        "x-lychd-recipient": peer_id,
        "x-lychd-task-schema": task_schema,
        "x-lychd-task-id": local_task_id,
        "x-lychd-attempt-id": attempt_id,
    }
    try:
        signer = cast(
            "_Signer",
            HTTPMessageSigner(signature_algorithm=algorithms.ED25519, key_resolver=_SigningKey(key_id, signing_key)),  # pyright: ignore[reportPrivateImportUsage]
        )
        now = datetime.now(UTC)
        signer.sign(
            _RequestMessage(endpoint, headers),
            key_id=key_id,
            nonce=nonce,
            tag=REQUEST_TAG,
            created=now,
            expires=now + timedelta(seconds=MAX_OPERATION_SECONDS),
            covered_component_ids=REQUEST_COMPONENTS,
            label=SIGNATURE_LABEL,
        )
    except Exception:  # noqa: BLE001 - Secret loaders/package errors are intentionally content-free.
        raise IntercomError(IntercomCode.AUTHENTICATION) from None
    fields = tuple(headers.items())
    _signature(_headers(fields, body), key_id=key_id, tag=REQUEST_TAG, components=REQUEST_COMPONENTS)
    wire = _serialize(endpoint, fields, body)
    return PreparedRequest(
        method,
        local_task_id,
        attempt_id,
        peer_id,
        workload_id,
        task_schema,
        endpoint,
        body,
        fields,
        wire,
        content_digest(body),
        nonce,
        visible_id(params["id"]) if method != "SendMessage" else None,
        expected_context_id,
    )


def verify_response(
    prepared: PreparedRequest,
    status: int,
    headers: Sequence[tuple[str, str]],
    body: bytes,
    peer_public_key: bytes,
    key_id: str,
) -> TaskObservation:
    """Authenticate exact pending request correlation, then decode quarantined text."""
    if type(body) is not bytes or not 0 < len(body) <= MAX_RESPONSE_BODY_BYTES:
        raise IntercomError(IntercomCode.LIMIT)
    fields = _headers(headers, body)
    nonce = _signature(fields, key_id=key_id, tag=RESPONSE_TAG, components=RESPONSE_COMPONENTS)
    expected = {
        "x-lychd-sender": prepared.peer_id,
        "x-lychd-recipient": prepared.workload_id,
        "x-lychd-task-schema": prepared.task_schema,
        "x-lychd-task-id": prepared.local_task_id,
        "x-lychd-attempt-id": prepared.attempt_id,
        "x-lychd-request-uri": prepared.request_uri,
        "x-lychd-request-digest": prepared.digest,
        "x-lychd-request-nonce": prepared.nonce,
    }
    if status != _OK_STATUS or any(fields.get(name) != value for name, value in expected.items()):
        raise IntercomError(IntercomCode.AUTHENTICATION)
    try:
        verifier = cast(
            "_Verifier",
            HTTPMessageVerifier(signature_algorithm=algorithms.ED25519, key_resolver=_PeerKey(key_id, peer_public_key)),  # pyright: ignore[reportPrivateImportUsage]
        )
        if (
            len(
                verifier.verify(
                    _ResponseMessage(
                        prepared.request_uri, {name.title(): value for name, value in fields.items()}, status
                    ),
                    expect_tag=RESPONSE_TAG,
                    max_age=timedelta(seconds=MAX_OPERATION_SECONDS),
                )
            )
            != 1
        ):
            raise IntercomError(IntercomCode.AUTHENTICATION)  # noqa: TRY301
    except Exception:  # noqa: BLE001 - Foreign diagnostics and package exceptions never leave this boundary.
        raise IntercomError(IntercomCode.AUTHENTICATION) from None
    return decode_response(
        body,
        method=prepared.method,
        local_task_id=prepared.local_task_id,
        expected_task_id=prepared.expected_task_id,
        expected_context_id=prepared.expected_context_id,
        response_nonce=nonce,
    )


class _SocketGate:
    def __init__(self, endpoint: IntercomEndpoint, prepared: PreparedRequest, gate: IntercomGate) -> None:
        self.endpoint, self.prepared, self.gate = endpoint, prepared, gate

    def handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:
        _request_fresh(self.prepared)
        if (
            handoff.target != NetworkTarget(self.endpoint.address, self.endpoint.port, self.endpoint.hostname, "origin")
            or handoff.phase not in {"connect", "tls", "http"}
            or (handoff.phase == "http" and handoff.application_bytes != self.prepared.wire)
            or (handoff.phase != "http" and handoff.application_bytes is not None)
        ):
            raise IntercomError(IntercomCode.EGRESS)
        phase = cast('Literal["connect", "tls", "http"]', handoff.phase)
        return self.gate.handoff(
            IntercomHandoff(self.endpoint, phase, handoff.wire_bytes, handoff.application_bytes), action
        )


def _request_fresh(prepared: PreparedRequest) -> None:
    """Refuse an expired wrapper at every physical handoff, including after TLS waits."""
    try:
        fields = _headers(prepared.headers, prepared.body)
        node = Dictionary()
        node.parse(fields["signature-input"].encode("ascii"))
        inputs = cast("InnerList", node[SIGNATURE_LABEL])
        key_id = cast("dict[str, object]", inputs.params)["keyid"]
        if (
            not isinstance(key_id, str)
            or _signature(fields, key_id=key_id, tag=REQUEST_TAG, components=REQUEST_COMPONENTS) != prepared.nonce
        ):
            raise IntercomError(IntercomCode.AUTHENTICATION)  # noqa: TRY301
    except Exception:  # noqa: BLE001 - Package structured-field diagnostics remain private.
        raise IntercomError(IntercomCode.AUTHENTICATION) from None


class BoundedIntercomHTTP:
    """One pinned TLS connection, one POST, one bounded response, always closed."""

    async def exchange(  # noqa: C901, PLR0912, PLR0915 - One finite response parser and owned closure boundary.
        self,
        endpoint: IntercomEndpoint,
        prepared: PreparedRequest,
        *,
        gate: IntercomGate,
        deadline: float,
    ) -> RawResponse:
        """Contact only after mandatory gate injection; never retry an uncertain send."""
        if (
            type(endpoint) is not IntercomEndpoint
            or not callable(getattr(gate, "handoff", None))
            or type(deadline) not in {int, float}
            or not math.isfinite(deadline)
            or not 0 < deadline - time.monotonic() <= MAX_OPERATION_SECONDS
        ):
            raise IntercomError(IntercomCode.CONFIG)
        try:
            address = ip_address(endpoint.address)
            authority = f"[{endpoint.hostname}]" if ":" in endpoint.hostname else endpoint.hostname
            uri = f"https://{authority}:{endpoint.port}{endpoint.path}"
            default_uri = f"https://{authority}{endpoint.path}"
            if (
                str(address) != endpoint.address
                or prepared.request_uri not in ({uri, default_uri} if endpoint.port == _HTTPS_PORT else {uri})
                or _serialize(prepared.request_uri, prepared.headers, prepared.body) != prepared.wire
            ):
                raise IntercomError(IntercomCode.CONFIG)
        except ValueError:
            raise IntercomError(IntercomCode.CONFIG) from None
        stream = None
        try:
            stream = await open_pinned_tls(
                NetworkTarget(endpoint.address, endpoint.port, endpoint.hostname, "origin"),
                gate=_SocketGate(endpoint, prepared, gate),
                deadline=deadline,
                ca_file=endpoint.ca_file,
            )
            await stream.send(prepared.wire)
            connection = h11.Connection(h11.CLIENT, max_incomplete_event_size=MAX_HEADER_BYTES)
            connection.send(
                h11.Request(
                    method=b"POST",
                    target=endpoint.path.encode("ascii"),
                    headers=[(b"Host", b"peer"), (b"Content-Length", str(len(prepared.body)).encode("ascii"))],
                )
            )
            connection.send(h11.Data(data=prepared.body))
            connection.send(h11.EndOfMessage())
            head = bytearray()
            content = bytearray()
            response: h11.Response | None = None
            ended = False
            total = 0
            while True:
                data = await stream.receive()
                total += len(data)
                if total > MAX_HEADER_BYTES + MAX_RESPONSE_BODY_BYTES:
                    raise IntercomError(IntercomCode.LIMIT)
                if response is None:
                    head.extend(data)
                    marker = head.find(b"\r\n\r\n")
                    if marker < 0 and len(head) > MAX_HEADER_BYTES:
                        raise IntercomError(IntercomCode.LIMIT)
                    if marker >= 0:
                        if marker + 4 > MAX_HEADER_BYTES:
                            raise IntercomError(IntercomCode.LIMIT)
                        _raw_head(bytes(head[: marker + 4]))
                        head.clear()
                connection.receive_data(data)
                while True:
                    event = connection.next_event()
                    if event is h11.NEED_DATA:
                        break
                    if isinstance(event, h11.Response):
                        if response is not None or event.status_code != _OK_STATUS:
                            raise IntercomError(IntercomCode.PROTOCOL)
                        response = event
                    elif isinstance(event, h11.Data):
                        if ended or response is None:
                            raise IntercomError(IntercomCode.PROTOCOL)
                        content.extend(event.data)
                        if len(content) > MAX_RESPONSE_BODY_BYTES:
                            raise IntercomError(IntercomCode.LIMIT)
                    elif isinstance(event, h11.EndOfMessage):
                        if response is None or event.headers or connection.trailing_data[0]:
                            raise IntercomError(IntercomCode.PROTOCOL)
                        ended = True
                        fields = tuple((k.decode("ascii"), v.decode("ascii")) for k, v in response.headers)
                        _headers(fields, bytes(content))
                        return RawResponse(response.status_code, fields, bytes(content))
                    else:
                        raise IntercomError(IntercomCode.PROTOCOL)
                if not data:
                    raise IntercomError(IntercomCode.PROTOCOL)
        except FetchError as exc:
            code = IntercomCode.TIMEOUT if exc.code == FetchCode.TIMEOUT else IntercomCode.TRANSPORT
            raise IntercomError(code) from None
        except (h11.ProtocolError, UnicodeError, OSError):
            raise IntercomError(IntercomCode.PROTOCOL) from None
        finally:
            if stream is not None:
                stream.close()


def _raw_head(head: bytes) -> None:
    """Reject ambiguous framing before h11 combines repeated Content-Length."""
    lines = head[:-4].split(b"\r\n")
    if not lines[0].startswith(b"HTTP/1.1 200 ") or len(lines) - 1 > MAX_HEADER_FIELDS:
        raise IntercomError(IntercomCode.PROTOCOL)
    names: set[bytes] = set()
    length: bytes | None = None
    for line in lines[1:]:
        name, separator, value = line.partition(b":")
        if not separator or name.lower() in names or name != name.strip() or value.startswith(b"\t"):
            raise IntercomError(IntercomCode.PROTOCOL)
        names.add(name.lower())
        if name.lower() == b"content-length":
            length = value.strip(b" ")
    if b"content-length" not in names or names & {b"transfer-encoding", b"content-encoding"}:
        raise IntercomError(IntercomCode.PROTOCOL)
    if (
        length is None
        or not length.isdigit()
        or len(length) > _MAX_LENGTH_DIGITS
        or not 0 < int(length) <= MAX_RESPONSE_BODY_BYTES
    ):
        raise IntercomError(IntercomCode.LIMIT)
