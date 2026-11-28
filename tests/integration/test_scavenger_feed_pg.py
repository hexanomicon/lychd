"""Real PostgreSQL/worker/Graph custody; queue, fetch and extraction remain controlled.

Run only inside the explicit isolated-database campaign plan. No installed app,
actual network contact, child containment, model inference or browser is qualified.
"""

from __future__ import annotations

import asyncio
import json
import os
import ssl
from collections.abc import AsyncGenerator, AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
import pytest
import pytest_asyncio
from alembic import command
from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.datastructures import State
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lychd.agents.router import Intent
from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.agents.workflows.observe_market import OBSERVE_MARKET
from lychd.compositions.scavenger.schemas import (
    CampaignSeed,
    LiteralFilter,
    ObserveMarketRequest,
    ScavengerRefused,
)
from lychd.compositions.scavenger.services import LocalScavengerPolicy, ScavengerService
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings import ScavengerCastingSettings, Settings, WeaverSettings
from lychd.db.checkpoints import PostgresStasisStore
from lychd.db.models.run import Run as RunRow
from lychd.db.models.run_delivery import RunDelivery
from lychd.db.models.scavenger import ScavengerObservation
from lychd.db.models.session import Session as SessionRow
from lychd.db.models.webcrawler import WebcrawlerAttempt, WebcrawlerBudget
from lychd.db.scavenger import DbScavengerStore
from lychd.db.sessions import DbBridgeSessionStore
from lychd.db.webcrawler import DbWebcrawlerAttemptStore
from lychd.domain.codex.ledger import CodexConsentLedger
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.codex.sigil import Sigil, default_local_sigil
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.scout.attempts import SCOUT_FEED_URL, NewScoutClaim, ScoutSettlement
from lychd.domain.scout.destination import preflight_destination
from lychd.domain.web.contracts import CsrfClientContract
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding, WebcrawlerFeedProfile
from lychd.ghouls.runs import perform_run
from lychd.interface.api.scavenger import ScavengerController
from lychd.interface.web import AltarController, BridgeController, OrbController
from lychd.interface.web.altar_services import AltarServices, build_altar_services
from lychd.interface.web.deps import web_dependencies
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin
from lychd.interface.web.webcrawler_review import WebcrawlerConsentReviews
from lychd.system.services.scout_http import serialize_rss_get
from lychd.system.services.webcrawler_workflow import WebcrawlerCompletions, WebcrawlerWorkflowService
from tests import scout_network_fixture as network
from tests.agents.conftest import make_services
from tests.agents.fakes import FakeConsents, FakeEvents, FakeOrchestrator, FakeTurns
from tests.integration import test_archive_migrations_pg as migration
from tests.integration import test_webcrawler_composed_runtime as composed_proof
from tests.runtime_guards import InertSoftActivationGuard
from tests.scout_network_fixture import require_namespace
from tests.scout_postgres_fixture import IsolatedPostgres, isolated_postgres
from tests.unit.domain.cortex.test_webcrawler_feed_admission import Queue
from tests.web.test_scavenger import AUTHORIZATION
from tests.webcrawler_feed_fixtures import Scenario, install_effects, scenario

pytestmark = [pytest.mark.integration, pytest.mark.container, pytest.mark.asyncio]


@pytest.fixture(scope="module")
def owned_database() -> Iterator[IsolatedPostgres]:
    """Own one cached, networkless database; never accept an ambient database URL."""
    require_namespace("LYCHD_REQUIRE_SCAVENGER_PG_PROOF")
    with isolated_postgres() as database:
        url = f"postgresql+asyncpg://scout:fixture@/scout?host={database.socket_directory}"
        command.upgrade(migration.config(url), "head")
        command.check(migration.config(url))
        yield database


@pytest_asyncio.fixture
async def factory(
    owned_database: IsolatedPostgres,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    url = f"postgresql+asyncpg://scout:fixture@/scout?host={owned_database.socket_directory}"
    engine = create_async_engine(url)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        # Own synthetic rows only, in this planned disposable database. This is
        # fixture cleanup, never application reset/recovery evidence.
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "TRUNCATE scavenger_observation,scout_attempt,scout_budget,run_checkpoint,consent,"
                    "run_delivery,step,run,session CASCADE"
                )
            )
        await engine.dispose()


