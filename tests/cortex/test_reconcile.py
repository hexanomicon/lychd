"""reconcile invariants (B10): AWAITING_CONSENT survives reconcile_runs; consents re-fire."""

# Structural fakes stand in for the GrantPort/registry ports.
# pyright: reportArgumentType=false
# White-box recovery tests exercise page and terminal helpers directly.
# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pytest

from lychd.agents.router import Intent
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.domain.codex.ledger import InMemoryConsentLedger
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.events import InProcessEventBus, RunEvent, RunEventKind
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.delegation import (
    DelegatedAgentCoordinator,
    DelegatedAgentJobRef,
    DelegatedAgentRequest,
    DelegatedAgentResult,
    InMemoryDelegatedAgentJobStore,
)
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.ghouls.runs import _emit_terminal, _reconcile_consent_page, reconcile_consents, reconcile_runs
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry


def _substrate() -> tuple[RunSubstrate, InMemoryRunLedger, InMemoryConsentLedger]:
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    consents = InMemoryConsentLedger()
    substrate = RunSubstrate(
        ledger=ledger,
        bus=InProcessEventBus(ledger=ledger),
        workflows=builtin_workflow_registry(),
        orchestrator=FakeOrchestrator(),
        dispatcher=FakeDispatcher(model=None),
        context=ContextOrchestrator(registry=FakeRegistry()),
        fragments=build_fragment_registry(),
        turns=BridgeSessionStore(),
        consents=consents,
        forge=default_forge(),
    )
    return substrate, ledger, consents


class _FailFirstTerminalLedger(InMemoryRunLedger):
    def __init__(self) -> None:
        super().__init__(honor_intent_run_id=True)
        self._terminal_failed = False

    async def append_event(self, event: RunEvent) -> None:
        if event.kind is RunEventKind.DONE and not self._terminal_failed:
            self._terminal_failed = True
            msg = "first terminal append failed"
            raise RuntimeError(msg)
        await super().append_event(event)


@pytest.mark.asyncio
async def test_terminal_evidence_repair_reopens_after_failed_persistence() -> None:
    ledger = _FailFirstTerminalLedger()
    substrate, _unused, _consents = _substrate()
    substrate.ledger = ledger
    substrate.bus = InProcessEventBus(ledger=ledger)
    intent = Intent(session_id="s", run_id="run_terminal_retry", prompt="p", source="bridge")
    await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status(intent.run_id, RunStatus.RUNNING)
    await ledger.set_status(intent.run_id, RunStatus.FAILED)

    with pytest.raises(RuntimeError, match="first terminal append failed"):
        await _emit_terminal(substrate, intent.run_id)

    assert substrate.bus.snapshot(intent.run_id) is None

    await _emit_terminal(substrate, intent.run_id)

    events = await ledger.list_events(intent.run_id)
    assert [(event.seq, event.kind, event.data) for event in events] == [(0, RunEventKind.DONE, RunStatus.FAILED.value)]


def _consent_checkpoint(run_id: str, consent_id: str) -> list[dict[str, Any]]:
    """Return the minimal raw shape of Pydantic Graph's next resumable node."""
    return [
        {
            "id": "AwaitConsent:test",
            "kind": "node",
            "node": {"node_id": "AwaitConsent"},
            "state": {
                "run_id": run_id,
                "pending_consent_id": consent_id,
            },
            "status": "created",
        }
    ]


def _delegate_checkpoint(run_id: str, job_id: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "DispatchDelegate:test",
            "kind": "node",
            "node": {"node_id": "DispatchDelegate"},
            "state": {"run_id": run_id, "job_id": job_id},
            "status": "created",
        }
    ]


@dataclass
class _DelegateRuntime:
    name: str = "fake"
    cancellations: list[str] = field(default_factory=list)

    async def start(self, request: DelegatedAgentRequest, job: DelegatedAgentJobRef) -> None:
        _ = (request, job)

    async def poll(self, job: DelegatedAgentJobRef) -> DelegatedAgentResult | None:
        _ = job
        return None

    async def cancel(self, job: DelegatedAgentJobRef) -> None:
        self.cancellations.append(job.job_id)


