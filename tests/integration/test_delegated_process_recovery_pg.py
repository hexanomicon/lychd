"""[LINUX] Clean-process delegated Graph recovery over an Alembic-upgraded database.

Two sequential spawn children construct independent Run/AgentJob/session/checkpoint
adapters. The no-effect reference runtime is held pending only in the first child.
The second reconstructs its pure result and resumes the retained delegated_rite@2
binding despite a changed admission default. Queue delivery is captured; neighboring
capability and consent ports are inert. This proves no crash, broker, application
startup, provider execution, or Coffin containment boundary.
"""

# pyright: reportPrivateUsage=false
# pyright: reportMissingImports=false
from __future__ import annotations

import asyncio
import json
import multiprocessing
import os
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pydantic_ai.models
import pytest

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from advanced_alchemy.alembic.commands import AlembicCommandConfig
from alembic import command
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from lychd.agents.router import Intent
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.agents.workflows.delegated_rite import (
    DELEGATED_RITE_BOUND,
    BoundDelegatedRiteState,
    DispatchBoundDelegate,
)
from lychd.config.constants import DB_MIGRATION_VERSION_TABLE, PATH_MIGRATION_CONFIG
from lychd.config.settings.weaver import DelegationCastingSettings, WeaverSettings
from lychd.db.checkpoints import PostgresStasisStore
from lychd.db.delegation import DbDelegatedAgentJobStore
from lychd.db.models import DelegatedAgentEventRecord, DelegatedAgentJobRecord, Run, RunDelivery, Step
from lychd.db.sessions import DbBridgeSessionStore
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus, RunEventKind
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.cortex.runs import RunDeliveryState, RunStatus
from lychd.domain.cortex.stasis import DurableStasisPhylactery, NodeSnapshot
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.delegation.models import (
    DelegatedAgentEventKind,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentProfile,
    DelegatedAgentRequest,
    DelegatedAgentResult,
    DelegatedRequest,
)
from lychd.domain.delegation.routing import DelegatedRuntimeBinding
from lychd.domain.delegation.services import DelegatedAgentCoordinator
from lychd.domain.web.fragments import build_fragment_registry
from lychd.extensions.builtin.delegation.reference import ReferenceDelegatedAgentRuntime
from lychd.ghouls.runs import _reconcile_delegate_page, perform_run
from tests.agents.fakes import FakeConsents, FakeDispatcher, FakeOrchestrator, FakeRegistry
from tests.support.blockworld import CapturedQueue

if TYPE_CHECKING:
    from collections.abc import Iterator
    from multiprocessing.connection import Connection

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.container]

_TASK = "carry the retained binding across processes"
_PROMPT = f"/delegate {_TASK}"
_ADMISSION_KEY = "delegated-clean-process-v2"
_SIGIL = "delegated-process-receipt"
_MAX_PAYLOAD = 4092  # One JSON report plus the Pipe header fits Linux PIPE_BUF.
_CHILD_SECONDS = 45
_CLEANUP_SECONDS = 5
_READ_BINDING = DelegatedRuntimeBinding(runtime="reference", profile=DelegatedAgentProfile.READ)


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    """Own a fresh disposable database and apply the actual linear migration head."""
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            command.upgrade(
                AlembicCommandConfig(
                    engine=engine,
                    version_table_name=DB_MIGRATION_VERSION_TABLE,
                    file_=PATH_MIGRATION_CONFIG,
                    render_as_batch=False,
                ),
                "head",
            )
        finally:
            asyncio.run(engine.dispose())
        yield url


@dataclass(frozen=True)
class _Identity:
    run_id: str
    session_id: str
    job_id: str
    request_id: str

    def validate(self) -> None:
        """Keep the handoff to four bounded identities, never serialized collaborators."""
        for value in (self.run_id, self.session_id, self.job_id, self.request_id):
            assert str(UUID(value)) == value


