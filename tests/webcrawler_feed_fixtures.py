"""Shared controlled feed fixture; no actual app custody, SQL, socket, child or provider."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from lychd.agents.router import Intent
from lychd.domain.codex.local_access import LocalOperatorAccess, LocalOperatorAuthentication
from lychd.domain.codex.schemas import ConsentView
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.cortex.runs import RunRecord, RunStatus
from lychd.domain.scout.attempts import (
    SCOUT_FEED_PURPOSE,
    SCOUT_FEED_URL,
    NewScoutClaim,
    ScoutAllowance,
    ScoutAttemptSnapshot,
    ScoutBudgetLimits,
    ScoutFeedConsumer,
    ScoutFeedPreparation,
    ScoutRunBinding,
    ScoutSettlement,
    document_digest,
)
from lychd.domain.scout.authority import ScoutAction, ScoutHostAuthorizer, ScoutHostPolicy
from lychd.domain.scout.destination import preflight_destination
from lychd.domain.scout.extraction import ExtractedFeed, FeedChannel, FeedItem
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding, WebcrawlerFeedProfile
from lychd.domain.webcrawler.profile import WebcrawlerReviewRef
from lychd.interface.web.webcrawler_feed_admission import WebcrawlerFeedAdmissionService
from lychd.system.scout_worker import RSS_STRATEGY, RSS_TRANSFORMATIONS
from lychd.system.services import webcrawler_workflow
from lychd.system.services.scout_fetch import FetchedFeed, FetchObservation
from lychd.system.services.webcrawler_workflow import WebcrawlerCompletions, WebcrawlerWorkflowService


@dataclass
class Scenario:
    access: LocalOperatorAccess
    authentication: LocalOperatorAuthentication
    authorizer: ScoutHostAuthorizer
    admission: WebcrawlerFeedAdmissionService
    binding: WebcrawlerFeedBinding
    run: RunRecord
    ledger: Mock
    store: Mock
    consents: Mock
    completions: WebcrawlerCompletions
    service: WebcrawlerWorkflowService
    review: WebcrawlerReviewRef
    snapshot: ScoutAttemptSnapshot
    settlement: ScoutSettlement | None = None


async def scenario() -> Scenario:
    credential = "synthetic-feed-coordinator-credential"
    access = LocalOperatorAccess(access_password=credential)
    authentication = access.authenticate(username=b"magus", password=credential.encode())
    assert authentication is not None
    allowance = ScoutAllowance(connects=3, transmissions=20, wire_bytes=10000)
    profile = WebcrawlerFeedProfile(
        binding_id="synthetic-feed-host",
        policy_revision=1,
        revocation_generation=0,
        resolver_address="127.0.0.1",
        resolver_custody_statement="Synthetic resolver assertion, no actual resolver or host proof.",
        ca_file=Path("/fixture/ca"),
        bwrap=Path("/fixture/bwrap"),
        python_root=Path("/fixture/python"),
        libraries=(),
        allowance=allowance,
        budget_limits=ScoutBudgetLimits(host=allowance, binding=allowance),
    )
    authorizer = ScoutHostAuthorizer(
        access=access,
        policy=ScoutHostPolicy(
            policy_revision=1,
            revocation_generation=0,
            actions=frozenset(ScoutAction),
            purposes=frozenset({SCOUT_FEED_PURPOSE}),
            categories=frozenset({"public-web-locator"}),
            binding_digests=frozenset({profile.binding_digest}),
            resolver_custody_digests=frozenset({profile.resolver_custody_digest}),
        ),
    )
    consumer = ScoutFeedConsumer(
        application_admission_id=uuid4(),
        application_request_digest="1" * 64,
        seed_digest="2" * 64,
        initial_filter_digest="3" * 64,
    )
    admission = WebcrawlerFeedAdmissionService(access=access, authorizer=authorizer, profile=profile)
    intent = Intent(session_id=str(uuid4()), prompt=str(consumer.application_admission_id), source="scavenger")
    proof = admission.declare(
        consumer=consumer,
        request_id=uuid4(),
        deadline=datetime.now(UTC) + timedelta(minutes=2),
        authentication=authentication,
    )
    binding = admission(intent, proof, profile)
    run = RunRecord(
        run_id=str(uuid4()),
        session_id=intent.session_id,
        workflow_name=consumer.pattern,
        pattern_manifest={"key": consumer.pattern, "revision": consumer.pattern_revision, "synthetic": True},
        source="scavenger",
        queue_name="runs",
        priority=50,
        status=RunStatus.RUNNING,
        prompt=intent.prompt,
        admitted_webcrawler=binding,
        admitted_capability_key=None,
        enqueue_seq=2,
    )
    ledger, store, consents = Mock(), Mock(), Mock()
    ledger.get = AsyncMock(return_value=run)
    store.read_run_binding = AsyncMock(
        return_value=ScoutRunBinding(
            run_id=UUID(run.run_id),
            enqueue_seq=run.enqueue_seq,
            sigil_name=run.sigil_name,
            workflow_name=run.workflow_name,
            pattern_digest=document_digest(run.pattern_manifest),
            intent_digest=document_digest(run.to_intent().model_dump(mode="json")),
        )
    )
    store.read_request = AsyncMock(return_value=None)
    store.read = AsyncMock()

    async def prepare(preparation: ScoutFeedPreparation, native: Any, review_bytes: bytes) -> ScoutAttemptSnapshot:
        assert type(preparation) is ScoutFeedPreparation
        assert preparation.capability_key is None
        assert preparation.consumer == consumer
        assert preparation.expires_at == binding.expires_at
        assert review_bytes
        snapshot = ScoutAttemptSnapshot(
            preparation=preparation, consent_id=uuid4(), native_binding=native, status="prepared"
        )
        store.read.return_value = snapshot
        store.read_request.return_value = snapshot
        return snapshot

    store.prepare = AsyncMock(side_effect=prepare)
    store.claim, store.settle, store.unknown = AsyncMock(), AsyncMock(), AsyncMock()
    completions = WebcrawlerCompletions()
    service = WebcrawlerWorkflowService(
        store=store,
        completions=completions,
        ledger=ledger,
        consents=consents,
        profile=profile,
        capability_key=None,
        authorizer=authorizer,
        fence=RunEffectFence(),
    )
    review = await service.prepare(run_id=run.run_id, binding=binding)
    snapshot = store.read.return_value
    s = Scenario(
        access,
        authentication,
        authorizer,
        admission,
        binding,
        run,
        ledger,
        store,
        consents,
        completions,
        service,
        review,
        snapshot,
    )
    consents.get = AsyncMock(
        return_value=ConsentView(
            id=str(snapshot.consent_id),
            run_id=run.run_id,
            tool_name="webcrawler.fetch_extract",
            status="granted",
            native_review_required=True,
            native_binding=snapshot.native_binding,
        )
    )

    async def claim(*args: Any, **kwargs: Any) -> NewScoutClaim | ScoutAttemptSnapshot:
        assert args == (snapshot.preparation.attempt_id, snapshot.preparation.digest)
        assert kwargs == {"enqueue_seq": run.enqueue_seq}
        if s.snapshot.status != "prepared":
            return s.snapshot
        s.snapshot = replace(s.snapshot, status="claimed")
        return NewScoutClaim(
            preparation=snapshot.preparation,
            consent_id=snapshot.consent_id,
            enqueue_seq=run.enqueue_seq,
            claim_id=uuid4(),
            committed_at=datetime.now(UTC),
        )

    async def settle(claim: NewScoutClaim, value: ScoutSettlement) -> ScoutAttemptSnapshot:
        # Exercise actual transient completion ownership; custody/SQL still substituted.
        completions.verify(claim, value)
        s.settlement = value
        s.snapshot = replace(
            s.snapshot,
            status=value.outcome,
            receipt_id=value.receipt_id,
            receipt_digest=sha256(value.model_dump_json().encode()).hexdigest(),
        )
        store.read.return_value = s.snapshot
        store.read_request.return_value = s.snapshot
        return s.snapshot

    store.claim.side_effect, store.settle.side_effect = claim, settle
    return s


def install_effects(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, AsyncMock, ExtractedFeed]:
    body = b"synthetic-feed-body-not-a-parser-proof"
    feed = ExtractedFeed(
        media_type="text/xml",
        channel=FeedChannel("CHANNEL-SECRET", "https://example.com/channel", "CHANNEL-SUMMARY"),
        items=(
            FeedItem("ITEM-TITLE-SECRET", "https://example.com/item", "ITEM-SUMMARY", "PUBLISHER-DATE", "PUBLISHER-ID"),
        ),
        omitted_elements=1,
        source_digest=sha256(body).hexdigest(),
        record_digest="a" * 64,
        strategy=RSS_STRATEGY,
        transformations=RSS_TRANSFORMATIONS,
    )
    observation = FetchObservation(
        candidate=preflight_destination(SCOUT_FEED_URL),
        addresses=("93.184.216.34",),
        peer="93.184.216.34",
        status=200,
        header_bytes=80,
        wire_body_bytes=len(body),
        encoded_body_bytes=len(body),
        decoded_body_bytes=len(body),
        http_response_digest="b" * 64,
    )
    fetch = AsyncMock(return_value=FetchedFeed("text/xml", body, (observation,)))
    extract = AsyncMock(return_value=feed)
    monkeypatch.setattr(webcrawler_workflow, "fetch_rss_feed", fetch)
    monkeypatch.setattr(webcrawler_workflow, "extract_rss_feed", extract)
    return fetch, extract, feed
