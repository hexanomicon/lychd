"""Webcrawler revision 4 through native Graph execution and PostgreSQL consent recovery.

Real admission, worker claims, Graph checkpoints, consent decisions, Webcrawler custody,
session settlement and terminal events share a disposable database. Queue publication,
dispatcher/model, Fetch syscalls and the extraction child remain controlled substitutes
from the older node proof. This does not qualify SAQ, network, model-service or sandbox
execution, nor a whole-process restart: the Webcrawler service retains its admitted authority.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.db.checkpoints import PostgresStasisStore
from lychd.db.models import RunCheckpoint, RunDelivery, WebcrawlerAttempt
from lychd.domain.codex.sigil import default_local_sigil
from lychd.domain.cortex.events import InProcessEventBus, RunEventKind
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.ghouls.runs import perform_run
from tests.integration import test_webcrawler_workflow_pg as database
from tests.integration.test_webcrawler_workflow_pg import (
    _ANSWER,  # pyright: ignore[reportPrivateUsage] - shared fixed oracle
    _PROMPT,  # pyright: ignore[reportPrivateUsage] - shared fixed oracle
    _SOURCE,  # pyright: ignore[reportPrivateUsage] - shared raw-source sentinel
    _URL,  # pyright: ignore[reportPrivateUsage] - shared fixed oracle
    _acquisition,  # pyright: ignore[reportPrivateUsage] - same controlled effects
    _synthetic_extraction_profile,  # pyright: ignore[reportPrivateUsage] - explicit synthetic runtime
)
from tests.webcrawler_workflow_fixture import WebcrawlerWorkflowFixture, assemble_workflow

pytestmark = [pytest.mark.asyncio, pytest.mark.integration, pytest.mark.container]
workflow_pg_url = database.workflow_pg_url
factory = database.factory


@pytest_asyncio.fixture
async def graph_factory(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Add the checkpoint table to the existing disposable custody database."""
    tables = [cast("Table", RunCheckpoint.__table__)]
    async with factory() as session, session.begin():
        connection = await session.connection()
        await connection.run_sync(RunCheckpoint.metadata.create_all, tables=tables)
    try:
        yield factory
    finally:
        async with factory() as session, session.begin():
            connection = await session.connection()
            await connection.run_sync(RunCheckpoint.metadata.drop_all, tables=tables)


class _ObservedStasisStore(PostgresStasisStore):
    """Retain readbacks of committed checkpoints, including ones later deleted."""

    def __init__(self, factory: async_sessionmaker[AsyncSession], writes: list[list[Any]]) -> None:
        super().__init__(factory)
        self.writes = writes

    async def replace(self, run_id: str, snapshots: list[Any]) -> None:
        await super().replace(run_id, snapshots)
        retained = await self.load(run_id)
        assert retained is not None
        self.writes.append(retained)


@asynccontextmanager
async def _worker(
    assembly: WebcrawlerWorkflowFixture,
    factory: async_sessionmaker[AsyncSession],
    writes: list[list[Any]],
) -> AsyncGenerator[RunSubstrate]:
    services = assembly.context.deps
    bus = InProcessEventBus(ledger=assembly.ledger)
    stasis = _ObservedStasisStore(factory, writes)
    engine = assembly.engine
    engine.bus, engine.consents, engine.stasis_store = bus, assembly.consents, stasis
    assert engine.workflows is not None
    substrate = RunSubstrate(
        ledger=assembly.ledger,
        bus=bus,
        workflows=engine.workflows,
        orchestrator=services.orchestrator,
        dispatcher=services.dispatcher,
        context=services.context,
        fragments=services.fragments,
        turns=assembly.turns,
        forge=services.forge,
        consents=assembly.consents,
        queues=engine.queues,
        stasis_store=stasis,
        effects=assembly.service,
        webcrawler=assembly.service,
    )
    try:
        yield substrate
    finally:
        await bus.aclose()


