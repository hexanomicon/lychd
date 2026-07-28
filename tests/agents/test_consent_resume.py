"""Offline park→resume through `perform_run` (C3, S4/S6). Scenarios 1-4.

Driven by a `FunctionModel` that calls the approval-required coven tool on the fresh
hop (→ `DeferredToolRequests`) and settles on the resume hop. Exercises the honest
consent path with NO real model request and NO Postgres — the graph parks into the
in-memory consent shim, the run re-enqueues, and the approved tool body runs under
the streaming API. Scenario 5 (durable restart) lives beside this in 4C-6.
"""

# White-box: reaches channel/ledger internals and reassigns methods for spies.
# pyright: reportPrivateUsage=false, reportArgumentType=false
# ruff: noqa: PT018 - compound run-state asserts read clearer than split ones here
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pydantic_ai.models
import pytest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.models.function import DeltaToolCall, FunctionModel

from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.domain.codex.ledger import InMemoryConsentLedger
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.stasis import InMemoryStasisStore
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.ghouls.runs import perform_run
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry, approval_test_toolset

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.models.function import AgentInfo

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


_COVEN_ARGS = '{"capability_key":"chat:local","reason":"swap"}'


async def _park_then_settle(messages: list[ModelMessage], info: AgentInfo) -> Any:
    """Call the coven tool on the first hop; settle with a BridgeReply thereafter (streamed)."""
    responded = any(isinstance(m, ModelResponse) for m in messages)
    if not responded:
        yield {0: DeltaToolCall(name="request_coven_swap", json_args=_COVEN_ARGS, tool_call_id="c1")}
    else:
        yield {
            0: DeltaToolCall(
                name=info.output_tools[0].name, json_args='{"answer":"done","fragments":[]}', tool_call_id="o1"
            )
        }


async def _always_park(messages: list[ModelMessage], info: AgentInfo) -> Any:
    """Always call the coven tool — drives chained consent rounds to the limit (streamed)."""
    _ = info
    n = sum(1 for m in messages if isinstance(m, ModelResponse))
    yield {0: DeltaToolCall(name="request_coven_swap", json_args=_COVEN_ARGS, tool_call_id=f"c{n}")}


async def _park_two_approvals(messages: list[ModelMessage], info: AgentInfo) -> Any:
    """Emit TWO approval-required coven calls in one response (the F5 multi-approval turn)."""
    responded = any(isinstance(m, ModelResponse) for m in messages)
    if not responded:
        yield {
            0: DeltaToolCall(name="request_coven_swap", json_args=_COVEN_ARGS, tool_call_id="c1"),
            1: DeltaToolCall(name="request_coven_swap", json_args=_COVEN_ARGS, tool_call_id="c2"),
        }
    else:
        yield {
            0: DeltaToolCall(
                name=info.output_tools[0].name, json_args='{"answer":"done","fragments":[]}', tool_call_id="o1"
            )
        }


def _substrate(model: Any) -> tuple[RunSubstrate, InMemoryRunLedger, InProcessEventBus, BridgeSessionStore, Any]:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    bus = InProcessEventBus(ledger=ledger)
    sessions = BridgeSessionStore()
    orch = FakeOrchestrator()
    substrate = RunSubstrate(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        orchestrator=orch,
        dispatcher=FakeDispatcher(model=model, toolsets=(approval_test_toolset(),)),
        context=ContextOrchestrator(registry=FakeRegistry()),
        fragments=build_fragment_registry(),
        turns=sessions,
        consents=InMemoryConsentLedger(),
        forge=default_forge(),
        stasis_store=InMemoryStasisStore(),
    )
    return substrate, ledger, bus, sessions, orch


async def _seed(ledger: InMemoryRunLedger, sessions: BridgeSessionStore, run_id: str) -> None:
    from lychd.agents.router import Intent
    from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT

    session = await sessions.create_session(title="t")
    intent = Intent(session_id=session.id, run_id=run_id, prompt="swap the coven", source="bridge")
    await ledger.create(
        intent,
        workflow_name="bridge_chat",
        pattern_manifest=BRIDGE_CHAT.manifest.snapshot(),
        queue_name="runs",
        priority=70,
    )