class _ObservedReferenceRuntime(ReferenceDelegatedAgentRuntime):
    """Record calls while preserving reference behavior except child A's held poll."""

    def __init__(self, *, hold_poll: bool) -> None:
        super().__init__()
        self.hold_poll = hold_poll
        self.starts = 0
        self.polls = 0
        self.poll_requests: list[DelegatedRequest] = []
        self.rehydrations = 0

    async def start(self, request: DelegatedRequest, job: DelegatedAgentJobRef) -> None:
        self.starts += 1
        await super().start(request, job)

    async def rehydrate_effect_free(self, request: DelegatedRequest, job: DelegatedAgentJobRef) -> None:
        self.rehydrations += 1
        await super().rehydrate_effect_free(request, job)

    async def poll(self, job: DelegatedAgentJobRef, *, request: DelegatedRequest) -> DelegatedAgentResult | None:
        self.polls += 1
        self.poll_requests.append(request)
        result = await super().poll(job, request=request)
        return None if self.hold_poll else result


@dataclass
class _Boot:
    database: AsyncEngine
    factory: async_sessionmaker[AsyncSession]
    ledger: DbRunLedger
    bus: InProcessEventBus
    sessions: DbBridgeSessionStore
    runtime: _ObservedReferenceRuntime
    delegates: DelegatedAgentCoordinator
    queue: CapturedQueue
    substrate: RunSubstrate
    engine: RunEngine


async def _boot(url: str, *, first: bool) -> _Boot:
    """Construct every process-owned handle anew; no database schema shortcuts."""
    database = create_async_engine(url)
    factory = async_sessionmaker(database, expire_on_commit=False)
    ledger = DbRunLedger(session_factory=factory)
    bus = InProcessEventBus(ledger=ledger)
    sessions = DbBridgeSessionStore(factory, sigil_name=_SIGIL)
    stasis = PostgresStasisStore(factory)
    runtime = _ObservedReferenceRuntime(hold_poll=first)
    delegates = DelegatedAgentCoordinator(runtimes={runtime.name: runtime}, store=DbDelegatedAgentJobStore(factory))
    casting = DelegationCastingSettings(
        revision="2",
        runtime="reference",
        profile=DelegatedAgentProfile.READ if first else DelegatedAgentProfile.CANDIDATE,
    )
    workflows = builtin_workflow_registry(weaver=WeaverSettings(delegation=casting))
    queue = CapturedQueue()
    substrate = RunSubstrate(
        ledger=ledger,
        bus=bus,
        workflows=workflows,
        orchestrator=FakeOrchestrator(),
        dispatcher=FakeDispatcher(model=None),
        context=ContextOrchestrator(registry=FakeRegistry()),
        fragments=build_fragment_registry(),
        turns=sessions,
        forge=default_forge(),
        consents=FakeConsents(),
        queues={"runs": queue},
        stasis_store=stasis,
        delegates=delegates,
    )
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=workflows,
        queue_router=QueueRouter(routing={"default": RouteRule(queue="runs", priority=50)}),
        queues=substrate.queues,
        stasis_store=stasis,
        delegates=delegates,
        delegation_binding=casting.binding(),
    )
    return _Boot(database, factory, ledger, bus, sessions, runtime, delegates, queue, substrate, engine)


def _intent(session_id: str) -> Intent:
    return Intent(session_id=session_id, prompt=_PROMPT, sigil_name=_SIGIL)


