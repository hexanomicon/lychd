"""Opt-in PostgreSQL worker custody, one-shot claims and explicit continuation.

The actual model and queue are inert. This is not a live Qwen qualification.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.compositions.creation.schemas import (
    ContinueRequest,
    CreationRefused,
    InvestigationRequest,
    OwnerDecision,
    canonical,
    decode,
    digest,
    validate_output,
)
from lychd.compositions.creation.services import InvestigationService, LocalCreationPolicy, register_agents
from lychd.compositions.creation.workflow import investigation_workflow
from lychd.db.checkpoints import PostgresStasisStore
from lychd.db.creation import DbCreationStore
from lychd.db.models import CodexPreauthorization, Consent, Run, RunCheckpoint, RunDelivery, Session, Step
from lychd.db.models.creation import CreationAdmission, CreationAttempt, CreationCase, CreationFeedback
from lychd.db.sessions import DbBridgeSessionStore
from lychd.domain.codex.ledger import CodexConsentLedger
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.sigil import default_local_sigil
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.web.fragments import build_fragment_registry
from lychd.ghouls.runs import perform_run, reconcile_runs
from tests.agents.fakes import FakeOrchestrator, FakeRegistry
from tests.support.blockworld import CapturedQueue, SimulatedProcessLoss
from tests.support.creation import (
    CreationDispatcher,
    CreationRegistry,
    assessment_document,
    candidate_document,
    capability,
    request_document,
    verdict_document,
)

ACCESS_VALUE = "inert-creation-password"

pytestmark = [pytest.mark.asyncio, pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest_asyncio.fixture
async def factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
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
            CreationCase.__table__,
            CreationAdmission.__table__,
            CreationAttempt.__table__,
            CreationFeedback.__table__,
        ],
    )
    async with engine.begin() as connection:
        await connection.run_sync(Run.metadata.drop_all, tables=tables)
        await connection.run_sync(Run.metadata.create_all, tables=tables)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


class Boot:
    def __init__(self, factory: async_sessionmaker[AsyncSession], messages: list[bytes] | None = None) -> None:
        self.factory = factory
        self.messages = messages if messages is not None else []
        self.access = LocalOperatorAccess(access_password=ACCESS_VALUE)
        self.authentication = self.access.authenticate(username=b"magus", password=b"inert-creation-password")
        self.policy = LocalCreationPolicy(self.access)
        self.ledger = DbRunLedger(session_factory=factory)
        self.consents = CodexConsentLedger(session_factory=factory)
        self.sessions = DbBridgeSessionStore(factory, sigil_name="magus")
        self.checkpoints = PostgresStasisStore(factory)
        self.leases = LeaseLedger()
        self.store = DbCreationStore(factory, self.policy)
        self.service = InvestigationService(
            store=self.store,
            policy=self.policy,
            registry=CreationRegistry(),
            leases=self.leases,
            capability_key=capability().key,
        )
        self.workflow = investigation_workflow(self.service)
        self.workflows = BuiltinWorkflowRegistry(workflows=(self.workflow,))
        self.queue = CapturedQueue()
        self.bus = InProcessEventBus(ledger=self.ledger)
        self.dispatcher = CreationDispatcher(FunctionModel(self.respond), self.leases)
        forge = default_forge()
        register_agents(forge)
        self.substrate = RunSubstrate(
            ledger=self.ledger,
            bus=self.bus,
            workflows=self.workflows,
            orchestrator=FakeOrchestrator(),
            dispatcher=cast("Any", self.dispatcher),
            context=ContextOrchestrator(registry=FakeRegistry()),
            fragments=build_fragment_registry(),
            turns=self.sessions,
            consents=self.consents,
            forge=forge,
            stasis_store=self.checkpoints,
            leases=self.leases,
            queues={"runs": self.queue},
        )
        self.engine = RunEngine(
            ledger=self.ledger,
            bus=self.bus,
            workflows=self.workflows,
            queue_router=QueueRouter({"default": RouteRule(queue="runs", priority=50)}),
            queues=self.substrate.queues,
            stasis_store=self.checkpoints,
            consents=self.consents,
            release_context=self.substrate.context.release,
        )

    async def respond(self, messages: Any, _info: Any) -> ModelResponse:
        self.messages.append(ModelMessagesTypeAdapter.dump_json(messages))
        output = candidate_document() if len(self.messages) == 1 else verdict_document()
        return ModelResponse(
            parts=[ToolCallPart("final_result", output.model_dump(mode="json"))],
            usage=RequestUsage(input_tokens=100, output_tokens=80),
        )

    async def submit(self, request: InvestigationRequest) -> str:
        view = await self.service.submit(
            request,
            authentication=self.authentication,
            principal=default_local_sigil(),
            engine=self.engine,
            sessions=self.sessions,
        )
        return cast("str", view.admissions[-1]["run_id"])

    async def drive(self, run_id: str) -> dict[str, Any]:
        run = await self.ledger.get(run_id)
        assert run is not None
        try:
            return await perform_run({"run_substrate": self.substrate}, run_id=run_id, enqueue_seq=run.enqueue_seq)
        finally:
            await self.bus.wait_persisted(run_id)


async def test_postgres_worker_candidate_crash_and_explicit_fresh_authority_continuation(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    boot = Boot(factory)
    request = request_document()
    first, replay = await asyncio.gather(boot.submit(request), boot.submit(request))
    assert first == replay
    run_id = first
    original_adopt = boot.store.adopt

    async def lose_after_adoption(*args: Any, **kwargs: Any) -> None:
        await original_adopt(*args, **kwargs)
        raise SimulatedProcessLoss

    monkeypatch.setattr(boot.store, "adopt", lose_after_adoption)
    with pytest.raises(SimulatedProcessLoss):
        await boot.drive(run_id)
    candidate = await boot.store.read(request.request_id)
    assert candidate.status == "candidate"
    assert candidate.slot_encumbered
    assert len(candidate.attempts) == 1
    assert candidate.attempts[0]["response"] is not None
    original_run = await boot.ledger.get(run_id)
    assert original_run is not None
    assert original_run.status is RunStatus.RUNNING
    restored = Boot(factory, boot.messages)
    reconciled = await reconcile_runs({"run_substrate": restored.substrate})
    assert reconciled["status"] == "reconciled"
    failed_run = await restored.ledger.get(run_id)
    assert failed_run is not None
    assert failed_run.status is RunStatus.FAILED
    assert restored.messages == boot.messages
    continued = await restored.service.continue_case(
        request.request_id,
        ContinueRequest(
            admission_id=uuid4(),
            request_digest=candidate.request_digest,
            candidate_digest=cast("str", candidate.candidate_digest),
            profile_digest=candidate.profile_digest,
        ),
        authentication=restored.authentication,
        principal=default_local_sigil(),
        engine=restored.engine,
        sessions=restored.sessions,
    )
    second_run = continued.admissions[-1]["run_id"]
    assert second_run != run_id
    assert continued.deadline == candidate.deadline
    assert (await restored.drive(second_run))["status"] == "done"
    result = await restored.store.read(request.request_id)
    assert result.status == "rejected"
    assert not result.slot_encumbered
    assert result.candidate == candidate.candidate
    assert [attempt["role"] for attempt in result.attempts] == ["constructor", "verifier"]
    assert result.admissions[0]["authentication_generation"] != result.admissions[1]["authentication_generation"]
    assert len(restored.messages) == 2
    assert candidate_document().summary.encode() in restored.messages[1]
    assert b"creation-constructor-v1" not in restored.messages[1]
    assert not restored.leases.active()


async def test_postgres_claim_survives_unknown_output_and_blocks_other_admission(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    boot = Boot(factory)
    request = request_document()
    run_id = await boot.submit(request)
    assert (await boot.ledger.try_claim_run(run_id, enqueue_seq=0)).acknowledged is True
    attempt_id = await boot.store.claim(request.request_id, run_id, "constructor", b'{"role":"constructor"}')
    await boot.store.fail(request.request_id, "transport_unknown", attempt_id)
    await boot.service.cancel(
        request.request_id, authentication=boot.authentication, principal=default_local_sigil(), engine=boot.engine
    )
    view = await boot.store.read(request.request_id)
    assert view.status == "cancelled"
    assert view.slot_encumbered
    assert view.attempts[0]["response"] is None
    with pytest.raises(CreationRefused, match="reservation_unavailable"):
        await boot.submit(request_document())
    with pytest.raises(CreationRefused):
        await boot.store.claim(request.request_id, run_id, "constructor", b"{}")
    async with factory() as session:
        attempts = list(
            await session.scalars(select(CreationAttempt).where(CreationAttempt.case_id == request.request_id))
        )
    assert len(attempts) == 1

    late_response = ModelMessagesTypeAdapter.dump_json(
        [
            ModelResponse(
                parts=[ToolCallPart("final_result", candidate_document().model_dump(mode="json"))],
                usage=RequestUsage(input_tokens=100, output_tokens=80),
            )
        ]
    )
    await boot.store.complete(attempt_id, late_response, {"input_tokens": 100, "output_tokens": 80})
    with pytest.raises(CreationRefused, match="run_fence"):
        await boot.store.adopt(
            attempt_id, run_id, canonical(candidate_document()), validate_output(request, candidate_document())
        )
    await boot.store.fail(request.request_id, "late_cancelled_response", attempt_id)
    late = await boot.store.read(request.request_id)
    assert late.status == "cancelled"
    assert not late.slot_encumbered
    assert late.candidate is None
    assert late.attempts[0]["response"] is not None
    assert not late.attempts[0]["adopted"]


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens", "accepted"),
    [(3584, 512, True), (3585, 512, False), (3584, 513, False)],
)
async def test_postgres_profile_two_adoption_checks_observed_usage_after_complete_custody(
    factory: async_sessionmaker[AsyncSession], input_tokens: int, output_tokens: int, *, accepted: bool
) -> None:
    boot = Boot(factory)
    request = request_document()
    run_id = await boot.submit(request)
    assert (await boot.ledger.try_claim_run(run_id, enqueue_seq=0)).acknowledged is True
    attempt_id = await boot.store.claim(request.request_id, run_id, "constructor", b'{"role":"constructor"}')
    response = ModelMessagesTypeAdapter.dump_json(
        [
            ModelResponse(
                parts=[ToolCallPart("final_result", candidate_document().model_dump(mode="json"))],
                usage=RequestUsage(input_tokens=input_tokens, output_tokens=output_tokens),
                finish_reason="stop",
            )
        ]
    )
    usage = {"input_tokens": input_tokens, "output_tokens": output_tokens, "precount_available": False}
    await boot.store.complete(attempt_id, response, usage)
    output = canonical(candidate_document())
    receipt = validate_output(request, candidate_document())
    if accepted:
        await boot.store.adopt(attempt_id, run_id, output, receipt)
    else:
        with pytest.raises(CreationRefused, match="observed_usage"):
            await boot.store.adopt(attempt_id, run_id, output, receipt)
        await boot.store.fail(request.request_id, "observed_usage", attempt_id)
    view = await boot.store.read(request.request_id)
    assert len(view.attempts) == 1
    assert view.attempts[0]["response"] == decode(response)
    assert view.attempts[0]["response_digest"] == digest(response)
    assert view.attempts[0]["usage"] == usage
    assert view.attempts[0]["adopted"] is accepted
    assert view.candidate == (candidate_document().model_dump(mode="json") if accepted else None)
    assert view.verdict is None
    assert view.status == ("candidate" if accepted else "incomplete")
    assert view.slot_encumbered is accepted


async def completed_feedback_case(factory: async_sessionmaker[AsyncSession]) -> tuple[Boot, UUID, Any]:
    boot = Boot(factory)

    async def accepted_response(messages: Any, _info: Any) -> ModelResponse:
        boot.messages.append(ModelMessagesTypeAdapter.dump_json(messages))
        output = (
            candidate_document()
            if len(boot.messages) == 1
            else verdict_document().model_copy(update={"disposition": "accepted"})
        )
        return ModelResponse(
            parts=[ToolCallPart("final_result", output.model_dump(mode="json"))],
            usage=RequestUsage(input_tokens=100, output_tokens=80),
        )

    boot.dispatcher.model = FunctionModel(accepted_response)
    request = request_document()
    run_id = await boot.submit(request)
    assert (await boot.drive(run_id))["status"] == "done"
    view = await boot.service.feedback(
        request.request_id, authentication=boot.authentication, principal=default_local_sigil()
    )
    assert view.status == "unassessed"
    assert view.target is not None
    return boot, request.request_id, assessment_document(view.target)


async def test_feedback_custody_replay_disagreement_restart_and_no_execution_change(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    boot, case_id, assessment = await completed_feedback_case(factory)
    original = canonical(await boot.store.read(case_id))
    messages = list(boot.messages)
    async with factory() as session:
        execution_before = list((await session.execute(select(Run.__table__))).mappings())
        deliveries_before = list((await session.execute(select(RunDelivery.__table__))).mappings())
    restored = Boot(factory, boot.messages)
    restored.service.registry = None  # historical closure needs no current capability
    kwargs: dict[str, Any] = {"authentication": restored.authentication, "principal": default_local_sigil()}
    entry = await restored.service.assess(case_id, assessment, **kwargs)
    assert entry.criterion_coverage == {"predicate": "not_assessed"}
    assert entry.body["report"].encode() == assessment.report.encode()
    assert entry.report_digest == digest(assessment.report.encode())
    assert restored.authentication is not None
    assert entry.attribution["authentication_generation"] == str(restored.authentication.authentication_generation)
    assert entry.attribution["principal"] != assessment.reviewer_label
    decision = OwnerDecision(
        decision_id=uuid4(),
        assessment_id=entry.id,
        assessment_digest=entry.body_digest,
        target=assessment.target,
        action="hold",
        reason="Native and external judgments disagree.",
    )
    held = await restored.service.decide(case_id, decision, **kwargs)
    projection = await restored.service.feedback(case_id, **kwargs)
    assert projection.status == "hold"
    assert projection.assessments[-1].body["disposition"] == "partial"
    assert projection.native_verdict == decode(original)["verdict"]
    assert projection.native_status == "accepted"
    later = assessment.model_copy(update={"assessment_id": uuid4(), "report": "Later external report"})
    await restored.service.assess(case_id, later, **kwargs)
    assert await restored.service.decide(case_id, decision, **kwargs) == held
    assert (await restored.service.feedback(case_id, **kwargs)).status == "review_required"
    with pytest.raises(CreationRefused, match="feedback_latest_assessment"):
        await restored.service.decide(case_id, decision.model_copy(update={"decision_id": uuid4()}), **kwargs)
    with pytest.raises(CreationRefused, match="conflicting_feedback_replay"):
        await restored.service.assess(case_id, assessment.model_copy(update={"report": "Changed report"}), **kwargs)
    assert boot.messages == messages
    async with factory() as session:
        assert list((await session.execute(select(Run.__table__))).mappings()) == execution_before
        assert list((await session.execute(select(RunDelivery.__table__))).mappings()) == deliveries_before
    other_request = request_document()
    await boot.submit(other_request)
    with pytest.raises(CreationRefused, match="conflicting_feedback_replay"):
        await restored.service.assess(other_request.request_id, assessment, **kwargs)
    third = Boot(factory)
    assert (
        await third.service.assess(
            case_id, assessment, authentication=third.authentication, principal=default_local_sigil()
        )
        == entry
    )
    restored.access.revoke()
    with pytest.raises(CreationRefused, match="local_authority"):
        await restored.service.assess(case_id, assessment, **kwargs)
    assert canonical(await boot.store.read(case_id)) == original
    async with factory() as session:
        retained = await session.get(CreationFeedback, entry.id)
        assert retained is not None
        assert retained.report_bytes == assessment.report.encode()


@pytest.mark.parametrize("failure", ["running", "delivery", "unresolved", "lease", "revision", "target"])
async def test_feedback_refuses_unsettled_or_wrong_closure_without_mutation(
    factory: async_sessionmaker[AsyncSession], failure: str
) -> None:
    boot, case_id, assessment = await completed_feedback_case(factory)
    async with factory() as session:
        row = await session.get(CreationCase, case_id)
        assert row is not None
        admission = await session.get(CreationAdmission, row.current_admission_id)
        assert admission is not None
        if failure == "running":
            run = await session.get(Run, admission.run_id)
            assert run is not None
            run.status = "running"
        elif failure == "delivery":
            delivery = await session.scalar(select(RunDelivery).where(RunDelivery.run_id == admission.run_id))
            assert delivery is not None
            delivery.state = "claimed"
        elif failure == "unresolved":
            attempt = await session.scalar(
                select(CreationAttempt).where(CreationAttempt.case_id == case_id, CreationAttempt.role == "verifier")
            )
            assert attempt is not None
            attempt.adopted, attempt.response_bytes = False, None
        elif failure == "revision":
            profile = decode(row.profile_bytes)
            profile["revision"] = "1"
            row.profile_bytes = canonical(profile)
            row.profile_digest = digest(row.profile_bytes)
        await session.commit()
    if failure == "lease":
        boot.service.leases = SimpleNamespace(active=lambda: [SimpleNamespace(holder=f"run:{admission.run_id}")])
    if failure == "target":
        assessment = assessment.model_copy(
            update={"target": assessment.target.model_copy(update={"criteria_digest": "0" * 64})}
        )
    original = canonical(await boot.store.read(case_id))
    with pytest.raises(CreationRefused, match="feedback_"):
        await boot.service.assess(
            case_id, assessment, authentication=boot.authentication, principal=default_local_sigil()
        )
    assert canonical(await boot.store.read(case_id)) == original
    async with factory() as session:
        assert list(await session.scalars(select(CreationFeedback))) == []


async def test_feedback_serial_sequence_latest_decision_and_capacity_replays(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    boot, case_id, assessment = await completed_feedback_case(factory)
    kwargs: dict[str, Any] = {"authentication": boot.authentication, "principal": default_local_sigil()}
    one, replay = await asyncio.gather(
        boot.service.assess(case_id, assessment, **kwargs), boot.service.assess(case_id, assessment, **kwargs)
    )
    assert one == replay
    decision = OwnerDecision(
        decision_id=uuid4(),
        assessment_id=one.id,
        assessment_digest=one.body_digest,
        target=assessment.target,
        action="hold",
        reason="Retain hold.",
    )
    decisions = await asyncio.gather(
        *(
            boot.service.decide(
                case_id,
                decision.model_copy(update={"decision_id": uuid4(), "action": "reject" if i % 2 else "hold"}),
                **kwargs,
            )
            for i in range(16)
        )
    )
    current = max(decisions, key=lambda d: d.sequence)
    view = await boot.service.feedback(case_id, **kwargs)
    assert view.current_decision_id == current.id
    assert view.status == ("hold" if current.body["action"] == "hold" else "rejected")
    original = decisions[0]
    assert await boot.service.decide(case_id, OwnerDecision.model_validate(original.body), **kwargs) == original
    with pytest.raises(CreationRefused, match="feedback_capacity"):
        await boot.service.decide(case_id, decision, **kwargs)
    for _ in range(15):
        await boot.service.assess(case_id, assessment.model_copy(update={"assessment_id": uuid4()}), **kwargs)
    assert await boot.service.assess(case_id, assessment, **kwargs) == one
    with pytest.raises(CreationRefused, match="feedback_capacity"):
        await boot.service.assess(case_id, assessment.model_copy(update={"assessment_id": uuid4()}), **kwargs)
    view = await boot.service.feedback(case_id, **kwargs)
    assert len({e.sequence for e in (*view.assessments, *view.decisions)}) == 32
    assert view.status == "review_required"


async def test_feedback_rechecks_revoked_authority_after_case_lock(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    boot, case_id, assessment = await completed_feedback_case(factory)
    original_case = boot.store._case  # pyright: ignore[reportPrivateUsage] - exercise authority recheck after real lock

    async def revoke_after_lock(session: Any, locked_id: UUID) -> Any:
        row = await original_case(session, locked_id)
        boot.access.revoke()
        return row

    monkeypatch.setattr(boot.store, "_case", revoke_after_lock)
    with pytest.raises(CreationRefused, match="local_authority"):
        await boot.service.assess(
            case_id, assessment, authentication=boot.authentication, principal=default_local_sigil()
        )
