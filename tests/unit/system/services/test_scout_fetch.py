"""Composition contracts; substituted transport does not qualify network effects."""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import replace
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest

from lychd.domain.scout.destination import DestinationAddresses, classify_destination_addresses, preflight_destination
from lychd.domain.scout.extraction import ExtractionCode, ExtractionError
from lychd.domain.scout.transport import FetchCode, FetchError, NetworkGate
from lychd.system.services import scout_fetch as fetch
from lychd.system.services.scout_dns import ResolverEndpoint
from lychd.system.services.scout_extraction import ScoutExtractionRuntime

_PAGE = preflight_destination("https://example.com/page?public=yes")


def test_maintained_transport_qualification_matches_source_and_dependencies() -> None:
    """A historical network proof cannot qualify changed transport or parser code."""
    root = Path(__file__).resolve().parents[4]
    receipt = json.loads((root / "tests/fixtures/scout/linux-fetch-runtime.json").read_text())
    assert receipt["schema"] == "scout-fetch-local-proof@1"
    assert receipt["status"] == "passed"
    assert receipt["network"] == "isolated-loopback-only"
    assert receipt["authority"] == "synthetic-audit-gate-not-durable-production-authority"
    assert receipt["extraction"] == "passed_with_explicit_runtime_profile"
    assert receipt["dependency_versions"] == {name: version(name) for name in ("h11", "dnspython")}
    assert set(receipt["source_fingerprints"]) == {
        "src/lychd/domain/scout/destination.py",
        "src/lychd/domain/scout/transport.py",
        "src/lychd/system/services/scout_dns.py",
        "src/lychd/system/services/scout_socket.py",
        "src/lychd/system/services/scout_http.py",
        "src/lychd/system/services/scout_fetch.py",
        "src/lychd/system/services/scout_extraction.py",
        "src/lychd/system/scout_worker.py",
        "tests/integration/test_scout_fetch_runtime.py",
        "tests/scout_network_fixture.py",
    }
    for path, digest in receipt["source_fingerprints"].items():
        assert sha256((root / path).read_bytes()).hexdigest() == digest, path


def _stream(response: bytes) -> Mock:
    stream = Mock()
    stream.send = AsyncMock()
    stream.receive = AsyncMock(side_effect=[response[:17], response[17:], b""])
    return stream


def _wire(body: bytes = b"Page text") -> bytes:
    return (
        b"HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: "
        + str(len(body)).encode()
        + b"\r\n\r\n"
        + body
    )


def _install(monkeypatch: pytest.MonkeyPatch, *responses: bytes) -> tuple[AsyncMock, AsyncMock, list[Mock]]:
    async def resolve(candidate: fetch.DestinationCandidate, **_kwargs: object) -> DestinationAddresses:
        return classify_destination_addresses(candidate, hostname=candidate.hostname, addresses=("93.184.216.34",))

    resolved = AsyncMock(side_effect=resolve)
    streams = [_stream(response) for response in responses]
    opened = AsyncMock(side_effect=streams)
    monkeypatch.setattr(fetch, "resolve_destination", resolved)
    monkeypatch.setattr(fetch, "open_pinned_tls", opened)
    return resolved, opened, streams


async def _fetch(*, redirects: tuple[fetch.DestinationCandidate, ...] = ()) -> fetch.FetchedPage:
    return await fetch.fetch_static_page(
        _PAGE,
        resolver=ResolverEndpoint("127.0.0.1"),
        gate=cast("NetworkGate", Mock()),
        ca_file=Path("/unused-ca"),
        deadline=time.monotonic() + 30,
        permitted_redirects=redirects,
    )


