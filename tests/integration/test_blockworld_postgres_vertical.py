"""Opt-in PostgreSQL placement history through the worker and native HTTP review.

Run, delivery, consent, checkpoint, session and placement custody use PostgreSQL.
Fresh adapters recover serialized state in the same test process; the queue and
world remain inert. This proves neither a broker, migrations nor a game adapter.
"""

from __future__ import annotations

import asyncio
import copy
import json
from collections.abc import AsyncIterator, Iterator
from hashlib import sha256
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import httpx
import pytest
import pytest_asyncio

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from litestar import Litestar
from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.middleware import DefineMiddleware
from litestar.middleware.authentication import AuthenticationResult
from sqlalchemy import Table, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.compositions.blockworld.ports import ActionSnapshot
from lychd.compositions.blockworld.review import BlockworldConsentReviewProducer
from lychd.compositions.blockworld.schemas import AdmittedPlacementV1
from lychd.compositions.blockworld.services import PlacementService
from lychd.compositions.blockworld.workflow import placement_workflow
from lychd.db.blockworld import DbPlacementStore
from lychd.db.checkpoints import PostgresStasisStore
from lychd.db.models import CodexPreauthorization, Consent, Run, RunCheckpoint, RunDelivery, Session, Step
from lychd.db.models.blockworld import BlockworldPlacementAction, BlockworldPlacementMission
from lychd.db.sessions import DbBridgeSessionStore
from lychd.domain.codex.ledger import CodexConsentLedger
from lychd.domain.codex.middleware import SigilAuthMiddleware
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.projection import EventProjector
from lychd.ghouls.runs import perform_run
from lychd.interface.web.bridge import BridgeController
from lychd.interface.web.deps import web_dependencies
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry
from tests.postgres_model_tables import with_referenced_tables
from tests.support.blockworld import (
    BUILDER,
    IDS,
    LITERAL,
    REVIEWER,
    CapturedQueue,
    ExternalAuthority,
    SimulatedProcessLoss,
    WorldJournal,
    WorldPort,
    admitted_document,
    canonical,
    digest,
    expected,
)
from tests.web.conftest import TEST_ACCESS_PASSWORD, TEST_AUTHORIZATION