async def _assert_parked(boot: _Boot, identity: _Identity) -> None:
    """Read the exact retained owner, request and typed resumable snapshot."""
    identity.validate()
    run = await boot.ledger.get(identity.run_id)
    assert run is not None
    assert (run.status, run.enqueue_seq) == (RunStatus.AWAITING_DELEGATE, 0)
    assert (run.session_id, run.delegated_job_id, run.consent_id) == (identity.session_id, identity.job_id, None)
    assert run.sigil_name == _SIGIL
    assert run.pattern_manifest == DELEGATED_RITE_BOUND.manifest.snapshot()
    assert run.admitted_delegation == _READ_BINDING
    assert run.to_intent().admitted_delegation == _READ_BINDING
    job = await boot.delegates.get(identity.job_id)
    assert job is not None
    assert job.status is DelegatedAgentJobStatus.RUNNING
    assert job.result is None
    assert job.request == DelegatedAgentRequest(
        request_id=identity.request_id,
        run_id=identity.run_id,
        step_id="dispatch_delegate",
        runtime="reference",
        profile=DelegatedAgentProfile.READ,
        prompt=_TASK,
    )
    assert (job.ref.request_id, job.ref.run_id, job.ref.runtime, job.ref.profile) == (
        identity.request_id,
        identity.run_id,
        "reference",
        DelegatedAgentProfile.READ,
    )
    persistence = DurableStasisPhylactery(job_id=identity.run_id, store=boot.substrate.stasis_store)
    persistence.set_graph_types(DELEGATED_RITE_BOUND.graph)
    snapshots = await persistence.load_all()
    resumable = [
        snapshot for snapshot in snapshots if isinstance(snapshot, NodeSnapshot) and snapshot.status == "created"
    ]
    assert len(resumable) == 1
    snapshot = resumable[0]
    assert isinstance(snapshot.node, DispatchBoundDelegate)
    state = snapshot.state
    assert isinstance(state, BoundDelegatedRiteState)
    assert (state.run_id, state.session_id, state.request_id, state.job_id) == (
        identity.run_id,
        identity.session_id,
        identity.request_id,
        identity.job_id,
    )
    assert state.binding == _READ_BINDING
    assert DELEGATED_RITE_BOUND.validate_state is not None
    DELEGATED_RITE_BOUND.validate_state(run.to_intent(), state)
    delivery = await boot.ledger.get_delivery(identity.run_id, enqueue_seq=0)
    assert delivery is not None
    assert not delivery.resume
    assert delivery.state is RunDeliveryState.SETTLED
    assert not any(event.kind is RunEventKind.DONE for event in await boot.ledger.list_events(identity.run_id))


async def _first(boot: _Boot) -> _Identity:
    session = await boot.sessions.create_session(title="Delegated process recovery")
    handle = await boot.engine.submit(_intent(session.id), idempotency_key=_ADMISSION_KEY)
    assert len(boot.queue.attempts) == 1
    assert boot.queue.attempts[0]["enqueue_seq"] == 0
    result = await perform_run({"run_substrate": boot.substrate}, run_id=handle.run_id, enqueue_seq=0)
    assert result["status"] == RunStatus.AWAITING_DELEGATE.value
    jobs = await boot.delegates.jobs_for_run(handle.run_id)
    assert len(jobs) == 1
    identity = _Identity(handle.run_id, session.id, jobs[0].ref.job_id, jobs[0].request.request_id)
    await boot.bus.wait_persisted(identity.run_id)
    await _assert_parked(boot, identity)
    assert (boot.runtime.starts, boot.runtime.polls) == (1, 1)
    assert boot.runtime.poll_requests == [jobs[0].request]
    assert len(boot.queue.attempts) == 1
    return identity


