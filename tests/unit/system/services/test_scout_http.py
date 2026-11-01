"""No-network qualification of request serialization and bounded HTTP decoding."""

from __future__ import annotations

import gzip
from dataclasses import replace
from typing import cast

import pytest

from lychd.domain.scout.destination import preflight_destination
from lychd.domain.scout.transport import FetchCode, FetchError
from lychd.system import scout_worker
from lychd.system.services.scout_http import (
    MAX_DECODED_BODY_BYTES,
    MAX_HEADER_BYTES,
    MAX_WIRE_BODY_BYTES,
    HttpResponse,
    HttpResponseParser,
    serialize_get,
)


def _response(body: bytes, *, headers: bytes = b"", framing: str = "length", status: bytes = b"200 OK") -> bytes:
    head = b"HTTP/1.1 " + status + b"\r\n" + headers
    if status == b"200 OK" and b"Content-Type:" not in headers:
        head += b"Content-Type: text/plain; charset=utf-8\r\n"
    if framing == "length":
        head += b"Content-Length: " + str(len(body)).encode() + b"\r\n"
    elif framing == "chunked":
        head += b"Transfer-Encoding: chunked\r\n"
    return head + b"\r\n" + body


def _parse(data: bytes, *, fragment: int | None = None, **limits: int) -> HttpResponse:
    parser = HttpResponseParser(**limits)
    if fragment is None:
        parser.feed(data)
    else:
        for offset in range(0, len(data), fragment):
            parser.feed(data[offset : offset + fragment])
    return parser.finish()


@pytest.mark.parametrize("suffix", ["", "?", "/", "/path?", "/a%2Fb?q=a%26b&q=c"])
def test_request_preserves_exact_path_query_and_has_only_host_owned_headers(suffix: str) -> None:
    candidate = preflight_destination("https://EXAMPLE.com:443" + suffix)
    request = serialize_get(candidate)
    target = suffix if suffix.startswith("/") else "/" + suffix
    assert request == (
        f"GET {target} HTTP/1.1\r\nHost: example.com\r\n".encode()
        + b"Accept: text/html,text/plain\r\nAccept-Encoding: gzip, identity\r\nConnection: close\r\n\r\n"
    )


def test_request_revalidates_candidate_and_brackets_ipv6() -> None:
    candidate = preflight_destination("https://[2606:4700:4700::1111]/?")
    assert b"Host: [2606:4700:4700::1111]\r\n" in serialize_get(candidate)
    with pytest.raises(FetchError) as raised:
        serialize_get(replace(candidate, hostname="localhost"))
    assert raised.value.code is FetchCode.DESTINATION


@pytest.mark.parametrize("framing", ["length", "chunked", "close"])
@pytest.mark.parametrize("fragment", [None, 1, 7, 4096])
def test_supported_body_framings_preserve_unicode_and_separate_usage(framing: str, fragment: int | None) -> None:
    body = "Plain café.\n".encode()
    wire = f"{len(body):X}\r\n".encode() + body + b"\r\n0\r\n\r\n" if framing == "chunked" else body
    response = _response(wire, framing=framing)
    result = _parse(response, fragment=fragment)
    assert result.status == 200
    assert result.body == body
    assert result.media_type == "text/plain"
    assert result.header_bytes == response.index(b"\r\n\r\n") + 4
    assert result.wire_body_bytes == len(wire)
    assert result.encoded_body_bytes == len(body)
    assert result.decoded_body_bytes == len(body)


@pytest.mark.parametrize("fragment", [None, 1, 11])
@pytest.mark.parametrize("framing", ["length", "chunked", "close"])
def test_gzip_html_decodes_to_actual_worker_input(fragment: int | None, framing: str) -> None:
    body = "<!DOCTYPE html><h1>Example</h1><p>Café &amp; tea.</p>".encode()
    encoded = gzip.compress(body, mtime=0)
    wire = f"{len(encoded):X}\r\n".encode() + encoded + b"\r\n0\r\n\r\n" if framing == "chunked" else encoded
    response = _response(wire, headers=b"Content-Type: text/html\r\nContent-Encoding: gzip\r\n", framing=framing)
    result = _parse(response, fragment=fragment)
    assert result.body == body
    assert result.encoded_body_bytes == len(encoded)
    assert result.decoded_body_bytes == len(body)
    assert scout_worker.extract_text(result.body, "text/html")["text"] == "Example\nCafé & tea."


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_redirect_is_only_an_observation_with_discarded_but_counted_body(status: int) -> None:
    response = _response(b"not retained", status=f"{status} Redirect".encode(), headers=b"Location: /next?\r\n")
    result = _parse(response)
    assert result.status == status
    assert result.location == "/next?"
    assert result.body == b""
    assert result.media_type is None
    assert result.decoded_body_bytes == len(b"not retained")


