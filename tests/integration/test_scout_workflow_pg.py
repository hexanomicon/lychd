"""Credential-backed Scout choreography with real PostgreSQL custody.

Only the disposable database is effectful. Fetch uses fixed bytes and synchronous
syscall substitutes; the real extraction supervisor receives a substituted child.
Model inference and queue publication are inert. This does not qualify network,
sandbox, model-service, SAQ-worker, or durable Graph-checkpoint behavior.
"""

from __future__ import annotations

import asyncio
import io
import json
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lychd.agents.workflows.scout_chat import (
    AcquireAndAnswerPage,
    SettlePageAnswer,
)
from lychd.db import scout as scout_db
from lychd.db.models import Consent, Run, RunDelivery, ScoutAttempt, ScoutBudget, Session, Step
from lychd.domain.scout.attempts import ScoutCommitUnknownError, ScoutSettlement
from lychd.domain.scout.destination import DestinationCandidate
from lychd.domain.scout.extraction import ExtractionCode, ExtractionError
from lychd.domain.scout.profile import ScoutProfile, ScoutWorkflowCode, ScoutWorkflowError
from lychd.domain.scout.transport import FetchError, NetworkGate, NetworkHandoff, NetworkTarget
from lychd.system import scout_worker
from lychd.system.services import scout_extraction, scout_workflow
from lychd.system.services.scout_fetch import FetchedPage, FetchObservation
from lychd.system.services.scout_http import serialize_get
from tests.postgres_model_tables import with_referenced_tables
from tests.scout_fixtures import scout_profile
from tests.scout_workflow_fixture import approve_workflow, assemble_workflow, workflow_service

pytestmark = [pytest.mark.integration, pytest.mark.container]

_URL = "https://8.8.8.8/page?fixture=1"
_PROMPT = f"/read-public {_URL}\nWhat does the fixed page report?"
_SOURCE = "SCOUT_INTEGRATION_RAW_SOURCE_73b29"
_BODY = f"{_SOURCE}: a fixed fixture claim.".encode()
_ANSWER = "The page reports a fixed fixture claim."
_IMAGE = "pgvector/pgvector:pg18-trixie"


@pytest.fixture(scope="module")
def workflow_pg_url() -> Iterator[str]:
    """Own one bounded cached container; never target an operator database."""
    pytest.importorskip("testcontainers")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("TESTCONTAINERS_RYUK_DISABLED", "true")
        from testcontainers.community.postgres import PostgresContainer

        postgres = PostgresContainer(
            _IMAGE,
            driver="asyncpg",
            username="scout",
            password="fixture",  # noqa: S106 - disposable database credential
            dbname="scout",
            mem_limit="512m",
            nano_cpus=1_000_000_000,
            pids_limit=128,
        )
        # Require the selected local image before testcontainers can attempt a pull.
        postgres.get_docker_client().client.images.get(_IMAGE)
        # Docker accepts an address/port tuple; testcontainers' annotation is narrower.
        cast("Any", postgres.ports)["5432"] = ("127.0.0.1", None)
        with postgres:
            yield postgres.get_connection_url(host="127.0.0.1")


@pytest_asyncio.fixture
async def factory(workflow_pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(workflow_pg_url)
    tables = cast(
        "list[Table]",
        [
            Session.__table__,
            Run.__table__,
            Consent.__table__,
            RunDelivery.__table__,
            Step.__table__,
            ScoutBudget.__table__,
            ScoutAttempt.__table__,
        ],
    )
    tables = with_referenced_tables(tables)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Run.metadata.drop_all, tables=tables)
            await connection.run_sync(Run.metadata.create_all, tables=tables)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def _synthetic_extraction_profile(tmp_path: Path) -> ScoutProfile:
    """Create placeholder runtime files for the substituted extraction child."""
    bwrap, python = tmp_path / "bwrap", tmp_path / "python"
    bwrap.touch()
    (python / "bin").mkdir(parents=True)
    (python / "bin/python3").touch()
    (python / "lib").mkdir()
    libraries = tuple(
        tmp_path / name
        for name in (
            "ld-linux-x86-64.so.2",
            "libc.so.6",
            "libdl.so.2",
            "libgcc_s.so.1",
            "libm.so.6",
            "libpthread.so.0",
            "librt.so.1",
            "libutil.so.1",
        )
    )
    for library in libraries:
        library.touch()
    return scout_profile().model_copy(update={"bwrap": bwrap, "python_root": python, "libraries": libraries})