async def _park(assembly: WebcrawlerWorkflowFixture, substrate: RunSubstrate) -> tuple[str, list[Any]]:
    run_id = assembly.context.state.run_id
    assert (await perform_run({"run_substrate": substrate}, run_id=run_id, enqueue_seq=0))[
        "status"
    ] == "awaiting_consent"
    run = await assembly.ledger.get(run_id)
    assert run is not None
    assert run.status is RunStatus.AWAITING_CONSENT
    assert run.consent_id is not None
    snapshots = await substrate.stasis_store.load(run_id)
    assert snapshots is not None
    cursor = next(item for item in snapshots if item["kind"] == "node" and item["status"] == "created")
    assert cursor["node"]["node_id"] == "AwaitPageConsent"
    assert cursor["state"]["review"]["consent_id"] == run.consent_id
    await substrate.bus.wait_persisted(run_id)
    events = await assembly.ledger.list_events(run_id)
    assert any(event.kind is RunEventKind.CONSENT for event in events)
    assert not any(event.kind is RunEventKind.DONE for event in events)
    retained = await assembly.turns.get_session(assembly.context.state.session_id)
    assert retained is not None
    assert not retained.message_history
    return run.consent_id, snapshots


async def _decide(assembly: WebcrawlerWorkflowFixture, consent_id: str, *, approved: bool) -> None:
    consent = await assembly.consents.get(consent_id)
    assert consent is not None
    assert consent.status == "pending"
    resolution = await assembly.reviews.resolve(
        consent=consent,
        reviewer=default_local_sigil(),
        purpose="decide",
        authentication=assembly.authentication,
    )
    assert resolution.decision_allowed
    assert resolution.document is not None
    assert any(fact.value == _URL for fact in resolution.document.facts)
    decided = await assembly.consents.decide(
        consent_id,
        approved=approved,
        decided_by=default_local_sigil().name,
        expected_native_binding=resolution.binding,
    )
    assert decided is not None
    assert decided.status == ("granted" if approved else "denied")
    await assembly.engine.resume_consent(consent_id)
    await assembly.engine.resume_consent(consent_id)
    queued = await assembly.ledger.get(assembly.context.state.run_id)
    assert queued is not None
    assert queued.status is RunStatus.QUEUED
    assert queued.enqueue_seq == 1


@pytest.mark.parametrize("approved", [True, False], ids=["approved", "denied"])
async def test_webcrawler_worker_resumes_exact_durable_consent_and_settles_once(  # noqa: PLR0915 - one complete causal passage
    graph_factory: async_sessionmaker[AsyncSession], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, approved: bool
) -> None:
    assembly = await assemble_workflow(
        graph_factory,
        profile=_synthetic_extraction_profile(tmp_path),
        prompt=_PROMPT,
        answer=_ANSWER,
        claim_initial=False,
    )
    calls, launch = _acquisition(monkeypatch)
    writes: list[list[Any]] = []
    run_id = assembly.context.state.run_id
    async with _worker(assembly, graph_factory, writes) as substrate:
        consent_id, parked = await _park(assembly, substrate)
        assert calls == []
        assert assembly.model_requests == []
    # Replace the graph/store/event-bus instances. The continuation must come from
    # PostgreSQL; the original helper's GraphRunContext was never executed.
    async with _worker(assembly, graph_factory, writes) as substrate:
        await _decide(assembly, consent_id, approved=approved)
        stale = await perform_run({"run_substrate": substrate}, run_id=run_id, enqueue_seq=0)
        assert stale["status"] == "skipped"
        assert calls == []
        result = await perform_run({"run_substrate": substrate}, run_id=run_id, enqueue_seq=1)
        assert result["status"] == "done"
        cursor = next(item for item in parked if item["kind"] == "node" and item["status"] == "created")
        assert cursor["state"]["pending_consent_id"] == consent_id
        for sequence in (0, 1):
            duplicate = await perform_run({"run_substrate": substrate}, run_id=run_id, enqueue_seq=sequence)
            assert duplicate["status"] == "skipped"
        await assembly.engine.resume_consent(consent_id)
        run = await assembly.ledger.get(run_id)
        assert run is not None
        assert run.status is RunStatus.DONE
        assert run.enqueue_seq == 1
        assert not await substrate.stasis_store.exists(run_id)
        await substrate.bus.wait_persisted(run_id)
        events = await assembly.ledger.list_events(run_id)
        assert [event.data for event in events if event.kind is RunEventKind.DONE] == ["done"]
        assert [event.seq for event in events] == sorted({event.seq for event in events})
    assert calls == ([_URL] if approved else [])
    assert launch.await_count == int(approved)
    assert len(assembly.model_requests) == int(approved)
    if approved:
        assert _SOURCE.encode() in assembly.model_requests[0]
    assert writes
    assert _SOURCE not in json.dumps(writes)
    gate_states = [
        item["state"]
        for document in writes
        for item in document
        if item["kind"] == "node" and item["node"]["node_id"] == "AwaitPageConsent"
    ]
    assert gate_states
    assert all(state["pending_consent_id"] == consent_id for state in gate_states)
    settled_states = [
        item["state"]
        for document in writes
        for item in document
        if item["kind"] == "node" and item["node"]["node_id"] == "SettlePageAnswer"
    ]
    assert settled_states
    assert all(state["pending_consent_id"] is None for state in settled_states)
    retained = await assembly.turns.get_session(assembly.context.state.session_id)
    assert retained is not None
    turns = [turn for turn in retained.turns if turn.role == "agent"]
    assert len(turns) == 1
    assert turns[0].content == (_ANSWER if approved else "The public-page request was refused (consent).")
    assert turns[0].state == "settled"
    assert _SOURCE not in json.dumps(retained.message_history)
    async with graph_factory() as session:
        deliveries = list(
            (
                await session.scalars(
                    select(RunDelivery).where(RunDelivery.run_id == UUID(run_id)).order_by(RunDelivery.enqueue_seq)
                )
            ).all()
        )
        assert [(row.enqueue_seq, row.state, row.resume) for row in deliveries] == [
            (0, "settled", False),
            (1, "settled", True),
        ]
        attempts = list((await session.scalars(select(WebcrawlerAttempt))).all())
        assert len(attempts) == 1
        assert attempts[0].status == ("succeeded" if approved else "prepared")