@pytest.mark.asyncio
async def test_original_hostname_and_exact_request_survive_numeric_pinning(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = _wire()
    resolved, opened, streams = _install(monkeypatch, wire)
    result = await _fetch()
    assert result.body == b"Page text"
    assert result.media_type == "text/plain"
    target = opened.call_args.args[0]
    assert target == fetch.NetworkTarget("93.184.216.34", 443, "example.com", "origin")
    assert resolved.call_args.kwargs["deadline"] == opened.call_args.kwargs["deadline"]
    assert resolved.call_args.kwargs["gate"] is opened.call_args.kwargs["gate"]
    streams[0].send.assert_awaited_once_with(fetch.serialize_get(_PAGE))
    streams[0].close.assert_called_once()
    (observed,) = result.observations
    assert observed.http_response_digest == sha256(wire).hexdigest()
    assert observed.decoded_body_bytes == len(result.body)
    assert "Page text" not in repr(result)
    assert "public=yes" not in repr(result)


@pytest.mark.asyncio
async def test_unlisted_redirect_stops_before_new_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    resolved, opened, streams = _install(
        monkeypatch, b"HTTP/1.1 302 Found\r\nLocation: /next\r\nContent-Length: 0\r\n\r\n"
    )
    with pytest.raises(FetchError) as caught:
        await _fetch()
    assert caught.value.code is FetchCode.REDIRECT
    assert caught.value.http_status == 302
    resolved.assert_awaited_once()
    opened.assert_awaited_once()
    streams[0].close.assert_called_once()


@pytest.mark.asyncio
async def test_exact_admitted_redirect_is_resolved_and_gated_again(monkeypatch: pytest.MonkeyPatch) -> None:
    following = preflight_destination("https://example.com/next?")
    redirect = b"HTTP/1.1 302 Found\r\nLocation: /next?\r\nContent-Length: 4\r\n\r\nbody"
    resolved, opened, streams = _install(monkeypatch, redirect, _wire())
    result = await _fetch(redirects=(following,))
    assert [call.args[0] for call in resolved.call_args_list] == [_PAGE, following]
    assert opened.await_count == 2
    assert len(result.observations) == 2
    assert result.observations[0].decoded_body_bytes == 4
    assert result.body == b"Page text"
    streams[1].send.assert_awaited_once_with(fetch.serialize_get(following))
    assert all(stream.close.call_count == 1 for stream in streams)


@pytest.mark.asyncio
async def test_redirect_cycle_stops_before_second_contact(monkeypatch: pytest.MonkeyPatch) -> None:
    resolved, _, _ = _install(
        monkeypatch, b"HTTP/1.1 302 Found\r\nLocation: /page?public=yes\r\nContent-Length: 0\r\n\r\n"
    )
    with pytest.raises(FetchError) as caught:
        await _fetch(redirects=(_PAGE,))
    assert caught.value.code is FetchCode.REDIRECT
    resolved.assert_awaited_once()


@pytest.mark.parametrize(
    "location",
    [
        "http://example.com/",
        "https://127.0.0.1/",
        "//other.example/#fragment",
        " /page",
        "/\\host",
        "/page\n",
        "a" * 4097,
    ],
)
def test_unsafe_location_refuses_without_repair(location: str) -> None:
    with pytest.raises(FetchError):
        fetch._redirect(_PAGE, location)


@pytest.mark.parametrize(
    "location",
    ["child//item", "./child//item", "../child//item", "https:/different.example/", "https:///different.example/"],
)
def test_ambiguous_relative_redirect_is_never_repaired(location: str) -> None:
    with pytest.raises(FetchError) as caught:
        fetch._redirect(_PAGE, location)
    assert caught.value.code is FetchCode.REDIRECT


@pytest.mark.parametrize("location", ["/child//item", "https://example.com/child//item", "//example.com/child//item"])
def test_absolute_redirect_preserves_empty_segments(location: str) -> None:
    assert fetch._redirect(_PAGE, location).normalized_url == "https://example.com/child//item"


@pytest.mark.asyncio
async def test_body_allowance_aggregates_across_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "_MAX_WIRE_BODY", 8)
    following = preflight_destination("https://example.com/next")
    redirect = b"HTTP/1.1 302 Found\r\nLocation: /next\r\nContent-Length: 4\r\n\r\nbody"
    _, _, streams = _install(monkeypatch, redirect, _wire(b"12345"))
    with pytest.raises(FetchError) as caught:
        await _fetch(redirects=(following,))
    assert caught.value.code is FetchCode.LIMIT
    assert all(stream.close.call_count == 1 for stream in streams)


