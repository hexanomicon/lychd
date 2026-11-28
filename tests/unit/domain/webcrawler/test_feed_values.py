"""Synthetic feed admission shapes; no authentication, claim or native effect proof."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from lychd.domain.scout.attempts import (
    SCOUT_FEED_PURPOSE,
    SCOUT_FEED_URL,
    LocatorInfluence,
    LocatorSource,
    PublicLocatorDeclaration,
    ScoutAllowance,
    ScoutBudgetLimits,
    ScoutFeedConsumer,
    ScoutFeedPreparation,
    ScoutPreparation,
    document_digest,
)
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding, WebcrawlerFeedProfile
from lychd.domain.webcrawler.feed_review import feed_review
from lychd.domain.webcrawler.profile import WebcrawlerBinding, WebcrawlerProfile, WebcrawlerWorkflowError

if TYPE_CHECKING:
    from lychd.db.models.run import Run
    from lychd.db.models.webcrawler import WebcrawlerAttempt


def fixture() -> tuple[ScoutFeedPreparation, WebcrawlerFeedBinding]:
    now = datetime(2026, 10, 18, 2, tzinfo=UTC)
    source = UUID(int=1)
    declaration = PublicLocatorDeclaration(
        url=SCOUT_FEED_URL,
        subject="synthetic-feed-operator",
        authentication_generation=UUID(int=2),
        purpose=SCOUT_FEED_PURPOSE,
        source_manifest=(LocatorSource(source_id=source, url=SCOUT_FEED_URL),),
        influence_manifest=(LocatorInfluence(source_id=source),),
        policy_revision=1,
        declared_at=now,
    )
    allowance = ScoutAllowance(connects=3, transmissions=20, wire_bytes=10000)
    profile = WebcrawlerFeedProfile(
        binding_id="synthetic-feed",
        policy_revision=1,
        revocation_generation=0,
        resolver_address="127.0.0.1",
        resolver_custody_statement="Synthetic resolver assertion, no custody proof.",
        ca_file=Path("/fixture/ca"),
        bwrap=Path("/fixture/bwrap"),
        python_root=Path("/fixture/python"),
        libraries=(),
        allowance=allowance,
        budget_limits=ScoutBudgetLimits(host=allowance, binding=allowance),
    )
    consumer = ScoutFeedConsumer(
        application_admission_id=UUID(int=3),
        application_request_digest="3" * 64,
        seed_digest="4" * 64,
        initial_filter_digest="5" * 64,
    )
    binding = WebcrawlerFeedBinding(
        profile=profile,
        declaration=declaration,
        consumer=consumer,
        request_id=UUID(int=4),
        expires_at=now + timedelta(minutes=5),
    )
    preparation = ScoutFeedPreparation(
        consumer=consumer,
        request_id=binding.request_id,
        attempt_id=UUID(int=5),
        run_id=UUID(int=6),
        enqueue_seq=0,
        sigil_name="magus",
        pattern_digest="6" * 64,
        intent_digest="7" * 64,
        subject=declaration.subject,
        authentication_generation=declaration.authentication_generation,
        declaration=declaration,
        url=declaration.url,
        binding_digest=profile.binding_digest,
        configuration_digest=profile.configuration_digest,
        resolver_address=profile.resolver_address,
        resolver_port=profile.resolver_port,
        resolver_custody_digest=profile.resolver_custody_digest,
        resolver_custody_statement=profile.resolver_custody_statement,
        policy_revision=1,
        revocation_generation=0,
        expires_at=now + timedelta(minutes=5),
        allowance=allowance,
    )
    return preparation, binding


def test_distinct_feed_encoding_has_explicit_no_model_and_reference_only_consumer() -> None:
    preparation, binding = fixture()
    assert preparation.capability_key is None
    assert preparation.model_dump(mode="json")["capability_key"] is None
    assert preparation.schema_version == "scout.feed-preparation@1"
    assert ScoutFeedPreparation.model_validate_json(preparation.canonical_bytes()) == preparation
    assert preparation.consumer.digest == document_digest(binding.consumer.model_dump(mode="json"))
    assert set(preparation.consumer.model_dump()) == {
        "composition",
        "composition_revision",
        "pattern",
        "pattern_revision",
        "observation_profile",
        "projection",
        "retention",
        "filter_revision",
        "application_admission_id",
        "application_request_digest",
        "seed_digest",
        "initial_filter_digest",
    }
    for old, document in (
        (ScoutPreparation, preparation.model_dump(mode="json")),
        (WebcrawlerBinding, binding.model_dump(mode="json")),
        (WebcrawlerProfile, binding.profile.model_dump(mode="json")),
    ):
        with pytest.raises(ValidationError):
            old.model_validate(document)
    assert "synthetic-feed-operator" not in repr(preparation)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("capability_key", "fake:chat"),
        ("capability_key", ""),
        ("profile", "static-public-page@1"),
        ("provider_id", "other"),
        ("workflow_name", "bridge_chat"),
        ("purpose", "scout:answer-public-page"),
        ("schema_version", "scout.feed-preparation@2"),
        ("url", SCOUT_FEED_URL + "&extra=1"),
        ("seed", "copied seed"),
        ("question", "fake model question"),
    ],
)
def test_feed_preparation_refuses_model_page_mixed_or_unknown_values(field: str, value: Any) -> None:
    preparation, _binding = fixture()
    with pytest.raises(ValidationError):
        ScoutFeedPreparation.model_validate(preparation.model_dump(mode="json") | {field: value})


@pytest.mark.parametrize("field", ["seed", "filter", "items", "capability_key", "unknown"])
def test_reference_consumer_rejects_payload_and_unknown_fields(field: str) -> None:
    preparation, binding = fixture()
    with pytest.raises(ValidationError):
        ScoutFeedConsumer.model_validate(preparation.consumer.model_dump(mode="json") | {field: "content"})
    with pytest.raises(ValidationError):
        WebcrawlerFeedBinding.model_validate(binding.model_dump(mode="json") | {field: "content"})


@pytest.mark.parametrize("field", ["pattern", "pattern_revision", "composition", "retention", "projection"])
def test_first_consumer_contract_has_no_nearby_route_or_custody_fallback(field: str) -> None:
    preparation, _binding = fixture()
    with pytest.raises(ValidationError):
        ScoutFeedConsumer.model_validate(preparation.consumer.model_dump(mode="json") | {field: "other"})


def test_native_feed_review_has_new_identity_complete_retention_and_no_payload() -> None:
    preparation, _binding = fixture()
    native, document = feed_review(preparation)
    assert native.review_profile == "webcrawler.public-feed"
    assert native.review_producer == "webcrawler.public-feed-review"
    assert native.review_profile_revision == native.review_producer_revision == "1"
    assert native.preparation_digest == preparation.digest
    assert native.review_digest == document.digest
    facts = {fact.key: fact.value for fact in document.facts}
    assert facts["url"] == SCOUT_FEED_URL
    assert "No model call" in facts["model"]
    assert "1 MiB" in facts["limits"]
    assert "256 KiB" in facts["retention"]
    assert "personal data" in facts["retention"]
    assert "terminal" in facts["retention"]
    assert "never refetched" in facts["recovery"]
    assert "backup erasure" in facts["receipts"]
    assert facts["seed_binding"] == preparation.consumer.seed_digest
    assert facts["filter_binding"] == preparation.consumer.initial_filter_digest
    assert document.canonical_bytes() == feed_review(preparation)[1].canonical_bytes()
    changed = preparation.model_dump(mode="json")
    changed["consumer"]["seed_digest"] = "8" * 64
    changed_native, _ = feed_review(ScoutFeedPreparation.model_validate(changed))
    assert changed_native.audience_digest != native.audience_digest
    assert changed_native.preparation_digest != native.preparation_digest


@pytest.mark.parametrize("field", ["max_context_chars", "capability_key", "model", "temperature"])
def test_feed_host_profile_has_no_chat_configuration(field: str) -> None:
    _preparation, binding = fixture()
    with pytest.raises(ValidationError):
        WebcrawlerFeedProfile.model_validate(binding.profile.model_dump(mode="json") | {field: 1})


def test_binding_refuses_another_url_even_with_self_consistent_declaration() -> None:
    _preparation, binding = fixture()
    document = binding.model_dump(mode="json")
    other = SCOUT_FEED_URL + "&other=1"
    document["declaration"]["url"] = other
    document["declaration"]["source_manifest"][0]["url"] = other
    with pytest.raises((ValidationError, WebcrawlerWorkflowError)):
        WebcrawlerFeedBinding.model_validate(document)


def test_closed_decoder_refuses_ambiguous_mixed_and_noncanonical_preparations() -> None:
    from lychd.domain.scout.attempts import decode_scout_preparation

    preparation, _ = fixture()
    raw = preparation.canonical_bytes()
    assert decode_scout_preparation(raw) == preparation
    for invalid in (
        raw + b" ",
        raw.replace(b'"capability_key":null', b'"capability_key":null,"capability_key":null'),
        b"[]",
        b"\xff",
    ):
        with pytest.raises(ValueError, match="Scout preparation encoding differs"):
            decode_scout_preparation(invalid)


def retained_fixture() -> tuple[ScoutFeedPreparation, Run, WebcrawlerAttempt]:
    from lychd.db.models.run import Run
    from lychd.db.models.webcrawler import WebcrawlerAttempt

    preparation, binding = fixture()
    # This is an explicit synthetic manifest, not registered/executable Graph evidence.
    manifest = {"key": "scavenger.observe_market", "revision": "2", "synthetic": True}
    intent = {"admitted_capability_key": None, "admitted_scout": binding.model_dump(mode="json")}
    preparation = ScoutFeedPreparation.model_validate(
        preparation.model_dump(mode="json")
        | {"pattern_digest": document_digest(manifest), "intent_digest": document_digest(intent)}
    )
    run = Run(
        id=preparation.run_id,
        workflow_name=preparation.workflow_name,
        pattern_manifest=manifest,
        sigil_name=preparation.sigil_name,
        source="scavenger",
        status="running",
        capability_key=None,
        enqueue_seq=0,
        queue_name="runs",
        priority=50,
        intent=intent,
    )
    native, document = feed_review(preparation)
    row = WebcrawlerAttempt(
        id=preparation.attempt_id,
        request_id=preparation.request_id,
        run_id=preparation.run_id,
        consent_id=UUID(int=9),
        preparation_enqueue_seq=0,
        preparation_bytes=preparation.canonical_bytes(),
        preparation_digest=preparation.digest,
        native_binding=native.document(),
        review_bytes=document.canonical_bytes(),
        status="prepared",
        claim_id=None,
        execution_enqueue_seq=None,
        receipt_id=None,
        settlement_bytes=None,
    )
    return preparation, run, row


def test_same_store_snapshot_reproduces_exact_feed_review_and_reference_binding() -> None:
    from lychd.db.webcrawler import _snapshot, _validate_run  # pyright: ignore[reportPrivateUsage]
    from lychd.domain.webcrawler.review import webcrawler_review

    preparation, run, row = retained_fixture()
    _validate_run(run, preparation)
    snapshot = _snapshot(row)
    assert snapshot.preparation == preparation
    assert snapshot.native_binding == webcrawler_review(preparation)[0]
    assert snapshot.status == "prepared"


@pytest.mark.parametrize("change", ["consumer", "capability", "source", "manifest"])
def test_store_refuses_nearby_consumer_even_after_retained_json_is_rehashed(change: str) -> None:
    from lychd.db.webcrawler import _validate_run  # pyright: ignore[reportPrivateUsage]
    from lychd.domain.scout.attempts import ScoutConflictError

    preparation, run, _ = retained_fixture()
    if change == "consumer":
        run.intent["admitted_scout"]["consumer"]["seed_digest"] = "f" * 64
    elif change == "capability":
        run.capability_key = "fake:model"
    elif change == "source":
        run.source = "bridge"
    else:
        run.pattern_manifest["revision"] = "1"
    preparation = ScoutFeedPreparation.model_validate(
        preparation.model_dump(mode="json")
        | {"pattern_digest": document_digest(run.pattern_manifest), "intent_digest": document_digest(run.intent)}
    )
    with pytest.raises(ScoutConflictError):
        _validate_run(run, preparation)


@pytest.mark.asyncio
async def test_actual_current_authorizer_accepts_only_live_feed_binding_and_fixed_rss_request() -> None:
    from unittest.mock import Mock

    from lychd.domain.codex.local_access import LocalOperatorAccess
    from lychd.domain.cortex.cancellation import RunEffectFence
    from lychd.domain.scout.attempts import NewScoutClaim
    from lychd.domain.scout.authority import ScoutAction, ScoutHostAuthorizer, ScoutHostPolicy, ScoutNetworkAuthority
    from lychd.domain.scout.destination import preflight_destination
    from lychd.domain.scout.transport import FetchError, NetworkHandoff
    from tests.unit.domain.webcrawler.test_authority import _origin  # pyright: ignore[reportPrivateUsage]

    credential = "synthetic-new-feed-credential"
    access = LocalOperatorAccess(access_password=credential)
    authentication = access.authenticate(username=b"magus", password=credential.encode())
    assert authentication is not None
    preparation, _ = fixture()
    document = preparation.model_dump(mode="json")
    now = datetime.now(UTC)
    document["declaration"].update(
        subject=authentication.subject,
        authentication_generation=str(authentication.authentication_generation),
        declared_at=now.isoformat(),
    )
    document.update(
        subject=authentication.subject,
        authentication_generation=str(authentication.authentication_generation),
        expires_at=(now + timedelta(seconds=30)).isoformat(),
    )
    preparation = ScoutFeedPreparation.model_validate(document)
    authorizer = ScoutHostAuthorizer(
        access=access,
        policy=ScoutHostPolicy(
            policy_revision=preparation.policy_revision,
            revocation_generation=preparation.revocation_generation,
            actions=frozenset(ScoutAction),
            purposes=frozenset({preparation.purpose}),
            categories=frozenset({"public-web-locator"}),
            binding_digests=frozenset({preparation.binding_digest}),
            resolver_custody_digests=frozenset({preparation.resolver_custody_digest}),
        ),
    )
    assert authorizer.authorize(ScoutAction.CONSUME, preparation).allowed
    fence = RunEffectFence()
    network = ScoutNetworkAuthority(authorizer=authorizer, fence=fence)
    claim = NewScoutClaim(
        preparation=preparation, consent_id=UUID(int=8), enqueue_seq=0, claim_id=UUID(int=9), committed_at=now
    )
    # Synthetic claim and substituted handoffs; there is no store issuance or syscall.
    gate = network.activate(claim)
    target = _origin(gate, claim)
    candidate = preflight_destination(SCOUT_FEED_URL)
    from lychd.domain.scout.authority import _rss_http_request  # pyright: ignore[reportPrivateUsage]

    expected = b"GET /rss.php?rub=pc HTTP/1.1\r\nHost: www.bazos.sk\r\nAccept: application/rss+xml,application/xml,text/xml\r\nAccept-Encoding: gzip, identity\r\nConnection: close\r\n\r\n"
    assert _rss_http_request(candidate) == expected
    assert gate.handoff(NetworkHandoff(target, "tls", b"hello", None), lambda: 5) == 5
    assert gate.handoff(NetworkHandoff(target, "http", b"cipher", expected), lambda: 6) == 6
    access.revoke()
    action = Mock(return_value=1)
    with pytest.raises(FetchError):
        gate.handoff(NetworkHandoff(target, "tls", b"x", None), action)
    action.assert_not_called()
    assert not authorizer.authorize(ScoutAction.CONSUME, preparation).allowed
    with pytest.raises(FetchError):
        network.activate(claim)
    gate.seal()