async def _second(boot: _Boot, identity: _Identity) -> None:  # noqa: PLR0915 - one retained recovery chain
    await _assert_parked(boot, identity)
    assert boot.engine.delegation_binding != _READ_BINDING
    assert (boot.runtime.starts, boot.runtime.polls, boot.runtime.rehydrations) == (0, 0, 0)
    job = await boot.delegates.get(identity.job_id)
    assert job is not None
    assert await boot.delegates.submit(job.request) == job.ref
    replay = await boot.engine.submit(_intent(identity.session_id), idempotency_key=_ADMISSION_KEY)
    assert replay.run_id == identity.run_id
    assert boot.queue.attempts == []
    assert boot.runtime.starts == 0

    result, cursor = await _reconcile_delegate_page(boot.engine, after=None)
    assert result["status"] == "reconciled"
    assert result["count"] == 1
    assert result["probe_errors"] == 0
    assert cursor is None
    assert (boot.runtime.starts, boot.runtime.polls, boot.runtime.rehydrations) == (0, 1, 1)
    assert boot.runtime.poll_requests == [job.request]
    assert len(boot.queue.attempts) == 1
    assert boot.queue.attempts[0]["run_id"] == identity.run_id
    assert boot.queue.attempts[0]["enqueue_seq"] == 1
    resumed = await boot.ledger.get_delivery(identity.run_id, enqueue_seq=1)
    assert resumed is not None
    assert resumed.resume
    assert resumed.state is RunDeliveryState.PUBLISHED
    assert await boot.engine.resume_delegate(identity.job_id) is False
    again, _ = await _reconcile_delegate_page(boot.engine, after=None)
    assert again["count"] == 0
    assert again["probe_errors"] == 0
    stale = await perform_run({"run_substrate": boot.substrate}, run_id=identity.run_id, enqueue_seq=0)
    assert stale["status"] == "skipped"
    finished = await perform_run({"run_substrate": boot.substrate}, run_id=identity.run_id, enqueue_seq=1, resume=False)
    assert finished["status"] == "done"  # Durable delivery, rather than payload, owns resume mode.
    await boot.bus.wait_persisted(identity.run_id)
    job = await boot.delegates.get(identity.job_id)
    assert job is not None
    assert job.status is DelegatedAgentJobStatus.SUCCEEDED
    assert job.result is not None
    assert job.request.profile is DelegatedAgentProfile.READ
    assert job.result.output == f"Reference delegate completed: {_TASK}"
    assert await boot.delegates.adopt(identity.job_id, job.result) is False
    assert await boot.delegates.submit(job.request) == job.ref
    assert await boot.engine.resume_delegate(identity.job_id) is False
    assert (await _reconcile_delegate_page(boot.engine, after=None))[0]["count"] == 0
    for sequence in (0, 1):
        duplicate = await perform_run({"run_substrate": boot.substrate}, run_id=identity.run_id, enqueue_seq=sequence)
        assert duplicate["status"] == "skipped"
    assert (
        await boot.engine.submit(_intent(identity.session_id), idempotency_key=_ADMISSION_KEY)
    ).run_id == identity.run_id
    assert (boot.runtime.starts, boot.runtime.polls, boot.runtime.rehydrations) == (0, 1, 1)
    assert boot.runtime.poll_requests == [job.request]
    assert len(boot.queue.attempts) == 1

    run = await boot.ledger.get(identity.run_id)
    assert run is not None
    assert run.status is RunStatus.DONE
    assert (run.enqueue_seq, run.delegated_job_id) == (1, identity.job_id)
    assert run.pattern_manifest == DELEGATED_RITE_BOUND.manifest.snapshot()
    assert run.admitted_delegation == _READ_BINDING
    assert not await boot.substrate.stasis_store.exists(identity.run_id)
    session = await boot.sessions.get_session(identity.session_id)
    assert session is not None
    assert len(session.turns) == 1
    assert (session.turns[0].run_id, session.turns[0].state, session.turns[0].content) == (
        identity.run_id,
        "settled",
        job.result.output,
    )
    events = await boot.ledger.list_events(identity.run_id)
    assert sum(event.kind is RunEventKind.DONE for event in events) == 1
    assert sum(event.kind is RunEventKind.STATUS and event.data == RunStatus.RUNNING.value for event in events) == 2
    assert [event.seq for event in events] == list(range(len(events)))
    assert sum(event.kind is DelegatedAgentEventKind.RESULT_ADOPTED for event in job.events) == 1
    async with boot.factory() as database_session:
        assert await database_session.scalar(select(func.count()).select_from(Run)) == 1
        assert await database_session.scalar(select(func.count()).select_from(DelegatedAgentJobRecord)) == 1
        assert await database_session.scalar(select(func.count()).select_from(RunDelivery)) == 2
        assert (
            await database_session.scalar(
                select(func.count())
                .select_from(DelegatedAgentEventRecord)
                .where(DelegatedAgentEventRecord.kind == DelegatedAgentEventKind.RESULT_ADOPTED.value)
            )
            == 1
        )
        assert (
            await database_session.scalar(
                select(func.count()).select_from(Step).where(Step.kind == RunEventKind.DONE.value)
            )
            == 1
        )
    for sequence in (0, 1):
        delivery = await boot.ledger.get_delivery(identity.run_id, enqueue_seq=sequence)
        assert delivery is not None
        assert delivery.state is RunDeliveryState.SETTLED


