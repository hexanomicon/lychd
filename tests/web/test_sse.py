"""SSE stream shape: server-projected payloads, event names, ids, terminal close.

The channel is fully pre-seeded (terminal `done` emitted before subscribing), so the
generator drains its replay buffer and completes — the read can never hang. Channels
now live on the `RunEventBus` (shed from `BridgeSessionStore` in Wave 2).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from lychd.domain.cortex.events import RunEventKind

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient


def test_stream_projects_every_event_kind(altar_client: TestClient[Litestar], fake_services: SimpleNamespace) -> None:
    """A scripted status/token/fragment/consent/done sequence frames correctly."""
    sessions = fake_services.bridge_sessions
    bus = fake_services.bus
    run_id = "run_sse"
    session = sessions.create_session()
    consent_id = sessions.park_consent(
        run_id=run_id, session_id=session.id, tool_name="request_coven_swap", args={}, requests=None
    )
    sessions.add_turn(session.id, _agent_turn(run_id=run_id))

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
    """A channel closed by `done` yields a finite stream (no hang)."""
    bus = fake_services.bus
    channel = bus.open("run_done")
    channel.emit(RunEventKind.STATUS, "settling")
    channel.emit(RunEventKind.DONE, "done")
    assert channel.closed is True

    response = altar_client.get("/bridge/runs/run_done/stream")
    assert response.status_code == 200
    assert "event: done" in response.text


def _agent_turn(*, run_id: str) -> object:
    from lychd.domain.web.schemas import BridgeTurn

    return BridgeTurn(role="agent", content="It is done.", run_id=run_id, state="settled")