def seed() -> CampaignSeed:
    return CampaignSeed(
        subject_profile="Technology@1",
        need="PRIVATE-SEED-NEED",
        inventory=(),
        hard_criteria=(),
        preferences=(),
        budget_minor=None,
        currency="EUR",
        deadline=datetime.now(UTC) + timedelta(hours=1),
        region=None,
        evidence_standard="Unverified publisher title/link only",
        travel_delivery="Not assessed",
        source_policy="admitted-public-feed-only@1",
        disclosure_policy="none",
        learning_mode="none",
        operating_mode="Watch",
    )


@dataclass
class Assembly:
    source: Scenario
    app: ScavengerService
    engine: RunEngine
    substrate: RunSubstrate
    binding: WebcrawlerFeedBinding
    run_id: str
    forbidden: Mock
    reviews: WebcrawlerConsentReviews
    bus: InProcessEventBus
    orchestrator: FakeOrchestrator


async def assemble(factory: async_sessionmaker[AsyncSession]) -> Assembly:
    s = await scenario()
    ledger, queue = DbRunLedger(session_factory=factory), Queue()
    bus = InProcessEventBus(ledger=ledger)
    consents = CodexConsentLedger(session_factory=factory)
    completions = WebcrawlerCompletions()
    webcrawler_store = DbWebcrawlerAttemptStore(factory, s.authorizer, s.binding.profile.budget_limits, completions)
    webcrawler = WebcrawlerWorkflowService(
        store=webcrawler_store,
        completions=completions,
        ledger=ledger,
        consents=consents,
        profile=s.binding.profile,
        capability_key=None,
        authorizer=s.authorizer,
        fence=RunEffectFence(),
    )
    app = ScavengerService(
        store=DbScavengerStore(factory, pattern=OBSERVE_MARKET.manifest.snapshot()),
        policy=LocalScavengerPolicy(access=s.access, profile=s.binding.profile, owner="magus"),
        webcrawler=webcrawler,
    )
    request_id = uuid4()
    admission = await app.reserve(
        request_id=request_id,
        seed=seed(),
        selection=LiteralFilter(query="PRIVATE-INITIAL-FILTER"),
        authentication=s.authentication,
        principal=default_local_sigil(),
    )
    proof = s.admission.declare(
        consumer=admission.consumer,
        request_id=request_id,
        deadline=admission.deadline,
        authentication=s.authentication,
    )
    workflows = BuiltinWorkflowRegistry(workflows=(OBSERVE_MARKET,))
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=workflows,
        queue_router=QueueRouter({"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": queue},
        feed_webcrawler=s.binding.profile,
        feed_webcrawler_admission=s.admission,
        effects=webcrawler,
        consents=consents,
    )
    turns = DbBridgeSessionStore(factory, sigil_name="magus")
    session = await turns.create_session()
    intent = Intent(
        session_id=session.id,
        prompt=str(admission.consumer.application_admission_id),
        source="scavenger",
        sigil_name=default_local_sigil().name,
        sigil_scopes=default_local_sigil().scopes,
    )
    binding = s.admission(intent, proof, s.binding.profile)

    async def retain(run_id: str) -> None:
        await app.retain_run(
            run_id=run_id,
            binding=binding,
            authentication=s.authentication,
            principal=default_local_sigil(),
        )

    handle = await engine.submit(
        intent,
        feed_declaration=proof,
        retain_before_publish=retain,
        idempotency_key=str(request_id),
    )
    orchestrator = FakeOrchestrator()
    assert orchestrator.worker_broker.claim_gate.is_set()
    services = make_services(
        model=object(),
        events=FakeEvents(),
        turns=FakeTurns(),
        consents=FakeConsents(),
        orchestrator=FakeOrchestrator(),
    )
    forbidden = Mock(side_effect=AssertionError("No provider, lease, transition or Bridge output."))
    substrate = RunSubstrate(
        ledger=ledger,
        bus=bus,
        workflows=workflows,
        dispatcher=forbidden,
        orchestrator=orchestrator,
        context=services.context,
        fragments=services.fragments,
        turns=turns,
        forge=forbidden,
        consents=consents,
        queues=engine.queues,
        effects=webcrawler,
        feed_webcrawler=webcrawler,
        scavenger=app,
        stasis_store=PostgresStasisStore(factory),
        cancellations=engine.cancellations,
    )
    engine.stasis_store = substrate.stasis_store
    return Assembly(
        s,
        app,
        engine,
        substrate,
        binding,
        handle.run_id,
        forbidden,
        WebcrawlerConsentReviews(access=s.access, authorizer=s.authorizer, store=webcrawler_store),
        bus,
        orchestrator,
    )