def _kinds(bus: InProcessEventBus, run_id: str) -> list[str]:
    channel = bus.open(run_id)
    return [str(e.kind) for e in channel._replay]


# --- Scenario 1: park, no DONE, snapshot at AwaitConsent, S4 emit ordering ----


@pytest.mark.asyncio
async def test_scenario1_parks_with_s4_emit_ordering() -> None:
    substrate, ledger, bus, sessions, _orch = _substrate(FunctionModel(stream_function=_park_then_settle))
    await _seed(ledger, sessions, "run_1")

    order: list[str] = []
    orig_set = ledger.set_status

    async def rec_set(rid: str, status: RunStatus, *, error: str | None = None) -> None:
        await orig_set(rid, status, error=error)
        order.append(f"status:{status.value}")

    ledger.set_status = rec_set  # type: ignore[method-assign]
    orig_emitter = bus.emitter

    def rec_emitter(rid: str) -> Any:
        em = orig_emitter(rid)
        orig_consent = em.consent

        def rec_consent(cid: str, *, tool_name: str = "") -> Any:
            order.append("emit:consent")
            return orig_consent(cid, tool_name=tool_name)

        em.consent = rec_consent  # type: ignore[method-assign]
        return em

    bus.emitter = rec_emitter  # type: ignore[method-assign]

    result = await perform_run({"run_substrate": substrate}, run_id="run_1")

    assert result["status"] == "awaiting_consent"
    run = await ledger.get("run_1")
    assert run is not None
    assert run.status is RunStatus.AWAITING_CONSENT
    assert run.consent_id is not None
    assert await substrate.stasis_store.exists("run_1")  # durable checkpoint written
    kinds = _kinds(bus, "run_1")
    assert "consent" in kinds
    assert "done" not in kinds  # a parked run never closes the stream
    # S4: the CONSENT event fires only AFTER set_status(AWAITING_CONSENT).
    assert "status:awaiting_consent" in order
    assert order.index("status:awaiting_consent") < order.index("emit:consent")


async def _park(substrate: RunSubstrate, run_id: str) -> str:
    result = await perform_run({"run_substrate": substrate}, run_id=run_id)
    assert result["status"] == "awaiting_consent"
    run = await substrate.ledger.get(run_id)
    assert run is not None and run.consent_id is not None
    return run.consent_id


async def _resume(substrate: RunSubstrate, run_id: str, consent_id: str, *, approved: bool) -> dict[str, Any]:
    await substrate.consents.decide(consent_id, approved=approved, decided_by="magus")  # verdict commits to the ledger
    await substrate.ledger.set_status(run_id, RunStatus.QUEUED)  # engine.approve edge (re-enqueue)
    return await perform_run({"run_substrate": substrate}, run_id=run_id, resume=True)


# --- Scenario 2: approve → tool body runs, single DONE, seq continues ---------