pytestmark = [pytest.mark.asyncio, pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest_asyncio.fixture
async def pg_factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(pg_url)
    tables = cast(
        "list[Table]",
        [
            Session.__table__,
            Run.__table__,
            RunDelivery.__table__,
            RunCheckpoint.__table__,
            Step.__table__,
            Consent.__table__,
            CodexPreauthorization.__table__,
            BlockworldPlacementMission.__table__,
            BlockworldPlacementAction.__table__,
        ],
    )
    tables = with_referenced_tables(tables)
    async with engine.begin() as connection:
        await connection.run_sync(Run.metadata.drop_all, tables=tables)
        await connection.run_sync(Run.metadata.create_all, tables=tables)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


class PostgresBoot:
    """Rebuild application adapters; only the independent world journal survives."""

    def __init__(self, factory: async_sessionmaker[AsyncSession], world: WorldJournal | None = None) -> None:
        self.factory = factory
        self.ledger = DbRunLedger(session_factory=factory)
        self.consents = CodexConsentLedger(session_factory=factory)
        self.checkpoints = PostgresStasisStore(factory)
        self.sessions = DbBridgeSessionStore(factory, sigil_name=BUILDER.name)
        self.authority = ExternalAuthority()
        self.world = world if world is not None else WorldJournal()
        self.store = DbPlacementStore(factory, self.authority)
        self.effect = WorldPort(self.world)
        self.service = PlacementService(self.store, self.authority, self.effect)
        self.workflow = placement_workflow(self.service)
        self.workflows = BuiltinWorkflowRegistry(workflows=(self.workflow,))
        self.queue = CapturedQueue()
        self.bus = InProcessEventBus(ledger=self.ledger)
        self.dispatcher = FakeDispatcher(model=None)
        self.orchestrator = FakeOrchestrator()
        self.fragments = build_fragment_registry()
        self.substrate = RunSubstrate(
            ledger=self.ledger,
            bus=self.bus,
            workflows=self.workflows,
            orchestrator=self.orchestrator,
            dispatcher=self.dispatcher,
            context=ContextOrchestrator(registry=FakeRegistry()),
            fragments=self.fragments,
            turns=self.sessions,
            consents=self.consents,
            forge=default_forge(),
            stasis_store=self.checkpoints,
            queues={"runs": self.queue},
        )
        self.engine = RunEngine(
            ledger=self.ledger,
            bus=self.bus,
            workflows=self.workflows,
            queue_router=QueueRouter({"default": RouteRule(queue="runs", priority=70)}),
            queues=self.substrate.queues,
            stasis_store=self.checkpoints,
            consents=self.consents,
            release_context=self.substrate.context.release,
        )
        self.producer = BlockworldConsentReviewProducer(self.store, self.authority)
        self.projector = EventProjector(
            fragments=self.fragments,
            sessions=self.sessions,
            consents=self.consents,
            consent_reviews=self.producer,
        )
        self.reviewers = [REVIEWER]

    async def admit(self) -> str:
        admission = AdmittedPlacementV1.model_validate(admitted_document())
        document = canonical(admission.model_dump(mode="json"))
        request = canonical(LITERAL["request"])
        async with self.factory() as session:
            session.add(
                BlockworldPlacementMission(
                    id=UUID(IDS["mission"]),
                    request_id=UUID(IDS["request"]),
                    action_id=UUID(IDS["action"]),
                    admission_bytes=document,
                    admission_digest=sha256(document).hexdigest(),
                    request_bytes=request,
                    request_digest=sha256(request).hexdigest(),
                    pattern_snapshot=copy.deepcopy(LITERAL["candidate_manifest"]),
                    pattern_digest=LITERAL["candidate_manifest"]["digest"],
                )
            )
            await session.commit()
        bridge_session = await self.sessions.create_session(title="PostgreSQL one-placement fixture")
        result = await self.service.submit(
            copy.deepcopy(LITERAL["request"]),
            engine=self.engine,
            ledger=self.ledger,
            session_id=bridge_session.id,
            principal=BUILDER,
        )
        assert result["kind"] == "admitted"
        run_id = result["run_id"]
        assert isinstance(run_id, str)
        self.world.vector = expected(run_id)
        return run_id

    async def drive(self, run_id: str) -> dict[str, Any]:
        run = await self.ledger.get(run_id)
        assert run is not None
        try:
            return await perform_run({"run_substrate": self.substrate}, run_id=run_id, enqueue_seq=run.enqueue_seq)
        finally:
            await self.bus.wait_persisted(run_id)

    def client(self) -> httpx.AsyncClient:
        reviewers = self.reviewers

        class ReviewerMiddleware(SigilAuthMiddleware):
            async def authenticate_request(
                self, connection: ASGIConnection[Any, Any, Any, Any]
            ) -> AuthenticationResult:
                await super().authenticate_request(connection)
                return AuthenticationResult(user=reviewers[0], auth=None)

        services = SimpleNamespace(
            ledger=self.ledger,
            consents=self.consents,
            run_engine=self.engine,
            projector=self.projector,
            bridge_sessions=self.sessions,
            bus=self.bus,
            workflows=self.workflows,
            fragments=self.fragments,
        )
        app = Litestar(
            route_handlers=[BridgeController],
            dependencies=web_dependencies,
            middleware=[DefineMiddleware(ReviewerMiddleware, access_password=TEST_ACCESS_PASSWORD)],
            state=State({"services": services}),
        )
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=cast("Any", app)),
            base_url="http://testserver.local",
            headers={"authorization": TEST_AUTHORIZATION},
        )


async def waiting(boot: PostgresBoot) -> tuple[str, ActionSnapshot]:
    run_id = await boot.admit()
    assert (await boot.drive(run_id))["status"] == "awaiting_consent"
    run = await boot.ledger.get(run_id)
    assert run is not None
    assert run.status is RunStatus.AWAITING_CONSENT
    action = await boot.store.read_action(IDS["action"])
    vector = expected(run_id)
    assert action.command_bytes == vector["command_bytes"]
    assert action.review_bytes == vector["review_bytes"]
    assert action.native_binding.digest == vector["binding_digest"]
    assert action.run_id == run_id
    assert run.consent_id == action.consent_id
    assert boot.world.invokes == []
    return run_id, action


async def approve(boot: PostgresBoot, action: ActionSnapshot) -> None:
    async with boot.client() as client:
        response = await client.post(
            f"/api/v1/bridge/consents/{action.consent_id}/decision",
            json={"verdict": "approve", "review_binding_digest": action.native_binding.digest},
        )
        assert response.status_code == 200, response.text


