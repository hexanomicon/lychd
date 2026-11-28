"""Current authority with in-memory syscall substitutes, never network effects."""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import Mock
from uuid import uuid4

import dns.message
import pytest

from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.scout import authority
from lychd.domain.scout.attempts import (
    LocatorInfluence,
    LocatorSource,
    NewScoutClaim,
    PublicLocatorDeclaration,
    ScoutAllowance,
    ScoutPreparation,
    document_digest,
)
from lychd.domain.scout.authority import ScoutAction, ScoutHostAuthorizer, ScoutHostPolicy, ScoutNetworkAuthority
from lychd.domain.scout.destination import preflight_destination
from lychd.domain.scout.transport import FetchCode, FetchError, NetworkHandoff, NetworkTarget
from lychd.system.services.scout_http import serialize_get

if TYPE_CHECKING:
    from lychd.domain.scout.authority import CurrentNetworkGate

_URL = "https://example.com/page?value=private-fixture"
_DIGEST = "a" * 64
_CUSTODY = "Explicit local test resolver custody assertion."


def _setup(
    *,
    url: str = _URL,
    allowance: ScoutAllowance | None = None,
) -> tuple[LocalOperatorAccess, ScoutHostAuthorizer, RunEffectFence, ScoutNetworkAuthority, NewScoutClaim]:
    credential = "test-credential"
    access = LocalOperatorAccess(access_password=credential)
    authentication = access.authenticate(username=b"magus", password=credential.encode())
    assert authentication is not None
    now = datetime.now(UTC)
    source_id = uuid4()
    declaration = PublicLocatorDeclaration(
        url=url,
        subject=authentication.subject,
        authentication_generation=authentication.authentication_generation,
        purpose="answer",
        source_manifest=(LocatorSource(source_id=source_id, url=url),),
        influence_manifest=(LocatorInfluence(source_id=source_id),),
        policy_revision=1,
        declared_at=now,
    )
    preparation = ScoutPreparation(
        request_id=uuid4(),
        attempt_id=uuid4(),
        run_id=uuid4(),
        enqueue_seq=0,
        workflow_name="bridge_chat",
        sigil_name="not-an-authorizer",
        pattern_digest=_DIGEST,
        intent_digest=_DIGEST,
        subject=authentication.subject,
        authentication_generation=authentication.authentication_generation,
        declaration=declaration,
        url=url,
        provider_id="native-static",
        profile="static-https@1",
        capability_key="local-answer-model",
        binding_digest=_DIGEST,
        configuration_digest=_DIGEST,
        resolver_address="127.0.0.1",
        resolver_port=5353,
        resolver_custody_digest=document_digest(_CUSTODY),
        resolver_custody_statement=_CUSTODY,
        purpose="answer",
        policy_revision=1,
        revocation_generation=2,
        expires_at=now + timedelta(seconds=30),
        allowance=allowance or ScoutAllowance(connects=3, transmissions=256, wire_bytes=600_000),
    )
    policy = ScoutHostPolicy(
        policy_revision=1,
        revocation_generation=2,
        actions=frozenset(ScoutAction),
        purposes=frozenset({"answer"}),
        categories=frozenset({"public-web-locator"}),
        binding_digests=frozenset({_DIGEST}),
        resolver_custody_digests=frozenset({document_digest(_CUSTODY)}),
    )
    authorizer = ScoutHostAuthorizer(access=access, policy=policy)
    fence = RunEffectFence()
    network = ScoutNetworkAuthority(authorizer=authorizer, fence=fence)
    claim = NewScoutClaim(
        preparation=preparation, consent_id=uuid4(), enqueue_seq=1, claim_id=uuid4(), committed_at=now
    )
    return access, authorizer, fence, network, claim


def _resolver(claim: NewScoutClaim) -> NetworkTarget:
    prep = claim.preparation
    return NetworkTarget(
        prep.resolver_address, prep.resolver_port, preflight_destination(prep.url).hostname, "resolver"
    )


def _query(hostname: str, family: str = "A") -> bytes:
    wire = dns.message.make_query(hostname + ".", family, use_edns=False, id=1234).to_wire()
    return len(wire).to_bytes(2, "big") + wire


def _resolve(gate: CurrentNetworkGate, claim: NewScoutClaim) -> None:
    target = _resolver(claim)
    for family in ("A", "AAAA"):
        assert gate.handoff(NetworkHandoff(target, "connect", b"", None), lambda: 0) == 0
        data = _query(target.hostname, family)
        assert gate.handoff(NetworkHandoff(target, "dns", data, data), lambda data=data: len(data)) == len(data)


