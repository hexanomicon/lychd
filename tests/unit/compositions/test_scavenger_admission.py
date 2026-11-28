"""Actual in-memory Engine with receiving custody substituted; no SQL or restart proof."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from lychd.agents.router import Intent
from lychd.agents.workflows import OBSERVE_MARKET, builtin_workflow_registry
from lychd.compositions.scavenger.schemas import CampaignSeed, LiteralFilter, ObserveMarketRequest, canonical, digest
from lychd.compositions.scavenger.services import LocalScavengerPolicy, ScavengerService
from lychd.config.settings import ScavengerCastingSettings, WeaverSettings
from lychd.db.scavenger import DbScavengerStore, ScavengerAdmission
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.sigil import default_local_sigil
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunDeliveryState
from lychd.domain.scout.attempts import ScoutFeedConsumer
from lychd.domain.web.orb import bridge_context_path, build_orb_snapshot
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding
from tests.unit.compositions.test_scavenger_values import seed_document
from tests.unit.domain.cortex.test_webcrawler_feed_admission import Queue
from tests.webcrawler_feed_fixtures import Scenario, scenario


class ReceivingPort:
    """Only the typed reservation/retention handoff; this is not a database oracle."""

    def __init__(self, request: ObserveMarketRequest, ledger: InMemoryRunLedger, queue: Queue) -> None:
        self.request, self.ledger, self.queue = request, ledger, queue
        self.consumer = ScoutFeedConsumer(
            application_admission_id=request.request_id,
            application_request_digest=digest(canonical(request)),
            seed_digest=request.seed.digest,
            initial_filter_digest=digest(canonical(request.initial_filter)),
        )
        self.binding: WebcrawlerFeedBinding | None = None
        self.run_id: UUID | None = None
        self.events: list[str] = []

    async def reserve(self, **kwargs: Any) -> ScavengerAdmission:
        kwargs["authorize"]()
        assert kwargs["request_id"] == self.request.request_id
        assert kwargs["seed"] == self.request.seed
        assert kwargs["selection"] == self.request.initial_filter
        self.events.append("reserve")
        return ScavengerAdmission(
            consumer=self.consumer,
            deadline=self.request.seed.deadline,
            run_id=self.run_id,
            status="bound" if self.run_id is not None else "reserved",
        )

    async def retain_run(self, **kwargs: Any) -> None:
        kwargs["authorize"]()
        run_id = str(kwargs["run_id"])
        run = await self.ledger.get(run_id)
        assert run is not None
        delivery = await self.ledger.get_delivery(run_id, enqueue_seq=run.enqueue_seq)
        assert delivery is not None
        assert delivery.state is RunDeliveryState.HELD
        assert self.queue.enqueued == []
        assert run.admitted_webcrawler == kwargs["binding"]
        kwargs["authorize"]()
        self.binding = kwargs["binding"]
        self.run_id = kwargs["run_id"]
        self.events.append("retain")


@dataclass
class Setup:
    source: Scenario
    request: ObserveMarketRequest
    store: ReceivingPort
    app: ScavengerService
    engine: RunEngine
    ledger: InMemoryRunLedger
    bus: InProcessEventBus
    queue: Queue


async def setup() -> Setup:
    s = await scenario()
    seed = CampaignSeed.model_validate(
        seed_document() | {"need": "UNIT-PRIVATE-NEED", "deadline": datetime.now(UTC) + timedelta(hours=1)}
    )
    request = ObserveMarketRequest(request_id=uuid4(), seed=seed, initial_filter=LiteralFilter(query="PRIVATE-FILTER"))
    ledger, bus, queue = InMemoryRunLedger(), InProcessEventBus(), Queue()
    store = ReceivingPort(request, ledger, queue)
    app = ScavengerService(
        store=cast("DbScavengerStore", store),
        policy=LocalScavengerPolicy(access=s.access, profile=s.binding.profile, owner="magus"),
        webcrawler=s.service,
    )
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(
            weaver=WeaverSettings(scavenger=ScavengerCastingSettings(revision="3", webcrawler=s.binding.profile))
        ),
        queue_router=QueueRouter({"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": queue},
        feed_webcrawler=s.binding.profile,
        feed_webcrawler_admission=s.admission,
        bridge_capability_key="ordinary:chat:unrelated",
    )
    return Setup(s, request, store, app, engine, ledger, bus, queue)


async def submit(s: Setup) -> Any:
    return await s.app.submit(
        s.request,
        authentication=s.source.authentication,
        principal=default_local_sigil(),
        engine=s.engine,
        admission=s.source.admission,
    )


@pytest.mark.asyncio
async def test_service_retains_before_publication_and_replays_one_app_scoped_run_without_bridge_session() -> None:
    s = await setup()
    try:
        first = await submit(s)
        replay = await submit(s)
        assert replay == first
        assert len(s.queue.enqueued) == 1
        assert s.store.events == ["reserve", "retain", "reserve"]
        run = await s.ledger.get(str(first.run_id))
        assert run is not None
        assert run.session_id == f"scavenger:{s.request.request_id}"
        assert run.admitted_capability_key is None
        wire = json.dumps(run.to_intent().model_dump(mode="json"))
        assert "UNIT-PRIVATE-NEED" not in wire
        assert "PRIVATE-FILTER" not in wire
        s.source.store.claim.assert_not_awaited()
    finally:
        await s.bus.aclose()


@pytest.mark.asyncio
async def test_held_replay_retains_winners_actual_binding_without_adopting_the_later_declaration() -> None:
    s = await setup()
    try:
        intent = Intent(
            session_id=f"scavenger:{s.request.request_id}",
            prompt=str(s.request.request_id),
            source="scavenger",
            sigil_name="magus",
            sigil_scopes=default_local_sigil().scopes,
        )
        original = s.source.admission.declare(
            consumer=s.store.consumer,
            request_id=s.request.request_id,
            deadline=s.request.seed.deadline,
            authentication=s.source.authentication,
        )
        binding = s.source.admission(intent, original, s.source.binding.profile)
        run, created = await s.ledger.create_idempotent(
            intent.model_copy(update={"admitted_webcrawler": binding}),
            idempotency_key=f"scavenger:{s.request.request_id}",
            workflow_name=OBSERVE_MARKET.name,
            pattern_manifest=OBSERVE_MARKET.manifest.snapshot(),
            queue_name="runs",
            priority=50,
            hold_delivery=True,
        )
        assert created
        await asyncio.sleep(0)
        declare = Mock(wraps=s.source.admission.declare)
        s.source.admission.declare = declare
        result = await submit(s)
        assert result.run_id == UUID(run.run_id)
        assert s.store.binding == binding
        assert s.store.binding is not None
        assert s.store.binding.declaration == original.declaration
        declare.assert_called_once()
        assert len(s.queue.enqueued) == 1
    finally:
        await s.bus.aclose()


@pytest.mark.asyncio
async def test_published_replay_with_fresh_application_marker_never_refreshes_the_acquisition() -> None:
    s = await setup()
    try:
        first = await submit(s)
        assert s.store.binding is not None
        original_binding = s.store.binding
        credential = "synthetic-restarted-application"
        current = LocalOperatorAccess(access_password=credential)
        marker = current.authenticate(username=b"magus", password=credential.encode())
        assert marker is not None
        assert marker.authentication_generation != s.source.authentication.authentication_generation
        s.app.policy.access = current
        forbidden = Mock(side_effect=AssertionError("A retained published Run must not get a fresh declaration."))
        s.source.admission.declare = forbidden
        replay = await s.app.submit(
            s.request,
            authentication=marker,
            principal=default_local_sigil(),
            engine=s.engine,
            admission=s.source.admission,
        )
        assert replay == first
        assert s.store.binding == original_binding
        assert len(s.queue.enqueued) == 1
        forbidden.assert_not_called()
    finally:
        await s.bus.aclose()


@pytest.mark.asyncio
async def test_app_run_orb_uses_retained_consumer_reference_without_inventing_a_bridge_session() -> None:
    s = await setup()
    admission = await submit(s)
    run = await s.ledger.get(str(admission.run_id))
    assert run is not None
    snapshot = await build_orb_snapshot(s.ledger, run)
    assert snapshot.run.bridge_path is None
    assert snapshot.run.application_path == f"/scavenger?observation={s.request.request_id}"
    assert "UNIT-PRIVATE-NEED" not in snapshot.model_dump_json()
    assert "PRIVATE-FILTER" not in snapshot.model_dump_json()
    assert bridge_context_path(run.session_id, run.workflow_name) is None
    assert bridge_context_path("existing-session", "ordinary-chat") == "/bridge/existing-session"