def _acquisition(monkeypatch: pytest.MonkeyPatch) -> tuple[list[str], AsyncMock]:
    calls: list[str] = []

    async def fetch(candidate: DestinationCandidate, *, gate: NetworkGate, **kwargs: Any) -> FetchedPage:
        _ = kwargs
        calls.append(candidate.original_url)
        target = NetworkTarget("8.8.8.8", 443, candidate.hostname, "origin")
        gate.handoff(NetworkHandoff(target, "connect", b"", None), lambda: 0)
        wire = b"inert fixture ciphertext"
        gate.handoff(NetworkHandoff(target, "http", wire, serialize_get(candidate)), lambda: len(wire))
        observation = FetchObservation(
            candidate=candidate,
            addresses=(target.address,),
            peer=target.address,
            status=200,
            header_bytes=0,
            wire_body_bytes=len(_BODY),
            encoded_body_bytes=len(_BODY),
            decoded_body_bytes=len(_BODY),
            http_response_digest=sha256(_BODY).hexdigest(),
        )
        return FetchedPage(media_type="text/plain", body=_BODY, observations=(observation,))

    header = json.dumps({"media_type": "text/plain", "body_bytes": len(_BODY)}).encode() + b"\n"
    output = io.BytesIO()
    assert scout_worker.run(io.BytesIO(header + _BODY), output) == 0
    stdout, stderr = asyncio.StreamReader(), asyncio.StreamReader()
    stdout.feed_data(output.getvalue())
    stdout.feed_eof()
    stderr.feed_eof()
    process = Mock(spec=asyncio.subprocess.Process)
    process.returncode, process.stdout, process.stderr = 0, stdout, stderr
    process.stdin = Mock(spec=asyncio.StreamWriter)
    process.stdin.drain = AsyncMock()
    process.wait = AsyncMock(return_value=0)
    launch = AsyncMock(return_value=process)
    monkeypatch.setattr(scout_workflow, "fetch_static_page", fetch)
    monkeypatch.setattr(scout_extraction.asyncio, "create_subprocess_exec", launch)
    return calls, launch