def _origin(gate: CurrentNetworkGate, claim: NewScoutClaim) -> NetworkTarget:
    candidate = preflight_destination(claim.preparation.url)
    if candidate.ip_literal is None:
        _resolve(gate, claim)
    target = NetworkTarget(candidate.ip_literal or "93.184.216.34", 443, candidate.hostname, "origin")
    gate.handoff(NetworkHandoff(target, "connect", b"", None), lambda: 0)
    return target


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url", [_URL, "https://EXAMPLE.com:443/?", "https://example.com/a//b?x=%2F", "https://8.8.8.8/"]
)
async def test_exact_native_disclosures_seal_truthful_snapshot(url: str) -> None:
    _, _, _, network, claim = _setup(url=url)
    gate = network.activate(claim)
    target = _origin(gate, claim)
    request = serialize_get(preflight_destination(url))
    for phase, wire, application in (
        ("tls", b"hello", None),
        ("http", b"ciphertext", request),
        ("tls", b"control", None),
    ):
        gate.handoff(NetworkHandoff(target, phase, wire, application), lambda wire=wire: len(wire))  # type: ignore[arg-type]
    snapshot = gate.seal()
    assert gate.seal() is snapshot
    assert snapshot.claim_id == claim.claim_id
    assert snapshot.preparation_digest == claim.preparation.digest
    assert snapshot.usage.connects == (1 if preflight_destination(url).ip_literal else 3)
    assert snapshot.usage.transmissions == (3 if preflight_destination(url).ip_literal else 5)
    assert snapshot.usage.wire_bytes == snapshot.accepted_wire_bytes
    assert all(item.outcome == "accepted" for item in snapshot.evidence)
    assert len(snapshot.evidence_bytes) < 256 * 1024
    action = Mock(return_value=1)
    with pytest.raises(FetchError):
        gate.handoff(NetworkHandoff(target, "tls", b"x", None), action)
    action.assert_not_called()
    for value in (url, target.address, target.hostname, _DIGEST, "test-credential"):
        assert value not in repr(snapshot)
        assert value not in repr(snapshot.evidence)


@pytest.mark.asyncio
async def test_action_authority_and_pre_run_classification_are_distinct() -> None:
    access, authorizer, _, _, claim = _setup()
    prep = claim.preparation
    authorizer.require_declaration(
        prep.declaration,
        binding_digest=_DIGEST,
        resolver_custody_digest=document_digest(_CUSTODY),
        revocation_generation=2,
    )
    for action in ScoutAction:
        decision = authorizer.authorize(action, prep)
        assert decision.allowed is True
        assert decision.action is action
        assert decision.preparation_digest == prep.digest
    authorizer.replace_policy(
        replace(
            authorizer._policy,
            actions=frozenset({ScoutAction.CLASSIFY_LOCATOR, ScoutAction.REVIEW}),
            revocation_generation=3,
        )
    )
    current = prep.model_copy(update={"revocation_generation": 3})
    assert authorizer.authorize(ScoutAction.REVIEW, current).allowed is True
    for action in (ScoutAction.JUDGE, ScoutAction.FETCH, ScoutAction.EXTRACT, ScoutAction.CONSUME):
        assert authorizer.authorize(action, current).allowed is False
    assert authorizer.authorize(ScoutAction.REVIEW, prep).allowed is False
    access.revoke()
    with pytest.raises(FetchError):
        authorizer.require_declaration(
            current.declaration,
            binding_digest=_DIGEST,
            resolver_custody_digest=document_digest(_CUSTODY),
            revocation_generation=3,
        )


@pytest.mark.asyncio
async def test_activation_is_one_use_and_failed_activation_cannot_be_retried() -> None:
    _, _, fence, network, claim = _setup()
    gate = network.activate(claim)
    gate.seal()
    with pytest.raises(FetchError):
        network.activate(replace(claim, consent_id=uuid4()))
    other = replace(claim, claim_id=uuid4())
    fence.fence_claim(str(claim.preparation.run_id), claim.enqueue_seq, "cancelled")
    with pytest.raises(FetchError):
        network.activate(other)
    assert other.claim_id in network._activated


@pytest.mark.asyncio
async def test_foreign_authentication_generation_has_no_sigil_fallback() -> None:
    _, authorizer, _, _, claim = _setup()
    prep = claim.preparation
    foreign = uuid4()
    declaration = prep.declaration.model_copy(update={"authentication_generation": foreign})
    stale = prep.model_copy(update={"declaration": declaration, "authentication_generation": foreign})
    for action in ScoutAction:
        assert authorizer.authorize(action, stale).allowed is False
    with pytest.raises(FetchError):
        authorizer.require_declaration(
            declaration,
            binding_digest=prep.binding_digest,
            resolver_custody_digest=prep.resolver_custody_digest,
            revocation_generation=prep.revocation_generation,
        )


