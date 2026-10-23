"""Authored PostgreSQL custody tests; execute only in the explicit container profile."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Literal, cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from sqlalchemy import Table, delete, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.compositions.blockworld.ports import NewClaim, PreparedAction, Refused
from lychd.compositions.blockworld.schemas import (
    AdmittedPlacementV1,
    CurrentPlacementFacts,
    PlacementCommitUnknownError,
    PlacementEvidence,
    PlacementNotFoundError,
    ReviewEligibility,
    UnknownEvidence,
    canonical_bytes,
)
from lychd.compositions.blockworld.services import PlacementService
from lychd.compositions.blockworld.workflow import placement_workflow
from lychd.db.blockworld import DbPlacementStore
from lychd.db.models import Consent, Run, RunDelivery, Session, Step
from lychd.db.models.blockworld import BlockworldPlacementAction, BlockworldPlacementMission
from lychd.db.models.codex import CodexPreauthorization
from lychd.db.sessions import DbBridgeSessionStore
from lychd.domain.codex.ledger import CodexConsentLedger
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import DbRunLedger
from tests.postgres_model_tables import with_referenced_tables
from tests.unit.compositions.blockworld.test_placement import admitted_document, identity

pytestmark = [pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest_asyncio.fixture
async def pg_factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(pg_url)
    tables = [
        Session.__table__,
        Run.__table__,
        Consent.__table__,
        RunDelivery.__table__,
        Step.__table__,
        CodexPreauthorization.__table__,
        BlockworldPlacementMission.__table__,
        BlockworldPlacementAction.__table__,
    ]
    tables = with_referenced_tables(cast("list[Table]", tables))
    async with engine.begin() as connection:
        await connection.run_sync(Run.metadata.drop_all, tables=tables)
        await connection.run_sync(Run.metadata.create_all, tables=tables)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


class _Authority:
    async def current(self, command_bytes: bytes, principal: Sigil) -> CurrentPlacementFacts:
        _ = command_bytes, principal
        return CurrentPlacementFacts(
            principal_name="builder",
            effect_allowed=True,
            authority_generation=4,
            mission_id=identity(2),
            mission_active=True,
            mission_policy_id=identity(10),
            mission_policy_generation=3,
            server_id=identity(4),
            world_id=identity(5),
            world_epoch=2,
            bot_id=identity(6),
            capability_revision="test.1",
            can_place=True,
            can_prove=True,
            lease_id=identity(9),
            lease_generation=2,
            lease_active=True,
            lease_expires_at="2035-01-01T12:02:00Z",
            target_before_digest="3" * 64,
            inventory_generation=5,
            inventory_digest="4" * 64,
            inventory_count=2,
            cursor=0,
            placements_remaining=1,
        )

    async def review_access(
        self, action_id: str, audience_digest: str, reviewer: Sigil, purpose: Literal["view", "decide"]
    ) -> ReviewEligibility:
        _ = action_id, audience_digest, reviewer, purpose
        msg = "SQL custody fixture does not resolve reviews."
        raise AssertionError(msg)


class _CapturedQueue:
    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> None:
        _ = job_or_func, kwargs

    async def job(self, job_key: str, /) -> Any:
        _ = job_key
        msg = "SQL admission fixture does not inspect jobs."
        raise AssertionError(msg)

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = job, error, ttl
        msg = "SQL admission fixture does not abort jobs."
        raise AssertionError(msg)


async def _wall_time(session: AsyncSession) -> datetime:
    value = await session.scalar(select(func.clock_timestamp()))
    assert isinstance(value, datetime)
    return value


async def _policy(session: AsyncSession, number: int) -> CodexPreauthorization:
    policy = await session.get(CodexPreauthorization, UUID(identity(number)))
    assert policy is not None
    return policy


async def _admit(
    factory: async_sessionmaker[AsyncSession], judgment_mode: str = "live", deadline: str | None = None
) -> tuple[DbPlacementStore, str, CodexConsentLedger]:
    values = admitted_document()
    if deadline is not None:
        values["deadline"] = deadline
    values["judgment_mode"] = judgment_mode
    values["policy_id"] = identity(20) if judgment_mode != "live" else None
    fixture = AdmittedPlacementV1.model_validate(values)
    document, request = canonical_bytes(fixture), canonical_bytes(fixture.request)
    async with factory() as session:
        session.add(
            BlockworldPlacementMission(
                id=UUID(identity(2)),
                request_id=UUID(identity(1)),
                action_id=UUID(identity(3)),
                run_id=None,
                admission_bytes=document,
                admission_digest=sha256(document).hexdigest(),
                request_bytes=request,
                request_digest=sha256(request).hexdigest(),
                pattern_snapshot=fixture.model_dump(mode="json")["pattern_snapshot"],
                pattern_digest=fixture.pattern_snapshot["digest"],
                cursor=0,
                placements_remaining=1,
                pending_action_id=None,
                result_bytes=None,
            )
        )
        await session.commit()
    authority = _Authority()
    store = DbPlacementStore(factory, authority)
    service = PlacementService(store, authority, AsyncMock())
    ledger = DbRunLedger(session_factory=factory)
    consents = CodexConsentLedger(session_factory=factory)
    registry = BuiltinWorkflowRegistry(workflows=(placement_workflow(service),))
    engine = RunEngine(
        ledger=ledger,
        bus=InProcessEventBus(ledger=ledger),
        workflows=registry,
        queue_router=QueueRouter(routing={"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": _CapturedQueue()},
        consents=consents,
    )
    session = await DbBridgeSessionStore(factory, sigil_name="builder").create_session(title="Placement SQL fixture")
    result = await service.submit(
        fixture.request,
        engine=engine,
        ledger=ledger,
        session_id=session.id,
        principal=Sigil(name="builder", scopes=frozenset({"blockworld:place"})),
    )
    assert result["kind"] == "admitted"
    return store, result["run_id"], consents


@pytest.mark.asyncio
async def test_concurrent_preparation_has_one_action_and_consent(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    store, run_id, _ = await _admit(pg_factory)
    prepared = await asyncio.gather(
        store.prepare_and_admit(run_id), DbPlacementStore(pg_factory, _Authority()).prepare_and_admit(run_id)
    )
    assert prepared[0] == prepared[1]
    async with pg_factory() as session:
        assert await session.scalar(select(func.count()).select_from(BlockworldPlacementAction)) == 1
        assert await session.scalar(select(func.count()).select_from(Consent)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("judgment_mode", ["live", "exact_preauth"])
async def test_action_insert_failure_rolls_back_consent(
    pg_factory: async_sessionmaker[AsyncSession], judgment_mode: str
) -> None:
    store, run_id, _ = await _admit(pg_factory, judgment_mode)
    if judgment_mode == "exact_preauth":
        await _install_exact_policy(pg_factory, run_id)
    async with pg_factory() as session:
        await session.execute(
            text(
                "CREATE FUNCTION reject_placement_insert() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected placement insert failure'; END $$"
            )
        )
        await session.execute(
            text(
                "CREATE TRIGGER reject_placement BEFORE INSERT ON blockworld_placement_action FOR EACH ROW EXECUTE FUNCTION reject_placement_insert()"
            )
        )
        await session.commit()
    try:
        with pytest.raises(DBAPIError, match="injected placement insert failure"):
            await store.prepare_and_admit(run_id)
        async with pg_factory() as session:
            assert await session.scalar(select(func.count()).select_from(BlockworldPlacementAction)) == 0
            assert await session.scalar(select(func.count()).select_from(Consent)) == 0
            if judgment_mode == "exact_preauth":
                assert (await _policy(session, 20)).uses == 0
                assert (await _policy(session, 21)).uses == 0
        with pytest.raises(PlacementNotFoundError):
            await store.read_action(identity(3))
    finally:
        async with pg_factory() as session:
            await session.execute(text("DROP TRIGGER reject_placement ON blockworld_placement_action"))
            await session.execute(text("DROP FUNCTION reject_placement_insert()"))
            await session.commit()


@pytest.mark.asyncio
async def test_one_committed_claim_survives_core_deletion_and_restricts_mission(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store, run_id, consents = await _admit(pg_factory)
    prepared = await store.prepare_and_admit(run_id)
    assert isinstance(prepared, PreparedAction)
    await consents.decide(
        prepared.consent_id, approved=True, decided_by="test:operator", expected_native_binding=prepared.native_binding
    )
    principal = Sigil(name="builder", scopes=frozenset({"blockworld:place"}))
    claims = await asyncio.gather(
        store.claim_issue(identity(3), prepared.native_binding, principal),
        DbPlacementStore(pg_factory, _Authority()).claim_issue(identity(3), prepared.native_binding, principal),
    )
    assert sum(isinstance(claim, NewClaim) for claim in claims) == 1
    async with pg_factory() as session:
        await session.execute(delete(Run).where(Run.id == UUID(run_id)))
        await session.commit()
    action = await DbPlacementStore(pg_factory, _Authority()).read_action(identity(3))
    assert action.status == "pending"
    assert action.issuance_judgment is not None
    assert action.issuance_judgment["consent_id"] == prepared.consent_id
    async with pg_factory() as session:
        assert await session.get(Consent, UUID(prepared.consent_id)) is None
        with pytest.raises(DBAPIError):
            await session.execute(
                delete(BlockworldPlacementMission).where(BlockworldPlacementMission.id == UUID(identity(2)))
            )


def _expected_digest(run_id: str) -> str:
    """Independently encode the protocol fixture, without the production builder."""
    fixture = admitted_document()
    request = fixture["request"]
    command = {
        "schema_version": 1,
        "operation": "place_block",
        "request_id": identity(1),
        "mission_id": identity(2),
        "action_id": identity(3),
        "run_id": run_id,
        "principal": {"name": "builder", "scopes": ["blockworld:place"]},
        "composition": {"key": "blockworld.inhabitant", "revision": "2"},
        "pattern": {
            "key": "blockworld.bounded_mission",
            "revision": "2",
            "manifest_digest": fixture["pattern_snapshot"]["digest"],
        },
        "adapter": {"key": "inert-placement", "revision": "1"},
        "mode": "managed",
        "server_id": identity(4),
        "world_id": identity(5),
        "world_epoch": 2,
        "bot_id": identity(6),
        "capability_revision": "test.1",
        "blueprint_id": identity(7),
        "blueprint_digest": "1" * 64,
        "plot": {"id": identity(8), "min": [-1, 63, -1], "max": [1, 65, 1]},
        "lease": {"id": identity(9), "generation": 2, "expires_at": "2035-01-01T12:02:00Z"},
        "mission_policy": {"id": identity(10), "generation": 3},
        "authority_generation": 4,
        "target": [0, 64, 0],
        "block_state": {"name": "test:stone", "properties": {"axis": "y"}},
        "target_before_digest": "3" * 64,
        "inventory_generation": 5,
        "inventory_digest": "4" * 64,
        "inventory_change": request["inventory_change"],
        "expected_cursor": 0,
        "deadline": "2035-01-01T12:01:00Z",
        "placement_budget": 1,
        "postcondition": {
            "target": [0, 64, 0],
            "block_state": {"name": "test:stone", "properties": {"axis": "y"}},
            "inventory_after": 1,
            "cursor": 1,
            "proof": "matching_response_and_authoritative_event",
        },
    }
    encoded = json.dumps(command, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return sha256(b"lychd.blockworld.placement.v1\n" + encoded).hexdigest()


async def _install_exact_policy(factory: async_sessionmaker[AsyncSession], run_id: str) -> None:
    async with factory() as session:
        session.add(
            CodexPreauthorization(
                id=UUID(identity(20)),
                slug="placement-exact",
                priority=1,
                klass="standard",
                sigil_pattern="builder",
                tool_pattern="blockworld.place_block",
                constraints={
                    "args": {
                        "action_id": [identity(3)],
                        "mission_id": [identity(2)],
                        "preparation_digest": [_expected_digest(run_id)],
                    }
                },
                expires_at=datetime(2035, 1, 1, 12, 1, tzinfo=UTC),
                max_uses=1,
                uses=0,
                enabled=True,
                source_present=True,
                granted_by="test:trusted-fixture",
            )
        )
        session.add(
            CodexPreauthorization(
                id=UUID(identity(21)),
                slug="broad-priority",
                priority=100,
                klass="standard",
                sigil_pattern="*",
                tool_pattern="*",
                constraints={},
                expires_at=None,
                max_uses=None,
                uses=0,
                enabled=True,
                source_present=True,
                granted_by="test:trusted-fixture",
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_exact_policy_last_use_remains_valid_but_source_revocation_before_final_refuses(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    from sqlalchemy import update

    store, run_id, _ = await _admit(pg_factory, "exact_preauth")
    await _install_exact_policy(pg_factory, run_id)
    prepared = await store.prepare_and_admit(run_id)
    assert isinstance(prepared, PreparedAction)
    principal = Sigil(name="builder", scopes=frozenset({"blockworld:place"}))
    claim = await store.claim_issue(identity(3), prepared.native_binding, principal)
    assert isinstance(claim, NewClaim)
    async with pg_factory() as session:
        exact = await _policy(session, 20)
        broad = await _policy(session, 21)
        assert (exact.uses, broad.uses) == (1, 0)
        await session.execute(
            update(CodexPreauthorization).where(CodexPreauthorization.id == exact.id).values(source_present=False)
        )
        await session.commit()
    outcome = await DbPlacementStore(pg_factory, _Authority()).validate_live_claim_before_invoke(claim, principal)
    assert isinstance(outcome, Refused)
    assert outcome.result.reason == "policy_changed"
    assert (await store.read_action(identity(3))).status == "not_issued"
    assert (await store.load_for_run(run_id)).pending_action_id is None


@pytest.mark.asyncio
async def test_missing_exact_policy_refusal_survives_later_policy_install(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store, run_id, _ = await _admit(pg_factory, "exact_preauth")
    first = await store.prepare_and_admit(run_id)
    await _install_exact_policy(pg_factory, run_id)
    second = await DbPlacementStore(pg_factory, _Authority()).prepare_and_admit(run_id)
    assert first == second
    async with pg_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Consent)) == 0
        assert await session.scalar(select(func.count()).select_from(BlockworldPlacementAction)) == 0
        assert (await _policy(session, 20)).uses == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("committed", [False, True])
async def test_mission_refusal_commit_uncertainty_uses_fresh_identity_without_expired_row_io(
    pg_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch, *, committed: bool
) -> None:
    store, run_id, _ = await _admit(pg_factory, "exact_preauth")
    original = AsyncSession.commit
    calls = 0

    async def lose_ack(session: AsyncSession) -> None:
        nonlocal calls
        calls += 1
        if committed:
            await original(session)
        msg = "injected commit acknowledgement loss"
        raise RuntimeError(msg)

    monkeypatch.setattr(AsyncSession, "commit", lose_ack)
    if committed:
        result = await store.prepare_and_admit(run_id)
        assert isinstance(result, Refused)
        assert result.result.kind == "not_issued"
    else:
        with pytest.raises(PlacementCommitUnknownError):
            await store.prepare_and_admit(run_id)
    assert calls == 1
    retained = await DbPlacementStore(pg_factory, _Authority()).load_for_run(run_id)
    assert (retained.result is not None) is committed


def _observed(digest: str) -> PlacementEvidence:
    return PlacementEvidence.model_validate(
        {
            "kind": "observed",
            "response": {
                "action_id": identity(3),
                "preparation_digest": digest,
                "server_id": identity(4),
                "world_id": identity(5),
                "world_epoch": 2,
                "bot_id": identity(6),
                "response_id": "response.1",
                "accepted": True,
            },
            "event": {
                "action_id": identity(3),
                "preparation_digest": digest,
                "server_id": identity(4),
                "world_id": identity(5),
                "world_epoch": 2,
                "bot_id": identity(6),
                "event_id": "event.1",
                "event_sequence": 7,
                "target": [0, 64, 0],
                "block_state": {"name": "test:stone", "properties": {"axis": "y"}},
                "inventory_after": 1,
                "cursor_before": 0,
                "cursor_after": 1,
            },
        }
    )


@pytest.mark.asyncio
async def test_receipt_failure_rolls_back_cursor_and_budget_then_settles_once(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store, run_id, consents = await _admit(pg_factory)
    prepared = await store.prepare_and_admit(run_id)
    assert isinstance(prepared, PreparedAction)
    await consents.decide(
        prepared.consent_id, approved=True, decided_by="test:operator", expected_native_binding=prepared.native_binding
    )
    await store.claim_issue(
        identity(3), prepared.native_binding, Sigil(name="builder", scopes=frozenset({"blockworld:place"}))
    )
    async with pg_factory() as session:
        await session.execute(
            text(
                "CREATE FUNCTION reject_placement_receipt() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.status = 'verified' THEN RAISE EXCEPTION 'injected receipt failure'; END IF; RETURN NEW; END $$"
            )
        )
        await session.execute(
            text(
                "CREATE TRIGGER reject_receipt BEFORE UPDATE ON blockworld_placement_action FOR EACH ROW EXECUTE FUNCTION reject_placement_receipt()"
            )
        )
        await session.commit()
    try:
        with pytest.raises(DBAPIError, match="injected receipt failure"):
            await store.settle_verified(identity(3), _observed(_expected_digest(run_id)))
        fresh = DbPlacementStore(pg_factory, _Authority())
        assert (await fresh.read_action(identity(3))).receipt_bytes is None
        mission = await fresh.load_for_run(run_id)
        assert (mission.cursor, mission.placements_remaining) == (0, 1)
    finally:
        async with pg_factory() as session:
            await session.execute(text("DROP TRIGGER reject_receipt ON blockworld_placement_action"))
            await session.execute(text("DROP FUNCTION reject_placement_receipt()"))
            await session.commit()
    outcomes = await asyncio.gather(
        store.settle_verified(identity(3), _observed(_expected_digest(run_id))),
        DbPlacementStore(pg_factory, _Authority()).settle_verified(identity(3), _observed(_expected_digest(run_id))),
    )
    assert outcomes[0] == outcomes[1]
    mission = await store.load_for_run(run_id)
    assert (mission.cursor, mission.placements_remaining) == (1, 0)


@pytest.mark.asyncio
async def test_final_check_samples_database_wall_time_after_authority_await(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with pg_factory() as session:
        deadline = await _wall_time(session) + timedelta(seconds=5)
    store, run_id, consents = await _admit(pg_factory, deadline=deadline.isoformat().replace("+00:00", "Z"))
    prepared = await store.prepare_and_admit(run_id)
    assert isinstance(prepared, PreparedAction)
    await consents.decide(
        prepared.consent_id, approved=True, decided_by="test:operator", expected_native_binding=prepared.native_binding
    )
    principal = Sigil(name="builder", scopes=frozenset({"blockworld:place"}))
    claim = await store.claim_issue(identity(3), prepared.native_binding, principal)
    assert isinstance(claim, NewClaim)
    entered, release = asyncio.Event(), asyncio.Event()

    class PausedAuthority(_Authority):
        async def current(self, command_bytes: bytes, principal: Sigil) -> CurrentPlacementFacts:
            entered.set()
            await release.wait()
            return await super().current(command_bytes, principal)

    final = asyncio.create_task(
        DbPlacementStore(pg_factory, PausedAuthority()).validate_live_claim_before_invoke(claim, principal)
    )
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        async with pg_factory() as session:
            before = await _wall_time(session)
            assert before < deadline
            await session.execute(select(func.pg_sleep((deadline - before).total_seconds() + 0.02)))
            assert await _wall_time(session) >= deadline
    finally:
        release.set()
    result = await final
    assert isinstance(result, Refused)
    assert result.result.reason == "deadline_expired"
    assert (await store.read_action(identity(3))).status == "not_issued"


@pytest.mark.asyncio
async def test_claim_commit_ack_loss_never_reconstructs_issuance_entitlement(
    pg_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import AsyncMock

    from lychd.compositions.blockworld.ports import ExistingDisposition

    store, run_id, consents = await _admit(pg_factory)
    prepared = await store.prepare_and_admit(run_id)
    assert isinstance(prepared, PreparedAction)
    await consents.decide(
        prepared.consent_id, approved=True, decided_by="test:operator", expected_native_binding=prepared.native_binding
    )
    principal = Sigil(name="builder", scopes=frozenset({"blockworld:place"}))
    original = AsyncSession.commit
    lost = False

    async def lose_first_ack(session: AsyncSession) -> None:
        nonlocal lost
        await original(session)
        if not lost:
            lost = True
            msg = "claim committed; acknowledgement lost"
            raise RuntimeError(msg)

    monkeypatch.setattr(AsyncSession, "commit", lose_first_ack)
    with pytest.raises(PlacementCommitUnknownError):
        await store.claim_issue(identity(3), prepared.native_binding, principal)
    fresh = DbPlacementStore(pg_factory, _Authority())
    replay = await fresh.claim_issue(identity(3), prepared.native_binding, principal)
    assert isinstance(replay, ExistingDisposition)
    assert replay.status == "pending"
    action = await fresh.read_action(identity(3))
    effect = AsyncMock()
    effect.status.return_value = UnknownEvidence(
        kind="unknown", action_id=identity(3), preparation_digest=action.preparation_digest
    )
    result = await PlacementService(fresh, _Authority(), effect).execute(
        identity(3), prepared.native_binding, principal
    )
    assert result.kind == "unverified_effect"
    effect.invoke.assert_not_awaited()
    effect.status.assert_awaited_once_with(action.command_bytes)


@pytest.mark.asyncio
async def test_settlement_commit_ack_loss_recovers_same_receipt_and_limits(
    pg_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    store, run_id, consents = await _admit(pg_factory)
    prepared = await store.prepare_and_admit(run_id)
    assert isinstance(prepared, PreparedAction)
    await consents.decide(
        prepared.consent_id, approved=True, decided_by="test:operator", expected_native_binding=prepared.native_binding
    )
    await store.claim_issue(
        identity(3), prepared.native_binding, Sigil(name="builder", scopes=frozenset({"blockworld:place"}))
    )
    original = AsyncSession.commit
    lost = False

    async def lose_first_ack(session: AsyncSession) -> None:
        nonlocal lost
        await original(session)
        if not lost:
            lost = True
            msg = "receipt committed; acknowledgement lost"
            raise RuntimeError(msg)

    monkeypatch.setattr(AsyncSession, "commit", lose_first_ack)
    evidence = _observed(_expected_digest(run_id))
    with pytest.raises(PlacementCommitUnknownError):
        await store.settle_verified(identity(3), evidence)
    fresh = DbPlacementStore(pg_factory, _Authority())
    before = await fresh.read_action(identity(3))
    replay = await fresh.settle_verified(identity(3), evidence)
    after = await fresh.read_action(identity(3))
    assert replay.kind == "verified"
    assert before.receipt_bytes == after.receipt_bytes
    assert before.receipt_digest == after.receipt_digest == replay.receipt_digest
    mission = await fresh.load_for_run(run_id)
    assert (mission.cursor, mission.placements_remaining, mission.pending_action_id) == (1, 0, None)
    assert mission.result == replay


@pytest.mark.asyncio
async def test_exact_policy_expiring_during_candidate_await_is_not_consumed(
    pg_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    from lychd.domain.codex.services import PreauthService

    store, run_id, _ = await _admit(pg_factory, "exact_preauth")
    await _install_exact_policy(pg_factory, run_id)
    async with pg_factory() as session:
        policy = await _policy(session, 20)
        expiry = await _wall_time(session) + timedelta(seconds=3)
        policy.expires_at = expiry
        await session.commit()
    original = PreauthService.get_many
    calls = 0

    async def delay_candidates(service: PreauthService, *args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        rows = await original(service, *args, **kwargs)
        calls += 1
        session = service.repository.session
        before = await _wall_time(session)
        assert before < expiry
        await session.execute(select(func.pg_sleep((expiry - before).total_seconds() + 0.02)))
        assert await _wall_time(session) >= expiry
        return rows

    monkeypatch.setattr(PreauthService, "get_many", delay_candidates)
    result = await store.prepare_and_admit(run_id)
    assert calls == 1
    assert isinstance(result, Refused)
    assert result.result.reason == "policy_changed"
    async with pg_factory() as session:
        assert (await _policy(session, 20)).uses == 0
        assert (await _policy(session, 21)).uses == 0
        assert await session.scalar(select(func.count()).select_from(Consent)) == 0
        assert await session.scalar(select(func.count()).select_from(BlockworldPlacementAction)) == 0
