"""[LINUX] DbRunLedger durable-substrate suite (F4/H5): CAS matrix + seq fidelity.

WRITTEN HERE, DEFERRED to the explicit container-test runtime pass. The whole module is skipped
unless that dependency group is selected. It validates the durable ledger's concurrency story on
a real Postgres:

- CAS: `set_status` is a compare-and-swap; a CANCELLED write can NOT land over a DONE
  that won the race (0 rows updated → re-read → `IllegalRunTransitionError`), and an
  idempotent same-target concurrent write is benign.
- Seq fidelity: `append_event` persists `RunEvent.seq` VERBATIM as `Step.seq`
  (no insert-time allocation), so Step order equals emit order (Orb evidence).
- Factory wire compatibility: plain `json` and versioned `jsonb` both round-trip through the
  production asyncpg codec hook.
"""
# The ordinary contributor gate omits the optional container-test group; the whole module is
# importorskip'd there. SQLAlchemy Table vs FromClause noise on create_all remains locally ignored.
# pyright: reportMissingImports=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportArgumentType=false

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
import pytest_asyncio

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from sqlalchemy import JSON, bindparam, cast, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.agents.router import Intent
from lychd.config.settings.server import DatabaseSettings
from lychd.db.delegation import DbDelegatedAgentJobStore
from lychd.db.factory import create_db_engine
from lychd.db.models import (
    Consent,
    DelegatedAgentEventRecord,
    DelegatedAgentJobRecord,
    Run,
    RunDelivery,
    Session,
    Step,
)
from lychd.domain.cortex.events import InProcessEventBus, RunEvent, RunEventKind
from lychd.domain.cortex.ledger import DbRunLedger, RunAdmissionConflictError
from lychd.domain.cortex.runs import IllegalRunTransitionError, RunDeliveryState, RunStatus
from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentProfile,
    DelegatedAgentRequest,
)
from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.web.sessions import DbBridgeSessionStore

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    """Keep one disposable PostgreSQL container alive for this module."""
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest_asyncio.fixture
async def pg_factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Build and dispose the asyncpg pool on the current pytest event loop."""
    engine: AsyncEngine = create_async_engine(pg_url)
    tables = [
        Session.__table__,
        Run.__table__,
        RunDelivery.__table__,
        Step.__table__,
        Consent.__table__,
        DelegatedAgentJobRecord.__table__,
        DelegatedAgentEventRecord.__table__,
    ]
    async with engine.begin() as connection:
        await connection.run_sync(Run.metadata.drop_all, tables=tables)
        await connection.run_sync(Run.metadata.create_all, tables=tables)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _seed(ledger: DbRunLedger, run_id_hint: str = "") -> str:
    intent = Intent(session_id="s", run_id=run_id_hint or None, prompt="p", source="bridge")
    run = await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=70)
    return run.run_id


@pytest.mark.asyncio
async def test_nonterminal_session_query_is_filtered_and_bounded(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = DbBridgeSessionStore(pg_factory, sigil_name="magus")
    bridge_session = await store.create_session(title="bounded admission")
    other_session = await store.create_session(title="other")
    ledger = DbRunLedger(session_factory=pg_factory)

    async def create(session_id: str, prompt: str) -> str:
        run = await ledger.create(
            Intent(session_id=session_id, prompt=prompt, source="bridge"),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )
        return run.run_id

    terminal_id = await create(bridge_session.id, "terminal")
    await ledger.set_status(terminal_id, RunStatus.RUNNING)
    await ledger.set_status(terminal_id, RunStatus.DONE)
    first_active_id = await create(bridge_session.id, "active first")
    later_active_id = await create(bridge_session.id, "active later")
    await create(other_session.id, "other")

    active = await ledger.get_nonterminal_for_session(bridge_session.id)

    assert active is not None
    assert active.run_id == first_active_id
    await ledger.set_status(first_active_id, RunStatus.RUNNING)
    await ledger.set_status(first_active_id, RunStatus.DONE)
    active = await ledger.get_nonterminal_for_session(bridge_session.id)
    assert active is not None
    assert active.run_id == later_active_id

    await ledger.set_status(later_active_id, RunStatus.RUNNING)
    await ledger.set_status(later_active_id, RunStatus.DONE)
    assert await ledger.get_nonterminal_for_session(bridge_session.id) is None
    assert await ledger.get_nonterminal_for_session("not-a-uuid") is None


@pytest.mark.asyncio
async def test_delegated_job_limit_selects_newest_suffix_in_creation_order(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = await _seed(DbRunLedger(session_factory=pg_factory))
    store = DbDelegatedAgentJobStore(pg_factory)
    for index in range(3):
        request = DelegatedAgentRequest(
            request_id=f"bounded-request-{index}",
            run_id=run_id,
            step_id="bounded-step",
            runtime="reference",
            profile=DelegatedAgentProfile.READ,
            prompt="bounded prompt",
        )
        ref = DelegatedAgentJobRef(
            job_id=f"bounded-job-{index}",
            request_id=request.request_id,
            run_id=run_id,
            runtime=request.runtime,
            profile=request.profile,
        )
        await store.create(request, ref)
        await store.transition(ref.job_id, DelegatedAgentJobStatus.ADMITTED)
        await store.transition(ref.job_id, DelegatedAgentJobStatus.PREPARING)
        await store.transition(ref.job_id, DelegatedAgentJobStatus.RUNNING)

    bounded = await store.jobs_for_run(run_id, limit=2, event_limit=2)

    assert [job.ref.request_id for job in bounded] == ["bounded-request-1", "bounded-request-2"]
    assert [[event.seq for event in job.events] for job in bounded] == [[2, 3], [2, 3]]
    assert await store.jobs_for_run(run_id, limit=0) == ()


async def _park_decided_consent(
    ledger: DbRunLedger,
    session_factory: async_sessionmaker[AsyncSession],
    run_id: str,
    *,
    label: str,
) -> str:
    """Create and bind one exact decided Consent owner for a ledger-only resume test."""
    now = datetime.now(UTC)
    async with session_factory() as session:
        consent = Consent(
            run_id=UUID(run_id),
            tool_name=label,
            tool_call_id=f"call-{label}",
            payload={"args": {}},
            status="granted",
            decided_by="magus:test",
            decided_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(consent)
        await session.commit()
        await session.refresh(consent)
    consent_id = str(consent.id)
    await ledger.park_consent(run_id, consent_id)
    return consent_id


@pytest.mark.asyncio
async def test_factory_json_and_jsonb_binary_codecs_round_trip(
    pg_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The factory's distinct wire codecs both survive a real PostgreSQL round trip."""
    url = make_url(pg_url)
    monkeypatch.setenv("LYCHD_DB_PASSWORD", url.password or "")
    settings = DatabaseSettings(
        host=url.host or "localhost",
        port=url.port or 5432,
        user=url.username or "postgres",
        database=url.database or "postgres",
        pool_size=1,
        max_overflow=0,
    )
    engine = create_db_engine(settings)
    payload = {"name": "LychD", "nested": {"depth": 2}}
    try:
        async with engine.connect() as connection:
            plain = await connection.scalar(
                select(cast(bindparam("plain_payload", type_=JSON), JSON)),
                {"plain_payload": payload},
            )
            binary = await connection.scalar(
                select(cast(bindparam("jsonb_payload", type_=JSONB), JSONB)),
                {"jsonb_payload": payload},
            )
    finally:
        await engine.dispose()

    assert plain == payload
    assert binary == payload


