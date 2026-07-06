"""The ghoul plane: perform_run drives the graph offline; reconcile heals orphans.

Offline floor: no real model request is permitted (`ALLOW_MODEL_REQUESTS = False`);
the graph runs on a `TestModel` handed through the fake dispatcher's grant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pydantic_ai.models
import pytest
from pydantic_ai.models.test import TestModel

from lychd.agents.router import Intent
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.events import InProcessEventBus, RunEventKind
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.ghouls.runs import perform_run, reconcile_runs
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


@dataclass
class _RaisingDispatcher:
    """A GrantPort that always fails to resolve a grant (forces a run failure)."""

    def resolve_capability_grant(self, intent_type: str) -> Any:
        msg = f"no capability for {intent_type}"
        raise RuntimeError(msg)


def _substrate(*, dispatcher: Any) -> tuple[RunSubstrate, InMemoryRunLedger, BridgeSessionStore]:
    ledger = InMemoryRunLedger()
    bus = InProcessEventBus(ledger=ledger)
    sessions = BridgeSessionStore()
    substrate = RunSubstrate(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        orchestrator=FakeOrchestrator(),
        dispatcher=dispatcher,
        context=ContextOrchestrator(registry=FakeRegistry()),
        fragments=build_fragment_registry(),
        sessions=sessions,
        forge=default_forge(),
    )
    return substrate, ledger, sessions


async def _seed_run(ledger: InMemoryRunLedger, sessions: BridgeSessionStore, run_id: str) -> Intent:
    session = sessions.create_session(title="t")
    intent = Intent(session_id=session.id, run_id=run_id, prompt="hello", source="bridge")
    await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=70)
    return intent


@pytest.mark.asyncio
async def test_perform_run_happy_path_trail_and_terminal_done() -> None:
    """A claimed run goes QUEUED→RUNNING→DONE and emits exactly one terminal DONE."""
    model = TestModel(custom_output_args={"answer": "risen", "fragments": []}, call_tools=[])
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=model))
    await _seed_run(ledger, sessions, "run_1")

    result = await perform_run({"run_substrate": substrate}, run_id="run_1")
    assert result["status"] == "done"

    run = await ledger.get("run_1")
    assert run is not None
    assert run.status is RunStatus.DONE
    assert run.started_at is not None
    assert run.finished_at is not None

    channel = substrate.bus.open("run_1")
    dones = [e for e in list(channel._replay) if e.kind is RunEventKind.DONE]
    assert len(dones) == 1
    assert dones[0].data == "done"
    # the settled agent turn landed on the session
    settled = [t for t in sessions.get_session(run.session_id).turns if t.state == "settled"]  # type: ignore[union-attr]
    assert settled
    assert settled[0].content == "risen"


@pytest.mark.asyncio
async def test_perform_run_skips_non_queued() -> None:
    """A stale / duplicate claim (run not QUEUED) is skipped without side effects."""
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "run_2")
    await ledger.set_status("run_2", RunStatus.RUNNING)  # already claimed

    result = await perform_run({"run_substrate": substrate}, run_id="run_2")
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_perform_run_failure_marks_failed_and_emits_done() -> None:
    """A node failure marks FAILED, writes a fault turn, and still emits a terminal DONE."""
    substrate, ledger, sessions = _substrate(dispatcher=_RaisingDispatcher())
    await _seed_run(ledger, sessions, "run_3")

    with pytest.raises(RuntimeError):
        await perform_run({"run_substrate": substrate}, run_id="run_3")

    run = await ledger.get("run_3")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert run.error is not None

    channel = substrate.bus.open("run_3")
    dones = [e for e in list(channel._replay) if e.kind is RunEventKind.DONE]
    assert len(dones) == 1
    assert dones[0].data == "failed"


@pytest.mark.asyncio
async def test_reconcile_runs_fails_orphaned_running() -> None:
    """reconcile_runs marks orphaned RUNNING rows FAILED and emits their terminal DONE."""
    substrate, ledger, sessions = _substrate(dispatcher=FakeDispatcher(model=TestModel()))
    await _seed_run(ledger, sessions, "orphan")
    await ledger.set_status("orphan", RunStatus.RUNNING)  # crash left it here

    result = await reconcile_runs({"run_substrate": substrate})
    assert result["count"] == 1

    run = await ledger.get("orphan")
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert run.error == "ghoul lost"
    channel = substrate.bus.open("orphan")
    assert channel.closed is True
