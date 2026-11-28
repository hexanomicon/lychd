"""Executable Graph with actual Webcrawler coordinator; acquisition and app custody substituted."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, replace
from typing import Any, cast
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from pydantic_graph import GraphRunContext

from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.observe_market import (
    OBSERVE_MARKET,
    AcquireMarketField,
    AwaitFeedConsent,
    FinishMarketObservation,
    ObserveMarketState,
    PrepareFeedReview,
)
from lychd.compositions.scavenger.ports import ObservationCommit
from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.cortex.runs import ConsentPending, RunParked
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding, WebcrawlerFeedMaterial
from lychd.domain.webcrawler.profile import WebcrawlerReviewRef, WebcrawlerWorkflowCode, WebcrawlerWorkflowError
from tests.agents.conftest import make_services
from tests.agents.fakes import FakeConsents, FakeEvents, FakeOrchestrator, FakeTurns
from tests.webcrawler_feed_fixtures import Scenario, install_effects, scenario


class NoTransition:
    async def handle_transition(self, *_args: Any, **_kwargs: Any) -> None:
        msg = "A model-free feed must never request a hardware transition."
        raise AssertionError(msg)


class App:
    """Process-only receiving substitute: no PostgreSQL or durable adoption proof."""

    def __init__(self, source: Scenario) -> None:
        self.source = source
        self.value: ObservationCommit | None = None
        self.adoptions = 0
        self.lose_ack = False
        self.revoke_during_adoption = False

    def current(self, run_id: str, binding: WebcrawlerFeedBinding) -> None:
        if (
            not self.source.access.current(self.source.authentication)
            or run_id != self.source.run.run_id
            or binding != self.source.binding
        ):
            raise WebcrawlerWorkflowError(WebcrawlerWorkflowCode.BINDING)

    async def committed(self, *, run_id: str, binding: WebcrawlerFeedBinding) -> ObservationCommit | None:
        await asyncio.sleep(0)
        self.current(run_id, binding)
        return self.value

    async def adopt(
        self,
        *,
        run_id: str,
        binding: WebcrawlerFeedBinding,
        review: WebcrawlerReviewRef,
        material: WebcrawlerFeedMaterial,
    ) -> ObservationCommit:
        await asyncio.sleep(0)
        if self.revoke_during_adoption:
            self.source.access.revoke()
        self.current(run_id, binding)
        self.source.service.authorize_feed_consume(run_id=run_id, binding=binding, review=review, material=material)
        self.adoptions += 1
        self.value = ObservationCommit(
            admission_id=binding.consumer.application_admission_id,
            observation_id=uuid4(),
            run_id=UUID(run_id),
            observation_digest="c" * 64,
            field_digest="d" * 64,
            item_count=len(material.extraction.items),
        )
        if self.lose_ack:
            msg = "Synthetic lost application commit acknowledgement."
            raise ConnectionError(msg)
        return self.value


@dataclass
class Setup:
    source: Scenario
    app: App
    ctx: GraphRunContext[ObserveMarketState, WorkflowServices]
    forbidden: Mock


async def setup() -> Setup:
    source = await scenario()
    app, forbidden = App(source), Mock(side_effect=AssertionError("No model, lease, transition or history expected."))
    services = replace(
        make_services(
            model=object(),
            events=FakeEvents(),
            turns=FakeTurns(),
            consents=FakeConsents(),
            orchestrator=FakeOrchestrator(),
        ),
        feed_webcrawler=source.service,
        scavenger=app,
    )
    # These are explicit negative controls, never substitute native effect evidence.
    services = replace(services, dispatcher=forbidden, orchestrator=forbidden, turns=forbidden, forge=forbidden)
    state = cast("ObserveMarketState", OBSERVE_MARKET.make_state(source.run.to_intent()))
    return Setup(source, app, GraphRunContext(state=state, deps=services), forbidden)


@pytest.mark.asyncio
async def test_actual_graph_parks_and_restores_consent_then_commits_only_reference_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = await setup()
    fetch, extract, _ = install_effects(monkeypatch)
    granted = s.source.consents.get.return_value
    s.source.consents.get.return_value = replace(granted, status="pending")
    memory = InMemoryStasisStore()
    validator = OBSERVE_MARKET.validate_state
    assert validator is not None
    runner = GraphRunner[ObserveMarketState](
        orchestrator=NoTransition(),
        persistence=DurableStasisPhylactery(job_id=s.source.run.run_id, store=memory),
        signal_priority=50,
        run_id=s.source.run.run_id,
        validate_state=lambda state: validator(s.source.run.to_intent(), state),
    )
    assert OBSERVE_MARKET.durable
    parked = await runner.run_graph(OBSERVE_MARKET.graph, PrepareFeedReview(), s.ctx.state, deps=s.ctx.deps)
    assert isinstance(parked, RunParked)
    assert parked.tool_name == "webcrawler.public-feed"
    fetch.assert_not_awaited()
    s.source.consents.get.return_value = granted
    result = await runner.resume_graph(OBSERVE_MARKET.graph, deps=s.ctx.deps)
    assert type(result) is ObservationCommit
    assert result == s.app.value
    assert s.app.adoptions == 1
    fetch.assert_awaited_once()
    extract.assert_awaited_once()
    assert s.forbidden.mock_calls == []
    wire = json.dumps(await memory.load(s.source.run.run_id))
    for excluded in ["ITEM-TITLE-SECRET", "ITEM-SUMMARY", "CHANNEL-SECRET", "PUBLISHER-ID", "PUBLISHER-DATE"]:
        assert excluded not in wire
    for excluded in ['"seed":', '"filter":', '"items":']:
        assert excluded not in wire


@pytest.mark.asyncio
async def test_lost_commit_ack_resolves_exact_retained_reference_without_second_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = await setup()
    fetch, _, _ = install_effects(monkeypatch)
    await PrepareFeedReview().run(s.ctx)
    s.app.lose_ack = True
    with pytest.raises(ConnectionError, match="Synthetic lost"):
        await AcquireMarketField().run(s.ctx)
    assert s.ctx.state.commit is None
    payload = s.ctx.state.model_dump(mode="json")
    assert payload["scout"] == s.ctx.state.webcrawler.model_dump(mode="json")
    assert "webcrawler" not in payload
    restored = ObserveMarketState.model_validate(payload)
    ctx = GraphRunContext(state=restored, deps=s.ctx.deps)
    await AcquireMarketField().run(ctx)
    result = await FinishMarketObservation().run(ctx)
    assert result.data == s.app.value
    assert s.app.adoptions == 1
    fetch.assert_awaited_once()
    # Even entry from the initial station resolves committed custody first.
    assert isinstance(await PrepareFeedReview().run(ctx), FinishMarketObservation)
    fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_lost_material_without_commit_never_refetches(monkeypatch: pytest.MonkeyPatch) -> None:
    s = await setup()
    fetch, _, _ = install_effects(monkeypatch)
    await PrepareFeedReview().run(s.ctx)
    assert s.ctx.state.review is not None
    await s.source.service.acquire(run_id=s.source.run.run_id, binding=s.source.binding, review=s.ctx.state.review)
    with pytest.raises(WebcrawlerWorkflowError) as error:
        await AcquireMarketField().run(s.ctx)
    assert error.value.code is WebcrawlerWorkflowCode.MATERIAL_UNAVAILABLE
    assert s.app.value is None
    assert s.app.adoptions == 0
    fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_denial_and_current_revocation_do_not_commit_or_request_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = await setup()
    fetch, _, _ = install_effects(monkeypatch)
    await PrepareFeedReview().run(s.ctx)
    granted = s.source.consents.get.return_value
    s.source.consents.get.return_value = replace(granted, status="denied")
    with pytest.raises(WebcrawlerWorkflowError):
        await AwaitFeedConsent().run(s.ctx)
    fetch.assert_not_awaited()
    s.source.consents.get.return_value = granted
    s.app.revoke_during_adoption = True
    with pytest.raises(WebcrawlerWorkflowError):
        await AcquireMarketField().run(s.ctx)
    fetch.assert_awaited_once()
    assert s.app.value is None
    assert s.app.adoptions == 0
    assert s.forbidden.mock_calls == []


@pytest.mark.asyncio
async def test_state_tampering_and_forged_commit_do_not_supply_application_authority() -> None:
    s = await setup()
    validator = OBSERVE_MARKET.validate_state
    assert validator is not None
    validator(s.source.run.to_intent(), s.ctx.state)
    with pytest.raises(WebcrawlerWorkflowError):
        validator(s.source.run.to_intent(), s.ctx.state.model_copy(update={"run_id": uuid4()}))
    s.ctx.state.commit = ObservationCommit(
        admission_id=s.source.binding.consumer.application_admission_id,
        observation_id=uuid4(),
        run_id=UUID(s.source.run.run_id),
        observation_digest="c" * 64,
        field_digest="d" * 64,
        item_count=1,
    )
    with pytest.raises(WebcrawlerWorkflowError):
        await FinishMarketObservation().run(s.ctx)
    s.source.access.revoke()
    with pytest.raises(WebcrawlerWorkflowError):
        await PrepareFeedReview().run(s.ctx)


@pytest.mark.asyncio
async def test_pending_consent_stays_explicit_and_wrong_admission_refuses() -> None:
    s = await setup()
    await PrepareFeedReview().run(s.ctx)
    granted = s.source.consents.get.return_value
    s.source.consents.get.return_value = replace(granted, status="pending")
    with pytest.raises(ConsentPending):
        await AwaitFeedConsent().run(s.ctx)
    intent = s.source.run.to_intent()
    for changes in [{"source": "bridge"}, {"prompt": "copied seed"}, {"admitted_capability_key": "placeholder"}]:
        with pytest.raises(WebcrawlerWorkflowError):
            OBSERVE_MARKET.make_state(intent.model_copy(update=changes))
