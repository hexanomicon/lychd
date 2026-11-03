"""DNS wire contracts use substituted streams, never ambient DNS or host sockets."""

# pyright: reportPrivateUsage=false
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import cast
from unittest.mock import AsyncMock, Mock

import dns.message
import dns.rcode
import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.rrset
import pytest
from dns import flags as dns_flags

from lychd.domain.scout.destination import preflight_destination
from lychd.domain.scout.transport import FetchCode, FetchError, NetworkGate
from lychd.system.services import scout_dns as resolver

_PAGE = preflight_destination("https://example.com/page?public=yes")
_RESOLVER = resolver.ResolverEndpoint("127.0.0.1", 5353)


def _response(query: dns.message.QueryMessage, address: str | None = None) -> dns.message.Message:
    response = dns.message.make_response(query)
    response.flags |= dns_flags.RA
    question = query.question[0]
    if address is not None:
        response.answer.append(dns.rrset.from_text(question.name, 60, "IN", question.rdtype, address))
    else:
        response.authority.append(
            dns.rrset.from_text("example.com.", 60, "IN", "SOA", "ns.example.com. hostmaster.example.com. 1 2 3 4 5")
        )
    return response


def _stream(answer: Callable[[dns.message.QueryMessage], bytes]) -> Mock:
    buffer = bytearray()

    async def send(data: bytes) -> None:
        assert int.from_bytes(data[:2], "big") == len(data) - 2
        query = dns.message.from_wire(data[2:])
        assert isinstance(query, dns.message.QueryMessage)
        assert query.edns == -1
        payload = answer(query)
        buffer.extend(len(payload).to_bytes(2, "big") + payload)

    async def receive(max_bytes: int) -> bytes:
        size = min(max_bytes, 3)
        result = bytes(buffer[:size])
        del buffer[:size]
        return result

    stream = Mock()
    stream.send = AsyncMock(side_effect=send)
    stream.receive = AsyncMock(side_effect=receive)
    return stream


@pytest.mark.asyncio
async def test_observes_both_exact_families_with_fixed_resolver_then_classifies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    streams = [
        _stream(lambda query: _response(query, "93.184.216.34").to_wire()),
        _stream(lambda query: _response(query).to_wire()),
    ]
    opened = AsyncMock(side_effect=streams)
    monkeypatch.setattr(resolver, "open_pinned_tcp", opened)
    gate = cast("NetworkGate", Mock())
    result = await resolver.resolve_destination(_PAGE, resolver=_RESOLVER, gate=gate, deadline=123.0)
    assert result.addresses == ("93.184.216.34",)
    for call, stream in zip(opened.call_args_list, streams, strict=True):
        assert call.args[0] == resolver.NetworkTarget("127.0.0.1", 5353, "example.com", "resolver")
        assert call.kwargs == {"gate": gate, "deadline": 123.0}
        stream.close.assert_called_once()
    questions = [dns.message.from_wire(stream.send.call_args.args[0][2:]).question[0] for stream in streams]
    assert [question.rdtype for question in questions] == [dns.rdatatype.A, dns.rdatatype.AAAA]
    assert all(question.name.to_text() == "example.com." for question in questions)


@pytest.mark.asyncio
@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "192.0.2.1"])
async def test_mixed_answers_refuse_origin_eligibility(monkeypatch: pytest.MonkeyPatch, address: str) -> None:
    def mixed(query: dns.message.QueryMessage) -> bytes:
        response = _response(query, "93.184.216.34")
        response.answer[0].add(dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.A, address))
        return response.to_wire()

    opened = AsyncMock(side_effect=[_stream(mixed), _stream(lambda query: _response(query).to_wire())])
    monkeypatch.setattr(resolver, "open_pinned_tcp", opened)
    with pytest.raises(FetchError) as caught:
        await resolver.resolve_destination(_PAGE, resolver=_RESOLVER, gate=cast("NetworkGate", Mock()), deadline=123.0)
    assert caught.value.code is FetchCode.DESTINATION
    assert address not in str(caught.value)


@pytest.mark.parametrize(
    "case", ["id", "question", "truncated", "referral", "nxdomain", "servfail", "not_recursive", "tail", "unrelated"]
)
def test_incomplete_or_unrelated_responses_refuse(case: str) -> None:
    query = dns.message.make_query("example.com.", "A")
    response = _response(query, "93.184.216.34")
    if case == "id":
        response.id ^= 1
    elif case == "question":
        response.question = dns.message.make_query("different.example.", "A").question
    elif case == "truncated":
        response.flags |= dns_flags.TC
    elif case == "referral":
        response.answer.clear()
    elif case == "nxdomain":
        response.set_rcode(dns.rcode.NXDOMAIN)
    elif case == "servfail":
        response.set_rcode(dns.rcode.SERVFAIL)
    elif case == "not_recursive":
        response.flags &= ~dns_flags.RA
    elif case == "unrelated":
        response.answer.append(dns.rrset.from_text("different.example.", 60, "IN", "A", "127.0.0.1"))
    wire = response.to_wire() + (b"tail" if case == "tail" else b"")
    with pytest.raises(FetchError) as caught:
        resolver._addresses(query, wire)
    assert caught.value.code is FetchCode.DNS


def test_record_count_is_bounded_before_chain_processing() -> None:
    query = dns.message.make_query("example.com.", "A")
    response = _response(query, "93.184.216.34")
    for index in range(64):
        response.answer.append(dns.rrset.from_text(f"other{index}.example.", 60, "IN", "A", "93.184.216.34"))
    with pytest.raises(FetchError) as caught:
        resolver._addresses(query, response.to_wire())
    assert caught.value.code is FetchCode.DNS


def test_complete_alias_chain_is_observation_without_a_new_question() -> None:
    query = dns.message.make_query("example.com.", "A")
    response = _response(query)
    response.answer.extend(
        [
            dns.rrset.from_text("example.com.", 60, "IN", "CNAME", "edge.example.com."),
            dns.rrset.from_text("edge.example.com.", 60, "IN", "A", "93.184.216.34"),
        ]
    )
    name, addresses = resolver._addresses(query, response.to_wire())
    assert name.to_text() == "edge.example.com."
    assert addresses == ("93.184.216.34",)


@pytest.mark.asyncio
async def test_first_family_failure_closes_without_second_contact(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _stream(lambda _query: b"not dns")
    opened = AsyncMock(return_value=stream)
    monkeypatch.setattr(resolver, "open_pinned_tcp", opened)
    with pytest.raises(FetchError):
        await resolver.resolve_destination(_PAGE, resolver=_RESOLVER, gate=cast("NetworkGate", Mock()), deadline=123.0)
    stream.close.assert_called_once()
    opened.assert_awaited_once()


@pytest.mark.asyncio
async def test_literal_needs_no_dns_and_forged_candidate_never_contacts(monkeypatch: pytest.MonkeyPatch) -> None:
    opened = AsyncMock()
    monkeypatch.setattr(resolver, "open_pinned_tcp", opened)
    literal = preflight_destination("https://93.184.216.34/")
    result = await resolver.resolve_destination(
        literal, resolver=_RESOLVER, gate=cast("NetworkGate", Mock()), deadline=123.0
    )
    assert result.addresses == ("93.184.216.34",)
    with pytest.raises(FetchError):
        await resolver.resolve_destination(
            replace(_PAGE, hostname="169.254.169.254"),
            resolver=_RESOLVER,
            gate=cast("NetworkGate", Mock()),
            deadline=123.0,
        )
    opened.assert_not_awaited()
