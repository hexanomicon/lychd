"""Native Graph/Run authority and custody checks using effect-free substitutes."""
# pyright: reportPrivateUsage=false
# pyright: reportArgumentType=false
# ruff: noqa: ARG002

from __future__ import annotations

import asyncio
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic_ai.models.test import TestModel

from lychd.agents.workflows import BuiltinWorkflowRegistry
from lychd.agents.workflows.native_public_peer import NATIVE_PUBLIC_PEER
from lychd.db.intercom import IntercomStore
from lychd.domain.codex.peer import PeerAuthorityError, PublicTextSource
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.runs import RunHandle, RunStatus
from lychd.domain.intercom.native import PeerTaskOutcomeError
from lychd.ghouls.runs import perform_run
from lychd.system.services.peer_runs import CompositeRunEffects, PeerRunService
from tests.agents.fakes import FakeDispatcher
from tests.unit.domain.cortex.test_perform_run import _substrate
from tests.unit.system.services.test_intercom import NativeMemoryCustody, setup


class Custody(NativeMemoryCustody):
    """Keep correlated claims and append-only authority evidence in memory."""

    def __init__(self) -> None:
        super().__init__()
        self.transmissions: dict[UUID, dict[str, Any]] = {}
        self.terminals: dict[UUID, dict[str, Any]] = {}
        self.authorizations: list[dict[str, Any]] = []

    async def claim(
        self, task_id: UUID, attempt_id: UUID, record: dict[str, Any], limits: dict[str, Any]
    ) -> dict[str, Any]:
        retained = await super().claim(task_id, attempt_id, record, limits)
        self.transmissions[task_id] = {
            "id": str(attempt_id),
            "task_id": str(task_id),
            "method": record["method"],
            "status": "claimed",
            "record": deepcopy(record),
            "settlement": None,
        }
        return retained

    async def settle(
        self, task_id: UUID, attempt_id: UUID, record: dict[str, Any], *, current: Callable[[], None] | None = None
    ) -> dict[str, Any]:
        if current is not None:
            current()
        task = self.tasks[task_id]
        task["local_status"] = record.get("local_status", "terminal" if record.get("terminal") else "pending")
        task["status"] = task["local_status"]
        task["settlement"] = deepcopy(record)
        task["foreign_task_id"] = record.get("foreign_task_id", task.get("foreign_task_id"))
        task["foreign_status"] = record.get("foreign_status", task.get("foreign_status"))
        self.transmissions[task_id].update(status=record["status"], settlement=deepcopy(record))
        return task.copy()

    async def native_transmission(self, task_id: UUID) -> dict[str, Any] | None:
        return deepcopy(self.transmissions.get(task_id))

    async def terminal_transmission(self, task_id: UUID) -> dict[str, Any] | None:
        return deepcopy(self.terminals.get(task_id))

    async def native_tasks(self, run_id: str) -> list[dict[str, Any]]:
        return [deepcopy(task) for task in self.tasks.values() if task.get("native_run_id") == run_id]

    async def record_native_authorization(
        self, run_id: str, task_id: UUID, record: dict[str, Any], *, current: Callable[[], None]
    ) -> None:
        current()
        assert self.tasks[task_id]["native_run_id"] == run_id
        self.authorizations.append(deepcopy(record))

    def terminal(self, task_id: UUID, *, method: str = "SendMessage") -> None:
        """Seed authenticated remote custody; transport cryptography has its own tests."""
        record = {
            "status": "received",
            "terminal": True,
            "foreign_task_id": "foreign-exact",
            "foreign_status": "TASK_STATE_COMPLETED",
            "context_id": "context-exact",
            "response_nonce": "fresh-response",
            "response_digest": "a" * 64,
            "result": {"origin": "authenticated-foreign-data", "text": ["Public companion planning answer."]},
        }
        self.tasks[task_id].update(
            local_status="terminal",
            status="terminal",
            submit_claimed=True,
            foreign_task_id="foreign-exact",
            foreign_status="TASK_STATE_COMPLETED",
            settlement=deepcopy(record),
        )
        self.terminals[task_id] = {
            "id": str(uuid4()),
            "task_id": str(task_id),
            "method": method,
            "status": "received",
            "record": {"method": "SendMessage"},
            "settlement": record,
        }
        if method == "SendMessage":
            self.transmissions[task_id] = deepcopy(self.terminals[task_id])