async def approve(a: Assembly) -> None:
    parked = await perform_run({"run_substrate": a.substrate}, run_id=a.run_id, enqueue_seq=0)
    assert parked["status"] == "awaiting_consent"
    run = await a.substrate.ledger.get(a.run_id)
    assert run is not None
    assert run.consent_id is not None
    consent = await a.substrate.consents.get(run.consent_id)
    assert consent is not None
    resolution = await a.reviews.resolve(
        consent=consent,
        reviewer=default_local_sigil(),
        purpose="decide",
        authentication=a.source.authentication,
    )
    assert resolution.decision_allowed
    assert resolution.document is not None
    assert all(
        "PRIVATE-SEED" not in fact.value and "PRIVATE-INITIAL" not in fact.value for fact in resolution.document.facts
    )
    decided = await a.substrate.consents.decide(
        run.consent_id,
        approved=True,
        decided_by="magus",
        expected_native_binding=resolution.binding,
    )
    assert decided is not None
    await a.engine.resume_consent(run.consent_id)


@pytest.mark.parametrize("lose_ack", [False, True])
async def test_native_worker_retains_whole_field_recovery_and_terminal_tombstone(  # noqa: PLR0915 - one causal passage
    factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    *,
    lose_ack: bool,
) -> None:
    a = await assemble(factory)
    fetch, extract, _ = install_effects(monkeypatch)
    try:
        await approve(a)
        original = a.app.store.adopt

        async def adopt(**kwargs: Any) -> Any:
            result = await original(**kwargs)
            if lose_ack:
                msg = "Injected loss after confirmed whole-field commit."
                raise ConnectionError(msg)
            return result

        monkeypatch.setattr(a.app.store, "adopt", adopt)
        if lose_ack:
            with pytest.raises(
                ConnectionError,
                match="Injected loss after confirmed whole-field commit",
            ):
                await perform_run({"run_substrate": a.substrate}, run_id=a.run_id, enqueue_seq=1)
        else:
            result = await perform_run({"run_substrate": a.substrate}, run_id=a.run_id, enqueue_seq=1)
            assert result["status"] == "done"
        read_args: dict[str, Any] = {
            "admission_id": a.binding.consumer.application_admission_id,
            "authentication": a.source.authentication,
            "principal": default_local_sigil(),
        }
        retained = await a.app.read(**read_args)
        assert retained.status == "committed"
        assert retained.observation is not None
        assert retained.observation.items[0].title == "ITEM-TITLE-SECRET"
        assert "ITEM-SUMMARY" not in repr(retained)
        # A fresh store has no acquisition or process-local result cache.
        fresh = DbScavengerStore(factory, pattern=OBSERVE_MARKET.manifest.snapshot())
        resolved = await fresh.committed(
            run_id=UUID(a.run_id),
            binding=a.binding,
            owner="magus",
            authorize=lambda: a.app.policy.worker(a.binding),
        )
        assert resolved is not None
        assert resolved.observation_digest == retained.observation.digest
        view = await a.app.view(**read_args, selection=LiteralFilter(query="no such title"))
        assert view.total_count == 1
        assert view.visible_count == 0
        assert view.unmatched_count == 1
        assert view.casefold_unicode_version
        fetch.assert_awaited_once()
        extract.assert_awaited_once()
        assert a.forbidden.mock_calls == []
        assert a.orchestrator.calls == []
        run = await a.substrate.ledger.get(a.run_id)
        assert run is not None
        assert run.admitted_capability_key is None
        assert run.status is (RunStatus.FAILED if lose_ack else RunStatus.DONE)
        wire = json.dumps(
            {
                "run": run.to_intent().model_dump(mode="json"),
                "checkpoints": await a.substrate.stasis_store.load(a.run_id),
                "events": [event.data for event in await a.substrate.ledger.list_events(a.run_id)],
            }
        )
        for private in [
            "PRIVATE-SEED-NEED",
            "PRIVATE-INITIAL-FILTER",
            "ITEM-TITLE-SECRET",
            "ITEM-SUMMARY",
            "CHANNEL-SECRET",
        ]:
            assert private not in wire
        async with factory() as session:
            attempts = list(await session.scalars(select(WebcrawlerAttempt)))
            assert len(attempts) == 1
            assert attempts[0].status == "succeeded"
            budgets = list(await session.scalars(select(WebcrawlerBudget)))
            before = [(b.scope, b.connects_used, b.connects_reserved, b.active_claims) for b in budgets]
        await a.app.delete(
            **read_args,
            request_digest=retained.request_digest,
            observation_digest=retained.observation_digest,
        )
        tombstone = await a.app.read(**read_args)
        assert tombstone.status == "deleted"
        assert tombstone.seed is None
        assert tombstone.initial_filter is None
        assert tombstone.observation is None
        with pytest.raises(ScavengerRefused, match="deleted"):
            await fresh.committed(
                run_id=UUID(a.run_id),
                binding=a.binding,
                owner="magus",
                authorize=lambda: None,
            )
        with pytest.raises(ScavengerRefused, match="delete_identity"):
            await a.app.delete(
                **read_args,
                request_digest="f" * 64,
                observation_digest=retained.observation_digest,
            )
        # Exact deletion replay is inert and never resets Webcrawler allowance.
        await a.app.delete(
            **read_args,
            request_digest=retained.request_digest,
            observation_digest=retained.observation_digest,
        )
        async with factory() as session:
            row = await session.get(ScavengerObservation, a.binding.consumer.application_admission_id)
            assert row is not None
            assert (
                row.seed_bytes,
                row.filter_bytes,
                row.observation_bytes,
                row.slot,
            ) == (None, None, None, None)
            budgets = list(await session.scalars(select(WebcrawlerBudget)))
            assert [(b.scope, b.connects_used, b.connects_reserved, b.active_claims) for b in budgets] == before
    finally:
        await a.bus.aclose()