async def _run_child(url: str, identity: _Identity | None) -> dict[str, Any]:
    pydantic_ai.models.ALLOW_MODEL_REQUESTS = False
    boot = await _boot(url, first=identity is None)
    try:
        async with boot.factory() as session:
            assert await session.scalar(text("SELECT version_num FROM lychd_db_version")) == "0015"
        if identity is None:
            identity = await _first(boot)
        else:
            await _second(boot, identity)
        await boot.bus.wait_persisted(identity.run_id)
        return {
            "ok": True,
            "run_id": identity.run_id,
            "session_id": identity.session_id,
            "job_id": identity.job_id,
            "request_id": identity.request_id,
            "starts": boot.runtime.starts,
            "polls": boot.runtime.polls,
            "rehydrations": boot.runtime.rehydrations,
            "publications": len(boot.queue.attempts),
        }
    finally:
        try:
            await boot.bus.aclose()
        finally:
            await boot.database.dispose()


def _child(sender: Connection, url: str, identity: _Identity | None) -> None:
    """Report only bounded identities/counters after durable writers and pools close."""
    try:
        report = asyncio.run(_run_child(url, identity))
        report.update(pid=os.getpid(), parent_pid=os.getppid(), start_method=multiprocessing.get_start_method())
        payload = json.dumps(report).encode()
        assert len(payload) <= _MAX_PAYLOAD
        sender.send_bytes(payload)
    finally:
        sender.close()


def _spawn(url: str, identity: _Identity | None) -> dict[str, Any]:
    """Bound child exit before reading a single small report, always reap failures."""
    context = multiprocessing.get_context("spawn")
    reader, sender = context.Pipe(duplex=False)
    child = context.Process(target=_child, args=(sender, url, identity), daemon=False)
    started = False
    try:
        deadline = time.monotonic() + _CHILD_SECONDS
        child.start()
        started = True
        sender.close()
        child.join(max(0, deadline - time.monotonic()))
        assert not child.is_alive(), "delegated recovery child exceeded its deadline"
        assert child.exitcode == 0, f"delegated recovery child failed with exit code {child.exitcode}"
        assert reader.poll(0), "delegated recovery child exited without a receipt"
        report = json.loads(reader.recv_bytes(_MAX_PAYLOAD))
        assert isinstance(report, dict)
        assert report["ok"] is True
        assert report["pid"] == child.pid
        assert report["parent_pid"] == os.getpid()
        assert report["start_method"] == "spawn"
        return cast("dict[str, Any]", report)
    finally:
        reader.close()
        sender.close()
        if started and child.is_alive():
            child.terminate()
            child.join(_CLEANUP_SECONDS)
            if child.is_alive():
                child.kill()
                child.join(_CLEANUP_SECONDS)
        if started:
            assert not child.is_alive(), "delegated recovery child could not be reaped"
            child.close()


def test_delegated_rite_recovers_once_in_a_fresh_process(pg_url: str) -> None:
    assert sys.platform == "linux", "bounded atomic Pipe reports require the Linux receipt profile"
    first = _spawn(pg_url, None)  # Returns only after A exited and was joined/closed.
    identity = _Identity(*(first[key] for key in ("run_id", "session_id", "job_id", "request_id")))
    identity.validate()
    second = _spawn(pg_url, identity)
    assert first["pid"] != second["pid"]
    assert (first["starts"], second["starts"]) == (1, 0)
    assert (first["publications"], second["publications"]) == (1, 1)
    assert all(first[key] == second[key] for key in ("run_id", "session_id", "job_id", "request_id"))