@pytest.mark.asyncio
async def test_scenario2_approve_resumes_and_runs_tool_body() -> None:
    substrate, ledger, bus, sessions, orch = _substrate(FunctionModel(stream_function=_park_then_settle))
    await _seed(ledger, sessions, "run_2")
    consent_id = await _park(substrate, "run_2")
    channel = bus.open("run_2")  # hold the ref: the resume's terminal closes + drops it
    seq_at_park = channel.next_seq
    parked = await ledger.get("run_2")
    assert parked is not None
    original_set_status = ledger.set_status
    checkpoint_existed_at_done = False

    async def record_terminal_order(run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        nonlocal checkpoint_existed_at_done
        if status is RunStatus.DONE:
            checkpoint_existed_at_done = await substrate.stasis_store.exists("run_2")
        await original_set_status(run_id, status, error=error)

    ledger.set_status = record_terminal_order

    result = await _resume(substrate, "run_2", consent_id, approved=True)

    assert result["status"] == "done"
    run = await ledger.get("run_2")
    assert run is not None and run.status is RunStatus.DONE
    assert checkpoint_existed_at_done is True  # GraphRunner did not delete before terminal commit
    assert not await substrate.stasis_store.exists("run_2")  # cleared on settle
    # The approved tool body RAN (request_transition reached the orchestrator).
    assert any(call[0] == "request" for call in orch.calls)
    kinds = [str(e.kind) for e in channel._replay]
    assert kinds.count("done") == 1  # exactly one terminal
    # seq strictly continues on the same channel (no restart-at-0).
    assert channel.next_seq > seq_at_park
    session = next(iter(sessions._sessions.values()))
    assert len(session.message_history) >= 4
    assert {message.get("run_id") for message in session.message_history} == {"run_2"}
    bounded = ContextOrchestrator(registry=FakeRegistry(), turn_window=1).assemble(
        run_id="run-next",
        session_id=session.id,
        query="what happened?",
        history=session.message_history,
    )
    assert bounded.state_window == session.message_history


# --- Scenario 3: refuse → no orchestrator call, prose, settles DONE -----------


@pytest.mark.asyncio
async def test_scenario3_refuse_resumes_without_orchestrator_call() -> None:
    substrate, ledger, bus, sessions, orch = _substrate(FunctionModel(stream_function=_park_then_settle))
    await _seed(ledger, sessions, "run_3")
    consent_id = await _park(substrate, "run_3")
    channel = bus.open("run_3")  # hold the ref before the resume's terminal drops it

    result = await _resume(substrate, "run_3", consent_id, approved=False)

    assert result["status"] == "done"
    run = await ledger.get("run_3")
    assert run is not None and run.status is RunStatus.DONE
    assert orch.calls == []  # refusal → the tool body never ran
    assert [str(e.kind) for e in channel._replay].count("done") == 1


# --- Scenario 4: chained approvals → round-3 bottleneck honest settle ----------


@pytest.mark.asyncio
async def test_scenario4_chained_rounds_hit_bottleneck() -> None:
    substrate, ledger, _bus, sessions, _orch = _substrate(FunctionModel(stream_function=_always_park))
    await _seed(ledger, sessions, "run_4")

    consent_id = await _park(substrate, "run_4")
    status = "awaiting_consent"
    resumes = 0
    while status == "awaiting_consent" and resumes < 5:
        result = await _resume(substrate, "run_4", consent_id, approved=True)
        status = result["status"]
        resumes += 1
        if status == "awaiting_consent":
            run = await ledger.get("run_4")
            assert run is not None and run.consent_id is not None
            consent_id = run.consent_id

    assert status == "done"  # settled honestly at the round limit
    run = await ledger.get("run_4")
    assert run is not None and run.status is RunStatus.DONE
    # The agent turn settled with the bottleneck prose (round limit reached).
    turn = await sessions.settled_turn_for_run("run_4")
    assert turn is not None
    assert "round limit" in turn.content.lower()


# --- Scenario 5: durable restart-resume — verdict lands, seq continues, no lost Steps


@pytest.mark.asyncio
async def test_scenario5_durable_restart_resume_seq_continuing() -> None:
    """Park → simulate restart (fresh bus/substrate, carried ledger+consents+stasis) → resume.

    The R1 keystone: the resumed run seeds its FRESH channel via `ledger.next_seq`, so Step
    seqs continue strictly across the restart — no re-collided, silently-shed Step rows.
    """
    import asyncio

    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    consents = InMemoryConsentLedger()
    orch = FakeOrchestrator()
    stasis_store = InMemoryStasisStore()

    def _mk_substrate(bus: InProcessEventBus, sessions: BridgeSessionStore) -> RunSubstrate:
        return RunSubstrate(
            ledger=ledger,
            bus=bus,
            workflows=builtin_workflow_registry(),
            orchestrator=orch,
            dispatcher=FakeDispatcher(
                model=FunctionModel(stream_function=_park_then_settle),
                toolsets=(approval_test_toolset(),),
            ),
            context=ContextOrchestrator(registry=FakeRegistry()),
            fragments=build_fragment_registry(),
            turns=sessions,
            consents=consents,
            forge=default_forge(),
            stasis_store=stasis_store,
        )

    # Boot 1: park.
    bus1 = InProcessEventBus(ledger=ledger)
    sessions = BridgeSessionStore()
    sub1 = _mk_substrate(bus1, sessions)
    await _seed(ledger, sessions, "run_5")
    park_result = await perform_run({"run_substrate": sub1}, run_id="run_5")
    assert park_result["status"] == "awaiting_consent"
    run = await ledger.get("run_5")
    assert run is not None and run.consent_id is not None
    consent_id = run.consent_id
    assert await stasis_store.exists("run_5")  # the durable checkpoint really survives
    session = next(iter(sessions._sessions.values()))
    assert session.message_history == []  # parked work is not completed conversation history
    await asyncio.sleep(0.05)  # let the ledger tee drain the pre-park Step rows
    pre_seqs = [e.seq for e in ledger.events("run_5")]
    assert pre_seqs  # some Step rows persisted before the park

    # RESTART: a fresh bus + substrate; the ledger + consents + checkpoint store carry over.
    bus2 = InProcessEventBus(ledger=ledger)
    sub2 = _mk_substrate(bus2, sessions)

    await consents.decide(consent_id, approved=True, decided_by="magus")
    await ledger.set_status("run_5", RunStatus.QUEUED)
    resume_result = await perform_run({"run_substrate": sub2}, run_id="run_5", resume=True)

    assert resume_result["status"] == "done"
    run = await ledger.get("run_5")
    assert run is not None and run.status is RunStatus.DONE
    assert not await stasis_store.exists("run_5")  # cleared on settle
    assert any(call[0] == "request" for call in orch.calls)  # the approved tool body ran
    assert len(session.message_history) >= 4
    assert {message.get("run_id") for message in session.message_history} == {"run_5"}
    await asyncio.sleep(0.05)  # let the resume-hop tee drain
    all_seqs = [e.seq for e in ledger.events("run_5")]
    # R1: NO lost Step rows — the fresh channel continued the seq, never re-collided at 0.
    assert len(all_seqs) == len(set(all_seqs)), f"duplicate Step seqs (lost rows): {all_seqs}"
    assert max(all_seqs) > max(pre_seqs)  # resume emits landed strictly past the pre-park history


# --- F5: a multi-approval turn degrades to an honest bottleneck, never a shared verdict


@pytest.mark.asyncio
async def test_multi_approval_turn_degrades_to_bottleneck() -> None:
    """Two approval-required calls in one turn settle as a bottleneck, not a shared verdict (F5).

    One card = one verdict; pydantic-ai requires answering every deferred call, so a
    single card could only resolve a >1-approval turn by silently applying its verdict
    to unseen calls. The turn is refused honestly instead — no park, no consent row.
    """
    substrate, ledger, _bus, sessions, _orch = _substrate(FunctionModel(stream_function=_park_two_approvals))
    await _seed(ledger, sessions, "run_m")

    result = await perform_run({"run_substrate": substrate}, run_id="run_m")

    assert result["status"] == "done"  # settled, not parked
    run = await ledger.get("run_m")
    assert run is not None
    assert run.status is RunStatus.DONE
    assert run.consent_id is None  # never parked on a consent
    turn = await sessions.settled_turn_for_run("run_m")
    assert turn is not None
    assert "not yet supported" in turn.content.lower()


# --- F1: a verdict recorded BEFORE the status flip (page-render approve) is not lost --


class _RecordingQueue:
    """A minimal RunQueue that records enqueues (the post-flip re-admission target)."""

    def __init__(self) -> None:
        self.enqueued: list[dict[str, Any]] = []

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        _ = job_or_func
        self.enqueued.append(kwargs)

    async def job(self, job_key: str, /) -> Any:
        _ = job_key
        return None

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)


