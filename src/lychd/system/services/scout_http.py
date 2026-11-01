"""Bounded GET serialization and HTTP/1.1 decoding, with no contact authority.

Callers supply decrypted HTTP octets and must call ``finish`` only on transport
EOF. No socket, redirect, retry, cookie store, or artifact is created here. A
successful parse establishes framing and representation facts, not source truth.
"""

from __future__ import annotations

import re
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import NoReturn, cast

import h11

from lychd.domain.scout.destination import DestinationCandidate, DestinationError, preflight_destination
from lychd.domain.scout.extraction import ExtractionMedia, RssMedia
from lychd.domain.scout.transport import FetchCode, FetchError

MAX_HEADER_BYTES = 64 * 1024
MAX_WIRE_BODY_BYTES = 2 * 1024 * 1024
MAX_DECODED_BODY_BYTES = 4 * 1024 * 1024
MAX_RSS_DECODED_BODY_BYTES = 1024 * 1024
MAX_EXPANSION_RATIO = 20
MAX_LOCATION_BYTES = 4096
_FEED_BYTES = 4096
_MAX_LENGTH_DIGITS = 20
_OK_STATUS = 200
_MIN_STATUS = 100
_MAX_STATUS = 599
_REDIRECTS = frozenset({301, 302, 303, 307, 308})
_STATUS = re.compile(rb"HTTP/1\.1 ([0-9]{3})(?: [\x20-\x7e]*)?")
_FIELD_NAME = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
_CONTROL_VALUE = re.compile(rb"[\x00-\x1f\x7f]")
_LOCATION = re.compile(rb"[!-~]+")
_CHUNK_SIZE = re.compile(rb"[0-9a-fA-F]{1,20}")
_CONTENT_TYPE = re.compile(rb'(text/html|text/plain)(?: *; *charset *= *(?:utf-8|"utf-8"))? *', re.IGNORECASE)

