"""Native peer durable waits retain exact custody and current resume authority."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import BaseModel
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.agents.workflows.base import PatternNode, PeerTaskNode
from lychd.agents.workflows.native_public_peer import NATIVE_PUBLIC_PEER, NativePublicPeerState, WaitPublicPeer
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine, admit_peer_resume
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.execution_context import current_occurrence_id, current_step_id
from lychd.domain.cortex.graph import build_serial_graph
from lychd.domain.cortex.graph_runner import GraphRunner, NodeOccurrenceEvent
from lychd.domain.cortex.ledger import InMemoryRunLedger, PeerAdmissionEvidence
from lychd.domain.cortex.runs import IllegalRunTransitionError, RunDeliveryState, RunRecord, RunStatus
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore
from lychd.domain.intercom.native import (
    PeerDeclarationProof,
    PeerRunBinding,
    PeerTaskParked,
    PeerTaskPending,
    PeerTaskRef,
)
from lychd.ghouls.runs import _commit_peer_park, _recoverable_peer_park, _validate_resume_owner, reconcile_peer_runs

if TYPE_CHECKING:
    from lychd.domain.cortex.substrate import RunSubstrate
    from lychd.domain.intercom.native import PeerWorkflowPort


def _binding() -> PeerRunBinding:
    return PeerRunBinding(
        request_id=uuid4(),
        declaration_id=uuid4(),
        operation_id=uuid4(),
        peer_id=uuid4(),
        purpose="public-test",
        task_schema="public-text@1",
        endpoint="https://peer.invalid/a2a",
        source_digest="a" * 64,
        text_digest="b" * 64,
        expires_at=datetime.now(UTC) + timedelta(minutes=2),
    )


async def _running() -> tuple[InMemoryRunLedger, RunRecord, PeerAdmissionEvidence]:
    binding = _binding()
    ledger = InMemoryRunLedger()
    run = await ledger.create(
        Intent(session_id="session", source="peer_public", prompt="public question", admitted_peer=binding),
        workflow_name=NATIVE_PUBLIC_PEER.name,
        pattern_manifest=NATIVE_PUBLIC_PEER.manifest.snapshot(),
        queue_name="runs",
        priority=50,
    )
    assert (await ledger.try_claim_run(run.run_id, enqueue_seq=0)).acknowledged
    run = await ledger.get(run.run_id)
    assert run is not None
    ref = PeerTaskRef(
        task_id=uuid4(),
        run_id=run.run_id,
        station="peer_wait",
        request_id=binding.request_id,
        binding_digest=binding.digest,
    )
    task: dict[str, Any] = {
        "task_id": str(ref.task_id),
        "native_run_id": run.run_id,
        "native_station": ref.station,
        "native_request_id": str(binding.request_id),
        "native_binding_digest": binding.digest,
        "native_pattern_digest": NATIVE_PUBLIC_PEER.manifest.digest,
        "native_enqueue_seq": 0,
        "native_step_id": str(uuid4()),
        "native_occurrence_id": str(uuid4()),
        "adoption_closed": False,
        "peer_id": str(binding.peer_id),
        "declaration_id": str(binding.declaration_id),
        "operation_id": str(binding.operation_id),
        "purpose": binding.purpose,
        "task_schema": binding.task_schema,
        "endpoint": binding.endpoint,
        "source_digest": binding.source_digest,
        "text_digest": binding.text_digest,
        "expires_at": binding.expires_at.isoformat(),
        "local_status": "prepared",
        "submit_claimed": False,
        "foreign_task_id": None,
        "foreign_status": None,
        "settlement": None,
    }
    return (
        ledger,
        run,
        PeerAdmissionEvidence(
            ref=ref,
            pattern_digest=NATIVE_PUBLIC_PEER.manifest.digest,
            enqueue_seq=0,
            step_id=task["native_step_id"],
            occurrence_id=task["native_occurrence_id"],
            task=task,
        ),
    )


def _terminal(evidence: PeerAdmissionEvidence) -> PeerAdmissionEvidence:
    settlement = {
        "status": "received",
        "terminal": True,
        "foreign_task_id": "foreign-1",
        "foreign_status": "TASK_STATE_COMPLETED",
        "response_nonce": "nonce-1",
        "response_digest": "c" * 64,
        "result": {"text": ["attributed response"], "origin": "authenticated-foreign-data"},
    }
    task = {
        **evidence.task,
        "local_status": "terminal",
        "submit_claimed": True,
        "foreign_task_id": "foreign-1",
        "foreign_status": "TASK_STATE_COMPLETED",
        "settlement": settlement,
    }
    return replace(
        evidence,
        task=task,
        transmission={
            "id": str(uuid4()),
            "task_id": str(evidence.ref.task_id),
            "status": "received",
            "settlement": settlement,
        },
    )


@pytest.mark.asyncio
async def test_peer_park_and_exact_terminal_cas_create_one_successor() -> None:
    ledger, run, prepared = await _running()
    await ledger.park_peer(run.run_id, prepared.ref, evidence=prepared)
    parked = await ledger.get(run.run_id)
    assert parked is not None
    assert parked.status is RunStatus.AWAITING_PEER
    assert parked.peer_task_id == str(prepared.ref.task_id)
    assert parked.consent_id is parked.delegated_job_id is None
    with pytest.raises(IllegalRunTransitionError):
        await ledger.set_status(run.run_id, RunStatus.QUEUED)
    assert await ledger.try_admit_peer(run.run_id, task_id=str(prepared.ref.task_id), current=lambda: None) is None
    evidence = _terminal(prepared)
    calls: list[str] = []
    seqs = await asyncio.gather(
        *(
            ledger.try_admit_peer(
                run.run_id,
                task_id=str(prepared.ref.task_id),
                evidence=evidence,
                current=lambda: calls.append("current"),
            )
            for _ in range(2)
        )
    )
    assert seqs == [1, None]
    assert calls == ["current"]
    delivery = await ledger.get_delivery(run.run_id, enqueue_seq=1)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PENDING
    assert delivery.resume
    current = await ledger.get(run.run_id)
    assert current is not None
    assert current.peer_task_id == str(prepared.ref.task_id)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("native_run_id", "another-run"),
        ("native_station", "another-station"),
        ("native_binding_digest", "d" * 64),
        ("native_pattern_digest", "d" * 64),
        ("native_enqueue_seq", 1),
        ("adoption_closed", True),
        ("source_digest", "d" * 64),
        ("declaration_id", str(uuid4())),
    ],
)
@pytest.mark.asyncio
async def test_peer_resume_refuses_changed_provenance(field: str, value: object) -> None:
    ledger, run, prepared = await _running()
    await ledger.park_peer(run.run_id, prepared.ref, evidence=prepared)
    evidence = _terminal(prepared)
    evidence = replace(evidence, task={**evidence.task, field: value})
    assert (
        await ledger.try_admit_peer(
            run.run_id, task_id=str(prepared.ref.task_id), evidence=evidence, current=lambda: None
        )
        is None
    )
    current = await ledger.get(run.run_id)
    assert current is not None
    assert current.status is RunStatus.AWAITING_PEER


@pytest.mark.asyncio
async def test_peer_resume_requires_correlated_received_transmission_and_current_authority() -> None:
    ledger, run, prepared = await _running()
    await ledger.park_peer(run.run_id, prepared.ref, evidence=prepared)
    terminal = _terminal(prepared)
    for transmission in (
        None,
        {"task_id": str(uuid4()), "status": "received", "settlement": terminal.task["settlement"]},
        {"task_id": str(prepared.ref.task_id), "status": "unknown", "settlement": terminal.task["settlement"]},
    ):
        assert (
            await ledger.try_admit_peer(
                run.run_id,
                task_id=str(prepared.ref.task_id),
                evidence=replace(terminal, transmission=transmission),
                current=lambda: None,
            )
            is None
        )

    def revoked() -> None:
        msg = "marker revoked"
        raise PermissionError(msg)

    with pytest.raises(PermissionError, match="marker revoked"):
        await ledger.try_admit_peer(run.run_id, task_id=str(prepared.ref.task_id), evidence=terminal, current=revoked)
    current = await ledger.get(run.run_id)
    assert current is not None
    assert current.status is RunStatus.AWAITING_PEER


@pytest.mark.asyncio
async def test_unknown_submit_routes_local_noncompletion_without_foreign_success() -> None:
    ledger, run, prepared = await _running()
    await ledger.park_peer(run.run_id, prepared.ref, evidence=prepared)
    task = {**prepared.task, "local_status": "unknown", "submit_claimed": True}
    evidence = replace(prepared, task=task)
    assert (
        await ledger.try_admit_peer(
            run.run_id, task_id=str(prepared.ref.task_id), evidence=evidence, current=lambda: None
        )
        is None
    )
    evidence = replace(
        evidence,
        transmission={
            "task_id": str(prepared.ref.task_id),
            "method": "SendMessage",
            "status": "unknown",
            "settlement": {"status": "unknown"},
        },
    )
    assert (
        await ledger.try_admit_peer(
            run.run_id, task_id=str(prepared.ref.task_id), evidence=evidence, current=lambda: None
        )
        == 1
    )
    current = await ledger.get(run.run_id)
    assert current is not None
    assert current.peer_task_id == str(prepared.ref.task_id)


@dataclass
class _Queue:
    fail: bool = False
    enqueued: list[dict[str, Any]] = field(default_factory=list)

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> object:
        if self.fail:
            msg = "broker unavailable"
            raise OSError(msg)
        self.enqueued.append({"func": job_or_func, **kwargs})
        return object()

    async def job(self, job_key: str, /) -> None:
        _ = job_key

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = job, error, ttl


@pytest.mark.asyncio
async def test_publication_failure_preserves_successor_for_delivery_relay() -> None:
    ledger, run, prepared = await _running()
    await ledger.park_peer(run.run_id, prepared.ref, evidence=prepared)
    queue = _Queue(fail=True)
    assert await admit_peer_resume({"runs": queue}, ledger, run, evidence=_terminal(prepared), current=lambda: None)
    current = await ledger.get(run.run_id)
    assert current is not None
    assert current.status is RunStatus.QUEUED
    delivery = await ledger.get_delivery(run.run_id, enqueue_seq=1)
    assert delivery is not None
    assert delivery.state is RunDeliveryState.PENDING


@pytest.mark.asyncio
async def test_worker_commits_peer_park_without_resident_network_probe() -> None:
    ledger, run, evidence = await _running()
    peer = SimpleNamespace(
        evidence=AsyncMock(return_value=evidence), drive_wait=AsyncMock(side_effect=AssertionError("resident contact"))
    )
    bus = InProcessEventBus()
    from lychd.domain.cortex.claims import RunClaimCoordinator

    substrate = cast("RunSubstrate", SimpleNamespace(peer=peer, claims=RunClaimCoordinator()))
    result = await _commit_peer_park(
        substrate, ledger, bus.emitter(run.run_id), run.run_id, PeerTaskParked(ref=evidence.ref)
    )
    assert result["status"] == "awaiting_peer"
    peer.drive_wait.assert_not_awaited()


@pytest.mark.asyncio
async def test_peer_prepark_recovery_accepts_only_one_created_exact_checkpoint() -> None:
    ledger, run, evidence = await _running()
    store = InMemoryStasisStore()
    persistence = DurableStasisPhylactery(job_id=run.run_id, store=store)
    persistence.set_graph_types(NATIVE_PUBLIC_PEER.graph)
    state = cast("NativePublicPeerState", NATIVE_PUBLIC_PEER.make_state(run.to_intent()))
    state.peer_task = evidence.ref
    await persistence.snapshot_node(state, WaitPublicPeer())
    substrate = cast(
        "RunSubstrate",
        SimpleNamespace(
            peer=SimpleNamespace(evidence=AsyncMock(return_value=evidence)),
            ledger=ledger,
            stasis_store=store,
            workflows=BuiltinWorkflowRegistry(workflows=(NATIVE_PUBLIC_PEER,)),
        ),
    )
    assert await _recoverable_peer_park(substrate, run) == evidence.ref
    document = await store.load(run.run_id)
    assert document is not None
    for status in ("pending", "running", "error"):
        mutated = [{**document[0], "status": status}]
        await store.replace(run.run_id, mutated)
        assert await _recoverable_peer_park(substrate, run) is None
    await store.replace(run.run_id, [*document, {**document[0], "id": "duplicate-created"}])
    assert await _recoverable_peer_park(substrate, run) is None


@pytest.mark.asyncio
async def test_first_restored_peer_node_requires_exact_task_station_and_kind() -> None:
    ledger, run, evidence = await _running()
    await ledger.park_peer(run.run_id, evidence.ref, evidence=evidence)
    parked = await ledger.get(run.run_id)
    assert parked is not None
    state = cast("NativePublicPeerState", NATIVE_PUBLIC_PEER.make_state(run.to_intent()))
    state.peer_task = evidence.ref
    _validate_resume_owner(parked, state, WaitPublicPeer(), workflow=NATIVE_PUBLIC_PEER)
    state.peer_task = evidence.ref.model_copy(update={"task_id": uuid4()})
    with pytest.raises(ValueError, match="current peer owner"):
        _validate_resume_owner(parked, state, WaitPublicPeer(), workflow=NATIVE_PUBLIC_PEER)
    state.peer_task = evidence.ref
    with pytest.raises(ValueError, match="current peer owner"):
        _validate_resume_owner(parked, state, End("foreign"), workflow=NATIVE_PUBLIC_PEER)


class _State(BaseModel):
    run_id: str
    peer_task: PeerTaskRef


@dataclass
class _PeerStation(PeerTaskNode, BaseNode[_State, list[tuple[str | None, str | None]], str]):
    async def run(self, ctx: GraphRunContext[_State, list[tuple[str | None, str | None]]]) -> End[str]:
        ctx.deps.append((current_occurrence_id(), current_step_id()))
        raise PeerTaskPending(ctx.state.peer_task)


class _UnusedOrchestrator:
    async def handle_transition(self, *_args: Any, **_kwargs: Any) -> None:
        pytest.fail("peer wait cannot become hardware stasis")


@pytest.mark.asyncio
async def test_graph_peer_signal_checkpoints_and_scopes_actual_entered_step() -> None:
    _, run, evidence = await _running()
    graph = build_serial_graph(
        nodes=(_PeerStation,),
        state_type=_State,
        deps_type=list[tuple[str | None, str | None]],
        output_type=str,
        name="peer",
    )
    persistence = DurableStasisPhylactery(job_id=run.run_id, store=InMemoryStasisStore())
    events: list[NodeOccurrenceEvent] = []
    step_id = str(uuid4())

    def observe(event: NodeOccurrenceEvent) -> str:
        events.append(event)
        return step_id

    runner = GraphRunner[_State](
        orchestrator=_UnusedOrchestrator(),
        persistence=persistence,
        signal_priority=50,
        on_node_event=observe,
        run_id=run.run_id,
    )
    identities: list[tuple[str | None, str | None]] = []
    result = await runner.run_graph(
        graph, _PeerStation(), _State(run_id=run.run_id, peer_task=evidence.ref), deps=identities
    )
    assert isinstance(result, PeerTaskParked)
    assert result.ref == evidence.ref
    assert identities == [(events[0].occurrence_id, step_id)]
    assert events[-1].wait_kind == "peer"
    assert events[-1].peer_task_id == str(evidence.ref.task_id)
    assert current_occurrence_id() is current_step_id() is None
    from lychd.domain.cortex.stasis import NodeSnapshot

    snapshot = (await persistence.load_all())[-1]
    assert isinstance(snapshot, NodeSnapshot)
    assert snapshot.status == "created"
    assert NATIVE_PUBLIC_PEER.durable
    with pytest.raises(ValueError, match="kind='peer'"):
        PatternNode(key="wrong", label="Wrong", implementation=_PeerStation)


@pytest.mark.asyncio
async def test_engine_peer_binding_requires_server_proof_and_silent_restart() -> None:
    binding = _binding()
    authentication = object()
    proof = PeerDeclarationProof(authentication=authentication, binding=binding)
    peer = SimpleNamespace(drive_wait=AsyncMock(return_value=False))
    current = True

    def admission(intent: Intent, proof: PeerDeclarationProof) -> PeerRunBinding:
        _ = intent
        if not current or proof.authentication is not authentication:
            msg = "current marker required"
            raise PermissionError(msg)
        return proof.binding

    ledger = InMemoryRunLedger()
    queue = _Queue()
    engine = RunEngine(
        ledger=ledger,
        bus=InProcessEventBus(),
        workflows=BuiltinWorkflowRegistry(workflows=(NATIVE_PUBLIC_PEER,)),
        queue_router=QueueRouter(routing={"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": queue},
        peer=cast("PeerWorkflowPort", peer),
        peer_admission=admission,
    )
    intent = Intent(session_id="session", prompt="public", source="peer_public")
    with pytest.raises(ValueError, match="authenticated"):
        await engine.submit(intent)
    with pytest.raises(ValueError, match="server-owned"):
        await engine.submit(intent.model_copy(update={"admitted_peer": binding}), peer_declaration=proof)
    handle = await engine.submit(intent, peer_declaration=proof, idempotency_key="request")
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.to_intent().admitted_peer == binding
    current = False
    with pytest.raises(PermissionError, match="marker"):
        await engine.submit(intent, peer_declaration=proof, idempotency_key="request")
    assert len(queue.enqueued) == 1
    assert await reconcile_peer_runs(engine=engine) == {"status": "reconciled", "count": 0, "probe_errors": 0}


@pytest.mark.asyncio
async def test_missing_restart_permission_keeps_successor_queued_and_unpublished() -> None:
    from lychd.domain.codex.peer import PeerAuthorityError
    from lychd.ghouls.runs import _publish_delivery, perform_run

    ledger, run, evidence = await _running()
    await ledger.park_peer(run.run_id, evidence.ref, evidence=evidence)
    assert (
        await ledger.try_admit_peer(
            run.run_id,
            task_id=str(evidence.ref.task_id),
            evidence=_terminal(evidence),
            current=lambda: None,
        )
        == 1
    )
    successor = await ledger.get(run.run_id)
    delivery = await ledger.get_delivery(run.run_id, enqueue_seq=1)
    assert successor is not None
    assert delivery is not None
    checks: list[int] = []

    def unavailable(_run_id: str, _task_id: str, *, enqueue_seq: int) -> None:
        checks.append(enqueue_seq)
        code = "native-permission"
        raise PeerAuthorityError(code)

    queue = _Queue()
    gate = asyncio.Event()
    gate.set()
    substrate = cast(
        "RunSubstrate",
        SimpleNamespace(
            ledger=ledger,
            peer=SimpleNamespace(require_resume=unavailable),
            queues={"runs": queue},
            orchestrator=SimpleNamespace(worker_broker=SimpleNamespace(claim_gate=gate)),
        ),
    )
    outcome = await _publish_delivery(substrate, successor, delivery, queue)
    assert outcome.revisit
    assert outcome.errors == 0
    assert queue.enqueued == []
    assert await perform_run({"run_substrate": substrate}, run_id=run.run_id, enqueue_seq=1) == {
        "status": "queued",
        "run_id": run.run_id,
    }
    still_queued = await ledger.get(run.run_id)
    assert still_queued is not None
    assert still_queued.status is RunStatus.QUEUED
    assert still_queued.enqueue_seq == 1
    assert checks == [1, 1]


@pytest.mark.asyncio
async def test_current_marker_lost_during_retention_cannot_publish_peer_admission() -> None:
    binding = _binding()
    proof = PeerDeclarationProof(authentication=object(), binding=binding)
    current = True

    def admission(intent: Intent, proof: PeerDeclarationProof) -> PeerRunBinding:
        _ = intent
        if not current:
            raise PermissionError
        return proof.binding

    async def retain(_run_id: str) -> None:
        nonlocal current
        current = False

    ledger = InMemoryRunLedger()
    queue = _Queue()
    engine = RunEngine(
        ledger=ledger,
        bus=InProcessEventBus(),
        workflows=BuiltinWorkflowRegistry(workflows=(NATIVE_PUBLIC_PEER,)),
        queue_router=QueueRouter(routing={"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": queue},
        peer=cast("PeerWorkflowPort", SimpleNamespace()),
        peer_admission=admission,
    )
    with pytest.raises(PermissionError):
        await engine.submit(
            Intent(session_id="session", prompt="public", source="peer_public"),
            peer_declaration=proof,
            retain_before_publish=retain,
        )
    assert queue.enqueued == []
    failed = await ledger.list_by_status(RunStatus.FAILED)
    assert len(failed) == 1


@pytest.mark.asyncio
async def test_new_wait_replaces_peer_owner_without_erasing_historical_task() -> None:
    ledger, run, evidence = await _running()
    await ledger.park_peer(run.run_id, evidence.ref, evidence=evidence)
    assert (
        await ledger.try_admit_peer(
            run.run_id,
            task_id=str(evidence.ref.task_id),
            evidence=_terminal(evidence),
            current=lambda: None,
        )
        == 1
    )
    assert (await ledger.try_claim_run(run.run_id, enqueue_seq=1)).acknowledged
    await ledger.park_delegate(run.run_id, "new-delegate")
    delegated = await ledger.get(run.run_id)
    assert delegated is not None
    assert delegated.delegated_job_id == "new-delegate"
    assert delegated.peer_task_id is None
    assert (
        await ledger.try_admit_peer(
            run.run_id,
            task_id=str(evidence.ref.task_id),
            evidence=_terminal(evidence),
            current=lambda: None,
        )
        is None
    )
