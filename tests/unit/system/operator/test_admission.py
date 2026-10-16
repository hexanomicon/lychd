from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import httpx
import pytest
from http_message_signatures import algorithms
from http_message_signatures.http_sfv.dictionary import Dictionary
from http_message_signatures.http_sfv.types import Token
from http_message_signatures.resolvers import HTTPSignatureKeyResolver
from http_message_signatures.signatures import HTTPMessageSigner, HTTPMessageVerifier

from lychd.config.constants import STOP_ADMISSION_LAUNCHER_PROFILE, STOP_ADMISSION_PATH
from lychd.system.operator.admission import (
    MAX_ADMISSION_BODY_BYTES,
    StopAdmissionError,
    StopAdmissionProtocol,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

_PASSWORD = "synthetic-stop-key-000000000000000000000000"  # noqa: S105 - Public synthetic test key.
_KEY_ID = "lychd-local-operator@1"
_REQUEST_TAG = "lychd-system-stop-request@2"
_REPLY_TAG = "lychd-system-stop-reply@2"
_URL = f"http://127.0.0.1:8000{STOP_ADMISSION_PATH}"
_NONCE = "0123456789abcdef0123456789abcdef"


class _Keys(HTTPSignatureKeyResolver):
    def __init__(self, password: str = _PASSWORD) -> None:
        self.key = password.encode("ascii")

    def resolve_private_key(self, key_id: str) -> bytes:
        del key_id  # Independent fixtures deliberately sign even an unadmitted key id.
        return self.key

    def resolve_public_key(self, key_id: str) -> bytes:
        return self.resolve_private_key(key_id)


def _encoded(body: dict[str, object]) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("ascii")


def _payload(message: httpx.Request | httpx.Response) -> dict[str, object]:
    return cast("dict[str, object]", json.loads(message.content))


def _digest(body: bytes) -> str:
    return str(Dictionary({"sha-256": hashlib.sha256(body).digest()}))


def _sign(
    message: httpx.Request | httpx.Response,
    *,
    reply: bool = False,
    components: Sequence[str] | None = None,
    created: datetime | None = None,
    expires: datetime | None = None,
    tag: str | None = None,
    key_id: str = _KEY_ID,
    nonce: str | None = _NONCE,
    include_alg: bool = True,
    include_expires: bool = True,
    label: str = "pyhms",
    password: str = _PASSWORD,
) -> None:
    message.headers["Content-Type"] = "application/json"
    message.headers["Content-Digest"] = _digest(message.content)
    signer = HTTPMessageSigner(
        signature_algorithm=algorithms.HMAC_SHA256,  # pyright: ignore[reportPrivateImportUsage]
        key_resolver=_Keys(password),
    )
    now = datetime.now(UTC)
    signer.sign(  # pyright: ignore[reportUnknownMemberType]
        message,
        key_id=key_id,
        nonce=nonce,
        tag=tag or (_REPLY_TAG if reply else _REQUEST_TAG),
        created=created or now,
        expires=(expires or now + timedelta(seconds=30)) if include_expires else None,
        covered_component_ids=components
        if components is not None
        else (
            ("@status", "content-type", "content-digest")
            if reply
            else ("@method", "@target-uri", "content-type", "content-digest")
        ),
        include_alg=include_alg,
        label=label,
    )


def _request(body: dict[str, object] | None = None, *, raw: bytes | None = None, url: str = _URL) -> httpx.Request:
    raw = (
        raw
        if raw is not None
        else _encoded(
            body
            if body is not None
            else {
                "version": 2,
                "nonce": _NONCE,
                "operation": "system-stop",
                "binding_generation": "generation-a",
                "launcher_profile": STOP_ADMISSION_LAUNCHER_PROFILE,
            }
        )
    )
    request = httpx.Request("POST", url, content=raw)
    _sign(request)
    return request


def _copy_request(
    request: httpx.Request,
    *,
    body: bytes | None = None,
    url: str | None = None,
    method: str | None = None,
    headers: httpx.Headers | None = None,
) -> httpx.Request:
    fields = httpx.Headers(request.headers if headers is None else headers)
    content = request.content if body is None else body
    fields["Content-Length"] = str(len(content))
    return httpx.Request(method or request.method, url or str(request.url), content=content, headers=fields)


def _copy_reply(response: httpx.Response, *, body: bytes | None = None, status: int = 200) -> httpx.Response:
    content = response.content if body is None else body
    fields = httpx.Headers(response.headers)
    fields["Content-Length"] = str(len(content))
    return httpx.Response(status, content=content, headers=fields, request=response.request)


def _core_accepts(message: httpx.Request | httpx.Response, *, reply: bool = False, tag: str | None = None) -> bool:
    verifier = HTTPMessageVerifier(
        signature_algorithm=algorithms.HMAC_SHA256,  # pyright: ignore[reportPrivateImportUsage]
        key_resolver=_Keys(),
    )
    return bool(verifier.verify(message, expect_tag=tag or (_REPLY_TAG if reply else _REQUEST_TAG)))  # pyright: ignore[reportUnknownMemberType]


def test_independent_package_request_gets_exact_signed_inert_ack() -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()

    response = protocol.admit(request)
    protocol.verify_reply(request, response)

    assert response.status_code == 200
    assert _payload(response) == {
        "version": 2,
        "request_nonce": _NONCE,
        "operation": "system-stop",
        "binding_generation": "generation-a",
        "launcher_profile": STOP_ADMISSION_LAUNCHER_PROFILE,
        "request_method": "POST",
        "request_uri": _URL,
        "request_content_digest": _digest(request.content),
        "decision": "admit",
    }
    assert _core_accepts(response, reply=True)
    assert "Authorization" not in request.headers
    assert _PASSWORD not in str(request.headers) + request.content.decode() + repr(protocol) + repr(response)
    assert base64.b64encode(_PASSWORD.encode()).decode() not in str(request.headers)
    protocol.verify_reply(request, protocol.admit(request))  # Repetition can produce only another inert ACK.


def test_generated_requests_have_distinct_public_128_bit_nonces() -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    first = protocol.request(_URL, "generation-a")
    second = protocol.request(_URL, "generation-a")
    nonce = cast("str", _payload(first)["nonce"])

    assert len(bytes.fromhex(nonce)) == 16
    assert nonce != _payload(second)["nonce"]
    assert first.method == "POST"
    assert str(first.url) == _URL
    assert _payload(first)["version"] == 2
    assert _payload(first)["launcher_profile"] == STOP_ADMISSION_LAUNCHER_PROFILE
    assert _core_accepts(first)
    protocol.verify_reply(first, protocol.admit(first))


def test_consumer_checks_actual_request_body_bytes_beyond_package_verification() -> None:
    request = _request()
    changed = _copy_request(request, body=request.content.replace(b"generation-a", b"generation-b"))

    assert _core_accepts(changed)
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(changed)


def test_consumer_checks_actual_reply_body_bytes_beyond_package_verification() -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    response = protocol.admit(request)
    changed = _copy_reply(response, body=response.content.replace(b'"version":2', b'"version": 2'))

    assert _payload(changed) == _payload(response)
    assert _core_accepts(changed, reply=True)
    with pytest.raises(StopAdmissionError):
        protocol.verify_reply(request, changed)


@pytest.mark.parametrize("reply", [False, True])
def test_consumer_requires_complete_coverage_even_for_valid_package_signature(*, reply: bool) -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    message = protocol.admit(request) if reply else request
    _sign(message, reply=reply, components=("@status",) if reply else ("@method",))

    assert _core_accepts(message, reply=reply)
    if isinstance(message, httpx.Response):
        with pytest.raises(StopAdmissionError):
            protocol.verify_reply(request, message)
    else:
        with pytest.raises(StopAdmissionError):
            protocol.admit(message)


@pytest.mark.parametrize("component", ["method", "uri", "content-type", "digest", "signature", "host"])
def test_changed_signed_request_evidence_refuses(component: str) -> None:
    request = _request()
    if component == "method":
        request = _copy_request(request, method="GET")
    elif component == "uri":
        request = _copy_request(request, url=_URL.replace(":8000", ":8001"))
        request.headers["Host"] = "127.0.0.1:8001"
    elif component == "content-type":
        request.headers["Content-Type"] = "text/plain"
    elif component == "digest":
        request.headers["Content-Digest"] = _digest(b"other")
    elif component == "signature":
        request.headers["Signature"] = "pyhms=:" + base64.b64encode(bytes(32)).decode() + ":"
    else:
        request.headers["Host"] = "127.0.0.1:8001"

    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(request)


@pytest.mark.parametrize(
    "url",
    [
        f"{_URL}?x=1",
        f"{_URL}?",
        f"{_URL}/",
        _URL.replace("stop-admission", "%73top-admission"),
        _URL.replace("127.0.0.1", "localhost"),
        _URL.replace("127.0.0.1", "192.0.2.1"),
        _URL.replace("http:", "https:"),
        _URL.replace("http://", "http://user:password@"),
        f"{_URL}#fragment",
    ],
)
def test_even_authentically_signed_other_targets_are_outside_profile(url: str) -> None:
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(_request(url=url))
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).request(url, "generation-a")