async def test_pending_delete_refuses_and_fresh_authority_is_required_after_waits(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    a = await assemble(factory)
    try:
        args: dict[str, Any] = {
            "admission_id": a.binding.consumer.application_admission_id,
            "authentication": a.source.authentication,
            "principal": default_local_sigil(),
        }
        retained = await a.app.read(**args)
        with pytest.raises(ScavengerRefused, match="terminal_disposition_required"):
            await a.app.delete(**args, request_digest=retained.request_digest, observation_digest=None)
        with pytest.raises(ScavengerRefused, match="application_authority"):
            await a.app.read(
                admission_id=a.binding.consumer.application_admission_id,
                authentication=replace(a.source.authentication),
                principal=default_local_sigil(),
            )
        with pytest.raises(ScavengerRefused, match="application_authority"):
            await a.app.read(
                admission_id=a.binding.consumer.application_admission_id,
                authentication=a.source.authentication,
                principal=Sigil(name="magus", scopes=frozenset()),
            )
        original = a.app.store._row  # pyright: ignore[reportPrivateUsage] - controlled post-await revocation

        async def revoke_after_row(*values: Any, **kwargs: Any) -> Any:
            row = await original(*values, **kwargs)
            a.source.access.revoke()
            return row

        monkey = pytest.MonkeyPatch()
        with monkey.context() as patch:
            patch.setattr(a.app.store, "_row", revoke_after_row)
            with pytest.raises(ScavengerRefused, match="application_authority"):
                await a.app.read(**args)
    finally:
        await a.bus.aclose()


async def test_concurrent_different_reservations_admit_one_complete_seed(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    s = await scenario()
    store = DbScavengerStore(factory, pattern=OBSERVE_MARKET.manifest.snapshot())
    common: dict[str, Any] = {
        "owner": "magus",
        "seed": seed(),
        "selection": LiteralFilter(query=""),
        "configuration_digest": s.binding.profile.configuration_digest,
        "authorize": lambda: None,
    }
    result = await asyncio.gather(
        store.reserve(request_id=uuid4(), **common),
        store.reserve(request_id=uuid4(), **common),
        return_exceptions=True,
    )
    assert sum(isinstance(value, ScavengerRefused) for value in result) == 1
    async with factory() as session:
        rows = list(await session.scalars(select(ScavengerObservation)))
        assert len(rows) == 1
        assert rows[0].seed_bytes is not None
        assert rows[0].status == "reserved"


@dataclass
class SelectedAPI:
    source: Scenario
    services: AltarServices
    client: httpx.AsyncClient
    request: ObserveMarketRequest
    run_id: str
    forbidden: Mock


@asynccontextmanager
async def selected_api(
    factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    *,
    profile: WebcrawlerFeedProfile | None = None,
) -> AsyncGenerator[SelectedAPI]:
    """Use actual selected composition with its only DB factory explicitly test-owned."""
    source = await scenario()
    monkeypatch.setattr("lychd.db.engine.get_session_factory", lambda: factory)
    forbidden = Mock(side_effect=AssertionError("The feed must not lease a model."))
    monkeypatch.setattr("lychd.domain.cortex.dispatcher.Dispatcher.lease_grant", forbidden)
    queue = Queue()
    services = build_altar_services(
        queues={"runs": queue, "rites": queue},
        runes=RuneRegistry(()),
        profile="postgres",
        settings=Settings(
            weaver=WeaverSettings(
                scavenger=ScavengerCastingSettings(revision="3", webcrawler=profile or source.binding.profile)
            )
        ),
        operator_access=source.access,
        soft_activation_guard=InertSoftActivationGuard(),
    )
    csrf_value = "synthetic-selected-scavenger-csrf"
    app = Litestar(
        route_handlers=[
            AltarController,
            BridgeController,
            OrbController,
            ScavengerController,
        ],
        dependencies=web_dependencies,
        state=State(
            {
                "services": services,
                "csrf_contract": CsrfClientContract(cookie_name="scavenger-csrf", header_name="x-scavenger-csrf"),
            }
        ),
        middleware=[sigil_auth_middleware(operator_access=source.access)],
        csrf_config=CSRFConfig(
            secret=csrf_value,
            cookie_name="scavenger-csrf",
            header_name="x-scavenger-csrf",
        ),
        plugins=[StrictPydanticSchemaPlugin()],
    )
    request = ObserveMarketRequest(request_id=uuid4(), seed=seed(), initial_filter=LiteralFilter(query=""))
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=cast("Any", app)),
            base_url="http://testserver.local",
            headers={"authorization": AUTHORIZATION},
        ) as client:
            shell = await client.get("/api/v1/altar/status")
            assert shell.status_code == 200, shell.text
            contract = shell.json()["csrf"]
            client.headers[contract["header_name"]] = client.cookies[contract["cookie_name"]]
            initial = await client.get("/api/v1/scavenger")
            assert initial.status_code == 200
            assert initial.json()["configured"] is True
            assert initial.json()["current"] is None
            accepted = await client.post("/api/v1/scavenger/observations", json=request.model_dump(mode="json"))
            assert accepted.status_code == 200, accepted.text
            assert "PRIVATE-SEED" not in accepted.text
            yield SelectedAPI(source, services, client, request, accepted.json()["run_id"], forbidden)
    finally:
        await services.aclose()


