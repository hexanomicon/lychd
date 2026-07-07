"""SSE stream shape + the ledger-first, never-hang contract (F5/H4).

The SSE handler consults the run ledger BEFORE subscribing (`bridge.stream`):
- unknown run → 404 (never an auto-minted channel that hangs on keepalives);
- already-terminal run → a synthetic STATUS + DONE, then end;
- live run → subscribe to its channel.

Every test seeds the run in the ledger so the handler takes the intended branch, and
pre-closes the channel (terminal `done`) so reads can never hang. Tests stay sync (the
`TestClient` owns its own loop); ledger seeding runs the loop-confined coroutines via
`asyncio.run` (the `InMemoryRunLedger` is a plain dict with no loop affinity).
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from lychd.agents.router import Intent
from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.runs import RunStatus

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient


def _seed_live_run(services: SimpleNamespace, run_id: str) -> None:
    """Persist a RUNNING run row so the stream takes the live-subscribe branch."""

    async def _seed() -> None:
        await services.ledger.create(
            Intent(session_id="s", run_id=run_id, prompt="p", source="bridge"),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )
        await services.ledger.set_status(run_id, RunStatus.RUNNING)

    asyncio.run(_seed())


def _seed_terminal_run(services: SimpleNamespace, run_id: str, status: RunStatus) -> None:
    """Persist a run row already in a terminal status (synthetic-replay branch)."""

    async def _seed() -> None:
        await services.ledger.create(
            Intent(session_id="s", run_id=run_id, prompt="p", source="bridge"),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )
        await services.ledger.set_status(run_id, RunStatus.RUNNING)
        await services.ledger.set_status(run_id, status)

    asyncio.run(_seed())


def test_stream_projects_every_event_kind(altar_client: TestClient[Litestar], fake_services: SimpleNamespace) -> None:
    """A scripted status/token/fragment/consent/done sequence frames correctly (live run)."""
    sessions = fake_services.bridge_sessions
    consents = fake_services.consents
    bus = fake_services.bus
    run_id = "run_sse"
    _seed_live_run(fake_services, run_id)

    async def _seed() -> tuple[str, str]:
        from lychd.domain.codex.sigil import Sigil

        session = await sessions.create_session()
        decision = await consents.park(
            run_id=run_id,
            tool_name="request_coven_swap",
            tool_call_id="c1",
            call_ids=("c1",),
            args={},
            sigil=Sigil(name="magus", scopes=frozenset({"*"})),
        )
        await sessions.add_turn(session.id, _agent_turn(run_id=run_id))
        return session.id, decision.consent_id

    _, consent_id = asyncio.run(_seed())

    emitter = bus.emitter(run_id)
    emitter.emit(RunEventKind.STATUS, "weaving")
    emitter.emit(RunEventKind.TOKEN, "<b>ashes</b>")
    emitter.emit(
        RunEventKind.FRAGMENT,
        json.dumps({"fragment": "genui.plan_checklist", "params": {"title": "Rite", "steps": ["a"]}}),
    )
    emitter.emit(RunEventKind.CONSENT, json.dumps({"consent_id": consent_id, "tool_name": "request_coven_swap"}))
    emitter.emit(RunEventKind.DONE, "done")

    response = altar_client.get(f"/bridge/runs/{run_id}/stream")
    assert response.status_code == 200
    body = response.text

    # event names match the emitted kinds; ids carry the seq
    for kind in ("status", "token", "fragment", "consent", "done"):
        assert f"event: {kind}" in body
    assert "id: 0" in body
    assert "id: 4" in body

    # token text is escaped by the Projector (emitter emits raw)
    assert "&lt;b&gt;ashes&lt;/b&gt;" in body
    # fragment is rendered server-side (genUI), not passed through as JSON
    assert "genui.plan_checklist" in body
    assert '"fragment"' not in body
    # consent renders the card + the OOB sigil
    assert "consent-card" in body or 'data-fragment="bridge.consent"' in body
    assert "consent-sigil" in body
    # done settles the streaming slot with the agent turn (OOB replace)
    assert 'data-state="done"' in body


def test_stream_closes_after_done(altar_client: TestClient[Litestar], fake_services: SimpleNamespace) -> None:
    """A live run whose channel is closed by `done` yields a finite stream (no hang)."""
    bus = fake_services.bus
    run_id = "run_done"
    _seed_live_run(fake_services, run_id)
    channel = bus.open(run_id)
    channel.emit(RunEventKind.STATUS, "settling")
    channel.emit(RunEventKind.DONE, "done")
    assert channel.closed is True

    response = altar_client.get(f"/bridge/runs/{run_id}/stream")
    assert response.status_code == 200
    assert "event: done" in response.text


def test_stream_unknown_run_is_404(altar_client: TestClient[Litestar]) -> None:
    """Never-hang matrix: an unknown run id → 404, never a minted-empty channel."""
    response = altar_client.get("/bridge/runs/does-not-exist/stream")
    assert response.status_code == 404


def test_stream_terminal_run_synthesizes_status_and_done(
    altar_client: TestClient[Litestar], fake_services: SimpleNamespace
) -> None:
    """Never-hang matrix: a reconnect onto an already-DONE run replays STATUS+DONE, then ends.

    No channel exists (it was closed and dropped after the run settled); the handler
    must synthesize from the ledger instead of hanging on an empty/absent channel.
    """
    run_id = "run_terminal"
    _seed_terminal_run(fake_services, run_id, RunStatus.DONE)
    # No channel is opened for this run — proving the synthetic path needs no channel.

    response = altar_client.get(f"/bridge/runs/{run_id}/stream")
    assert response.status_code == 200
    body = response.text
    assert "event: status" in body
    assert "event: done" in body


def _agent_turn(*, run_id: str) -> object:
    from lychd.domain.web.schemas import BridgeTurn

    return BridgeTurn(role="agent", content="It is done.", run_id=run_id, state="settled")