async def rig() -> tuple[Any, ...]:
    intercom, original, authority, marker, peer_id, uri, _ = await setup()
    policy = replace(authority.policy, actions=authority.policy.actions | {"admit", "adopt", "resume", "inspect"})
    authority._policy = policy
    custody = Custody()
    custody.peers = deepcopy(original.peers)
    custody.peers[peer_id]["policy"] = policy.record()
    intercom._store = cast("IntercomStore", custody)
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    registry = BuiltinWorkflowRegistry(workflows=(NATIVE_PUBLIC_PEER,))
    substrate.workflows = registry
    fence = RunEffectFence()
    peer = PeerRunService(
        store=cast("IntercomStore", custody), intercom=intercom, ledger=ledger, authority=authority, fence=fence
    )
    engine = RunEngine(
        ledger=ledger,
        bus=substrate.bus,
        workflows=registry,
        queue_router=QueueRouter(routing={"default": RouteRule(queue="runs", priority=50)}),
        queues=substrate.queues,
        stasis_store=substrate.stasis_store,
        cancellations=substrate.cancellations,
        peer=peer,
        peer_admission=peer.admission,
        effects=peer,
    )
    peer.bind_engine(engine)
    substrate.peer, substrate.effects = peer, peer
    session = await sessions.create_session(title="Explicit public task")
    handle = await peer.admit_public_run(
        marker,
        session_id=session.id,
        request_id=uuid4(),
        source=PublicTextSource("Offer a public Blockworld companion planning explanation.", public_assertion=True),
        peer_id=peer_id,
        purpose="test-public",
        task_schema="public.text@1",
        endpoint=uri,
    )
    return peer, engine, substrate, ledger, custody, authority, marker, handle, intercom


@pytest.mark.asyncio
async def test_real_native_graph_prepares_then_parks_without_contact_and_resumes_once() -> None:
    peer, engine, substrate, ledger, custody, _, _, handle, _ = await rig()
    parked = await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    assert parked["status"] == "awaiting_peer"
    assert custody.claims == 0
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.peer_task_id is not None
    task_id = UUID(run.peer_task_id)
    task = custody.tasks[task_id]
    assert UUID(task["native_step_id"]) != UUID(task["native_occurrence_id"])
    assert await substrate.stasis_store.exists(handle.run_id)
    custody.terminal(task_id)
    results = await asyncio.gather(*(peer.drive_wait(handle.run_id) for _ in range(6)))
    assert results.count(True) == 1
    assert len(engine.queues["runs"].enqueued) == 2
    done = await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=1)
    assert done["status"] == "done"
    assert (await ledger.get(handle.run_id)).status is RunStatus.DONE
    assert not await substrate.stasis_store.exists(handle.run_id)
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_reconstructed_owner_stays_silent_until_explicit_fresh_marker_reauthorization() -> None:
    _, engine, substrate, ledger, custody, authority, marker, handle, intercom = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.peer_task_id is not None
    assert run.admitted_peer is not None
    custody.terminal(UUID(run.peer_task_id))
    replacement = PeerRunService(
        store=cast("IntercomStore", custody),
        intercom=intercom,
        ledger=ledger,
        authority=authority,
        fence=RunEffectFence(),
    )
    replacement.bind_engine(engine)
    assert not await replacement.drive_wait(handle.run_id)
    assert custody.claims == 0
    assert len(engine.queues["runs"].enqueued) == 1
    with pytest.raises(PeerAuthorityError, match="authentication"):
        await replacement.reauthorize_existing_run(
            replace(marker),
            run_id=run.run_id,
            expected_task_id=run.peer_task_id,
            expected_binding_digest=run.admitted_peer.digest,
            actions=frozenset({"read", "adopt", "resume"}),
        )
    await replacement.reauthorize_existing_run(
        marker,
        run_id=run.run_id,
        expected_task_id=run.peer_task_id,
        expected_binding_digest=run.admitted_peer.digest,
        actions=frozenset({"read", "adopt", "resume"}),
    )
    assert len(custody.authorizations) == 1
    assert await replacement.drive_wait(handle.run_id)
    assert not await replacement.drive_wait(handle.run_id)
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_unknown_no_foreign_id_takes_explicit_failure_and_never_resubmits() -> None:
    peer, _, substrate, ledger, custody, _, _, handle, _ = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    assert await peer.drive_wait(handle.run_id)  # BrokenContact fixture loses response.
    assert custody.claims == 1
    with pytest.raises(PeerTaskOutcomeError, match="unknown"):
        await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=1)
    assert (await ledger.get(handle.run_id)).status is RunStatus.FAILED
    assert custody.claims == 1
    assert not await peer.drive_wait(handle.run_id)
    task = next(iter(custody.tasks.values()))
    assert task["adoption_closed"]
    assert task["settlement"]["status"] == "unknown"
    assert task["foreign_task_id"] is None
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_cancel_without_remote_authority_closes_prepared_custody_and_keeps_uncertainty() -> None:
    _, engine, substrate, ledger, custody, authority, _, handle, _ = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    authority._access.revoke()
    await engine.cancel(handle.run_id)
    assert (await ledger.get(handle.run_id)).status is RunStatus.CANCELLED
    task = next(iter(custody.tasks.values()))
    assert task["adoption_closed"]
    assert task["closure_reason"] == "cancelled"
    assert task["foreign_task_id"] is None
    assert custody.claims == 0
    assert not await substrate.stasis_store.exists(handle.run_id)
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_success_dictionary_without_correlated_transmission_cannot_resume() -> None:
    peer, engine, substrate, ledger, custody, _, _, handle, _ = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.peer_task_id is not None
    custody.terminal(UUID(run.peer_task_id))
    custody.transmissions.clear()
    custody.terminals.clear()
    assert not await peer.drive_wait(handle.run_id)
    assert len(engine.queues["runs"].enqueued) == 1
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_composite_effects_attempts_all_owners_and_propagates_required_failure() -> None:
    stopped: list[str] = []

    class Effect:
        def fence(self, run_id: str, reason: str) -> None:
            pass

        def fence_claim(self, run_id: str, enqueue_seq: int, reason: str) -> None:
            pass

        def fence_all(self, reason: str) -> None:
            pass

        async def contain(self, run_id: str) -> None:
            stopped.append(run_id)

        async def contain_all(self) -> None:
            stopped.append("all")

    class Failure(Effect):
        async def contain(self, run_id: str) -> None:
            msg = "required local child remains live"
            raise RuntimeError(msg)

    effects = CompositeRunEffects(Failure(), Effect())
    with pytest.raises(ExceptionGroup, match="containment"):
        await effects.contain("run")
    assert stopped == ["run"]