@pytest.mark.parametrize("name", ["Origin", "Authorization", "Transfer-Encoding"])
def test_browser_basic_or_streaming_headers_refuse(name: str) -> None:
    request = _request()
    request.headers[name] = ""
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(request)


@pytest.mark.parametrize(
    "name", ["Host", "Content-Type", "Content-Digest", "Content-Length", "Signature", "Signature-Input"]
)
def test_duplicate_critical_request_headers_refuse(name: str) -> None:
    request = _request()
    duplicate = httpx.Headers([*request.headers.multi_items(), (name.swapcase(), request.headers[name])])
    changed = httpx.Request("POST", request.url, headers=duplicate, content=request.content)
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(changed)


@pytest.mark.parametrize("name", ["Content-Type", "Content-Digest", "Content-Length", "Signature", "Signature-Input"])
def test_duplicate_critical_reply_headers_refuse(name: str) -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    response = protocol.admit(request)
    response.headers = httpx.Headers([*response.headers.multi_items(), (name.swapcase(), response.headers[name])])
    with pytest.raises(StopAdmissionError):
        protocol.verify_reply(request, response)


@pytest.mark.parametrize("reply", [False, True])
@pytest.mark.parametrize(
    "parameter",
    [
        "expired",
        "future",
        "long",
        "reversed",
        "missing-expires",
        "missing-alg",
        "missing-nonce",
        "nonce",
        "keyid",
        "role",
        "label",
        "extra",
    ],
)
def test_signed_profile_parameter_substitution_refuses(parameter: str, *, reply: bool) -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    message = protocol.admit(request) if reply else request
    now = datetime.now(UTC)
    created, expires = now, now + timedelta(seconds=30)
    if parameter == "expired":
        created, expires = now - timedelta(seconds=20), now - timedelta(seconds=1)
    elif parameter == "future":
        created, expires = now + timedelta(seconds=2), now + timedelta(seconds=20)
    elif parameter == "long":
        expires = now + timedelta(seconds=31)
    elif parameter == "reversed":
        expires = now - timedelta(seconds=1)
    _sign(
        message,
        reply=reply,
        created=created,
        expires=expires,
        include_alg=parameter != "missing-alg",
        include_expires=parameter != "missing-expires",
        nonce=None if parameter == "missing-nonce" else ("f" * 32 if parameter == "nonce" else _NONCE),
        key_id="other-key" if parameter == "keyid" else _KEY_ID,
        tag=(_REQUEST_TAG if reply else _REPLY_TAG) if parameter == "role" else None,
        label="other" if parameter == "label" else "pyhms",
    )
    if parameter in {
        "expired",
        "future",
        "long",
        "reversed",
        "missing-expires",
        "missing-alg",
        "missing-nonce",
        "nonce",
        "keyid",
        "label",
    }:
        assert _core_accepts(message, reply=reply)
    if parameter == "extra":
        message.headers["Signature-Input"] += ";extra=1"
    if isinstance(message, httpx.Response):
        with pytest.raises(StopAdmissionError):
            protocol.verify_reply(request, message)
    else:
        with pytest.raises(StopAdmissionError):
            protocol.admit(message)