@pytest.mark.parametrize("owner", ["missing", "wrong"])
async def test_webcrawler_worker_rejects_checkpoint_without_exact_consent_owner(
    graph_factory: async_sessionmaker[AsyncSession], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner: str
) -> None:
    assembly = await assemble_workflow(
        graph_factory,
        profile=_synthetic_extraction_profile(tmp_path),
        prompt=_PROMPT,
        answer=_ANSWER,
        claim_initial=False,
    )
    calls, launch = _acquisition(monkeypatch)
    writes: list[list[Any]] = []
    run_id = assembly.context.state.run_id
    async with _worker(assembly, graph_factory, writes) as substrate:
        consent_id, snapshots = await _park(assembly, substrate)
        cursor = next(item for item in snapshots if item["kind"] == "node" and item["status"] == "created")
        if owner == "missing":
            cursor["state"].pop("pending_consent_id", None)
        else:
            cursor["state"]["pending_consent_id"] = str(uuid4())
        await substrate.stasis_store.replace(run_id, snapshots)
        before = await assembly.ledger.list_events(run_id)
        await _decide(assembly, consent_id, approved=True)
        refusal = "consent owner" if owner == "missing" else "Webcrawler page answer refused: binding"
        with pytest.raises(ValueError, match=refusal):
            await perform_run({"run_substrate": substrate}, run_id=run_id, enqueue_seq=1)
        run = await assembly.ledger.get(run_id)
        assert run is not None
        assert run.status is RunStatus.FAILED
        assert not await substrate.stasis_store.exists(run_id)
        await substrate.bus.wait_persisted(run_id)
        after = await assembly.ledger.list_events(run_id)
        assert [event for event in after if event.kind is RunEventKind.NODE] == [
            event for event in before if event.kind is RunEventKind.NODE
        ]
        assert [event.data for event in after if event.kind is RunEventKind.DONE] == ["failed"]
        assert (await perform_run({"run_substrate": substrate}, run_id=run_id, enqueue_seq=1))["status"] == "skipped"
    assert calls == []
    launch.assert_not_called()
    assert assembly.model_requests == []
    assert _SOURCE not in json.dumps(writes)
    retained = await assembly.turns.get_session(assembly.context.state.session_id)
    assert retained is not None
    assert retained.turns[-1].state == "failed"
    assert _SOURCE not in json.dumps(retained.message_history)
