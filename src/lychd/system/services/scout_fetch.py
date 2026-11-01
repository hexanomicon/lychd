"""Bounded native HTTPS acquisition under caller-owned current effect authority.

These mechanisms do not mint grants, reserve durable attempts, or expose a web
endpoint. The host must supply a live gate backed by that separate authority.
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field
from hashlib import sha256
from http import HTTPStatus
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urljoin

from lychd.domain.scout.destination import DestinationCandidate, DestinationError, preflight_destination
from lychd.domain.scout.transport import FetchCode, FetchError, NetworkTarget
from lychd.system.services.scout_dns import resolve_destination
from lychd.system.services.scout_extraction import extract_static_text
from lychd.system.services.scout_http import HttpResponseParser, RssResponseParser, serialize_get, serialize_rss_get
from lychd.system.services.scout_socket import open_pinned_tls

if TYPE_CHECKING:
    from pathlib import Path

    from lychd.domain.scout.extraction import ExtractedText, ExtractionMedia, RssMedia
    from lychd.domain.scout.transport import NetworkGate
    from lychd.system.services.scout_dns import ResolverEndpoint
    from lychd.system.services.scout_extraction import ScoutExtractionRuntime
    from lychd.system.services.scout_http import HttpResponse, RssResponse

_MAX_WIRE_BODY = 2 * 1024 * 1024
_MAX_DECODED_BODY = 4 * 1024 * 1024
_MAX_RSS_DECODED_BODY = 1024 * 1024
_MAX_REDIRECTS = 3
_MAX_SECONDS = 30.0
_MAX_LOCATION = 4096


@dataclass(frozen=True, slots=True)
class FetchObservation:
    """Restricted response attribution, not a durable receipt or permission."""

    candidate: DestinationCandidate = field(repr=False)
    addresses: tuple[str, ...] = field(repr=False)
    peer: str = field(repr=False)
    status: int
    header_bytes: int
    wire_body_bytes: int
    encoded_body_bytes: int
    decoded_body_bytes: int
    http_response_digest: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class FetchedPage:
    """Ephemeral decoded bytes; no custody or trust is conferred by acquisition."""

    media_type: ExtractionMedia
    body: bytes = field(repr=False)
    observations: tuple[FetchObservation, ...] = field(repr=False)


@dataclass(frozen=True, slots=True)
class FetchedFeed:
    """Ephemeral RSS/XML bytes awaiting separately authorized extraction."""

    media_type: RssMedia
    body: bytes = field(repr=False)
    observations: tuple[FetchObservation, ...] = field(repr=False)


@dataclass(frozen=True, slots=True)
class AcquiredText:
    """Ephemeral text plus exact contacted-source attribution."""

    extraction: ExtractedText = field(repr=False)
    observations: tuple[FetchObservation, ...] = field(repr=False)


def _candidate(candidate: DestinationCandidate) -> DestinationCandidate:
    try:
        if type(candidate) is not DestinationCandidate or candidate != preflight_destination(candidate.original_url):
            raise FetchError(FetchCode.DESTINATION)
    except DestinationError:
        raise FetchError(FetchCode.DESTINATION) from None
    return candidate


def _deadline(deadline: float) -> float:
    if type(deadline) not in (float, int) or not math.isfinite(deadline):
        raise FetchError(FetchCode.CONFIG)
    now = time.monotonic()
    if deadline <= now:
        raise FetchError(FetchCode.TIMEOUT)
    return min(deadline, now + _MAX_SECONDS)


def _redirect(current: DestinationCandidate, location: str) -> DestinationCandidate:
    if not location or len(location) > _MAX_LOCATION or any(not "!" <= char <= "~" for char in location):
        raise FetchError(FetchCode.REDIRECT)
    if "#" in location or "\\" in location:
        raise FetchError(FetchCode.REDIRECT)
    try:
        if location.startswith("https://"):
            return preflight_destination(location)
        if location.startswith("//"):
            return preflight_destination(f"https:{location}")
        path = location.split("?", 1)[0]
        if ":" in path.split("/", 1)[0] or (not path.startswith("/") and "//" in path):
            # urljoin repairs malformed same-scheme locators and collapses empty
            # segments in relative paths. Refuse rather than change the target.
            raise FetchError(FetchCode.REDIRECT)
        absolute = urljoin(current.normalized_url, location)
        if location.endswith("?"):
            # urllib omits an empty query and may inherit the previous query.
            absolute = absolute.split("?", 1)[0] + "?"
        return preflight_destination(absolute)
    except (ValueError, DestinationError):
        raise FetchError(FetchCode.REDIRECT) from None


async def _response(
    candidate: DestinationCandidate,
    *,
    resolver: ResolverEndpoint,
    gate: NetworkGate,
    ca_file: Path,
    deadline: float,
    remaining_wire: int,
    remaining_decoded: int,
) -> tuple[HttpResponse, FetchObservation]:
    return await _read_response(
        candidate,
        resolver=resolver,
        gate=gate,
        ca_file=ca_file,
        deadline=deadline,
        request=serialize_get(candidate),
        parser=HttpResponseParser(remaining_wire_bytes=remaining_wire, remaining_decoded_bytes=remaining_decoded),
    )


class _ResponseReader[Response](Protocol):
    @property
    def http_status(self) -> int | None: ...

    def feed(self, data: bytes) -> None: ...

    def finish(self) -> Response: ...


async def _read_response[Response: (HttpResponse, RssResponse)](
    candidate: DestinationCandidate,
    *,
    resolver: ResolverEndpoint,
    gate: NetworkGate,
    ca_file: Path,
    deadline: float,
    request: bytes,
    parser: _ResponseReader[Response],
) -> tuple[Response, FetchObservation]:
    digest = sha256()
    try:
        async with asyncio.timeout(deadline - time.monotonic()):
            addresses = await resolve_destination(candidate, resolver=resolver, gate=gate, deadline=deadline)
            # There is one selected address, never a retry or happy-eyeballs race.
            peer = addresses.addresses[0]
            stream = await open_pinned_tls(
                NetworkTarget(peer, 443, candidate.hostname, "origin"), gate=gate, deadline=deadline, ca_file=ca_file
            )
            try:
                await stream.send(request)
                while part := await stream.receive():
                    digest.update(part)
                    parser.feed(part)
                response = parser.finish()
            finally:
                stream.close()
    except TimeoutError:
        raise FetchError(FetchCode.TIMEOUT, http_status=parser.http_status) from None
    except FetchError as error:
        raise FetchError(error.code, http_status=error.http_status or parser.http_status) from None
    return response, FetchObservation(
        candidate=candidate,
        addresses=addresses.addresses,
        peer=peer,
        status=response.status,
        header_bytes=response.header_bytes,
        wire_body_bytes=response.wire_body_bytes,
        encoded_body_bytes=response.encoded_body_bytes,
        decoded_body_bytes=response.decoded_body_bytes,
        http_response_digest=digest.hexdigest(),
    )


async def fetch_static_page(
    candidate: DestinationCandidate,
    *,
    resolver: ResolverEndpoint,
    gate: NetworkGate,
    ca_file: Path,
    deadline: float,
    permitted_redirects: tuple[DestinationCandidate, ...] = (),
) -> FetchedPage:
    """Fetch under a 30-second ceiling with exact pre-admitted redirect targets.

    Each address and handoff is checked again. The permitted list only narrows
    contacts; it does not replace the mandatory current authority gate.
    The caller's deadline begins at durable preparation, before this method.
    """
    current = _candidate(candidate)
    end = _deadline(deadline)
    if type(permitted_redirects) is not tuple or len(permitted_redirects) > _MAX_REDIRECTS:
        raise FetchError(FetchCode.CONFIG)
    permitted = {_candidate(item).normalized_url for item in permitted_redirects}
    seen = {current.normalized_url}
    observations: list[FetchObservation] = []
    remaining_wire, remaining_decoded = _MAX_WIRE_BODY, _MAX_DECODED_BODY
    for hop in range(_MAX_REDIRECTS + 1):
        response, observation = await _response(
            current,
            resolver=resolver,
            gate=gate,
            ca_file=ca_file,
            deadline=end,
            remaining_wire=remaining_wire,
            remaining_decoded=remaining_decoded,
        )
        observations.append(observation)
        remaining_wire -= response.wire_body_bytes
        remaining_decoded -= response.decoded_body_bytes
        if response.status == HTTPStatus.OK and response.media_type is not None:
            return FetchedPage(response.media_type, response.body, tuple(observations))
        if response.location is None or hop == _MAX_REDIRECTS:
            raise FetchError(FetchCode.REDIRECT, http_status=response.status)
        try:
            following = _redirect(current, response.location)
        except FetchError as error:
            raise FetchError(error.code, http_status=response.status) from None
        if following.normalized_url in seen or following.normalized_url not in permitted:
            raise FetchError(FetchCode.REDIRECT, http_status=response.status)
        seen.add(following.normalized_url)
        current = following
    raise FetchError(FetchCode.PROTOCOL)


async def fetch_rss_feed(
    candidate: DestinationCandidate,
    *,
    resolver: ResolverEndpoint,
    gate: NetworkGate,
    ca_file: Path,
    deadline: float,
) -> FetchedFeed:
    """Acquire one bounded feed passage without redirects, retries or extraction."""
    current = _candidate(candidate)
    end = _deadline(deadline)
    response, observation = await _read_response(
        current,
        resolver=resolver,
        gate=gate,
        ca_file=ca_file,
        deadline=end,
        request=serialize_rss_get(current),
        parser=RssResponseParser(remaining_decoded_bytes=_MAX_RSS_DECODED_BODY),
    )
    if response.status != HTTPStatus.OK or response.media_type is None:
        raise FetchError(FetchCode.REDIRECT, http_status=response.status)
    return FetchedFeed(response.media_type, response.body, (observation,))


async def acquire_static_text(
    candidate: DestinationCandidate,
    *,
    resolver: ResolverEndpoint,
    gate: NetworkGate,
    ca_file: Path,
    runtime: ScoutExtractionRuntime,
    deadline: float,
    permitted_redirects: tuple[DestinationCandidate, ...] = (),
) -> AcquiredText:
    """Keep Fetch and network-denied Extract inside the same remaining deadline.

    Cancellation awaits extractor containment; an uncertain cleanup remains an
    extraction CLEANUP refusal instead of being reported as an ordinary timeout.
    """
    end = _deadline(deadline)
    try:
        async with asyncio.timeout(end - time.monotonic()):
            page = await fetch_static_page(
                candidate,
                resolver=resolver,
                gate=gate,
                ca_file=ca_file,
                deadline=end,
                permitted_redirects=permitted_redirects,
            )
            extracted = await extract_static_text(page.body, media_type=page.media_type, runtime=runtime)
            return AcquiredText(extracted, page.observations)
    except TimeoutError:
        raise FetchError(FetchCode.TIMEOUT) from None