async def assert_settled(boot: PostgresBoot, run_id: str) -> bytes:
    action = await boot.store.read_action(IDS["action"])
    assert action.status == "verified"
    assert action.receipt_bytes is not None
    receipt = json.loads(action.receipt_bytes)
    expected_receipt = expected(run_id)["receipt"]
    expected_receipt["receipt_id"] = receipt["receipt_id"]
    assert action.receipt_bytes == canonical(expected_receipt)
    assert action.receipt_digest == digest("lychd.blockworld.receipt.v1\n", expected_receipt)
    mission = await boot.store.load_for_run(run_id)
    assert (mission.cursor, mission.placements_remaining, mission.pending_action_id) == (1, 0, None)
    assert mission.result is not None
    assert mission.result.kind == "verified"
    assert (len(boot.world.invokes), boot.world.effects) == (1, 1)
    assert boot.world.invokes == [expected(run_id)["command_bytes"]]
    return action.receipt_bytes


@pytest.mark.parametrize("lost_ack", [False, True], ids=["acknowledged", "unknown-effect"])
async def test_postgres_worker_review_and_restart_preserve_one_placement(  # noqa: PLR0915 - one connected history
    pg_factory: async_sessionmaker[AsyncSession], *, lost_ack: bool
) -> None:
    first = PostgresBoot(pg_factory)
    run_id, action = await waiting(first)
    snapshots = await first.checkpoints.load(run_id)
    assert snapshots is not None
    async with pg_factory() as session:
        stored = await session.scalar(select(RunCheckpoint.snapshots).where(RunCheckpoint.run_id == UUID(run_id)))
    assert canonical(stored) == canonical(snapshots)
    active = [item for item in snapshots if item.get("status") == "created"]
    assert len(active) == 1
    assert active[0]["state"]["pending_consent_id"] == action.consent_id
    assert active[0]["state"]["preparation_digest"] == action.preparation_digest

    restored = PostgresBoot(pg_factory, first.world)
    assert restored.engine is not first.engine
    assert restored.checkpoints is not first.checkpoints
    assert restored.consents is not first.consents
    assert restored.store is not first.store
    assert canonical(await restored.checkpoints.load(run_id)) == canonical(snapshots)
    async with restored.client() as client:
        snapshot = await client.get("/api/v1/bridge")
        assert snapshot.status_code == 200
        card = snapshot.json()["pending_consents"][0]
        assert card["native_review_status"] == "available"
        assert card["native_review"] == {k: v for k, v in expected(run_id)["review"].items() if k != "schema_version"}
        assert card["review_binding_digest"] == action.native_binding.digest
        endpoint = f"/api/v1/bridge/consents/{action.consent_id}/decision"
        assert (await client.post(endpoint, json={"verdict": "approve"})).status_code == 409
        stale = {"verdict": "approve", "review_binding_digest": "0" * 64}
        assert (await client.post(endpoint, json=stale)).status_code == 409
        restored.reviewers[0] = Sigil(name="scope-only", scopes=frozenset({"runs:approve"}))
        bound = {"verdict": "approve", "review_binding_digest": action.native_binding.digest}
        assert (await client.post(endpoint, json=bound)).status_code == 403
        assert await restored.consents.verdict(action.consent_id) is None
        restored.reviewers[0] = REVIEWER
    await approve(restored, action)
    resumed = PostgresBoot(pg_factory, first.world)
    run = await resumed.ledger.get(run_id)
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert run.enqueue_seq == 1
    resumed.world.lose_ack = lost_ack
    assert (await resumed.drive(run_id))["status"] == "done"
    assert not await resumed.checkpoints.exists(run_id)
    reopened = PostgresBoot(pg_factory, first.world)
    if lost_ack:
        unknown = await reopened.store.read_action(IDS["action"])
        assert unknown.status == "unverified_effect"
        assert unknown.receipt_bytes is None
        mission = await reopened.store.load_for_run(run_id)
        assert (mission.cursor, mission.placements_remaining) == (0, 1)
        assert (await reopened.service.reconcile(IDS["action"])).kind == "verified"
    receipt = await assert_settled(reopened, run_id)
    assert (await reopened.drive(run_id))["status"] == "skipped"
    assert (await reopened.service.reconcile(IDS["action"])).kind == "verified"
    assert await assert_settled(reopened, run_id) == receipt
    assert resumed.dispatcher.calls == []
    assert resumed.orchestrator.calls == []