@pytest.mark.asyncio
async def test_cas_cancelled_cannot_land_over_done(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    """CAS: once DONE wins, a later CANCELLED write raises against the fresh truth."""
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    await ledger.set_status(run_id, RunStatus.RUNNING)
    await ledger.set_status(run_id, RunStatus.DONE)  # DONE wins

    with pytest.raises(IllegalRunTransitionError):
        await ledger.set_status(run_id, RunStatus.CANCELLED)  # illegal over terminal DONE

    row = await ledger.get(run_id)
    assert row is not None
    assert row.status is RunStatus.DONE


@pytest.mark.asyncio
async def test_idempotent_admission_converges_across_database_sessions(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    first = DbRunLedger(session_factory=pg_factory)
    second = DbRunLedger(session_factory=pg_factory)
    intent = Intent(session_id="s", prompt="one durable offering", source="bridge")
    kwargs = {
        "idempotency_key": "bridge:s:request-1",
        "workflow_name": "bridge_chat",
        "queue_name": "runs",
        "priority": 70,
        "hold_delivery": True,
    }

    admitted = await asyncio.gather(
        first.create_idempotent(intent, **kwargs),
        second.create_idempotent(intent, **kwargs),
    )

    assert admitted[0][0].run_id == admitted[1][0].run_id
    assert sorted(created for _run, created in admitted) == [False, True]
    canonical = await first.get(admitted[0][0].run_id)
    delivery = await first.get_delivery(admitted[0][0].run_id, enqueue_seq=0)
    assert canonical is not None
    assert delivery is not None
    assert delivery.state is RunDeliveryState.HELD

    with pytest.raises(RunAdmissionConflictError):
        await first.create_idempotent(
            Intent(session_id="s", prompt="different work", source="bridge"),
            **kwargs,
        )


@pytest.mark.asyncio
async def test_cas_concurrent_same_target_is_benign(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    """CAS: two racing writers to the SAME terminal target both settle without error."""
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    await ledger.set_status(run_id, RunStatus.RUNNING)

    await asyncio.gather(
        ledger.set_status(run_id, RunStatus.DONE),
        ledger.set_status(run_id, RunStatus.DONE),
    )
    row = await ledger.get(run_id)
    assert row is not None
    assert row.status is RunStatus.DONE


@pytest.mark.asyncio
async def test_concurrent_run_claim_has_one_winner(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    """At-least-once broker delivery is fenced by one QUEUED→RUNNING CAS."""
    first = DbRunLedger(session_factory=pg_factory)
    second = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(first)

    results = await asyncio.gather(
        first.try_claim_run(run_id, enqueue_seq=0),
        second.try_claim_run(run_id, enqueue_seq=0),
    )

    assert sorted(results) == [False, True]
    row = await first.get(run_id)
    assert row is not None
    assert row.status is RunStatus.RUNNING


@pytest.mark.asyncio
async def test_publication_ack_cannot_move_a_cancelled_delivery_backwards(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A late broker acknowledgement loses to canonical cancellation truth."""
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    elected = await ledger.begin_cancel(run_id)
    assert elected is not None
    assert await ledger.finish_cancel(run_id, enqueue_seq=elected.enqueue_seq)

    assert await ledger.mark_delivery_published(run_id, enqueue_seq=elected.enqueue_seq) is False
    row = await ledger.get(run_id)
    delivery = await ledger.get_delivery(run_id, enqueue_seq=elected.enqueue_seq)
    assert row is not None
    assert delivery is not None
    assert row.status is RunStatus.CANCELLED
    assert delivery.state is RunDeliveryState.SETTLED


@pytest.mark.asyncio
async def test_release_and_held_refusal_have_exactly_one_winner(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Admission compensation cannot fail a delivery whose release already won."""
    releaser = DbRunLedger(session_factory=pg_factory)
    refuser = DbRunLedger(session_factory=pg_factory)
    run = await releaser.create(
        Intent(session_id="s", prompt="p", source="bridge"),
        workflow_name="bridge_chat",
        queue_name="runs",
        priority=70,
        hold_delivery=True,
    )

    released, refused = await asyncio.gather(
        releaser.release_delivery(run.run_id, enqueue_seq=0),
        refuser.try_fail_held(run.run_id, enqueue_seq=0, error="retention failed"),
    )

    assert sorted((released, refused)) == [False, True]
    row = await releaser.get(run.run_id)
    delivery = await releaser.get_delivery(run.run_id, enqueue_seq=0)
    assert row is not None
    assert delivery is not None
    if released:
        assert row.status is RunStatus.QUEUED
        assert delivery.state is RunDeliveryState.PENDING
    else:
        assert row.status is RunStatus.FAILED
        assert delivery.state is RunDeliveryState.SETTLED


@pytest.mark.asyncio
async def test_claimed_failure_cannot_overwrite_new_resume_hop(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The failure CAS is fenced by the enqueue sequence that this worker claimed."""
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    assert await ledger.bump_enqueue_seq(run_id) == 1
    assert await ledger.try_claim_run(run_id, enqueue_seq=1) is True

    consent_id = await _park_decided_consent(
        ledger,
        pg_factory,
        run_id,
        label="claimed-failure",
    )
    assert await ledger.try_admit_consent(run_id, consent_id=consent_id) == 2
    assert await ledger.try_claim_run(run_id, enqueue_seq=2) is True

    assert await ledger.try_fail_claimed(run_id, enqueue_seq=1, error="old hop failed") is False
    running = await ledger.get(run_id)
    assert running is not None
    assert running.status is RunStatus.RUNNING
    assert running.enqueue_seq == 2

    assert await ledger.try_fail_claimed(run_id, enqueue_seq=2, error="current hop failed") is True
    failed = await ledger.get(run_id)
    assert failed is not None
    assert failed.status is RunStatus.FAILED
    assert failed.error == "current hop failed"


@pytest.mark.asyncio
async def test_stale_consent_delivery_cannot_claim_retried_hop(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Postgres admission and hop allocation are one CAS; stale jobs cannot claim."""
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    assert await ledger.try_claim_run(run_id, enqueue_seq=0) is True
    first_consent_id = await _park_decided_consent(
        ledger,
        pg_factory,
        run_id,
        label="first-hop",
    )

    assert await ledger.try_admit_consent(run_id, consent_id=first_consent_id) == 1
    assert await ledger.try_claim_run(run_id, enqueue_seq=1) is True
    second_consent_id = await _park_decided_consent(
        ledger,
        pg_factory,
        run_id,
        label="second-hop",
    )
    assert await ledger.try_admit_consent(run_id, consent_id=second_consent_id) == 2

    assert await ledger.try_claim_run(run_id, enqueue_seq=1) is False
    assert await ledger.try_claim_run(run_id, enqueue_seq=2) is True


@pytest.mark.asyncio
async def test_resumed_claim_preserves_original_started_at(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    assert await ledger.try_claim_run(run_id, enqueue_seq=0) is True
    first = await ledger.get(run_id)
    assert first is not None
    assert first.started_at is not None

    consent_id = await _park_decided_consent(
        ledger,
        pg_factory,
        run_id,
        label="started-at",
    )
    assert await ledger.try_admit_consent(run_id, consent_id=consent_id) == 1
    assert await ledger.try_claim_run(run_id, enqueue_seq=1) is True

    resumed = await ledger.get(run_id)
    assert resumed is not None
    assert resumed.started_at == first.started_at


@pytest.mark.asyncio
async def test_historical_consent_cannot_admit_a_later_postgres_wait(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    assert await ledger.try_claim_run(run_id, enqueue_seq=0)
    now = datetime.now(UTC)
    async with pg_factory() as session:
        old = Consent(
            run_id=UUID(run_id),
            tool_name="first",
            tool_call_id="call-first",
            payload={"args": {}},
            status="granted",
            decided_by="magus:first",
            decided_at=now - timedelta(seconds=1),
            created_at=now - timedelta(seconds=1),
            updated_at=now - timedelta(seconds=1),
        )
        session.add(old)
        await session.commit()
        await session.refresh(old)
        old_id = str(old.id)
    await ledger.park_consent(run_id, old_id)
    assert await ledger.try_admit_consent(run_id, consent_id=old_id) == 1
    assert await ledger.try_claim_run(run_id, enqueue_seq=1)

    async with pg_factory() as session:
        current = Consent(
            run_id=UUID(run_id),
            tool_name="second",
            tool_call_id="call-second",
            payload={"args": {}},
            status="granted",
            decided_by="magus:second",
            decided_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(current)
        await session.commit()
        await session.refresh(current)
        current_id = str(current.id)
    await ledger.park_consent(run_id, current_id)

    assert await ledger.get_by_consent(old_id) is None
    assert await ledger.try_admit_consent(run_id, consent_id=old_id) is None
    waiting = await ledger.get(run_id)
    assert waiting is not None
    assert waiting.status is RunStatus.AWAITING_CONSENT
    assert await ledger.try_admit_consent(run_id, consent_id=current_id) == 2


@pytest.mark.asyncio
async def test_pending_consent_cannot_admit_a_postgres_resume(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    assert await ledger.try_claim_run(run_id, enqueue_seq=0)
    now = datetime.now(UTC)
    async with pg_factory() as session:
        consent = Consent(
            run_id=UUID(run_id),
            tool_name="pending",
            tool_call_id="call-pending",
            payload={"args": {}},
            status="pending",
            created_at=now,
            updated_at=now,
        )
        session.add(consent)
        await session.commit()
        await session.refresh(consent)
        consent_id = str(consent.id)
    await ledger.park_consent(run_id, consent_id)

    assert await ledger.try_admit_consent(run_id, consent_id=consent_id) is None
    waiting = await ledger.get(run_id)
    assert waiting is not None
    assert waiting.status is RunStatus.AWAITING_CONSENT

    async with pg_factory() as session:
        row = await session.get(Consent, UUID(consent_id))
        assert row is not None
        row.status = "granted"
        with pytest.raises(IntegrityError, match="ck_consent_decision_receipt"):
            await session.commit()
        await session.rollback()
        row = await session.get(Consent, UUID(consent_id))
        assert row is not None
        row.status = "granted"
        row.decided_by = "magus:test"
        row.decided_at = datetime.now(UTC)
        await session.commit()
    assert await ledger.try_admit_consent(run_id, consent_id=consent_id) == 1


@pytest.mark.asyncio
async def test_nonterminal_delegate_cannot_admit_a_postgres_resume(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    assert await ledger.try_claim_run(run_id, enqueue_seq=0)
    job_id = "job-pending-resume"
    async with pg_factory() as session:
        session.add(
            DelegatedAgentJobRecord(
                job_id=job_id,
                request_id="request-pending-resume",
                run_id=UUID(run_id),
                runtime="test-runtime",
                profile="test-profile",
                status="running",
                request={"task": "test"},
                result=None,
            )
        )
        await session.commit()
    await ledger.park_delegate(run_id, job_id)

    assert await ledger.try_admit_delegate(run_id, job_id=job_id) is None
    waiting = await ledger.get(run_id)
    assert waiting is not None
    assert waiting.status is RunStatus.AWAITING_DELEGATE

    async with pg_factory() as session:
        row = await session.scalar(select(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job_id))
        assert row is not None
        row.status = "succeeded"
        row.result = {"job_id": job_id, "status": "succeeded", "unexpected": True}
        await session.commit()
    assert await ledger.try_admit_delegate(run_id, job_id=job_id) is None

    async with pg_factory() as session:
        row = await session.scalar(select(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job_id))
        assert row is not None
        row.result = {"job_id": job_id, "status": "succeeded", "output": "done", "artifacts": [], "error": None}
        await session.commit()
    assert await ledger.try_admit_delegate(run_id, job_id=job_id) == 1


@pytest.mark.asyncio
async def test_postgres_consent_resume_uses_the_explicit_park_owner(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    assert await ledger.try_claim_run(run_id, enqueue_seq=0)
    now = datetime.now(UTC)
    async with pg_factory() as session:
        explicitly_parked = Consent(
            run_id=UUID(run_id),
            tool_name="explicit",
            tool_call_id="call-explicit",
            payload={"args": {}},
            status="granted",
            decided_by="magus:explicit",
            decided_at=now,
            created_at=now,
            updated_at=now,
        )
        newer_unrelated = Consent(
            run_id=UUID(run_id),
            tool_name="newer",
            tool_call_id="call-newer",
            payload={"args": {}},
            status="granted",
            decided_by="magus:newer",
            decided_at=now + timedelta(seconds=1),
            created_at=now + timedelta(seconds=1),
            updated_at=now + timedelta(seconds=1),
        )
        session.add_all((explicitly_parked, newer_unrelated))
        await session.commit()
        await session.refresh(explicitly_parked)
        await session.refresh(newer_unrelated)

    parked_id = str(explicitly_parked.id)
    unrelated_id = str(newer_unrelated.id)
    await ledger.park_consent(run_id, parked_id)

    assert await ledger.get_by_consent(unrelated_id) is None
    assert await ledger.try_admit_consent(run_id, consent_id=unrelated_id) is None
    assert await ledger.try_admit_consent(run_id, consent_id=parked_id) == 1


@pytest.mark.asyncio
async def test_delivery_candidates_include_missing_delivery_truth(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    from sqlalchemy import delete

    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    async with pg_factory() as session:
        await session.execute(delete(RunDelivery).where(RunDelivery.run_id == UUID(run_id)))
        await session.commit()

    candidates = await ledger.list_delivery_candidates()

    assert [candidate.run_id for candidate in candidates] == [run_id]


@pytest.mark.asyncio
async def test_delivery_cursor_sees_old_run_newly_admitted_for_resume(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    ledger = DbRunLedger(session_factory=pg_factory)
    old_id = await _seed(ledger)
    assert await ledger.try_claim_run(old_id, enqueue_seq=0)
    consent_id = await _park_decided_consent(ledger, pg_factory, old_id, label="cursor")

    current_id = await _seed(ledger)
    current = await ledger.get(current_id)
    assert current is not None
    cursor = (current.updated_at, current.run_id)

    assert await ledger.try_admit_consent(old_id, consent_id=consent_id) == 1
    candidates = await ledger.list_delivery_candidates(after=cursor)

    assert [candidate.run_id for candidate in candidates] == [old_id]


@pytest.mark.asyncio
async def test_cancel_election_fences_the_current_delivery_generation(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A delivery rotation cannot make cancellation settle a stale copied sequence."""
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)

    assert await ledger.rotate_delivery(run_id, enqueue_seq=0) == 1
    elected = await ledger.begin_cancel(run_id)
    assert elected is not None
    assert elected.status is RunStatus.CANCELLING
    assert elected.enqueue_seq == 1
    assert await ledger.finish_cancel(run_id, enqueue_seq=0) is False
    assert await ledger.finish_cancel(run_id, enqueue_seq=1) is True

    row = await ledger.get(run_id)
    assert row is not None
    assert row.status is RunStatus.CANCELLED
    old_delivery = await ledger.get_delivery(run_id, enqueue_seq=0)
    current_delivery = await ledger.get_delivery(run_id, enqueue_seq=1)
    assert old_delivery is not None
    assert old_delivery.state is RunDeliveryState.SETTLED
    assert current_delivery is not None
    assert current_delivery.state is RunDeliveryState.SETTLED


@pytest.mark.asyncio
async def test_cancel_after_completion_is_benign(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    """A cancel observing settled DONE is a benign no-op, not a 500."""
    from lychd.domain.cortex.engine import QueueRouter
    from lychd.domain.cortex.engine import RunEngine as CortexRunEngine

    ledger = DbRunLedger(session_factory=pg_factory)
    completer = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    await ledger.set_status(run_id, RunStatus.RUNNING)

    class _Queue:
        async def enqueue(self, job_or_func: str, /, **kwargs: object) -> object:
            _ = (job_or_func, kwargs)
            return None

        async def job(self, job_key: str, /) -> object:
            _ = job_key
            return None

        async def abort(self, job: object, error: str, /, ttl: float = 5) -> None:
            _ = (job, error, ttl)

    engine = CortexRunEngine(
        ledger=ledger,
        bus=InProcessEventBus(ledger=ledger),
        workflows=None,
        queue_router=QueueRouter(),
        queues={"runs": _Queue()},
    )

    await completer.set_status(run_id, RunStatus.DONE)
    await engine.cancel(run_id)

    row = await ledger.get(run_id)
    assert row is not None
    assert row.status is RunStatus.DONE  # completion won; cancel was a benign no-op


@pytest.mark.asyncio
async def test_reconcile_orphaned_running_lands_terminal_step(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """R1: a reconciled orphan (with a persisted Step) lands its terminal Step instead of colliding.

    Restart shape: the run reached RUNNING and persisted Step(seq=0); the process
    died; a FRESH bus restarts channel seqs at 0. Without seeding, reconcile's terminal
    emit would write Step(seq=0) → `uq_step_run_seq` violation → dropped. With the R1
    seed (`open(from_seq=next_seq)`), the terminal lands at seq 1.
    """
    from types import SimpleNamespace
    from uuid import UUID

    from sqlalchemy import select

    from lychd.domain.cortex.stasis import InMemoryStasisStore
    from lychd.ghouls.runs import reconcile_runs

    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    await ledger.set_status(run_id, RunStatus.RUNNING)
    await ledger.append_event(RunEvent(run_id=run_id, seq=0, kind=RunEventKind.STATUS, data="running"))

    # Fresh process: a brand-new bus (channel seqs restart at 0). reconcile only needs
    # the substrate's ledger + bus, so a namespace stand-in is sufficient here.
    class _NoBrokerJob:
        async def job(self, job_key: str, /) -> None:
            _ = job_key

        async def abort(self, job: object, error: str, /, ttl: float = 5) -> None:
            _ = (job, error, ttl)

    bus = InProcessEventBus(ledger=ledger)
    substrate = SimpleNamespace(
        ledger=ledger,
        bus=bus,
        queues={"runs": _NoBrokerJob()},
        stasis_store=InMemoryStasisStore(),
        consents=None,
        delegates=None,
    )
    result = await reconcile_runs({"run_substrate": substrate})
    assert result["count"] >= 1

    async with pg_factory() as session:
        rows = (await session.execute(select(Step.seq).where(Step.run_id == UUID(run_id)).order_by(Step.seq))).scalars()
        seqs = list(rows)
    assert seqs == [0, 1]  # pre-existing status + the reconciled terminal — no collision, nothing dropped


@pytest.mark.asyncio
async def test_append_event_persists_seq_verbatim(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    """Seq fidelity: Step.seq equals the RunEvent.seq (no insert-time allocation)."""
    from sqlalchemy import select

    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    for seq, kind in ((0, RunEventKind.STATUS), (1, RunEventKind.NODE), (2, RunEventKind.DONE)):
        await ledger.append_event(RunEvent(run_id=run_id, seq=seq, kind=kind, data="x"))

    async with pg_factory() as session:
        from uuid import UUID

        rows = (await session.execute(select(Step.seq).where(Step.run_id == UUID(run_id)).order_by(Step.seq))).scalars()
        assert list(rows) == [0, 1, 2]  # verbatim, ordered


@pytest.mark.asyncio
async def test_concurrent_session_turn_appends_are_not_lost(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Concurrent writers serialize on the Session row and retain every JSONB turn."""
    store = DbBridgeSessionStore(pg_factory, sigil_name="magus")
    bridge_session = await store.create_session(title="concurrent")
    turns = [BridgeTurn(role="agent", content=f"turn-{index}") for index in range(16)]

    await asyncio.gather(*(store.add_turn(bridge_session.id, turn) for turn in turns))

    persisted = await store.get_session(bridge_session.id)
    assert persisted is not None
    assert {turn.content for turn in persisted.turns} == {turn.content for turn in turns}
    assert len(persisted.turns) == len(turns)