async def approve_selected(a: SelectedAPI) -> None:
    parked = await perform_run({"run_substrate": a.services.substrate}, run_id=a.run_id, enqueue_seq=0)
    assert parked["status"] == "awaiting_consent"
    route = f"/api/v1/scavenger/observations/{a.request.request_id}"
    current = await a.client.get(route)
    assert current.status_code == 200
    assert current.json()["status"] == "awaiting_consent"
    assert current.json()["terminal_disposition"] == "pending"
    card = await a.client.get(f"{route}/consent")
    assert card.status_code == 200, card.text
    review = card.json()
    assert review["native_review_status"] == "available"
    assert review["can_decide"] is True
    assert "PRIVATE-SEED" not in card.text
    decision = await a.client.post(
        f"/api/v1/bridge/consents/{review['id']}/decision",
        json={
            "verdict": "approve",
            "review_binding_digest": review["review_binding_digest"],
        },
    )
    assert decision.status_code == 200, decision.text


async def assert_application_navigation(a: SelectedAPI) -> None:
    orb = await a.client.get(f"/api/v1/orb/runs/{a.run_id}")
    assert orb.status_code == 200, orb.text
    assert orb.json()["run"]["bridge_path"] is None
    assert orb.json()["run"]["application_path"] == f"/scavenger?observation={a.request.request_id}"
    assert "ITEM-TITLE-SECRET" not in orb.text
    catalogue = await a.client.get("/api/v1/orb/runs")
    assert catalogue.status_code == 200, catalogue.text
    own = next(row for row in catalogue.json()["runs"] if row["run_id"] == a.run_id)
    assert own["bridge_path"] is None
    assert own["application_path"] is None
    assert "ITEM-TITLE-SECRET" not in catalogue.text