async def _delegate_job(coordinator: DelegatedAgentCoordinator, *, run_id: str) -> DelegatedAgentJobRef:
    return await coordinator.submit(
        DelegatedAgentRequest(
            request_id=f"request-{run_id}",
            run_id=run_id,
            step_id="dispatch_delegate",
            runtime="fake",
            prompt="inspect",
        )
    )


class _OrphanQueue:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.aborted: list[str] = []

    async def job(self, job_key: str, /) -> object:
        _ = job_key
        return object()

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> None:
        _ = (job_or_func, kwargs)

    async def abort(self, job: object, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)

    async def abort_orphan(self, job: object, error: str, /) -> None:
        _ = (job, error)
        self.aborted.append(self.run_id)


async def _seed_awaiting_consent(ledger: InMemoryRunLedger, run_id: str, consent_id: str) -> None:
    intent = Intent(session_id="s", run_id=run_id, prompt="p", source="bridge")
    await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status(run_id, RunStatus.RUNNING)
    await ledger.set_status(run_id, RunStatus.AWAITING_CONSENT)
    await ledger.set_consent(run_id, consent_id)


@pytest.mark.asyncio
async def test_reconcile_runs_never_touches_awaiting_consent() -> None:
    """A parked (AWAITING_CONSENT) run must survive the orphan sweep untouched (B10)."""
    substrate, ledger, _consents = _substrate()
    await _seed_awaiting_consent(ledger, "run_p", "c_p")

    await reconcile_runs({"run_substrate": substrate})

    run = await ledger.get("run_p")
    assert run is not None
    assert run.status is RunStatus.AWAITING_CONSENT  # NOT swept to FAILED


@pytest.mark.asyncio
async def test_reconcile_recovers_checkpointed_pending_consent_park() -> None:
    """Restart closes the checkpoint→Run-status crash window without rerunning work."""
    substrate, ledger, consents = _substrate()
    intent = Intent(session_id="s", run_id="run_recover", prompt="p", source="bridge")
    await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status("run_recover", RunStatus.RUNNING)
    decision = await consents.park(
        run_id="run_recover",
        tool_name="request_coven_swap",
        tool_call_id="recover-call",
        call_ids=("recover-call",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    await substrate.stasis_store.replace(
        "run_recover",
        _consent_checkpoint("run_recover", decision.consent_id),
    )

    queue = _OrphanQueue("run_recover")
    substrate.queues = {"runs": queue}

    result = await reconcile_runs({"run_substrate": substrate})

    run = await ledger.get("run_recover")
    assert run is not None
    assert run.status is RunStatus.AWAITING_CONSENT
    assert run.consent_id == decision.consent_id
    assert await substrate.stasis_store.exists("run_recover")
    assert queue.aborted == ["run_recover"]
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0}


@pytest.mark.asyncio
async def test_reconcile_recovers_checkpointed_decided_consent_then_refires_it() -> None:
    substrate, ledger, consents = _substrate()
    intent = Intent(session_id="s", run_id="run_decided_window", prompt="p", source="bridge")
    await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status("run_decided_window", RunStatus.RUNNING)
    decision = await consents.park(
        run_id="run_decided_window",
        tool_name="request_coven_swap",
        tool_call_id="decided-call",
        call_ids=("decided-call",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    await substrate.stasis_store.replace(
        "run_decided_window",
        _consent_checkpoint("run_decided_window", decision.consent_id),
    )
    await consents.decide(decision.consent_id, approved=True, decided_by="magus")
    substrate.queues = {"runs": _OrphanQueue("run_decided_window")}

    await reconcile_runs({"run_substrate": substrate})

    parked = await ledger.get("run_decided_window")
    assert parked is not None
    assert parked.status is RunStatus.AWAITING_CONSENT
    engine = _RecordingEngine()
    result = await reconcile_consents({"run_substrate": substrate}, engine=engine)
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0}
    assert engine.approvals == [(decision.consent_id, True)]


@pytest.mark.asyncio
async def test_reconcile_recovers_exact_checkpointed_delegate_park() -> None:
    substrate, ledger, _consents = _substrate()
    runtime = _DelegateRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={"fake": runtime},
        store=InMemoryDelegatedAgentJobStore(),
    )
    substrate.delegates = coordinator
    intent = Intent(session_id="s", run_id="run_delegate_recover", prompt="p", source="bridge")
    await ledger.create(intent, workflow_name="delegated_rite", queue_name="runs", priority=50)
    await ledger.set_status("run_delegate_recover", RunStatus.RUNNING)
    job = await _delegate_job(coordinator, run_id="run_delegate_recover")
    await substrate.stasis_store.replace(
        "run_delegate_recover",
        _delegate_checkpoint("run_delegate_recover", job.job_id),
    )
    substrate.queues = {"runs": _OrphanQueue("run_delegate_recover")}

    result = await reconcile_runs({"run_substrate": substrate})

    run = await ledger.get("run_delegate_recover")
    assert run is not None
    assert run.status is RunStatus.AWAITING_DELEGATE
    assert run.delegated_job_id == job.job_id
    assert runtime.cancellations == []
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0}


