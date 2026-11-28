"""Actual host classes with synthetic custody and substituted effects, never native delivery."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from lychd.agents.router import Intent
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.scout.transport import FetchError
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding, WebcrawlerFeedMaterial
from lychd.domain.webcrawler.profile import WebcrawlerReviewRef, WebcrawlerWorkflowError
from lychd.system.services.scout_fetch import FetchedFeed
from lychd.system.services.webcrawler_workflow import WebcrawlerWorkflowService
from tests.webcrawler_feed_fixtures import install_effects, scenario


@pytest.mark.asyncio
async def test_feed_passage_selects_no_model_and_preserves_transient_identity_without_content_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = await scenario()
    fetch, extract, feed = install_effects(monkeypatch)
    assert await s.service.consent(run_id=s.run.run_id, binding=s.binding, review=s.review) == "granted"
    material = await s.service.acquire(run_id=s.run.run_id, binding=s.binding, review=s.review)
    assert type(material) is WebcrawlerFeedMaterial
    assert material.extraction is feed
    fetch.assert_awaited_once()
    extract.assert_awaited_once()
    assert fetch.call_args.kwargs["gate"] is not None
    assert extract.call_args.kwargs["media_type"] == "text/xml"
    assert s.settlement is not None
    assert s.settlement.child == "not_started"  # No real child in this controlled test.
    assert s.settlement.outcome == "succeeded"
    evidence = s.settlement.handoff_evidence
    for marker in (
        b"CHANNEL-SECRET",
        b"CHANNEL-SUMMARY",
        b"ITEM-TITLE-SECRET",
        b"ITEM-SUMMARY",
        b"PUBLISHER-ID",
        b"PUBLISHER-DATE",
        b"example.com/item",
    ):
        assert marker not in evidence
    s.service.authorize_feed_consume(run_id=s.run.run_id, binding=s.binding, review=s.review, material=material)
    for forged in (replace(material),):
        with pytest.raises(WebcrawlerWorkflowError):
            s.service.authorize_feed_consume(run_id=s.run.run_id, binding=s.binding, review=s.review, material=forged)
    with pytest.raises(WebcrawlerWorkflowError):
        cast("Any", s.service).authorize_consume(
            run_id=s.run.run_id, binding=s.binding, review=s.review, material=material, capability_key=None
        )
    with pytest.raises(WebcrawlerWorkflowError):
        await cast("Any", s.service).authorize_settle(
            run_id=s.run.run_id, binding=s.binding, review=s.review, receipt_id=material.receipt_id
        )
    with pytest.raises(WebcrawlerWorkflowError):
        await s.service.acquire(run_id=s.run.run_id, binding=s.binding, review=s.review)
    fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_feed_revocation_after_fetch_refuses_before_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    s = await scenario()
    fetch, extract, _ = install_effects(monkeypatch)
    page = fetch.return_value

    async def revoked(*args: Any, **kwargs: Any) -> FetchedFeed:
        await asyncio.sleep(0)
        s.access.revoke()
        return page

    fetch.side_effect = revoked
    with pytest.raises(FetchError):
        await s.service.acquire(run_id=s.run.run_id, binding=s.binding, review=s.review)
    extract.assert_not_awaited()
    assert s.settlement is not None
    assert s.settlement.outcome == "refused"
    s.store.unknown.assert_not_awaited()


@pytest.mark.asyncio
async def test_feed_consumer_and_review_substitution_refuse_even_with_actual_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = await scenario()
    install_effects(monkeypatch)
    material = await s.service.acquire(run_id=s.run.run_id, binding=s.binding, review=s.review)
    document = s.binding.model_dump(mode="json")
    document["consumer"]["seed_digest"] = "f" * 64
    other = WebcrawlerFeedBinding.model_validate(document)
    with pytest.raises(WebcrawlerWorkflowError):
        s.service.authorize_feed_consume(run_id=s.run.run_id, binding=other, review=s.review, material=material)
    for field, value in (("consent_id", uuid4()), ("native_binding_digest", "f" * 64), ("attempt_id", uuid4())):
        review = WebcrawlerReviewRef.model_validate(s.review.model_dump() | {field: value})
        with pytest.raises(WebcrawlerWorkflowError):
            s.service.authorize_feed_consume(run_id=s.run.run_id, binding=s.binding, review=review, material=material)
    s.access.revoke()
    with pytest.raises(FetchError):
        s.service.authorize_feed_consume(run_id=s.run.run_id, binding=s.binding, review=s.review, material=material)


@pytest.mark.asyncio
async def test_feed_binding_keeps_original_expiry_and_reconstruction_never_refetches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = await scenario()
    fetch, _extract, _ = install_effects(monkeypatch)
    assert await s.service.prepare(run_id=s.run.run_id, binding=s.binding) == s.review
    s.store.prepare.assert_awaited_once()
    await s.service.acquire(run_id=s.run.run_id, binding=s.binding, review=s.review)
    fresh = WebcrawlerWorkflowService(
        store=s.store,
        completions=s.completions,
        ledger=s.ledger,
        consents=s.consents,
        profile=s.binding.profile,
        capability_key=None,
        authorizer=s.authorizer,
        fence=RunEffectFence(),
    )
    with pytest.raises(WebcrawlerWorkflowError):
        await fresh.acquire(run_id=s.run.run_id, binding=s.binding, review=s.review)
    fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_feed_issuer_requires_actual_marker_exact_source_and_fresh_deadline() -> None:
    s = await scenario()
    for marker in (None, replace(s.authentication), Mock()):
        with pytest.raises(WebcrawlerWorkflowError):
            s.admission.declare(
                consumer=s.binding.consumer,
                request_id=uuid4(),
                deadline=datetime.now(UTC) + timedelta(seconds=30),
                authentication=marker,
            )
    for deadline in (datetime.now(UTC) - timedelta(seconds=1), datetime(2026, 1, 1)):  # noqa: DTZ001 - Deliberately challenge a missing deadline timezone.
        with pytest.raises(WebcrawlerWorkflowError):
            s.admission.declare(
                consumer=s.binding.consumer, request_id=uuid4(), deadline=deadline, authentication=s.authentication
            )
    deadline = datetime.now(UTC) + timedelta(seconds=30)
    proof = s.admission.declare(
        consumer=s.binding.consumer, request_id=uuid4(), deadline=deadline, authentication=s.authentication
    )
    assert proof.expires_at == deadline
    for intent in (
        Intent(session_id=s.run.session_id, prompt=str(s.binding.consumer.application_admission_id), source="bridge"),
        Intent(session_id=s.run.session_id, prompt=str(uuid4()), source="scavenger"),
    ):
        with pytest.raises(WebcrawlerWorkflowError):
            s.admission(intent, proof, s.binding.profile)
    s.access.revoke()
    with pytest.raises(WebcrawlerWorkflowError):
        s.admission(s.run.to_intent(), proof, s.binding.profile)


@pytest.mark.asyncio
async def test_feed_prepare_rechecks_fence_after_awaited_request_lookup() -> None:
    s = await scenario()

    async def fenced(_request: UUID) -> None:
        await asyncio.sleep(0)
        s.service.fence(s.run.run_id, "cancelled")

    s.store.read_request.side_effect = fenced
    with pytest.raises(WebcrawlerWorkflowError):
        await s.service.prepare(run_id=s.run.run_id, binding=s.binding)
    s.store.prepare.assert_awaited_once()


@pytest.mark.asyncio
async def test_feed_profile_refuses_any_placeholder_capability_before_use() -> None:
    s = await scenario()
    with pytest.raises(WebcrawlerWorkflowError):
        WebcrawlerWorkflowService(
            store=s.store,
            completions=s.completions,
            ledger=s.ledger,
            consents=s.consents,
            profile=s.binding.profile,
            capability_key="fake:chat",
            authorizer=s.authorizer,
            fence=RunEffectFence(),
        )