@pytest.mark.asyncio
async def test_pending_send_uses_correlated_terminal_poll_instead_of_first_send_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    peer, _, substrate, ledger, custody, _, marker, handle, intercom = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.peer_task_id is not None
    task_id = UUID(run.peer_task_id)
    task = custody.tasks[task_id]
    task.update(submit_claimed=True, local_status="pending", foreign_task_id="foreign-exact")
    custody.transmissions[task_id] = {
        "task_id": str(task_id),
        "method": "SendMessage",
        "status": "received",
        "settlement": {"status": "received", "terminal": False, "foreign_status": "TASK_STATE_WORKING"},
    }
    polls: list[UUID] = []

    async def poll(
        authentication: object, *, task_id: UUID, current: Callable[[], None], **kwargs: Any
    ) -> dict[str, Any]:
        assert authentication is marker
        current()
        polls.append(task_id)
        custody.terminal(task_id, method="GetTask")
        current()
        return task.copy()

    monkeypatch.setattr(intercom, "poll", poll)
    assert await peer.drive_wait(handle.run_id)
    assert polls == [task_id]
    assert custody.transmissions[task_id]["settlement"]["terminal"] is False
    assert (await peer.evidence(run_id=handle.run_id, task_id=str(task_id))).transmission["method"] == "GetTask"
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=1)
    assert await peer.read_result(marker, run_id=handle.run_id) == "Public companion planning answer."
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_queued_successor_survives_missing_grant_then_fresh_reauthorization() -> None:
    peer, engine, substrate, ledger, custody, authority, marker, handle, intercom = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.peer_task_id is not None
    assert run.admitted_peer is not None
    custody.terminal(UUID(run.peer_task_id))
    assert await peer.drive_wait(run.run_id)
    replacement = PeerRunService(
        store=cast("IntercomStore", custody),
        intercom=intercom,
        ledger=ledger,
        authority=authority,
        fence=RunEffectFence(),
    )
    replacement.bind_engine(engine)
    substrate.peer = replacement
    engine.peer = replacement
    queued = await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=1)
    assert queued["status"] == "queued"
    assert (await ledger.get(run.run_id)).status is RunStatus.QUEUED
    await replacement.reauthorize_existing_run(
        marker,
        run_id=run.run_id,
        expected_task_id=run.peer_task_id,
        expected_binding_digest=run.admitted_peer.digest,
        actions=frozenset({"read", "adopt", "resume"}),
    )
    assert (await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=1))["status"] == "done"
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_explicit_inspection_retains_uncertainty_despite_remote_revocation() -> None:
    peer, engine, substrate, ledger, custody, authority, marker, handle, _ = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.admitted_peer is not None
    authority.fence(run.admitted_peer.peer_id)
    authority.uncertain(run.admitted_peer.peer_id)
    await engine.cancel(run.run_id)
    projection = await peer.status(marker, run_id=run.run_id)
    assert projection["status"] == "cancelled"
    assert projection["tasks"][0]["remote_outcome_unknown"] is False
    assert projection["tasks"][0]["submit_claimed"] is False
    assert projection["tasks"][0]["remote_containment"] == "unproved"
    assert "source" not in str(projection)
    assert "Public companion" not in str(projection)
    assert next(iter(custody.tasks.values()))["adoption_closed"]
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_graceful_shutdown_retires_locally_without_closing_restart_wait() -> None:
    peer, _, substrate, ledger, custody, _, _, handle, _ = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    await peer.contain_all()
    assert next(iter(custody.tasks.values()))["adoption_closed"] is False
    assert (await ledger.get(handle.run_id)).status is RunStatus.AWAITING_PEER
    assert not await peer.drive_wait(handle.run_id)
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_abandoned_claim_after_live_submit_retires_only_after_fresh_authorization(  # noqa: PLR0915 - preserve ordered live/retired crash proof
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, engine, substrate, ledger, custody, authority, marker, handle, intercom = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.peer_task_id is not None
    assert run.admitted_peer is not None
    task_id = UUID(run.peer_task_id)
    claimed, release = asyncio.Event(), asyncio.Event()
    original_claim = custody.claim

    async def claim(*args: Any, **kwargs: Any) -> dict[str, Any]:
        value = await original_claim(*args, **kwargs)
        claimed.set()
        await release.wait()  # Exact crash window: claim committed; no gate or wire yet.
        return value

    monkeypatch.setattr(custody, "claim", claim)
    sender = asyncio.create_task(
        intercom.send_prepared(
            marker,
            task_id=task_id,
            peer_id=run.admitted_peer.peer_id,
            purpose=run.admitted_peer.purpose,
            task_schema=run.admitted_peer.task_schema,
            endpoint=run.admitted_peer.endpoint,
            current=intercom._native_guards[task_id],
        )
    )
    try:
        await claimed.wait()
        assert custody.tasks[task_id]["local_status"] == "submitting"
        assert custody.transmissions[task_id]["status"] == "claimed"
        assert custody.transmissions[task_id]["settlement"] is None
        assert not intercom._pending
        replacement = PeerRunService(
            store=cast("IntercomStore", custody),
            intercom=intercom,
            ledger=ledger,
            authority=authority,
            fence=RunEffectFence(),
        )
        replacement.bind_engine(engine)
        assert not await replacement.drive_wait(run.run_id)
        await replacement.reauthorize_existing_run(
            marker,
            run_id=run.run_id,
            expected_task_id=run.peer_task_id,
            expected_binding_digest=run.admitted_peer.digest,
            actions=frozenset({"read", "adopt", "resume"}),
        )
        assert not await replacement.drive_wait(run.run_id)
        assert custody.transmissions[task_id]["settlement"] is None
        assert task_id not in intercom._abandoned_native_submits
        sender.cancel()
        with pytest.raises(asyncio.CancelledError):
            await sender
        assert not intercom._native_submits
        assert await replacement.drive_wait(run.run_id)
        assert custody.transmissions[task_id]["status"] == "unknown"
        assert custody.transmissions[task_id]["settlement"]["accepted_network_bytes"] == 0
        assert custody.tasks[task_id]["submit_claimed"] is True
        assert custody.tasks[task_id]["foreign_task_id"] is None
        assert custody.claims == 1
        substrate.peer = replacement
        with pytest.raises(PeerTaskOutcomeError, match="unknown"):
            await perform_run({"run_substrate": substrate}, run_id=run.run_id, enqueue_seq=1)
        projection = await replacement.status(marker, run_id=run.run_id)
        assert projection["status"] == "failed"
        assert projection["tasks"][0]["remote_outcome_unknown"] is True
        assert projection["tasks"][0]["remote_containment"] == "unproved"
        assert custody.claims == 1
    finally:
        release.set()
        if not sender.done():
            sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)
        await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_key_retirement_at_resume_cas_wait_prevents_old_terminal_successor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    peer, engine, substrate, ledger, custody, authority, _, handle, _ = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.peer_task_id is not None
    assert run.admitted_peer is not None
    custody.terminal(UUID(run.peer_task_id))
    original = ledger.try_admit_peer

    async def admit(*args: Any, **kwargs: Any) -> int | None:
        authority.retire_key(run.admitted_peer.peer_id, 1)
        return await original(*args, **kwargs)

    monkeypatch.setattr(ledger, "try_admit_peer", admit)
    assert not await peer.drive_wait(run.run_id)
    assert (await ledger.get(run.run_id)).status is RunStatus.AWAITING_PEER
    assert len(engine.queues["runs"].enqueued) == 1
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_key_retirement_after_cas_prevents_first_restored_station() -> None:
    peer, _, substrate, ledger, custody, authority, _, handle, _ = await rig()
    await perform_run({"run_substrate": substrate}, run_id=handle.run_id, enqueue_seq=0)
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.peer_task_id is not None
    assert run.admitted_peer is not None
    custody.terminal(UUID(run.peer_task_id))
    assert await peer.drive_wait(run.run_id)
    authority.retire_key(run.admitted_peer.peer_id, 1)
    result = await perform_run({"run_substrate": substrate}, run_id=run.run_id, enqueue_seq=1)
    assert result["status"] == "queued"
    assert (await ledger.get(run.run_id)).status is RunStatus.QUEUED
    await substrate.bus.aclose()