@pytest.mark.parametrize("header", ["Signature", "Signature-Input"])
def test_multiple_or_duplicate_signature_dictionary_members_refuse(header: str) -> None:
    for alternate_label in ("pyhms", "another"):
        request = _request()
        value = request.headers[header]
        request.headers[header] = value + ", " + value.replace("pyhms=", alternate_label + "=", 1)
        with pytest.raises(StopAdmissionError):
            StopAdmissionProtocol(_PASSWORD).admit(request)


@pytest.mark.parametrize("field", ["version", "nonce", "operation", "binding_generation", "launcher_profile", "extra"])
@pytest.mark.parametrize("value", [None, True, 1.0, "", "wrong"])
def test_authentically_signed_invalid_request_schema_refuses(field: str, value: object) -> None:
    body = _payload(_request())
    body[field] = value
    if field == "binding_generation" and value == "wrong":
        body[field] = "bad generation"
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(_request(body))


@pytest.mark.parametrize("raw", [b"[]", b"null", b"{", b"\xff", b'{"version":1,"version":1}', b"{}"])
def test_malformed_or_duplicate_json_objects_refuse(raw: bytes) -> None:
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(_request(raw=raw))


@pytest.mark.parametrize("generation", ["", "x" * 257, "has space", "line\nbreak", "nonascii-\u00e9"])
def test_outbound_binding_generation_is_bounded(generation: str) -> None:
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).request(_URL, generation)


