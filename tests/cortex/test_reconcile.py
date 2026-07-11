"""reconcile invariants (B10): AWAITING_CONSENT survives reconcile_runs; consents re-fire."""

# Structural fakes stand in for the GrantPort/registry ports.
# pyright: reportArgumentType=false
from __future__ import annotations

from typing import Any

import pytest

from lychd.agents.router import Intent
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.domain.codex.ledger import InMemoryConsentLedger
from lychd.domain.codex.sigil import Sigil
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.ghouls.runs import reconcile_consents, reconcile_runs
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


class _RecordingEngine:
    def __init__(self) -> None:
        self.approvals: list[tuple[str, bool]] = []

    async def approve(self, consent_id: str, *, approved: bool) -> None:
        self.approvals.append((consent_id, approved))


@pytest.mark.asyncio
async def test_reconcile_consents_refires_decided_but_unenqueued() -> None:
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

    engine = _RecordingEngine()
    result: dict[str, Any] = await reconcile_consents({"run_substrate": substrate}, engine=engine)

    assert result["count"] == 1
    assert engine.approvals == [(decision.consent_id, True)]  # only the decided one re-fired