@pytest.mark.asyncio
async def test_received_response_tail_is_not_hidden_by_declared_length(monkeypatch: pytest.MonkeyPatch) -> None:
    _, _, streams = _install(monkeypatch, _wire() + b"UNEXPECTED")
    with pytest.raises(FetchError) as caught:
        await _fetch()
    assert caught.value.code is FetchCode.PROTOCOL
    streams[0].close.assert_called_once()


@pytest.mark.asyncio
async def test_cancellation_closes_owned_stream_without_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    _, opened, streams = _install(monkeypatch, _wire())
    started = asyncio.Event()

    async def pending() -> bytes:
        started.set()
        await asyncio.Future[None]()
        return b""

    streams[0].receive.side_effect = pending
    task = asyncio.create_task(_fetch())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    streams[0].close.assert_called_once()
    opened.assert_awaited_once()


@pytest.mark.parametrize("observed_head", [False, True])
@pytest.mark.parametrize("failure", ["transport", "timeout"])
@pytest.mark.asyncio
async def test_read_failure_keeps_only_status_from_this_validated_head(
    monkeypatch: pytest.MonkeyPatch, *, observed_head: bool, failure: str
) -> None:
    _, _, streams = _install(monkeypatch, _wire())
    error = FetchError(FetchCode.TRANSPORT) if failure == "transport" else TimeoutError()
    prefix = [b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 20\r\n\r\n"] if observed_head else []
    streams[0].receive.side_effect = [*prefix, error]
    with pytest.raises(FetchError) as caught:
        await _fetch()
    assert caught.value.code is (FetchCode.TRANSPORT if failure == "transport" else FetchCode.TIMEOUT)
    assert caught.value.http_status == (200 if observed_head else None)
    streams[0].close.assert_called_once()


@pytest.mark.asyncio
async def test_deadline_after_validated_head_keeps_status_and_closes_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    _, opened, streams = _install(monkeypatch, _wire())
    calls = 0

    async def receive() -> bytes:
        nonlocal calls
        calls += 1
        if calls == 1:
            return b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 20\r\n\r\n"
        await asyncio.Future[None]()
        return b""

    streams[0].receive.side_effect = receive
    with pytest.raises(FetchError) as caught:
        await fetch.fetch_static_page(
            _PAGE,
            resolver=ResolverEndpoint("127.0.0.1"),
            gate=cast("NetworkGate", Mock()),
            ca_file=Path("/unused-ca"),
            deadline=time.monotonic() + 0.01,
        )
    assert caught.value.code is FetchCode.TIMEOUT
    assert caught.value.http_status == 200
    streams[0].close.assert_called_once()
    opened.assert_awaited_once()


@pytest.mark.asyncio
async def test_expired_or_forged_admission_never_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    resolved, _, _ = _install(monkeypatch)
    for candidate, deadline in [
        (_PAGE, time.monotonic() - 1),
        (replace(_PAGE, hostname="different.example"), time.monotonic() + 1),
    ]:
        with pytest.raises(FetchError):
            await fetch.fetch_static_page(
                candidate,
                resolver=ResolverEndpoint("127.0.0.1"),
                gate=cast("NetworkGate", Mock()),
                ca_file=Path("/unused-ca"),
                deadline=deadline,
            )
    resolved.assert_not_awaited()


@pytest.mark.asyncio
async def test_extraction_uncertain_cleanup_is_not_relabelled_success_or_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, _wire())
    extracted = AsyncMock(side_effect=ExtractionError(ExtractionCode.CLEANUP))
    monkeypatch.setattr(fetch, "extract_static_text", extracted)
    with pytest.raises(ExtractionError) as caught:
        await fetch.acquire_static_text(
            _PAGE,
            resolver=ResolverEndpoint("127.0.0.1"),
            gate=cast("NetworkGate", Mock()),
            ca_file=Path("/unused-ca"),
            runtime=cast("ScoutExtractionRuntime", Mock()),
            deadline=time.monotonic() + 1,
        )
    assert caught.value.code is ExtractionCode.CLEANUP
    assert extracted.call_args.args[0] == b"Page text"