@pytest.mark.parametrize("status", [403, 404, 429, 503])
def test_refused_http_status_is_retained_without_consuming_or_exposing_body(status: int) -> None:
    parser = HttpResponseParser()
    head = f"HTTP/1.1 {status} Foreign reason\r\nContent-Length: 1000000\r\n\r\n".encode()
    with pytest.raises(FetchError) as raised:
        parser.feed(head)
    assert raised.value.code is FetchCode.PROTOCOL
    assert raised.value.http_status == status
    assert parser.wire_body_bytes == parser.encoded_body_bytes == parser.decoded_body_bytes == 0
    assert str(raised.value) == "Scout fetch refused: protocol."
    with pytest.raises(FetchError) as repeated:
        parser.finish()
    assert repeated.value.http_status == status


@pytest.mark.parametrize(
    "head",
    [
        b"HTTP/1.1 malformed\r\n\r\n",
        b"HTTP/1.1 099 Invalid\r\n\r\n",
        b"HTTP/1.1 600 Invalid\r\n\r\n",
        b"HTTP/1.1 403 Forbidden\r\nInvalid field\r\n\r\n",
        b"HTTP/1.1 403 Forbidden\r\n",
    ],
)
def test_unknown_or_invalid_http_head_does_not_invent_status(head: bytes) -> None:
    with pytest.raises(FetchError) as raised:
        _parse(head)
    assert raised.value.http_status is None


def test_post_header_media_refusal_preserves_observed_ok_status() -> None:
    with pytest.raises(FetchError) as raised:
        _parse(_response(b"foreign", headers=b"Content-Type: application/json\r\n"))
    assert raised.value.code is FetchCode.MEDIA
    assert raised.value.http_status == 200


@pytest.mark.parametrize("status", [99, 600, True, "403", 403.0])
def test_fetch_error_rejects_invalid_numeric_status_without_foreign_diagnostic(status: object) -> None:
    with pytest.raises(ValueError, match=r"^Scout HTTP status is invalid\.$"):
        FetchError(FetchCode.PROTOCOL, http_status=cast("int", status))


@pytest.mark.parametrize("fragment", [None, 1, 4096])
def test_raw_header_limit_includes_terminator_before_any_complete_event_can_bypass_it(fragment: int | None) -> None:
    prefix = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 0\r\nX-Pad: "
    accepted = prefix + b"a" * (MAX_HEADER_BYTES - len(prefix) - 4) + b"\r\n\r\n"
    assert _parse(accepted, fragment=fragment).header_bytes == MAX_HEADER_BYTES
    with pytest.raises(FetchError) as raised:
        _parse(accepted[:-4] + b"a\r\n\r\n", fragment=fragment)
    assert raised.value.code is FetchCode.LIMIT


@pytest.mark.parametrize(
    "response",
    [
        b"HTTP/1.1 100 Continue\r\n\r\n",
        b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: secret\r\n\r\n",
        _response(b"", headers=b"Upgrade: secret\r\n"),
        _response(b"", headers=b"Connection: keep-alive, upgrade\r\n"),
        b"HTTP/1.1 200 secret\x00\r\n\r\n",
        b"HTTP/1.1 200 OK\nX: secret\n\n",
        _response(b"", headers=b"X: secret\x1b\r\n"),
        _response(b"", headers=b" folded: secret\r\n"),
        _response(b"", headers=b"Content-Length: 0\r\n"),
        _response(b"", headers=b"Content-Length: 0, 0\r\n", framing="close"),
        _response(b"", headers=b"Content-Length: +0\r\n", framing="close"),
        _response(b"", headers=b"Content-Length: -1\r\n", framing="close"),
        _response(b"", headers=b"Transfer-Encoding: chunked\r\n"),
        _response(b"0\r\n\r\n", headers=b"Transfer-Encoding: chunked\r\n", framing="chunked"),
        _response(b"0\r\n\r\n", headers=b"Transfer-Encoding: gzip, chunked\r\n", framing="close"),
        _response(b"0\r\nX: secret\r\n\r\n", framing="chunked"),
        _response(b"1\r\na!\r\n0\r\n\r\n", framing="chunked"),
        _response(b"a", headers=b"Content-Length: 2\r\n", framing="close"),
        _response(b"a", headers=b"Content-Length: 0\r\n", framing="close"),
        _response(b"2\r\na\r\n", framing="chunked"),
        _response(b"", status=b"302 Redirect"),
    ],
)
def test_ambiguous_malformed_informational_and_truncated_responses_refuse_content_free(response: bytes) -> None:
    with pytest.raises(FetchError) as raised:
        _parse(response, fragment=3)
    assert raised.value.code is FetchCode.PROTOCOL
    assert "secret" not in str(raised.value)


@pytest.mark.parametrize("media", [b"application/json", b"text/plain;charset=latin1", b"text/html;charset=ascii", b""])
def test_unsupported_media_or_charset_refuses(media: bytes) -> None:
    with pytest.raises(FetchError) as raised:
        _parse(_response(b"", headers=b"Content-Type: " + media + b"\r\n"))
    assert raised.value.code is FetchCode.MEDIA