def test_another_invocations_authentic_reply_is_not_a_ticket() -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    first = protocol.request(_URL, "generation-a")
    second = protocol.request(_URL, "generation-a")
    other = protocol.admit(second)
    with pytest.raises(StopAdmissionError):
        protocol.verify_reply(first, other)


@pytest.mark.parametrize("change", ["legacy", "version", "missing-profile", "unknown-profile", "old-role"])
@pytest.mark.parametrize("reply", [False, True])
def test_authentic_old_or_unqualified_launcher_profiles_refuse(change: str, *, reply: bool) -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    message = protocol.admit(request) if reply else request
    body = _payload(message)
    if change in {"legacy", "version"}:
        body["version"] = 1
    if change in {"legacy", "missing-profile"}:
        del body["launcher_profile"]
    elif change == "unknown-profile":
        body["launcher_profile"] = "caged-owned-lifespan@1"
    changed = (
        _copy_reply(message, body=_encoded(body))
        if isinstance(message, httpx.Response)
        else _copy_request(message, body=_encoded(body))
    )
    tag = (
        ("lychd-system-stop-reply@1" if reply else "lychd-system-stop-request@1")
        if change in {"legacy", "old-role"}
        else None
    )
    _sign(changed, reply=reply, tag=tag)
    assert _core_accepts(changed, reply=reply, tag=tag)
    if isinstance(changed, httpx.Response):
        with pytest.raises(StopAdmissionError):
            protocol.verify_reply(request, changed)
    else:
        with pytest.raises(StopAdmissionError):
            protocol.admit(changed)


@pytest.mark.parametrize(
    "field",
    [
        "request_nonce",
        "operation",
        "binding_generation",
        "launcher_profile",
        "request_method",
        "request_uri",
        "request_content_digest",
        "decision",
        "extra",
        "version",
    ],
)
def test_authentically_signed_changed_reply_context_refuses(field: str) -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    response = protocol.admit(request)
    body = _payload(response)
    body[field] = True if field == "version" else "other"
    response = _copy_reply(response, body=_encoded(body))
    _sign(response, reply=True)
    with pytest.raises(StopAdmissionError):
        protocol.verify_reply(request, response)


@pytest.mark.parametrize("resign", [False, True])
def test_changed_status_refuses_with_or_without_new_authentic_signature(*, resign: bool) -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    response = _copy_reply(protocol.admit(request), status=403)
    if resign:
        _sign(response, reply=True)
    with pytest.raises(StopAdmissionError):
        protocol.verify_reply(request, response)


def test_wrong_installation_key_cannot_admit_request_or_forge_reply() -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    other = StopAdmissionProtocol("other-synthetic-key-000000000000000000000")
    request = protocol.request(_URL, "generation-a")
    with pytest.raises(StopAdmissionError):
        other.admit(request)
    reply = protocol.admit(request)
    _sign(
        reply,
        reply=True,
        nonce=cast("str", _payload(request)["nonce"]),
        password="other-synthetic-key-000000000000000000000",  # noqa: S106 - Public synthetic test key.
    )
    with pytest.raises(StopAdmissionError):
        protocol.verify_reply(request, reply)


@pytest.mark.parametrize("reply", [False, True])
def test_oversized_bodies_refuse_even_with_authentic_package_signature(*, reply: bool) -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    raw = b" " * (MAX_ADMISSION_BODY_BYTES + 1)
    message = _copy_reply(protocol.admit(request), body=raw) if reply else _copy_request(request, body=raw)
    _sign(message, reply=reply)
    assert _core_accepts(message, reply=reply)
    if isinstance(message, httpx.Response):
        with pytest.raises(StopAdmissionError):
            protocol.verify_reply(request, message)
    else:
        with pytest.raises(StopAdmissionError):
            protocol.admit(message)