async def test_selected_http_assembly_worker_consent_and_whole_field_lifecycle(
    factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with selected_api(factory, monkeypatch) as a:
        fetch, extract, _ = install_effects(monkeypatch)
        route = f"/api/v1/scavenger/observations/{a.request.request_id}"
        before = await a.client.get(route)
        refused = await a.client.post(
            f"{route}/delete",
            json={
                "request_digest": before.json()["request_digest"],
                "observation_digest": None,
            },
        )
        assert refused.status_code == 409
        await approve_selected(a)
        fetch.assert_not_awaited()
        done = await perform_run({"run_substrate": a.services.substrate}, run_id=a.run_id, enqueue_seq=1)
        assert done["status"] == "done"
        observed = await a.client.get(route)
        assert observed.status_code == 200, observed.text
        field = observed.json()
        assert field["status"] == "observed"
        assert field["observation"]["items"][0]["title"] == "ITEM-TITLE-SECRET"
        assert field["terminal_disposition"] == "terminal"
        await assert_application_navigation(a)
        filtered = await a.client.post(f"{route}/view", json={"query": "no matching literal"})
        assert filtered.status_code == 200, filtered.text
        assert filtered.json()["total_count"] == 1
        assert filtered.json()["visible_count"] == 0
        replay = await a.client.post("/api/v1/scavenger/observations", json=a.request.model_dump(mode="json"))
        assert replay.status_code == 200, replay.text
        assert replay.json()["run_id"] == a.run_id
        fetch.assert_awaited_once()
        extract.assert_awaited_once()
        a.forbidden.assert_not_called()
        async with factory() as session:
            run = await session.get(RunRow, UUID(a.run_id))
            assert run is not None
            assert run.session_id is None
            assert run.intent["session_id"] == f"scavenger:{a.request.request_id}"
            assert list(await session.scalars(select(SessionRow))) == []
        deleted = await a.client.post(
            f"{route}/delete",
            json={
                "request_digest": field["request_digest"],
                "observation_digest": field["observation_digest"],
            },
        )
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["status"] == "deleted"
        after = await a.client.get(route)
        assert after.json()["status"] == "deleted"
        assert after.json()["observation"] is None
        assert (await a.client.get("/api/v1/scavenger")).json()["current"] is None
        stale = await a.client.post("/api/v1/scavenger/observations", json=a.request.model_dump(mode="json"))
        assert stale.status_code == 409
        assert stale.json()["extra"]["code"] == "deleted"
        fetch.assert_awaited_once()


async def test_unknown_claim_custody_blocks_delete_and_same_key_admission_does_not_refetch(
    factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inject custody loss after an actual DB claim, without claiming a physical crash."""
    async with selected_api(factory, monkeypatch) as a:
        fetch, extract, _ = install_effects(monkeypatch)
        await approve_selected(a)
        assert (await a.services.ledger.try_claim_run(a.run_id, enqueue_seq=1)).acknowledged is True
        run = await a.services.ledger.get(a.run_id)
        assert run is not None
        assert type(run.admitted_webcrawler) is WebcrawlerFeedBinding
        service = a.services.webcrawler
        assert service is not None
        review = await service.prepare(run_id=a.run_id, binding=run.admitted_webcrawler)
        # Host port invocation and state injection are intentional, not a sandbox proof.
        store = service._store  # pyright: ignore[reportPrivateUsage]
        claim = await store.claim(review.attempt_id, review.preparation_digest, enqueue_seq=1)
        assert type(claim) is NewScoutClaim
        unknown = await store.unknown(claim)
        assert unknown.status == "unknown_after_crash"
        assert await a.services.ledger.try_fail_claimed(a.run_id, enqueue_seq=1, error="synthetic custody loss")
        route = f"/api/v1/scavenger/observations/{a.request.request_id}"
        current = await a.client.get(route)
        field = current.json()
        assert field["status"] == "unknown"
        assert field["terminal_disposition"] == "unknown"
        refused = await a.client.post(
            f"{route}/delete",
            json={
                "request_digest": field["request_digest"],
                "observation_digest": None,
            },
        )
        assert refused.status_code == 409
        repeated = await store.claim(review.attempt_id, review.preparation_digest, enqueue_seq=1)
        assert repeated == unknown
        replay = await a.client.post("/api/v1/scavenger/observations", json=a.request.model_dump(mode="json"))
        assert replay.status_code == 200
        assert replay.json()["run_id"] == a.run_id
        async with factory() as session:
            budget = await session.scalar(select(WebcrawlerBudget).where(WebcrawlerBudget.scope == "binding"))
            assert budget is not None
            assert budget.active_claims == 1
            assert budget.wire_bytes_reserved == a.source.binding.profile.allowance.wire_bytes
        fetch.assert_not_awaited()
        extract.assert_not_awaited()


async def test_actual_driver_private_failure_rolls_back_and_is_a_closed_http_refusal(
    factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with selected_api(factory, monkeypatch) as a:
        route = f"/api/v1/scavenger/observations/{a.request.request_id}"
        original_lock = DbScavengerStore._lock  # pyright: ignore[reportPrivateUsage]
        observed_private_driver_error: list[bool] = []
        marker = "SYNTHETIC-PRIVATE-SQL-SENTINEL"

        async def failing_statement(session: AsyncSession, authorize: Callable[[], None]) -> None:
            await original_lock(session, authorize)
            try:
                await session.execute(
                    text("SELECT CAST(:private_value AS INTEGER)"),
                    {"private_value": marker},
                )
            except DBAPIError as error:
                observed_private_driver_error.append(marker in str(error))
                raise

        with monkeypatch.context() as scoped:
            scoped.setattr(DbScavengerStore, "_lock", staticmethod(failing_statement))
            response = await a.client.get(route)
        assert observed_private_driver_error == [True]
        assert response.status_code == 503
        assert response.json()["extra"] == {"code": "application_storage"}
        assert marker not in response.text
        normal = await a.client.get(route)
        assert normal.status_code == 200, normal.text
        assert normal.json()["status"] == "pending"
        assert normal.json()["seed"]["need"] == a.request.seed.need
        a.forbidden.assert_not_called()


async def test_pending_core_cancellation_withdraws_review_before_explicit_payload_deletion(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    async with selected_api(factory, monkeypatch) as a:
        fetch, extract, _ = install_effects(monkeypatch)
        parked = await perform_run({"run_substrate": a.services.substrate}, run_id=a.run_id, enqueue_seq=0)
        assert parked["status"] == "awaiting_consent"
        route = f"/api/v1/scavenger/observations/{a.request.request_id}"
        card = await a.client.get(f"{route}/consent")
        assert card.json()["can_decide"] is True
        cancelled = await a.client.post(f"/api/v1/bridge/runs/{a.run_id}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["run_id"] == a.run_id
        assert cancelled.json()["run_status"] == "cancelled"
        assert cancelled.json()["content"] == ""
        current = await a.client.get(route)
        assert current.status_code == 200, current.text
        document = current.json()
        assert document["run_status"] == "cancelled"
        assert document["terminal_disposition"] == "terminal"
        assert document["seed"]["need"] == a.request.seed.need
        assert document["observation"] is None
        assert (await a.client.get(f"{route}/consent")).json() is None
        deleted = await a.client.post(
            f"{route}/delete",
            json={
                "request_digest": document["request_digest"],
                "observation_digest": None,
            },
        )
        assert deleted.status_code == 200, deleted.text
        assert (await a.client.get(route)).json()["seed"] is None
        async with factory() as session:
            assert list(await session.scalars(select(SessionRow))) == []
        fetch.assert_not_awaited()
        extract.assert_not_awaited()
        a.forbidden.assert_not_called()


async def test_delayed_held_retention_replay_accepts_exact_published_and_committed_run(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = DbScavengerStore.retain_run
    released = asyncio.Event()
    replay_tasks: list[asyncio.Task[None]] = []

    async def retain_with_delayed_peer(store: DbScavengerStore, **kwargs: Any) -> None:
        async with factory() as session:
            delivery = await session.scalar(select(RunDelivery).where(RunDelivery.run_id == kwargs["run_id"]))
            assert delivery is not None
            assert delivery.state == "held"

        async def delayed_peer() -> None:
            await released.wait()
            await original(store, **kwargs)

        replay_tasks.append(asyncio.create_task(delayed_peer()))
        await original(store, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(DbScavengerStore, "retain_run", retain_with_delayed_peer)
        a = await assemble(factory)
    fetch, extract, _ = install_effects(monkeypatch)
    try:
        assert len(replay_tasks) == 1
        released.set()
        await asyncio.wait_for(replay_tasks[0], timeout=5)
        await approve(a)
        result = await perform_run({"run_substrate": a.substrate}, run_id=a.run_id, enqueue_seq=1)
        assert result["status"] == "done"
        args: dict[str, Any] = {
            "run_id": UUID(a.run_id),
            "binding": a.binding,
            "owner": "magus",
            "authorize": lambda: a.app.policy.worker(a.binding),
        }
        first = await a.app.store.committed(**args)
        assert first is not None
        await a.app.store.retain_run(**args)
        assert await a.app.store.committed(**args) == first
        fetch.assert_awaited_once()
        extract.assert_awaited_once()
        a.forbidden.assert_not_called()
    finally:
        released.set()
        await asyncio.gather(*replay_tasks, return_exceptions=True)
        await a.bus.aclose()


async def native_feed_passage(a: SelectedAPI, fixture: network.ScoutNetworkFixture) -> dict[str, Any]:
    """Exercise selected HTTP/Graph/custody; queue is still the controlled port."""
    await approve_selected(a)
    result = await perform_run({"run_substrate": a.services.substrate}, run_id=a.run_id, enqueue_seq=1)
    assert result["status"] == "done"
    route = f"/api/v1/scavenger/observations/{a.request.request_id}"
    response = await a.client.get(route)
    assert response.status_code == 200, response.text
    document = response.json()
    assert document["status"] == "observed"
    assert document["observation"]["requested_url"] == SCOUT_FEED_URL
    assert [item["title"] for item in document["observation"]["items"]] == ["Synthetic & GPU", None]
    await fixture.settle()
    before = (tuple(fixture.queries), tuple(fixture.requests))
    assert fixture.requests == [serialize_rss_get(preflight_destination(SCOUT_FEED_URL))]
    assert fixture.sni == ["www.bazos.sk"]
    filtered = await a.client.post(f"{route}/view", json={"query": "no matching literal"})
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["total_count"] == 2
    assert filtered.json()["visible_count"] == 0
    replay = await a.client.post("/api/v1/scavenger/observations", json=a.request.model_dump(mode="json"))
    assert replay.status_code == 200, replay.text
    assert replay.json()["run_id"] == a.run_id
    assert (await a.client.get(route)).json()["observation_digest"] == document["observation_digest"]
    await fixture.settle()
    assert before == (tuple(fixture.queries), tuple(fixture.requests))
    a.forbidden.assert_not_called()
    return document


async def test_selected_native_feed_dns_tls_child_and_durable_whole_field(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    network.require_namespace(
        "LYCHD_REQUIRE_WEBCRAWLER_COMPOSED_PROOF"
        if "LYCHD_REQUIRE_WEBCRAWLER_COMPOSED_PROOF" in os.environ
        else "LYCHD_REQUIRE_SCOUT_COMPOSED_PROOF"
    )
    runtime = composed_proof._runtime()  # pyright: ignore[reportPrivateUsage] - exact shared opt-in runtime loader
    certificate, key = await asyncio.to_thread(
        network.certificate, tmp_path, "scavenger", "www.bazos.sk", include_ip=False
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    context.set_alpn_protocols(["http/1.1"])
    fixture = network.ScoutNetworkFixture(context, context, hostname="www.bazos.sk")
    body = (
        b'<rss version="2.0"><channel><title>Synthetic market</title>'
        b"<link>https://www.bazos.sk/rss.php?rub=pc</link><description>Claims only</description>"
        b"<item><title>Synthetic &amp; GPU</title><link>https://pc.bazos.sk/item/1</link>"
        b"<description>Omitted application prose</description></item>"
        b"<item><link>https://pc.bazos.sk/item/1</link><description>Summary without title</description></item></channel></rss>"
    )
    fixture.response = (
        b"HTTP/1.1 200 OK\r\nContent-Type: application/rss+xml; charset=utf-8\r\nConnection: close\r\n"
        + f"Content-Length: {len(body)}\r\n\r\n".encode()
        + body
    )
    try:
        resolver = await fixture.start()
        source = await scenario()
        values = source.binding.profile.model_dump()
        values.update(
            bwrap=runtime.bwrap,
            python_root=runtime.python_root,
            libraries=runtime.libraries,
            resolver_address=resolver.address,
            resolver_port=resolver.port,
            ca_file=certificate,
            resolver_custody_statement="Synthetic DNS/TLS in this proof's isolated loopback-only namespace.",
        )
        async with selected_api(factory, monkeypatch, profile=WebcrawlerFeedProfile.model_validate(values)) as a:
            document = await native_feed_passage(a, fixture)
            async with factory() as session:
                attempts = list(await session.scalars(select(WebcrawlerAttempt)))
                assert len(attempts) == 1
                assert attempts[0].settlement_bytes is not None
                settlement = ScoutSettlement.model_validate_json(attempts[0].settlement_bytes)
                assert settlement.outcome == "succeeded"
                assert settlement.child == "reaped"
                assert settlement.sockets == "closed"
                assert settlement.usage.connects == 3
                assert list(await session.scalars(select(SessionRow))) == []
            receipt = {
                "schema": "scavenger-native-local-proof@1",
                "status": "passed",
                "execution": "selected-ASGI-and-native-worker-function",
                "network": "isolated-loopback-only",
                "queue": "controlled-port",
                "model_calls": 0,
                "http_requests": len(fixture.requests),
                "items": len(document["observation"]["items"]),
                "field_digest": document["view"]["field_digest"],
                "child": settlement.child,
                "sockets": settlement.sockets,
                "usage": settlement.usage.model_dump(),
            }
            (tmp_path / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    finally:
        await fixture.close()