@pytest.mark.parametrize(
    "encoded",
    [
        gzip.compress(b"one", mtime=0) + gzip.compress(b"two", mtime=0),
        gzip.compress(b"one", mtime=0) + b"tail",
        b"bad",
        gzip.compress(b"one", mtime=0)[:-1],
    ],
)
@pytest.mark.parametrize("fragment", [None, 1])
def test_gzip_requires_exactly_one_complete_stream(encoded: bytes, fragment: int | None) -> None:
    with pytest.raises(FetchError) as raised:
        _parse(_response(encoded, headers=b"Content-Encoding: gzip\r\n"), fragment=fragment)
    assert raised.value.code is FetchCode.ENCODING


def test_gzip_expansion_and_decoded_limit_are_distinct_refusals() -> None:
    encoded = gzip.compress(b"a" * 10000, mtime=0)
    for fragment in (None, 1, 7):
        with pytest.raises(FetchError) as raised:
            _parse(_response(encoded, headers=b"Content-Encoding: gzip\r\n"), fragment=fragment)
        assert raised.value.code is FetchCode.LIMIT
    encoded = gzip.compress(b"a" * (MAX_DECODED_BODY_BYTES + 1), mtime=0)
    with pytest.raises(FetchError) as raised:
        _parse(_response(encoded, headers=b"Content-Encoding: gzip\r\n"))
    assert raised.value.code is FetchCode.LIMIT


def test_body_limits_include_chunk_framing_and_narrow_without_widening() -> None:
    assert _parse(_response(b"abc"), remaining_wire_bytes=3, remaining_decoded_bytes=3).body == b"abc"
    for limits in ({"remaining_wire_bytes": 2}, {"remaining_decoded_bytes": 2}):
        with pytest.raises(FetchError) as raised:
            _parse(_response(b"abc"), **limits)
        assert raised.value.code is FetchCode.LIMIT
    chunked = b"3\r\nabc\r\n0\r\n\r\n"
    assert _parse(_response(chunked, framing="chunked"), remaining_wire_bytes=len(chunked)).body == b"abc"
    with pytest.raises(FetchError) as raised:
        _parse(_response(chunked, framing="chunked"), remaining_wire_bytes=len(chunked) - 1)
    assert raised.value.code is FetchCode.LIMIT
    for value in (-1, MAX_WIRE_BODY_BYTES + 1, True):
        with pytest.raises(FetchError) as raised:
            HttpResponseParser(remaining_wire_bytes=value)
        assert raised.value.code is FetchCode.LIMIT


def test_final_utf8_is_strict_and_never_silently_repaired() -> None:
    with pytest.raises(FetchError) as raised:
        _parse(_response(b"\xff"))
    assert raised.value.code is FetchCode.ENCODING


def test_completed_frame_does_not_allow_ignored_tail_or_second_response() -> None:
    parser = HttpResponseParser()
    parser.feed(_response(b"okay"))
    with pytest.raises(FetchError):
        parser.feed(b"HTTP/1.1 200 OK\r\n\r\nsecret")
    with pytest.raises(FetchError):
        parser.finish()


def test_large_complete_trailer_refuses_at_its_first_field() -> None:
    body = b"0\r\nX-Trailer: " + b"a" * MAX_HEADER_BYTES + b"\r\n\r\n"
    with pytest.raises(FetchError) as raised:
        _parse(_response(body, framing="chunked"))
    assert raised.value.code is FetchCode.PROTOCOL


@pytest.mark.parametrize("fragment", [None, 1, 2, 7])
@pytest.mark.parametrize(
    "wire",
    [
        b"0;\x00\r\n\r\n",
        b"0;anything not valid extension\r\n\r\n",
        b"1\r\na\r\n0\r\n\n",
        b"0;valid=value\r\n\r\n",
        b"1;valid=value\r\na\r\n0\r\n\r\n",
        b"1 \r\na\r\n0\r\n\r\n",
        b"1\na\r\n0\r\n\r\n",
        b"1\r\na\n0\r\n\r\n",
        b"0\r\n\r",
        b"0\r\n\r\r\n",
    ],
)
def test_chunk_extensions_and_inexact_delimiters_refuse_for_every_fragmentation(
    wire: bytes, fragment: int | None
) -> None:
    with pytest.raises(FetchError) as raised:
        _parse(_response(wire, framing="chunked"), fragment=fragment)
    assert raised.value.code is FetchCode.PROTOCOL


@pytest.mark.parametrize("fragment", [None, 1, 2, 7])
def test_chunk_guard_skips_payload_delimiters_and_counts_all_framing(fragment: int | None) -> None:
    payload = b"0;\x00\r\n\n0\r\n\r\n"
    wire = f"{len(payload):x}\r\n".encode() + payload + b"\r\n01\r\nz\r\n00\r\n\r\n"
    result = _parse(_response(wire, framing="chunked"), fragment=fragment, remaining_wire_bytes=len(wire))
    assert result.body == payload + b"z"
    assert result.wire_body_bytes == len(wire)
    assert result.encoded_body_bytes == len(payload) + 1