@pytest.mark.parametrize("case", ["count", "individual", "total", "control", "length"])
def test_bounded_request_headers_refuse(case: str) -> None:
    request = _request()
    if case == "count":
        request.headers.update({f"X-Test-{index}": "a" for index in range(33)})
    elif case == "individual":
        request.headers["X-Test"] = "a" * 2049
    elif case == "total":
        request.headers.update({f"X-Test-{index}": "a" * 1500 for index in range(6)})
    elif case == "control":
        request.headers["X-Test"] = "a\nb"
    else:
        request.headers["Content-Length"] = "0"
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(request)


def test_all_refusal_errors_have_fixed_secret_free_text() -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    request.headers["Signature-Input"] = _PASSWORD
    with pytest.raises(StopAdmissionError, match=r"^Local stop admission refused$") as caught:
        protocol.admit(request)
    assert _PASSWORD not in repr(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("password", ["short", "x" * 257, "x" * 31 + " ", "x" * 31 + "\n", "x" * 31 + "\u00e9"])
def test_invalid_credential_shape_refuses_without_exposing_it(password: str) -> None:
    with pytest.raises(StopAdmissionError, match=r"^Local stop admission refused$"):
        StopAdmissionProtocol(password)


def test_body_bound_accepts_4096_bytes_then_refuses_one_more_signed_byte() -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    raw = _request().content
    bounded = _request(raw=raw + b" " * (MAX_ADMISSION_BODY_BYTES - len(raw)))
    protocol.verify_reply(bounded, protocol.admit(bounded))
    oversized = _request(raw=bounded.content + b" ")
    assert _core_accepts(oversized)
    with pytest.raises(StopAdmissionError):
        protocol.admit(oversized)


@pytest.mark.parametrize("reply", [False, True])
def test_duplicate_json_field_refuses_even_when_decoded_value_would_match(*, reply: bool) -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    message = protocol.admit(request) if reply else request
    raw = message.content.replace(b'"version":2', b'"version":2,"version":2')
    assert json.loads(raw) == _payload(message)
    changed = (
        _copy_reply(message, body=raw) if isinstance(message, httpx.Response) else _copy_request(message, body=raw)
    )
    _sign(changed, reply=reply)
    assert _core_accepts(changed, reply=reply)
    if isinstance(changed, httpx.Response):
        with pytest.raises(StopAdmissionError):
            protocol.verify_reply(request, changed)
    else:
        with pytest.raises(StopAdmissionError):
            protocol.admit(changed)


@pytest.mark.parametrize("name", ["Content-Type", "Content-Digest", "Signature", "Signature-Input"])
def test_missing_required_critical_header_refuses(name: str) -> None:
    request = _request()
    del request.headers[name]
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(request)


def test_signature_byte_sequence_cannot_carry_unsigned_parameters() -> None:
    request = _request()
    request.headers["Signature"] += ";extra=1"
    assert _core_accepts(request)
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(request)


def test_duplicate_signature_parameter_cannot_hide_behind_parser_overwrite() -> None:
    request = _request()
    request.headers["Signature-Input"] += f';nonce="{_NONCE}"'
    assert _core_accepts(request)
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(request)


def test_signature_nonce_requires_a_string_instead_of_a_structured_field_token() -> None:
    body = _payload(_request())
    body["nonce"] = "a" * 32
    request = _request(body)
    _sign(request, nonce=Token("a" * 32))
    assert _core_accepts(request)
    with pytest.raises(StopAdmissionError):
        StopAdmissionProtocol(_PASSWORD).admit(request)


def test_fresh_reply_cannot_extend_an_expired_pending_request() -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = _request()
    response = protocol.admit(request)
    now = datetime.now(UTC)
    _sign(request, created=now - timedelta(seconds=20), expires=now - timedelta(seconds=1))
    assert _core_accepts(request)
    assert _core_accepts(response, reply=True)
    with pytest.raises(StopAdmissionError):
        protocol.verify_reply(request, response)


@pytest.mark.parametrize("password_length", [32, 256])
def test_existing_settings_credential_length_boundaries_are_sufficient(password_length: int) -> None:
    protocol = StopAdmissionProtocol("x" * password_length)
    request = protocol.request(_URL, "g" * 256)
    protocol.verify_reply(request, protocol.admit(request))


def test_literal_ipv6_loopback_roundtrip_preserves_bracketed_authority() -> None:
    protocol = StopAdmissionProtocol(_PASSWORD)
    request = protocol.request(f"http://[::1]:8000{STOP_ADMISSION_PATH}", "generation-a")
    assert request.headers["Host"] == "[::1]:8000"
    protocol.verify_reply(request, protocol.admit(request))