@pytest.mark.asyncio
async def test_concurrent_identical_admission_retains_one_source_proof_and_exact_retry(  # noqa: PLR0915 - ordered two-caller proof and immutable retry
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lychd.domain.cortex.admission import RunAdmissionCoordinator

    peer, engine, substrate, ledger, custody, _, marker, handle, intercom = await rig()
    run = await ledger.get(handle.run_id)
    assert run is not None
    assert run.admitted_peer is not None
    binding = run.admitted_peer
    request_id = uuid4()
    create_entered, release_create, second_waiting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    original_create = ledger.create_idempotent
    original_wait = RunAdmissionCoordinator.wait
    declarations_before = len(custody.declarations)
    original_declare = intercom.declare_public
    declarations: list[UUID] = []

    async def create(*args: Any, **kwargs: Any) -> Any:
        create_entered.set()
        await release_create.wait()
        return await original_create(*args, **kwargs)

    async def wait(coordinator: RunAdmissionCoordinator, key: tuple[str, str]) -> None:
        if coordinator is engine.admissions:
            second_waiting.set()
        await original_wait(coordinator, key)

    async def declare(*args: Any, **kwargs: Any) -> Any:
        declaration = await original_declare(*args, **kwargs)
        declarations.append(declaration.declaration_id)
        return declaration

    monkeypatch.setattr(ledger, "create_idempotent", create)
    monkeypatch.setattr(RunAdmissionCoordinator, "wait", wait)
    monkeypatch.setattr(intercom, "declare_public", declare)
    arguments = {
        "session_id": run.session_id,
        "request_id": request_id,
        "source": PublicTextSource("One exact concurrent public request.", public_assertion=True),
        "peer_id": binding.peer_id,
        "purpose": binding.purpose,
        "task_schema": binding.task_schema,
        "endpoint": binding.endpoint,
    }
    first = asyncio.create_task(peer.admit_public_run(marker, **arguments))
    second: asyncio.Task[Any] | None = None
    try:
        await create_entered.wait()
        second = asyncio.create_task(peer.admit_public_run(marker, **arguments))
        await second_waiting.wait()
        assert len(declarations) == 1
        assert len(custody.declarations) == declarations_before + 1
    finally:
        release_create.set()
        results = await asyncio.gather(first, *([second] if second is not None else []), return_exceptions=True)
    assert len(results) == 2
    assert not any(isinstance(value, BaseException) for value in results)
    first_result, second_result = results
    assert isinstance(first_result, RunHandle)
    assert isinstance(second_result, RunHandle)
    assert first_result.run_id == second_result.run_id
    retained = await ledger.get(first_result.run_id)
    assert retained is not None
    assert retained.status is RunStatus.QUEUED
    assert retained.admitted_peer is not None
    assert retained.admitted_peer.declaration_id == declarations[0]
    retry = await peer.admit_public_run(marker, **arguments)
    assert retry.run_id == retained.run_id
    assert len(declarations) == 1
    changed = {**arguments, "source": PublicTextSource("Changed public input.", public_assertion=True)}
    with pytest.raises(ValueError, match=r"different intent|native-binding"):
        await peer.admit_public_run(marker, **changed)
    with pytest.raises(PeerAuthorityError, match="policy"):
        await peer.admit_public_run(marker, **{**arguments, "endpoint": "https://other.example/a2a"})
    assert (await ledger.get(retained.run_id)).status is RunStatus.QUEUED
    assert len(declarations) == 1
    await substrate.bus.aclose()