def test_authority_and_gate_refuse_foreign_control_loop() -> None:
    async def original_loop() -> tuple[ScoutHostAuthorizer, ScoutNetworkAuthority, NewScoutClaim, CurrentNetworkGate]:
        _, authorizer, _, network, claim = _setup()
        return authorizer, network, claim, network.activate(claim)

    authorizer, network, claim, gate = asyncio.run(original_loop())
    action = Mock(return_value=0)

    async def foreign_loop() -> None:
        with pytest.raises(FetchError):
            authorizer.authorize(ScoutAction.FETCH, claim.preparation)
        with pytest.raises(FetchError):
            authorizer.replace_policy(replace(authorizer._policy, revocation_generation=3))
        with pytest.raises(FetchError):
            network.activate(replace(claim, claim_id=uuid4()))
        with pytest.raises(FetchError):
            gate.handoff(NetworkHandoff(_resolver(claim), "connect", b"", None), action)
        with pytest.raises(FetchError):
            gate.seal()

    asyncio.run(foreign_loop())
    action.assert_not_called()


@pytest.mark.asyncio
async def test_delayed_activation_uses_retained_claim_deadline() -> None:
    _, _, _, network, claim = _setup()
    delayed = replace(claim, committed_at=datetime.now(UTC) - timedelta(seconds=25))
    gate = network.activate(delayed)
    assert 0 < gate.deadline - authority.time.monotonic() <= 5
    expired = replace(claim, claim_id=uuid4(), committed_at=datetime.now(UTC) - timedelta(seconds=31))
    with pytest.raises(FetchError) as caught:
        network.activate(expired)
    assert caught.value.code is FetchCode.TIMEOUT
    assert expired.claim_id in network._activated


@pytest.mark.asyncio
@pytest.mark.parametrize("revoke", ["authentication", "policy", "claim", "run", "shutdown", "deadline"])
async def test_revocation_after_await_refuses_before_next_syscall(revoke: str, monkeypatch: pytest.MonkeyPatch) -> None:
    access, authorizer, fence, network, claim = _setup()
    gate = network.activate(claim)
    target = _origin(gate, claim)
    await asyncio.sleep(0)
    if revoke == "authentication":
        access.revoke()
    elif revoke == "policy":
        authorizer.replace_policy(replace(authorizer._policy, revocation_generation=3))
    elif revoke == "claim":
        fence.fence_claim(str(claim.preparation.run_id), claim.enqueue_seq, "worker_interrupted")
    elif revoke == "run":
        fence.fence(str(claim.preparation.run_id), "cancelled")
    elif revoke == "shutdown":
        fence.fence_all("shutdown")
    else:
        monkeypatch.setattr(authority.time, "monotonic", lambda: gate.deadline + 1)
    action = Mock(return_value=3)
    with pytest.raises(FetchError):
        gate.handoff(NetworkHandoff(target, "tls", b"tls", None), action)
    action.assert_not_called()
    assert gate.seal().evidence[-1].outcome == "refused"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"), [("address", "127.0.0.2"), ("port", 53), ("hostname", "other.example"), ("role", "origin")]
)
async def test_resolver_identity_substitution_refuses(field: str, value: object) -> None:
    _, _, _, network, claim = _setup()
    gate = network.activate(claim)
    action = Mock(return_value=0)
    with pytest.raises(FetchError):
        gate.handoff(NetworkHandoff(replace(_resolver(claim), **{field: value}), "connect", b"", None), action)
    action.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["host", "family", "flags", "tail", "frame"])
async def test_dns_question_substitution_refuses(mutation: str) -> None:
    _, _, _, network, claim = _setup()
    gate = network.activate(claim)
    target = _resolver(claim)
    gate.handoff(NetworkHandoff(target, "connect", b"", None), lambda: 0)
    data = _query("other.example" if mutation == "host" else target.hostname, "AAAA" if mutation == "family" else "A")
    if mutation == "flags":
        data = data[:4] + b"\x00" + data[5:]
    elif mutation == "tail":
        data += b"secret"
    elif mutation == "frame":
        data = b"\x00\x00" + data[2:]
    action = Mock(return_value=len(data))
    with pytest.raises(FetchError):
        gate.handoff(NetworkHandoff(target, "dns", data, data), action)
    action.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation", ["private", "hostname", "peer", "http", "tls_plaintext", "redirect", "extra_connect"]
)
async def test_origin_and_application_substitution_refuse(mutation: str) -> None:
    _, _, _, network, claim = _setup()
    gate = network.activate(claim)
    _resolve(gate, claim)
    target = NetworkTarget("127.0.0.1" if mutation == "private" else "93.184.216.34", 443, "example.com", "origin")
    handoff = NetworkHandoff(target, "connect", b"", None)
    if mutation == "hostname":
        handoff = replace(handoff, target=replace(target, hostname="other.example"))
    if mutation not in {"private", "hostname"}:
        gate.handoff(handoff, lambda: 0)
        handoff = NetworkHandoff(target, "http", b"cipher", serialize_get(preflight_destination(_URL)))
        if mutation == "peer":
            handoff = replace(handoff, target=replace(target, address="8.8.8.8"))
        elif mutation == "http":
            handoff = replace(handoff, application_bytes=b"POST /secret HTTP/1.1\r\n\r\n")
        elif mutation == "tls_plaintext":
            handoff = replace(handoff, phase="tls")
        elif mutation == "redirect":
            handoff = replace(
                handoff, application_bytes=serialize_get(preflight_destination("https://example.com/other"))
            )
        elif mutation == "extra_connect":
            handoff = NetworkHandoff(target, "connect", b"", None)
    action = Mock(return_value=0)
    with pytest.raises(FetchError):
        gate.handoff(handoff, action)
    action.assert_not_called()