async def test_postgres_worker_unknown_receipt_failure_rolls_back_and_reconciles_once(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    first = PostgresBoot(pg_factory)
    run_id, action = await waiting(first)
    await approve(first, action)
    first.world.lose_ack = True
    assert (await first.drive(run_id))["status"] == "done"
    restored = PostgresBoot(pg_factory, first.world)
    async with pg_factory() as session:
        await session.execute(
            text(
                "CREATE FUNCTION reject_vertical_settlement() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.cursor = 1 THEN RAISE EXCEPTION 'injected mission settlement failure'; END IF; RETURN NEW; END $$"
            )
        )
        await session.execute(
            text(
                "CREATE TRIGGER reject_vertical_settlement BEFORE UPDATE ON blockworld_placement_mission FOR EACH ROW EXECUTE FUNCTION reject_vertical_settlement()"
            )
        )
        await session.commit()
    try:
        with pytest.raises(DBAPIError, match="injected mission settlement failure"):
            await restored.service.reconcile(IDS["action"])
        fresh = PostgresBoot(pg_factory, first.world)
        unknown = await fresh.store.read_action(IDS["action"])
        mission = await fresh.store.load_for_run(run_id)
        assert unknown.status == "unverified_effect"
        assert unknown.receipt_bytes is None
        assert unknown.receipt_digest is None
        assert (mission.cursor, mission.placements_remaining, mission.pending_action_id) == (0, 1, IDS["action"])
        assert mission.result is not None
        assert mission.result.kind == "unverified_effect"
    finally:
        async with pg_factory() as session:
            await session.execute(text("DROP TRIGGER reject_vertical_settlement ON blockworld_placement_mission"))
            await session.execute(text("DROP FUNCTION reject_vertical_settlement()"))
            await session.commit()
    competitor = PostgresBoot(pg_factory, first.world)
    outcomes = await asyncio.gather(
        restored.service.reconcile(IDS["action"]), competitor.service.reconcile(IDS["action"])
    )
    assert outcomes[0] == outcomes[1]
    assert outcomes[0].kind == "verified"
    await assert_settled(competitor, run_id)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [("effect_allowed", False, "authority_revoked"), ("world_epoch", 8, "epoch_changed")],
)
async def test_postgres_worker_rechecks_approved_authority_after_restart(
    pg_factory: async_sessionmaker[AsyncSession], field: str, value: object, reason: str
) -> None:
    first = PostgresBoot(pg_factory)
    run_id, action = await waiting(first)
    await approve(first, action)
    restored = PostgresBoot(pg_factory, first.world)
    restored.authority.facts[field] = value
    assert (await restored.drive(run_id))["status"] == "done"
    refused = await restored.store.read_action(IDS["action"])
    assert (refused.status, refused.reason, refused.receipt_bytes) == ("not_issued", reason, None)
    mission = await restored.store.load_for_run(run_id)
    assert (mission.cursor, mission.placements_remaining, mission.pending_action_id) == (0, 1, None)
    assert await restored.consents.verdict(action.consent_id) is True
    assert restored.world.invokes == []
    assert restored.world.effects == 0


async def test_postgres_interrupted_unknown_effect_keeps_checkpoint_without_reissuing(
    pg_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    first = PostgresBoot(pg_factory)
    run_id, action = await waiting(first)
    await approve(first, action)
    first.world.lose_ack = True
    record_unknown = first.store.record_unknown

    async def lose_process_after_unknown(action_id: str, reason: str) -> Any:
        await record_unknown(action_id, reason)
        raise SimulatedProcessLoss

    monkeypatch.setattr(first.store, "record_unknown", lose_process_after_unknown)
    with pytest.raises(SimulatedProcessLoss):
        await first.drive(run_id)
    snapshots = await first.checkpoints.load(run_id)
    assert snapshots is not None
    states = [item["state"] for item in snapshots if item.get("state", {}).get("action_id") == IDS["action"]]
    assert states
    assert all(state["preparation_digest"] == action.preparation_digest for state in states)

    restored = PostgresBoot(pg_factory, first.world)
    assert canonical(await restored.checkpoints.load(run_id)) == canonical(snapshots)
    retained = await restored.store.read_action(IDS["action"])
    assert retained.status == "unverified_effect"
    assert retained.command_bytes == expected(run_id)["command_bytes"]
    assert retained.claim_id is not None
    assert retained.receipt_bytes is None
    # Recovery reads the retained action; an orphaned worker is not a new grant.
    assert (await restored.service.reconcile(IDS["action"])).kind == "verified"
    receipt = await assert_settled(restored, run_id)
    assert (await restored.service.execute(IDS["action"], action.native_binding, BUILDER)).kind == "verified"
    assert await assert_settled(restored, run_id) == receipt
    assert (await restored.drive(run_id))["status"] == "skipped"