_RSS_CONTENT_TYPE = re.compile(
    rb'(application/rss\+xml|application/xml|text/xml)(?: *; *charset *= *(?:utf-8|"utf-8"))? *',
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Completed ephemeral representation and explicitly separated byte counts.

    ``header_bytes`` includes the initial status line and CRLF terminator.
    ``wire_body_bytes`` counts every decrypted HTTP octet after that head,
    including chunk sizes, extensions, delimiters and trailers, but not TLS
    records. ``encoded_body_bytes`` counts only h11 Data payload octets, before
    gzip decoding. ``decoded_body_bytes`` counts representation bytes after
    decoding, including redirect bodies intentionally omitted from ``body``.
    A redirect's location is an untrusted observation requiring fresh admission.
    """

    status: int
    media_type: ExtractionMedia | None
    body: bytes = field(repr=False)
    location: str | None = field(repr=False)
    header_bytes: int
    wire_body_bytes: int
    encoded_body_bytes: int
    decoded_body_bytes: int


@dataclass(frozen=True, slots=True)
class RssResponse:
    """Completed feed representation with the same separated HTTP byte counts."""

    status: int
    media_type: RssMedia | None
    body: bytes = field(repr=False)
    location: str | None = field(repr=False)
    header_bytes: int
    wire_body_bytes: int
    encoded_body_bytes: int
    decoded_body_bytes: int


def serialize_get(candidate: DestinationCandidate) -> bytes:
    """Serialize host-owned headers while preserving the exact path/query meaning."""
    return _serialize_get(candidate, b"text/html,text/plain")


def serialize_rss_get(candidate: DestinationCandidate) -> bytes:
    """Serialize one fixed RSS/XML GET without caller-supplied headers."""
    return _serialize_get(candidate, b"application/rss+xml,application/xml,text/xml")


def _serialize_get(candidate: DestinationCandidate, accept: bytes) -> bytes:
    try:
        if type(candidate) is not DestinationCandidate or candidate != preflight_destination(candidate.original_url):
            raise FetchError(FetchCode.DESTINATION)
    except DestinationError:
        raise FetchError(FetchCode.DESTINATION) from None
    authority = f"[{candidate.hostname}]" if ":" in candidate.hostname else candidate.hostname
    target = candidate.normalized_url[len("https://") + len(authority) :]
    if not target.startswith("/"):
        target = "/" + target
    connection = h11.Connection(h11.CLIENT)
    try:
        head = connection.send(
            h11.Request(
                method=b"GET",
                target=target.encode("ascii"),
                headers=[
                    (b"Host", authority.encode("ascii")),
                    (b"Accept", accept),
                    (b"Accept-Encoding", b"gzip, identity"),
                    (b"Connection", b"close"),
                ],
            )
        )
        end = connection.send(h11.EndOfMessage())
    except h11.LocalProtocolError:
        raise FetchError(FetchCode.PROTOCOL) from None
    return head + end


def _single(headers: dict[bytes, list[bytes]], name: bytes) -> bytes | None:
    values = headers.get(name, [])
    if len(values) > 1:
        raise FetchError(FetchCode.PROTOCOL)
    return values[0] if values else None


def _raw_headers(head: bytes) -> tuple[int, dict[bytes, list[bytes]]]:
    lines = head[:-4].split(b"\r\n")
    status = _STATUS.fullmatch(lines[0])
    if status is None:
        raise FetchError(FetchCode.PROTOCOL)
    headers: dict[bytes, list[bytes]] = {}
    for line in lines[1:]:
        name, separator, value = line.partition(b":")
        if not separator or _FIELD_NAME.fullmatch(name) is None:
            raise FetchError(FetchCode.PROTOCOL)
        # OWS around a field is framing; embedded controls never become values.
        value = value.strip(b" \t")
        if _CONTROL_VALUE.search(value) is not None:
            raise FetchError(FetchCode.PROTOCOL)
        headers.setdefault(name.lower(), []).append(value)
    return int(status[1]), headers


class _ChunkFraming:
    """Narrow h11's permissive chunk metadata to sizes and exact CRLF only.

    Payload bytes are skipped by length and remain h11's responsibility. No
    extensions or trailer fields are admitted; metadata storage is at most
    twenty hex digits and a CR, regardless of input fragmentation.
    """

    def __init__(self) -> None:
        self._remaining = 0
        self._size = bytearray()
        self._delimiter = b""
        self._last = False
        self.complete = False

    def _size_octet(self, octet: bytes) -> None:
        if octet == b"\n":
            if not self._size.endswith(b"\r") or _CHUNK_SIZE.fullmatch(self._size[:-1]) is None:
                raise FetchError(FetchCode.PROTOCOL)
            self._remaining = int(self._size[:-1], 16)
            self._size.clear()
            if self._remaining == 0:
                self._last = True
                self._delimiter = b"\r\n"
        elif (
            len(self._size) >= _MAX_LENGTH_DIGITS + 1
            or self._size.endswith(b"\r")
            or octet not in b"0123456789abcdefABCDEF\r"
        ):
            raise FetchError(FetchCode.PROTOCOL)
        else:
            self._size.extend(octet)

    def feed(self, data: bytes) -> None:
        offset = 0
        while offset < len(data):
            if self.complete:
                raise FetchError(FetchCode.PROTOCOL)
            if self._remaining:
                count = min(self._remaining, len(data) - offset)
                offset += count
                self._remaining -= count
                if self._remaining == 0:
                    self._delimiter = b"\r\n"
            elif self._delimiter:
                count = min(len(self._delimiter), len(data) - offset)
                if data[offset : offset + count] != self._delimiter[:count]:
                    raise FetchError(FetchCode.PROTOCOL)
                offset += count
                self._delimiter = self._delimiter[count:]
                if not self._delimiter and self._last:
                    self.complete = True
            else:
                self._size_octet(data[offset : offset + 1])
                offset += 1


class _ResponseParser[Media: str, Response](ABC):
    """Consume one bounded HTTP/1.1 GET response using h11's framing machinery.

    Remaining body budgets may narrow the fixed profile, including to zero.
    Gzip expansion is checked over the complete encoded representation, making
    acceptance independent of network fragmentation. Decoded size is enforced
    during every decompression call. Chunk extensions and trailer fields are
    unsupported and refuse; all chunk framing requires exact CRLF delimiters.
    Once a refusal occurs this instance cannot produce a successful result.
    """

    def __init__(
        self,
        *,
        remaining_wire_bytes: int,
        remaining_decoded_bytes: int,
        maximum_decoded_bytes: int,
    ) -> None:
        """Pin finite narrowing budgets without acquiring or sending anything."""
        for value, maximum in (
            (remaining_wire_bytes, MAX_WIRE_BODY_BYTES),
            (remaining_decoded_bytes, maximum_decoded_bytes),
        ):
            if type(value) is not int or not 0 <= value <= maximum:
                raise FetchError(FetchCode.LIMIT)
        self._wire_limit = remaining_wire_bytes
        self._decoded_limit = remaining_decoded_bytes
        self._connection = h11.Connection(h11.CLIENT, max_incomplete_event_size=MAX_HEADER_BYTES)
        # Prime protocol state for the fixed GET; these bytes are never transmitted.
        self._connection.send(h11.Request(method=b"GET", target=b"/", headers=[(b"Host", b"scout.invalid")]))
        self._connection.send(h11.EndOfMessage())
        self._head = bytearray()
        self._body = bytearray()
        self._gzip = zlib.decompressobj(wbits=16 + zlib.MAX_WBITS)
        self._gzip_enabled = False
        self._chunks: _ChunkFraming | None = None
        self._status: int | None = None
        self._media_type: Media | None = None
        self._location: str | None = None
        self._complete = False
        self._finished = False
        self._failure: FetchCode | None = None
        self.header_bytes = 0
        self.wire_body_bytes = 0
        self.encoded_body_bytes = 0
        self.decoded_body_bytes = 0

    def _refuse(self, code: FetchCode) -> NoReturn:
        self._failure = code
        raise FetchError(code, http_status=self._status) from None

    @property
    def http_status(self) -> int | None:
        """Return only a valid status from a complete syntactically valid head."""
        return self._status

    def _configure_framing(self, headers: dict[bytes, list[bytes]]) -> None:
        length = _single(headers, b"content-length")
        transfer = _single(headers, b"transfer-encoding")
        if length is not None and transfer is not None:
            self._refuse(FetchCode.PROTOCOL)
        if length is not None:
            if not length.isdigit() or len(length) > _MAX_LENGTH_DIGITS:
                self._refuse(FetchCode.PROTOCOL)
            if int(length) > self._wire_limit:
                self._refuse(FetchCode.LIMIT)
        if transfer is not None and transfer.lower() != b"chunked":
            self._refuse(FetchCode.PROTOCOL)
        self._chunks = _ChunkFraming() if transfer is not None else None
        encoding = _single(headers, b"content-encoding")
        if encoding is not None and encoding.lower() not in {b"identity", b"gzip"}:
            self._refuse(FetchCode.ENCODING)
        if encoding is not None and encoding.lower() == b"gzip":
            self._gzip_enabled = True

    def _configure(self, head: bytes) -> None:
        status, headers = _raw_headers(head)
        if not _MIN_STATUS <= status <= _MAX_STATUS:
            self._refuse(FetchCode.PROTOCOL)
        self._status = status
        if status != _OK_STATUS and status not in _REDIRECTS:
            self._refuse(FetchCode.PROTOCOL)
        connection_tokens = b",".join(headers.get(b"connection", [])).lower().split(b",")
        if b"upgrade" in headers or any(token.strip() == b"upgrade" for token in connection_tokens):
            self._refuse(FetchCode.PROTOCOL)
        self._configure_framing(headers)
        if status == _OK_STATUS:
            media = _single(headers, b"content-type")
            self._media_type = self._parse_media(media)
        else:
            location = _single(headers, b"location")
            if not location or len(location) > MAX_LOCATION_BYTES or _LOCATION.fullmatch(location) is None:
                self._refuse(FetchCode.PROTOCOL)
            self._location = location.decode("ascii")

    def _data(self, data: bytes) -> None:
        self.encoded_body_bytes += len(data)
        if self._gzip_enabled:
            if self._gzip.eof and data:
                self._refuse(FetchCode.ENCODING)
            try:
                decoded = self._gzip.decompress(data, self._decoded_limit - self.decoded_body_bytes + 1)
            except zlib.error:
                self._refuse(FetchCode.ENCODING)
            if self._gzip.unused_data:
                self._refuse(FetchCode.ENCODING)
        else:
            decoded = data
        self.decoded_body_bytes += len(decoded)
        if self.decoded_body_bytes > self._decoded_limit:
            self._refuse(FetchCode.LIMIT)
        if self._status == _OK_STATUS:
            self._body.extend(decoded)

    def _events(self) -> None:
        try:
            while True:
                event = self._connection.next_event()
                if event is h11.NEED_DATA or event is h11.PAUSED or isinstance(event, h11.ConnectionClosed):
                    return
                if isinstance(event, h11.Response):
                    if event.status_code != self._status or event.http_version != b"1.1":
                        self._refuse(FetchCode.PROTOCOL)
                elif isinstance(event, h11.Data):
                    self._data(bytes(event.data))
                elif isinstance(event, h11.EndOfMessage):
                    if event.headers:
                        self._refuse(FetchCode.PROTOCOL)
                    self._complete = True
                    if self._connection.trailing_data[0]:
                        self._refuse(FetchCode.PROTOCOL)
                else:
                    self._refuse(FetchCode.PROTOCOL)
        except (h11.LocalProtocolError, h11.RemoteProtocolError):
            self._refuse(FetchCode.PROTOCOL)

    def _feed_body(self, data: bytes) -> None:
        if self._complete and data:
            self._refuse(FetchCode.PROTOCOL)
        self.wire_body_bytes += len(data)
        if self.wire_body_bytes > self._wire_limit:
            self._refuse(FetchCode.LIMIT)
        offset = 0
        while offset < len(data):
            # Public trailing_data exposes unprocessed octets. Bound before feed,
            # even when an entire oversized metadata event arrives in one call.
            pending = len(self._connection.trailing_data[0])
            allowance = min(_FEED_BYTES, MAX_HEADER_BYTES - pending)
            if allowance <= 0:
                self._refuse(FetchCode.LIMIT)
            piece = data[offset : offset + allowance]
            if self._chunks is not None:
                self._chunks.feed(piece)
            self._connection.receive_data(piece)
            self._events()
            offset += len(piece)
            if self._complete and offset < len(data):
                self._refuse(FetchCode.PROTOCOL)

    def feed(self, data: bytes) -> None:
        """Consume non-EOF input, enforcing raw head bounds before h11 sees it."""
        if self._failure is not None:
            raise FetchError(self._failure, http_status=self._status)
        if self._finished or type(data) is not bytes:
            self._refuse(FetchCode.PROTOCOL)
        try:
            if self._status is not None:
                self._feed_body(data)
                return
            take = min(len(data), MAX_HEADER_BYTES + 1 - len(self._head))
            self._head.extend(data[:take])
            marker = self._head.find(b"\r\n\r\n")
            if marker < 0:
                if len(self._head) > MAX_HEADER_BYTES:
                    self._refuse(FetchCode.LIMIT)
                return
            end = marker + 4
            if end > MAX_HEADER_BYTES:
                self._refuse(FetchCode.LIMIT)
            head = bytes(self._head[:end])
            tail = bytes(self._head[end:])
            self.header_bytes = end
            self._configure(head)
            self._connection.receive_data(head)
            self._events()
            self._head.clear()
            self._feed_body(tail)
            self._feed_body(data[take:])
        except FetchError as error:
            self._refuse(error.code)

    def finish(self) -> Response:
        """Mark real transport EOF and return only a complete validated response."""
        if self._failure is not None:
            raise FetchError(self._failure, http_status=self._status)
        if self._finished or self._status is None:
            self._refuse(FetchCode.PROTOCOL)
        if self._chunks is not None and not self._chunks.complete:
            self._refuse(FetchCode.PROTOCOL)
        self._connection.receive_data(b"")
        self._events()
        if not self._complete:
            self._refuse(FetchCode.PROTOCOL)
        if self._gzip_enabled and (not self._gzip.eof or self._gzip.unused_data or self._gzip.unconsumed_tail):
            self._refuse(FetchCode.ENCODING)
        if self.decoded_body_bytes > MAX_EXPANSION_RATIO * self.encoded_body_bytes:
            self._refuse(FetchCode.LIMIT)
        body = bytes(self._body)
        if self._status == _OK_STATUS:
            try:
                body.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                self._refuse(FetchCode.ENCODING)
        self._finished = True
        return self._result(self._status, body)

    @abstractmethod
    def _parse_media(self, media: bytes | None) -> Media:
        """Apply the fixed representation profile."""

    @abstractmethod
    def _result(self, status: int, body: bytes) -> Response:
        """Build the profile-specific immutable response."""


class HttpResponseParser(_ResponseParser[ExtractionMedia, HttpResponse]):
    """Decode the unchanged bounded HTML/plain-text HTTP/1.1 profile."""

    def __init__(
        self,
        *,
        remaining_wire_bytes: int = MAX_WIRE_BODY_BYTES,
        remaining_decoded_bytes: int = MAX_DECODED_BODY_BYTES,
    ) -> None:
        """Pin finite narrowing budgets without acquiring or sending anything."""
        super().__init__(
            remaining_wire_bytes=remaining_wire_bytes,
            remaining_decoded_bytes=remaining_decoded_bytes,
            maximum_decoded_bytes=MAX_DECODED_BODY_BYTES,
        )

    def _parse_media(self, media: bytes | None) -> ExtractionMedia:
        match = _CONTENT_TYPE.fullmatch(media) if media is not None else None
        if match is None:
            self._refuse(FetchCode.MEDIA)
        return "text/html" if match[1].lower() == b"text/html" else "text/plain"

    def _result(self, status: int, body: bytes) -> HttpResponse:
        return HttpResponse(
            status=status,
            media_type=self._media_type,
            body=body,
            location=self._location,
            header_bytes=self.header_bytes,
            wire_body_bytes=self.wire_body_bytes,
            encoded_body_bytes=self.encoded_body_bytes,
            decoded_body_bytes=self.decoded_body_bytes,
        )


class RssResponseParser(_ResponseParser[RssMedia, RssResponse]):
    """Decode only fixed RSS/XML media, strict UTF-8 and at most 1 MiB decoded."""

    def __init__(
        self,
        *,
        remaining_wire_bytes: int = MAX_WIRE_BODY_BYTES,
        remaining_decoded_bytes: int = MAX_RSS_DECODED_BODY_BYTES,
    ) -> None:
        """Pin finite narrowing budgets without acquiring or sending anything."""
        super().__init__(
            remaining_wire_bytes=remaining_wire_bytes,
            remaining_decoded_bytes=remaining_decoded_bytes,
            maximum_decoded_bytes=MAX_RSS_DECODED_BODY_BYTES,
        )

    def _parse_media(self, media: bytes | None) -> RssMedia:
        match = _RSS_CONTENT_TYPE.fullmatch(media) if media is not None else None
        if match is None:
            self._refuse(FetchCode.MEDIA)
        return cast("RssMedia", match[1].decode("ascii").lower())

    def _result(self, status: int, body: bytes) -> RssResponse:
        return RssResponse(
            status=status,
            media_type=self._media_type,
            body=body,
            location=self._location,
            header_bytes=self.header_bytes,
            wire_body_bytes=self.wire_body_bytes,
            encoded_body_bytes=self.encoded_body_bytes,
            decoded_body_bytes=self.decoded_body_bytes,
        )