@pytest.mark.asyncio
async def test_partial_send_and_would_block_refund_only_proved_unaccepted_bytes() -> None:
    _, _, _, network, claim = _setup()
    gate = network.activate(claim)
    target = _resolver(claim)
    gate.handoff(NetworkHandoff(target, "connect", b"", None), lambda: 0)
    data = _query(target.hostname)
    gate.handoff(NetworkHandoff(target, "dns", data, data), lambda: 3)
    remaining = NetworkHandoff(target, "dns", data[3:], data)
    blocked = Mock(side_effect=BlockingIOError("private-failure"))
    with pytest.raises(BlockingIOError) as caught:
        gate.handoff(remaining, blocked)
    assert "private-failure" not in str(caught.value)
    gate.handoff(remaining, lambda: len(data) - 3)
    snapshot = gate.seal()
    assert snapshot.usage.connects == 1
    assert snapshot.usage.transmissions == 3
    assert snapshot.usage.wire_bytes == len(data)
    assert snapshot.accepted_wire_bytes == len(data)
    assert [item.accepted_bytes for item in snapshot.evidence] == [0, 3, 0, len(data) - 3]


@pytest.mark.asyncio
async def test_uncertain_syscall_holds_offered_allowance_and_sanitizes_failure() -> None:
    _, _, _, network, claim = _setup()
    gate = network.activate(claim)
    target = _origin(gate, claim)
    offered = b"private-wire"
    before = gate._charged
    with pytest.raises(FetchError) as caught:
        gate.handoff(NetworkHandoff(target, "tls", offered, None), Mock(side_effect=OSError("private-error")))
    assert caught.value.code is FetchCode.TRANSPORT
    assert "private" not in repr(caught.value)
    snapshot = gate.seal()
    assert snapshot.usage.wire_bytes == before + len(offered)
    assert snapshot.accepted_wire_bytes == before
    assert snapshot.evidence[-1].outcome == "uncertain"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "allowance",
    [
        ScoutAllowance(connects=0, transmissions=10, wire_bytes=1000),
        ScoutAllowance(connects=3, transmissions=0, wire_bytes=1000),
        ScoutAllowance(connects=3, transmissions=10, wire_bytes=0),
    ],
)
async def test_reserved_counters_refuse_before_syscall(allowance: ScoutAllowance) -> None:
    _, _, _, network, claim = _setup(allowance=allowance)
    gate = network.activate(claim)
    target = _resolver(claim)
    action = Mock(return_value=0)
    connect = NetworkHandoff(target, "connect", b"", None)
    if allowance.connects:
        gate.handoff(connect, lambda: 0)
        data = _query(target.hostname)
        handoff = NetworkHandoff(target, "dns", data, data)
    else:
        handoff = connect
    with pytest.raises(FetchError) as caught:
        gate.handoff(handoff, action)
    assert caught.value.code is FetchCode.LIMIT
    action.assert_not_called()


@pytest.mark.asyncio
async def test_bounded_evidence_and_reentrant_actions() -> None:
    _, _, _, network, claim = _setup(url="https://8.8.8.8/")
    gate = network.activate(claim)
    target = _origin(gate, claim)
    packet = NetworkHandoff(target, "tls", b"x", None)
    for _ in range(authority._MAX_HANDOFFS - 1):
        gate.handoff(packet, lambda: 1)
    with pytest.raises(FetchError) as caught:
        gate.handoff(packet, lambda: 1)
    assert caught.value.code is FetchCode.LIMIT
    assert len(gate.seal().evidence_bytes) < 256 * 1024

    other = network.activate(replace(claim, claim_id=uuid4()))
    target = _origin(other, claim)
    packet = NetworkHandoff(target, "tls", b"x", None)
    inner = Mock(return_value=1)
    with pytest.raises(FetchError):
        other.handoff(packet, lambda: other.handoff(packet, inner))
    inner.assert_not_called()
    assert other.seal().evidence[-1].outcome == "uncertain"
