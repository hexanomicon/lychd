"""Semantic JSON SSE shape and the ledger-first never-hang contract."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from lychd.agents.router import Intent
from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.runs import RunStatus

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient


def _seed_live_run(services: SimpleNamespace, run_id: str) -> None:
    async def _seed() -> None:
        await services.ledger.create(
            Intent(session_id="s", run_id=run_id, prompt="p", source="bridge"),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )
        await services.ledger.set_status(run_id, RunStatus.RUNNING)

    asyncio.run(_seed())


def _seed_terminal_run(
    services: SimpleNamespace,
    run_id: str,
    status: RunStatus,
) -> None:
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


def _sse_events(body: str) -> list[dict[str, Any]]:
    """Parse the finite JSON events emitted by the test streams."""
    events: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in body.splitlines():
        if not line:
            if current:
                events.append(current)
                current = {}
            continue
        if line.startswith("event: "):
            current["event"] = line.removeprefix("event: ")
        elif line.startswith("id: "):
            current["id"] = int(line.removeprefix("id: "))
        elif line.startswith("data: "):
            current["data"] = json.loads(line.removeprefix("data: "))
    if current:
        events.append(current)
    return events


def test_stream_projects_every_event_kind(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    sessions = fake_services.bridge_sessions
    consents = fake_services.consents
    bus = fake_services.bus
    run_id = "run_sse"
    _seed_live_run(fake_services, run_id)

    async def _seed() -> str:
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
        return decision.consent_id

    consent_id = asyncio.run(_seed())

    emitter = bus.emitter(run_id)
    emitter.emit(RunEventKind.STATUS, "weaving")
    emitter.emit(RunEventKind.TOKEN, "<b>ashes</b>")
    emitter.emit(
        RunEventKind.FRAGMENT,
        json.dumps(
            {
                "fragment": "genui.plan_checklist",
                "params": {"title": "Rite", "steps": ["a"]},
            },
        ),
    )
    emitter.emit(
        RunEventKind.CONSENT,
        json.dumps(
            {
                "consent_id": consent_id,
                "tool_name": "request_coven_swap",
            },
        ),
    )
    emitter.emit(RunEventKind.DONE, "done")

    response = altar_client.get(f"/api/v1/bridge/runs/{run_id}/events")

    assert response.status_code == 200
    events = _sse_events(response.text)
    assert [event["event"] for event in events] == [
        "status",
        "token",
        "fragment",
        "consent",
        "done",
    ]
    assert [event["id"] for event in events] == list(range(5))
    assert events[1]["data"]["payload"]["text"] == "<b>ashes</b>"
    assert events[2]["data"]["payload"]["kind"] == "genui.plan_checklist"
    assert events[3]["data"]["payload"]["consent"]["id"] == consent_id
    assert events[4]["data"]["payload"]["turn"]["state"] == "settled"
    assert all(event["data"]["schema_version"] == 1 for event in events)


def test_stream_closes_after_done(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    run_id = "run_done"
    _seed_live_run(fake_services, run_id)
    channel = fake_services.bus.open(run_id)
    channel.emit(RunEventKind.STATUS, "settling")
    channel.emit(RunEventKind.DONE, "done")

    response = altar_client.get(f"/api/v1/bridge/runs/{run_id}/events")

    assert response.status_code == 200
    assert [event["event"] for event in _sse_events(response.text)] == [
        "status",
        "done",
    ]


def test_stream_unknown_run_is_404(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get(
        "/api/v1/bridge/runs/does-not-exist/events",
    )
    assert response.status_code == 404


def test_stream_terminal_run_synthesizes_status_and_done(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    run_id = "run_terminal"
    _seed_terminal_run(fake_services, run_id, RunStatus.DONE)

    response = altar_client.get(f"/api/v1/bridge/runs/{run_id}/events")

    assert response.status_code == 200
    events = _sse_events(response.text)
    assert [event["event"] for event in events] == ["status", "done"]
    assert events[0]["data"]["payload"]["text"] == "done"


def _agent_turn(*, run_id: str) -> object:
    from lychd.domain.web.schemas import BridgeTurn

    return BridgeTurn(
        role="agent",
        content="It is done.",
        run_id=run_id,
        state="settled",
    )