class _FailingResumeQueue(_RecordingQueue):
    """A broker failure after the post-park admission CAS."""

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        _ = (job_or_func, kwargs)
        msg = "resume broker down"
        raise RuntimeError(msg)


@pytest.mark.asyncio
async def test_preflip_verdict_is_not_lost() -> None:
    """A verdict recorded before the AWAITING_CONSENT flip is re-admitted, not stranded (F1).

    Simulate the Bridge PAGE-RENDER approve landing in the pre-flip window: the instant
    `park_on_consent` commits the consent row (while the run is still RUNNING), the Magus
    approves. `engine.approve` would no-op then (row not yet AWAITING_CONSENT). Without
    the fix the run stays AWAITING_CONSENT forever; with it, `perform_run` re-reads the
    verdict after the flip, wins the same CAS admission gate, and enqueues the resume.
    """
    substrate, ledger, bus, sessions, _orch = _substrate(FunctionModel(stream_function=_park_then_settle))
    queue = _RecordingQueue()
    substrate.queues = {"runs": queue}  # the re-admission needs a queue to enqueue onto
    await _seed(ledger, sessions, "run_pf")

    # The graph parks with a PENDING verdict (AwaitConsent raises); `perform_run` then
    # calls `set_consent` (run still RUNNING) BEFORE the AWAITING_CONSENT flip. Hook it to
    # land the Magus's approve in exactly that pre-flip window — where `engine.approve`
    # would no-op because the row is not yet AWAITING_CONSENT.
    orig_set_consent = ledger.set_consent

    async def set_consent_then_preflip_approve(run_id: str, consent_id: str | None) -> None:
        await orig_set_consent(run_id, consent_id)
        if consent_id is not None:
            await substrate.consents.decide(consent_id, approved=True, decided_by="magus")

    ledger.set_consent = set_consent_then_preflip_approve

    channel = bus.open("run_pf")
    result = await perform_run({"run_substrate": substrate}, run_id="run_pf")

    assert result["status"] == "queued"  # re-admitted, not left awaiting_consent
    run = await ledger.get("run_pf")
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert len(queue.enqueued) == 1
    assert queue.enqueued[0]["resume"] is True
    assert channel.closed is False  # a re-admitted run keeps its stream open for the resume hop