@pytest.mark.asyncio
async def test_retained_consent_to_transient_answer_and_lost_material_refusal(
    factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assembly = await assemble_workflow(
        factory, profile=_synthetic_extraction_profile(tmp_path), prompt=_PROMPT, answer=_ANSWER
    )
    calls, launch = _acquisition(monkeypatch)
    await approve_workflow(assembly, expected_url=_URL)
    assert calls == []
    ctx = assembly.context
    async with factory() as session:
        deliveries = list(
            (
                await session.scalars(
                    select(RunDelivery).where(RunDelivery.run_id == ctx.state.run_id).order_by(RunDelivery.enqueue_seq)
                )
            ).all()
        )
        assert [(row.enqueue_seq, row.state, row.resume) for row in deliveries] == [
            (0, "settled", False),
            (1, "claimed", True),
        ]
    assert isinstance(await AcquireAndAnswerPage().run(ctx), SettlePageAnswer)
    assert ctx.state.answer == _ANSWER
    assert _SOURCE not in ctx.state.model_dump_json()
    assert len(assembly.model_requests) == 1
    assert _SOURCE.encode() in assembly.model_requests[0]
    result = await SettlePageAnswer().run(ctx)
    assert result.data.answer == _ANSWER
    retained = await assembly.turns.get_session(ctx.state.session_id)
    assert retained is not None
    assert retained.turns[-1].content == _ANSWER
    assert _SOURCE not in json.dumps(retained.message_history)
    assert ctx.state.review is not None
    async with factory() as session:
        row = await session.get(ScoutAttempt, ctx.state.review.attempt_id)
        assert row is not None
        assert row.status == "succeeded"
        assert row.execution_enqueue_seq == 1
        settlement = ScoutSettlement.model_validate_json(row.settlement_bytes or b"")
        assert settlement.child == "reaped"
        assert settlement.usage.connects == 1
        assert _SOURCE.encode() not in settlement.handoff_evidence
        budgets = list((await session.scalars(select(ScoutBudget))).all())
        assert {row.scope for row in budgets} == {"host", "binding"}
        assert all(row.active_claims == 0 and row.connects_reserved == 0 and row.connects_used == 1 for row in budgets)
    _, restarted = workflow_service(factory, assembly.profile, assembly.authorizer, assembly.ledger, assembly.consents)
    for owner in (assembly.service, restarted):
        with pytest.raises(ScoutWorkflowError) as error:
            await owner.acquire(run_id=ctx.state.run_id, binding=ctx.state.scout, review=ctx.state.review)
        assert error.value.code is ScoutWorkflowCode.MATERIAL_UNAVAILABLE
    assembly.access.revoke()
    with pytest.raises(FetchError):
        await restarted.authorize_settle(
            run_id=ctx.state.run_id, binding=ctx.state.scout, review=ctx.state.review, receipt_id=ctx.state.receipt_id
        )
    assert calls == [_URL]
    launch.assert_awaited_once()


@pytest.mark.asyncio
async def test_committed_claim_lost_acknowledgement_restarts_unknown_without_refetch(
    factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assembly = await assemble_workflow(
        factory, profile=_synthetic_extraction_profile(tmp_path), prompt=_PROMPT, answer=_ANSWER
    )
    calls, launch = _acquisition(monkeypatch)
    await approve_workflow(assembly, expected_url=_URL)
    ctx = assembly.context
    assert ctx.state.review is not None
    commit = scout_db._commit  # pyright: ignore[reportPrivateUsage] - inject loss after the actual commit

    async def lost_ack(session: AsyncSession) -> None:
        await commit(session)
        message = "Synthetic lost acknowledgement."
        raise ScoutCommitUnknownError(message)

    with monkeypatch.context() as patch:
        patch.setattr(scout_db, "_commit", lost_ack)
        with pytest.raises(ScoutCommitUnknownError):
            await assembly.service.acquire(run_id=ctx.state.run_id, binding=ctx.state.scout, review=ctx.state.review)
    _, restarted = workflow_service(factory, assembly.profile, assembly.authorizer, assembly.ledger, assembly.consents)
    assert await restarted.reconcile_before(datetime.now(UTC) + timedelta(seconds=1)) == 1
    with pytest.raises(ScoutWorkflowError) as error:
        await restarted.acquire(run_id=ctx.state.run_id, binding=ctx.state.scout, review=ctx.state.review)
    assert error.value.code is ScoutWorkflowCode.MATERIAL_UNAVAILABLE
    async with factory() as session:
        row = await session.get(ScoutAttempt, ctx.state.review.attempt_id)
        assert row is not None
        assert row.status == "unknown_after_crash"
        assert row.receipt_id is None
        budgets = list((await session.scalars(select(ScoutBudget))).all())
        assert {row.scope for row in budgets} == {"host", "binding"}
        assert all(
            row.connects_reserved == assembly.profile.allowance.connects and row.connects_used == 0 for row in budgets
        )
        assert next(row for row in budgets if row.scope == "binding").active_claims == 1
    assert calls == []
    launch.assert_not_called()


@pytest.mark.asyncio
async def test_real_extractor_preflight_refusal_settles_not_started(
    factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assembly = await assemble_workflow(
        factory, profile=_synthetic_extraction_profile(tmp_path), prompt=_PROMPT, answer=_ANSWER
    )
    calls, launch = _acquisition(monkeypatch)
    await approve_workflow(assembly, expected_url=_URL)
    assembly.profile.bwrap.unlink()
    ctx = assembly.context
    assert ctx.state.review is not None
    with pytest.raises(ExtractionError) as error:
        await assembly.service.acquire(run_id=ctx.state.run_id, binding=ctx.state.scout, review=ctx.state.review)
    assert error.value.code is ExtractionCode.CONTAINMENT
    async with factory() as session:
        row = await session.get(ScoutAttempt, ctx.state.review.attempt_id)
        assert row is not None
        assert row.status == "refused"
        assert ScoutSettlement.model_validate_json(row.settlement_bytes or b"").child == "not_started"
        budgets = list((await session.scalars(select(ScoutBudget))).all())
        assert {row.scope for row in budgets} == {"host", "binding"}
        assert all(row.active_claims == 0 and row.connects_reserved == 0 for row in budgets)
    await assembly.service.contain(ctx.state.run_id)
    assert calls == [_URL]
    launch.assert_not_called()