@pytest.mark.asyncio
async def test_reconcile_contains_uncheckpointed_delegate_before_parent_failure() -> None:
    substrate, ledger, _consents = _substrate()
    runtime = _DelegateRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={"fake": runtime},
        store=InMemoryDelegatedAgentJobStore(),
    )
    substrate.delegates = coordinator
    intent = Intent(session_id="s", run_id="run_delegate_lost", prompt="p", source="bridge")
    await ledger.create(intent, workflow_name="delegated_rite", queue_name="runs", priority=50)
    await ledger.set_status("run_delegate_lost", RunStatus.RUNNING)
    job = await _delegate_job(coordinator, run_id="run_delegate_lost")
    substrate.queues = {"runs": _OrphanQueue("run_delegate_lost")}

    result = await reconcile_runs({"run_substrate": substrate})

    run = await ledger.get("run_delegate_lost")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert runtime.cancellations == [job.job_id]
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0}


@pytest.mark.asyncio
async def test_reconcile_rejects_pending_consent_bound_to_older_checkpoint() -> None:
    """A later consent row cannot park a Run on an earlier round's checkpoint."""
    substrate, ledger, consents = _substrate()
    intent = Intent(session_id="s", run_id="run_stale", prompt="p", source="bridge")
    await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status("run_stale", RunStatus.RUNNING)
    older = await consents.park(
        run_id="run_stale",
        tool_name="request_coven_swap",
        tool_call_id="old-call",
        call_ids=("old-call",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    await asyncio.sleep(0.001)
    current = await consents.park(
        run_id="run_stale",
        tool_name="request_coven_swap",
        tool_call_id="new-call",
        call_ids=("new-call",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    await substrate.stasis_store.replace(
        "run_stale",
        _consent_checkpoint("run_stale", older.consent_id),
    )
    queue = _OrphanQueue("run_stale")
    substrate.queues = {"runs": queue}

    result = await reconcile_runs({"run_substrate": substrate})

    run = await ledger.get("run_stale")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert run.consent_id is None
    assert run.error == "ghoul lost"
    assert current.consent_id != older.consent_id
    current_view = await consents.get(current.consent_id)
    assert current_view is not None
    assert current_view.status == "cancelled"
    assert not await substrate.stasis_store.exists("run_stale")
    assert queue.aborted == ["run_stale"]
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0}


class _RecordingEngine:
    def __init__(self) -> None:
        self.approvals: list[tuple[str, bool]] = []

    async def approve(self, consent_id: str, *, approved: bool) -> None:
        self.approvals.append((consent_id, approved))


@pytest.mark.asyncio
async def test_consent_page_revisits_a_clean_pending_decision() -> None:
    substrate, ledger, consents = _substrate()
    pending = await consents.park(
        run_id="run-pending-revisit",
        tool_name="request_coven_swap",
        tool_call_id="call-pending",
        call_ids=("call-pending",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    await _seed_awaiting_consent(ledger, "run-pending-revisit", pending.consent_id)

    result, _cursor = await _reconcile_consent_page(substrate, _RecordingEngine(), after=None)

    assert result == {"status": "reconciled", "count": 0, "probe_errors": 0, "_revisit": True}


@pytest.mark.asyncio
async def test_reconcile_consents_refires_decided_but_unenqueued(monkeypatch: pytest.MonkeyPatch) -> None:
    """A decided-but-unenqueued park (crash before approve) is re-fired; pending is left alone."""
    substrate, ledger, consents = _substrate()

    # A decided park (verdict recorded, but no re-enqueue happened — process died).
    decision = await consents.park(
        run_id="run_decided",
        tool_name="request_coven_swap",
        tool_call_id="c1",
        call_ids=("c1",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    await _seed_awaiting_consent(ledger, "run_decided", decision.consent_id)
    await consents.decide(decision.consent_id, approved=True, decided_by="magus")

    # A still-pending park — must be LEFT ALONE.
    pending = await consents.park(
        run_id="run_pending",
        tool_name="request_coven_swap",
        tool_call_id="c2",
        call_ids=("c2",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    await _seed_awaiting_consent(ledger, "run_pending", pending.consent_id)

    page_calls: list[tuple[tuple[datetime, str] | None, int | None]] = []
    list_by_status = ledger.list_by_status

    async def record_page(
        status: RunStatus,
        *,
        after: tuple[datetime, str] | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        page_calls.append((after, limit))
        return await list_by_status(status, after=after, limit=limit)

    monkeypatch.setattr("lychd.ghouls.runs.STARTUP_RECONCILIATION_BATCH_SIZE", 1)
    monkeypatch.setattr(ledger, "list_by_status", record_page)

    engine = _RecordingEngine()
    result: dict[str, Any] = await reconcile_consents({"run_substrate": substrate}, engine=engine)

    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0}
    assert engine.approvals == [(decision.consent_id, True)]  # only the decided one re-fired
    assert page_calls[0] == (None, 1)
    assert len(page_calls) == 3
    assert page_calls[1][0] is not None


@pytest.mark.asyncio
async def test_reconcile_consents_uses_the_run_exact_owner_not_a_newer_row() -> None:
    substrate, ledger, consents = _substrate()
    owner = await consents.park(
        run_id="run-exact-owner",
        tool_name="request_coven_swap",
        tool_call_id="owner-call",
        call_ids=("owner-call",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )
    await _seed_awaiting_consent(ledger, "run-exact-owner", owner.consent_id)
    await consents.decide(owner.consent_id, approved=True, decided_by="magus")
    newer = await consents.park(
        run_id="run-exact-owner",
        tool_name="request_coven_swap",
        tool_call_id="unrelated-newer-call",
        call_ids=("unrelated-newer-call",),
        args={},
        sigil=Sigil(name="magus", scopes=frozenset({"*"})),
    )

    engine = _RecordingEngine()
    result, _cursor = await _reconcile_consent_page(substrate, engine, after=None)

    assert newer.consent_id != owner.consent_id
    assert result == {"status": "reconciled", "count": 1, "probe_errors": 0, "_revisit": False}
    assert engine.approvals == [(owner.consent_id, True)]


@pytest.mark.asyncio
async def test_reconcile_consents_degrades_on_missing_authority_row() -> None:
    """A parked status without its consent authority cannot pass startup as clean."""
    substrate, ledger, _consents = _substrate()
    await _seed_awaiting_consent(ledger, "run_orphan", "missing-consent")

    engine = _RecordingEngine()
    result = await reconcile_consents({"run_substrate": substrate}, engine=engine)

    assert result == {"status": "degraded", "count": 0, "probe_errors": 1}
    assert engine.approvals == []