@pytest.mark.asyncio
async def test_preflip_resume_enqueue_failure_restores_consent_wait() -> None:
    """The post-park race path compensates a failed enqueue and remains replayable."""
    from lychd.domain.cortex.engine import QueueRouter, RunEngine

    substrate, ledger, bus, sessions, _orch = _substrate(FunctionModel(stream_function=_park_then_settle))
    substrate.queues = {"runs": _FailingResumeQueue()}
    await _seed(ledger, sessions, "run_pf_fail")

    original_set_consent = ledger.set_consent

    async def set_consent_then_preflip_approve(run_id: str, consent_id: str | None) -> None:
        await original_set_consent(run_id, consent_id)
        if consent_id is not None:
            await substrate.consents.decide(consent_id, approved=True, decided_by="magus")

    ledger.set_consent = set_consent_then_preflip_approve

    with pytest.raises(RuntimeError, match="resume broker down"):
        await perform_run({"run_substrate": substrate}, run_id="run_pf_fail")

    restored = await ledger.get("run_pf_fail")
    assert restored is not None
    assert restored.status is RunStatus.AWAITING_CONSENT
    assert restored.consent_id is not None
    assert restored.enqueue_seq == 1

    retry_queue = _RecordingQueue()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=substrate.workflows,
        queue_router=QueueRouter(),
        queues={"runs": retry_queue},
    )
    await engine.approve(restored.consent_id, approved=True)

    retried = await ledger.get("run_pf_fail")
    assert retried is not None
    assert retried.status is RunStatus.QUEUED
    assert len(retry_queue.enqueued) == 1
    assert retry_queue.enqueued[0]["resume"] is True


# --- stasis lost: resume with the checkpoint gone → honest FAILED, never a silent re-run


@pytest.mark.asyncio
async def test_stasis_lost_resume_fails_honestly() -> None:
    substrate, ledger, _bus, sessions, _orch = _substrate(FunctionModel(stream_function=_park_then_settle))
    await _seed(ledger, sessions, "run_sl")
    consent_id = await _park(substrate, "run_sl")
    run = await ledger.get("run_sl")
    assert run is not None
    await substrate.stasis_store.delete("run_sl")  # the checkpoint vanished

    await substrate.consents.decide(consent_id, approved=True, decided_by="magus")
    await ledger.set_status("run_sl", RunStatus.QUEUED)
    result = await perform_run({"run_substrate": substrate}, run_id="run_sl", resume=True)

    assert result["status"] == "failed"
    run = await ledger.get("run_sl")
    assert run is not None and run.status is RunStatus.FAILED
    assert run.error == "stasis lost"
    assert not await substrate.stasis_store.exists("run_sl")
