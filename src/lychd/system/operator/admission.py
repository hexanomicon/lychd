"""Fixed, inert installation-stop message admission (ADR 09).

The signature package authenticates HTTP components. This consumer additionally
checks body bytes, the complete fixed profile, and each pending request's reply.
It owns no host effect, runtime readiness, credential revocation, or replay ledger.
The fixed key id is ``lychd-local-operator@1``; signed role tags distinguish
``lychd-system-stop-request@2`` from ``lychd-system-stop-reply@2``. Version 2 requires
the source-owned native launcher profile in both authenticated bodies. Only the package's
``pyhms`` label, six signature parameters, and ordered component lists are admitted.
Headers are bounded to 32 fields, 8 KiB total and 2 KiB per value; request URIs to
2 KiB, generation to 256 visible ASCII characters, and nonces to 32 lowercase hex
characters. Message bodies and freshness use the explicit limits below.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import secrets
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol, cast

import httpx
from http_message_signatures import algorithms
from http_message_signatures.http_sfv.dictionary import Dictionary
from http_message_signatures.http_sfv.item import InnerList, Item
from http_message_signatures.resolvers import HTTPSignatureKeyResolver
from http_message_signatures.signatures import HTTPMessageSigner, HTTPMessageVerifier

from lychd.config.constants import STOP_ADMISSION_LAUNCHER_PROFILE, STOP_ADMISSION_PATH

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

MAX_ADMISSION_BODY_BYTES = 4096
_PROTOCOL_VERSION = 2
_ACK_STATUS = 200
_KEY_ID = "lychd-local-operator@1"
_REQUEST_TAG = "lychd-system-stop-request@2"
_REPLY_TAG = "lychd-system-stop-reply@2"
_REQUEST_COMPONENTS = ("@method", "@target-uri", "content-type", "content-digest")
_REPLY_COMPONENTS = ("@status", "content-type", "content-digest")
_SIGNATURE_PARAMETERS = {"alg", "keyid", "created", "expires", "nonce", "tag"}
_REQUEST_FIELDS = {"version", "nonce", "operation", "binding_generation", "launcher_profile"}
_MAX_VALIDITY_SECONDS = 30
_MAX_URI_BYTES = 2048
_MAX_HEADER_COUNT = 32
_MAX_HEADER_BYTES = 8192
_MAX_HEADER_VALUE_BYTES = 2048
_HMAC_SHA256_BYTES = 32
_MIN_PASSWORD_LENGTH = 32
_MAX_PASSWORD_LENGTH = 256
_ASCII_SPACE = 32
_ASCII_FIRST_VISIBLE = 33
_ASCII_LAST_VISIBLE = 126
_NONCE = re.compile(r"[0-9a-f]{32}")
_GENERATION = re.compile(r"[\x21-\x7e]{1,256}")
_CRITICAL_HEADERS = {
    "host",
    "content-type",
    "content-digest",
    "content-length",
    "signature",
    "signature-input",
}


class StopAdmissionError(ValueError):
    """A fixed refusal that cannot carry credentials or untrusted message data."""

    def __init__(self) -> None:
        """Construct the sole public, secret-free error text."""
        super().__init__("Local stop admission refused")


@contextmanager
def _refusal_boundary() -> Generator[None]:
    try:
        yield
    except Exception:  # noqa: BLE001 - The package can include untrusted input in several exception types.
        raise StopAdmissionError from None


# The package's public API is partly unannotated; these types describe only the
# installed 2.0.1 calls/results consumed here, without replacing its implementation.
class _Signer(Protocol):
    def sign(
        self,
        message: httpx.Request | httpx.Response,
        *,
        key_id: str,
        nonce: str,
        tag: str,
        created: datetime,
        expires: datetime,
        covered_component_ids: Sequence[str],
    ) -> None: ...


class _VerifiedMessage(Protocol):
    covered_components: dict[str, str]
    parameters: dict[str, object]


class _Verifier(Protocol):
    def verify(
        self, message: httpx.Request | httpx.Response, *, expect_tag: str, max_age: timedelta
    ) -> list[_VerifiedMessage]: ...


class _LocalKey(HTTPSignatureKeyResolver):
    def __init__(self, key: bytes) -> None:
        self._key = key

    def resolve_private_key(self, key_id: str) -> bytes:
        if key_id != _KEY_ID:
            raise StopAdmissionError
        return self._key

    def resolve_public_key(self, key_id: str) -> bytes:
        return self.resolve_private_key(key_id)


def _encoded(body: dict[str, object]) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _digest(body: bytes) -> str:
    return str(Dictionary({"sha-256": hashlib.sha256(body).digest()}))


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StopAdmissionError
        result[key] = value
    return result


def _body(raw: bytes) -> dict[str, object]:
    if not 0 < len(raw) <= MAX_ADMISSION_BODY_BYTES:
        raise StopAdmissionError
    decoded = cast("object", json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object))
    if not isinstance(decoded, dict):
        raise StopAdmissionError
    return cast("dict[str, object]", decoded)


def _request_body(raw: bytes) -> dict[str, object]:
    body = _body(raw)
    nonce, generation = body.get("nonce"), body.get("binding_generation")
    if (
        set(body) != _REQUEST_FIELDS
        or type(body.get("version")) is not int
        or body["version"] != _PROTOCOL_VERSION
        or body["operation"] != "system-stop"
        or body["launcher_profile"] != STOP_ADMISSION_LAUNCHER_PROFILE
        or not isinstance(nonce, str)
        or _NONCE.fullmatch(nonce) is None
        or not isinstance(generation, str)
        or _GENERATION.fullmatch(generation) is None
    ):
        raise StopAdmissionError
    return body


def _target(request: httpx.Request) -> None:
    url = request.url
    if (
        request.method != "POST"
        or url.scheme != "http"
        or not ipaddress.ip_address(url.host).is_loopback
        or url.username
        or url.password
        or "#" in str(url)
        or url.raw_path != STOP_ADMISSION_PATH.encode("ascii")
        or len(str(url).encode("ascii")) > _MAX_URI_BYTES
        or request.headers.get("host") != url.netloc.decode("ascii")
    ):
        raise StopAdmissionError


def _headers(message: httpx.Request | httpx.Response) -> None:
    fields = message.headers.raw
    if len(fields) > _MAX_HEADER_COUNT or sum(len(key) + len(value) for key, value in fields) > _MAX_HEADER_BYTES:
        raise StopAdmissionError
    for key, value in fields:
        if (
            len(value) > _MAX_HEADER_VALUE_BYTES
            or not key
            or any(byte < _ASCII_FIRST_VISIBLE or byte > _ASCII_LAST_VISIBLE for byte in key)
            or any(byte < _ASCII_SPACE or byte > _ASCII_LAST_VISIBLE for byte in value)
        ):
            raise StopAdmissionError
    for name in _CRITICAL_HEADERS:
        if len(message.headers.get_list(name)) > 1:
            raise StopAdmissionError
    if any(name in message.headers for name in ("authorization", "origin", "transfer-encoding")):
        raise StopAdmissionError
    if (
        message.headers.get("content-type") != "application/json"
        or message.headers.get("content-digest") != _digest(message.content)
        or ("content-length" in message.headers and message.headers["content-length"] != str(len(message.content)))
    ):
        raise StopAdmissionError
    _signature_headers(message.headers)


def _signature_headers(headers: httpx.Headers) -> None:
    for name in ("signature", "signature-input"):
        raw = headers[name]
        field = Dictionary()
        field.parse(raw.encode("ascii"))
        if set(field) != {"pyhms"} or str(field) != raw:
            raise StopAdmissionError
        item = cast("Item | InnerList", field["pyhms"])
        if name == "signature":
            if (
                not isinstance(item, Item)
                or item.params
                or not isinstance(item.value, bytes)
                or len(item.value) != _HMAC_SHA256_BYTES
            ):
                raise StopAdmissionError
        elif not isinstance(item, InnerList):
            raise StopAdmissionError


class StopAdmissionProtocol:
    """Authenticate one fixed request and its inert, invocation-bound ACK."""

    def __init__(self, password: str) -> None:
        """Retain the installation credential solely in the fixed local key resolver."""
        with _refusal_boundary():
            if (
                not _MIN_PASSWORD_LENGTH <= len(password) <= _MAX_PASSWORD_LENGTH
                or not password.isascii()
                or any(not _ASCII_FIRST_VISIBLE <= ord(char) <= _ASCII_LAST_VISIBLE for char in password)
            ):
                raise StopAdmissionError
            resolver = _LocalKey(password.encode("ascii"))
            self._signer = cast(
                "_Signer",
                HTTPMessageSigner(signature_algorithm=algorithms.HMAC_SHA256, key_resolver=resolver),  # pyright: ignore[reportPrivateImportUsage]
            )
            self._verifier = cast(
                "_Verifier",
                HTTPMessageVerifier(signature_algorithm=algorithms.HMAC_SHA256, key_resolver=resolver),  # pyright: ignore[reportPrivateImportUsage]
            )

    def request(self, url: str, binding_generation: str) -> httpx.Request:
        """Sign a fresh loopback request requiring the sole owned native profile."""
        with _refusal_boundary():
            body: dict[str, object] = {
                "version": _PROTOCOL_VERSION,
                "nonce": secrets.token_hex(16),
                "operation": "system-stop",
                "binding_generation": binding_generation,
                "launcher_profile": STOP_ADMISSION_LAUNCHER_PROFILE,
            }
            raw = _encoded(body)
            _request_body(raw)
            request = httpx.Request("POST", url, content=raw)
            _target(request)
            self._sign(request, nonce=cast("str", body["nonce"]), reply=False)
            return request
        raise StopAdmissionError

    def admit(self, request: httpx.Request) -> httpx.Response:
        """Verify all request evidence before producing a signed, effect-free ACK."""
        with _refusal_boundary():
            body = self._verified_request(request)
            response = httpx.Response(_ACK_STATUS, content=_encoded(self._reply_body(request, body)), request=request)
            self._sign(response, nonce=cast("str", body["nonce"]), reply=True)
            return response
        raise StopAdmissionError

    def verify_reply(self, request: httpx.Request, response: httpx.Response) -> None:
        """Accept only an authenticated ACK for this still-valid pending request."""
        with _refusal_boundary():
            pending = self._verified_request(request)
            body = _body(response.content)
            nonce = self._verify(response, reply=True)
            if (
                response.status_code != _ACK_STATUS
                or type(body.get("version")) is not int
                or body != self._reply_body(request, pending)
                or nonce != pending["nonce"]
            ):
                raise StopAdmissionError

    def _sign(self, message: httpx.Request | httpx.Response, *, nonce: str, reply: bool) -> None:
        if not 0 < len(message.content) <= MAX_ADMISSION_BODY_BYTES:
            raise StopAdmissionError
        message.headers["Content-Type"] = "application/json"
        message.headers["Content-Digest"] = _digest(message.content)
        now = datetime.now(UTC)
        self._signer.sign(
            message,
            key_id=_KEY_ID,
            nonce=nonce,
            tag=_REPLY_TAG if reply else _REQUEST_TAG,
            created=now,
            expires=now + timedelta(seconds=_MAX_VALIDITY_SECONDS),
            covered_component_ids=_REPLY_COMPONENTS if reply else _REQUEST_COMPONENTS,
        )

    def _verified_request(self, request: httpx.Request) -> dict[str, object]:
        _target(request)
        body = _request_body(request.content)
        if self._verify(request, reply=False) != body["nonce"]:
            raise StopAdmissionError
        return body

    def _verify(self, message: httpx.Request | httpx.Response, *, reply: bool) -> str:
        _headers(message)
        tag = _REPLY_TAG if reply else _REQUEST_TAG
        results = self._verifier.verify(message, expect_tag=tag, max_age=timedelta(seconds=_MAX_VALIDITY_SECONDS))
        if len(results) != 1:
            raise StopAdmissionError
        result = results[0]
        expected = _REPLY_COMPONENTS if reply else _REQUEST_COMPONENTS
        if tuple(result.covered_components) != (*tuple(f'"{name}"' for name in expected), '"@signature-params"'):
            raise StopAdmissionError
        params = result.parameters
        created, expires, nonce = params.get("created"), params.get("expires"), params.get("nonce")
        now = time.time()
        if (
            set(params) != _SIGNATURE_PARAMETERS
            or type(params["alg"]) is not str
            or params["alg"] != "hmac-sha256"
            or type(params["keyid"]) is not str
            or params["keyid"] != _KEY_ID
            or type(params["tag"]) is not str
            or params["tag"] != tag
            or type(created) is not int
            or type(expires) is not int
            or not 0 < expires - created <= _MAX_VALIDITY_SECONDS
            or created > now
            or expires <= now
            or type(nonce) is not str
            or _NONCE.fullmatch(nonce) is None
        ):
            raise StopAdmissionError
        return nonce

    @staticmethod
    def _reply_body(request: httpx.Request, body: dict[str, object]) -> dict[str, object]:
        return {
            "version": _PROTOCOL_VERSION,
            "request_nonce": body["nonce"],
            "operation": body["operation"],
            "binding_generation": body["binding_generation"],
            "launcher_profile": body["launcher_profile"],
            "request_method": request.method,
            "request_uri": str(request.url),
            "request_content_digest": request.headers["content-digest"],
            "decision": "admit",
        }
