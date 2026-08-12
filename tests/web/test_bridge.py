"""Bridge JSON contract: session creation, message admission, and inspector."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from lychd.agents.router import Intent
from lychd.agents.workflows import DELEGATED_RITE, BuiltinWorkflowRegistry
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT
from lychd.domain.cortex.events import RunEvent, RunEventKind
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.delegation.models import DelegatedAgentProfile, DelegatedAgentRequest
from lychd.domain.web.schemas import BridgeTurn

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient

_REQUEST_ID = "31d80d31-92ef-4e9c-a1e7-e8b755eed888"


def _session(fake_services: SimpleNamespace) -> Any:
    return asyncio.run(fake_services.bridge_sessions.create_session())


def test_create_session_returns_typed_identity(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.post("/api/v1/bridge/sessions")

    assert response.status_code == 201
    session = response.json()["session"]
    assert session["id"]
    assert session["turns"] == []


def test_snapshot_lists_created_session(altar_client: TestClient[Litestar]) -> None:
    created = altar_client.post("/api/v1/bridge/sessions").json()["session"]

    snapshot = altar_client.get("/api/v1/bridge")

    assert snapshot.status_code == 200
    assert snapshot.json()["session"]["id"] == created["id"]
    assert snapshot.json()["sessions"][0]["id"] == created["id"]


def test_snapshot_reconstructs_selected_ledger_runs_without_requiring_a_live_channel(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    selected = _session(fake_services)
    other = _session(fake_services)

    async def _seed() -> None:
        for session_id, run_id in (
            (selected.id, "run_selected"),
            (selected.id, "run_without_process_channel"),
            (other.id, "run_other"),
        ):
            await fake_services.ledger.create(
                Intent(
                    session_id=session_id,
                    run_id=run_id,
                    prompt="raise the dead",
                    source="bridge",
                ),
                workflow_name="bridge_chat",
                queue_name="runs",
                priority=70,
            )
            await fake_services.ledger.set_status(run_id, RunStatus.RUNNING)

    asyncio.run(_seed())
    selected_emitter = fake_services.bus.emitter("run_selected")
    selected_emitter.emit(RunEventKind.STATUS, "weaving")
    selected_emitter.emit(RunEventKind.TOKEN, "still speaking")
    selected_emitter.emit(
        RunEventKind.FRAGMENT,
        json.dumps(
            {
                "fragment": "genui.plan_checklist",
                "params": {"title": "Rite", "steps": ["listen"]},
            },
        ),
    )
    fake_services.bus.emitter("run_other").emit(RunEventKind.TOKEN, "not selected")

    response = altar_client.get(f"/api/v1/bridge/sessions/{selected.id}")

    assert response.status_code == 200
    assert response.json()["active_runs"] == [
        {
            "schema_version": 1,
            "session_id": selected.id,
            "run_id": "run_selected",
            "cursor": 2,
            "content": "still speaking",
            "run_status": "running",
            "activity": "weaving",
            "pattern_id": "bridge_chat",
            "pattern_revision": "legacy-unversioned",
            "loom_path": None,
            "orb_path": "/orb/run_selected",
            "evidence_capture": "process_local",
            "fragments": [
                {
                    "kind": "genui.plan_checklist",
                    "schema_version": 1,
                    "props": {"title": "Rite", "steps": ["listen"]},
                    "actions": [],
                },
            ],
            "occurrence_id": None,
            "dispatch_occurrence_id": None,
            "grant_id": None,
            "capability_key": None,
            "transition_occurrence_id": None,
            "transition_request_id": None,
            "transition_phase": None,
            "delegated_job_id": None,
            "delegated_runtime": None,
            "delegated_profile": None,
            "delegated_status": None,
            "terminal": False,
        },
        {
            "schema_version": 1,
            "session_id": selected.id,
            "run_id": "run_without_process_channel",
            "cursor": -1,
            "content": "",
            "run_status": "running",
            "activity": "running",
            "pattern_id": "bridge_chat",
            "pattern_revision": "legacy-unversioned",
            "loom_path": None,
            "orb_path": "/orb/run_without_process_channel",
            "evidence_capture": "process_local",
            "fragments": [],
            "occurrence_id": None,
            "dispatch_occurrence_id": None,
            "grant_id": None,
            "capability_key": None,
            "transition_occurrence_id": None,
            "transition_request_id": None,
            "transition_phase": None,
            "delegated_job_id": None,
            "delegated_runtime": None,
            "delegated_profile": None,
            "delegated_status": None,
            "terminal": False,
        },
    ]


def test_cancel_run_is_idempotent_and_remains_visible_without_a_settled_turn(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)

    async def _seed() -> None:
        await fake_services.ledger.create(
            Intent(
                session_id=session.id,
                run_id="run_cancelled",
                prompt="stop",
                source="bridge",
            ),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )

    asyncio.run(_seed())

    first = altar_client.post("/api/v1/bridge/runs/run_cancelled/cancel")
    second = altar_client.post("/api/v1/bridge/runs/run_cancelled/cancel")
    restored = altar_client.get(f"/api/v1/bridge/sessions/{session.id}")

    assert first.status_code == 200
    assert first.json()["run_status"] == "cancelled"
    assert first.json()["terminal"] is True
    assert second.status_code == 200
    assert second.json()["run_status"] == "cancelled"
    assert [run["run_id"] for run in restored.json()["active_runs"]] == ["run_cancelled"]
    assert restored.json()["active_runs"][0]["run_status"] == "cancelled"


def test_terminal_run_with_only_a_user_turn_remains_visible(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)

    async def _seed() -> None:
        await fake_services.ledger.create(
            Intent(
                session_id=session.id,
                run_id="run_failed_before_reply",
                prompt="fail visibly",
                source="bridge",
            ),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )
        await fake_services.bridge_sessions.add_turn(
            session.id,
            BridgeTurn(role="user", content="fail visibly", run_id="run_failed_before_reply"),
        )
        await fake_services.ledger.set_status("run_failed_before_reply", RunStatus.RUNNING)
        await fake_services.ledger.set_status("run_failed_before_reply", RunStatus.FAILED)

    asyncio.run(_seed())

    restored = altar_client.get(f"/api/v1/bridge/sessions/{session.id}")

    assert restored.status_code == 200
    assert [run["run_id"] for run in restored.json()["active_runs"]] == ["run_failed_before_reply"]
    assert restored.json()["active_runs"][0]["terminal"] is True


def test_durable_terminal_status_overrides_a_lagging_live_channel(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)

    async def _seed() -> None:
        await fake_services.ledger.create(
            Intent(session_id=session.id, run_id="run_terminal_live", prompt="fail", source="bridge"),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )
        await fake_services.ledger.set_status("run_terminal_live", RunStatus.RUNNING)

    asyncio.run(_seed())
    fake_services.bus.emitter("run_terminal_live").emit(RunEventKind.STATUS, "weaving")
    asyncio.run(fake_services.ledger.set_status("run_terminal_live", RunStatus.FAILED))

    response = altar_client.get("/api/v1/bridge/runs/run_terminal_live")

    assert response.status_code == 200
    assert response.json()["run_status"] == "failed"
    assert response.json()["activity"] == "failed"
    assert response.json()["terminal"] is True


def test_terminal_refresh_reconstructs_settled_genui_descriptors(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    descriptor: dict[str, Any] = {
        "kind": "genui.plan_checklist",
        "schema_version": 1,
        "props": {"title": "Retained plan", "steps": ["inspect"]},
        "actions": [],
    }

    async def _seed() -> None:
        await fake_services.ledger.create(
            Intent(session_id=session.id, run_id="run_genui", prompt="plan", source="bridge"),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )
        await fake_services.ledger.set_status("run_genui", RunStatus.RUNNING)
        await fake_services.ledger.set_status("run_genui", RunStatus.DONE)
        await fake_services.bridge_sessions.add_turn(
            session.id,
            BridgeTurn(
                role="agent",
                content="The plan remains visible.",
                run_id="run_genui",
                fragments=(descriptor,),
            ),
        )

    asyncio.run(_seed())

    run = altar_client.get("/api/v1/bridge/runs/run_genui")
    restored = altar_client.get(f"/api/v1/bridge/sessions/{session.id}")

    assert run.status_code == 200
    assert run.json()["fragments"] == [descriptor]
    assert restored.status_code == 200
    assert restored.json()["session"]["turns"][0]["fragments"] == [descriptor]


def test_run_snapshot_reconstructs_latest_dispatch_and_transition_from_ledger(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    run_id = "run_reconstructed"

    async def _seed() -> None:
        await fake_services.ledger.create(
            Intent(
                session_id=session.id,
                run_id=run_id,
                prompt="raise the dead",
                source="bridge",
            ),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )
        await fake_services.ledger.set_status(run_id, RunStatus.RUNNING)
        await fake_services.ledger.set_status(run_id, RunStatus.AWAITING_HARDWARE)
        await fake_services.ledger.append_event(
            RunEvent(
                run_id=run_id,
                seq=0,
                kind=RunEventKind.DISPATCH,
                data="chat:local",
                meta={"occurrence_id": "occ-1", "grant_id": "grant-1"},
            )
        )
        await fake_services.ledger.append_event(
            RunEvent(
                run_id=run_id,
                seq=1,
                kind=RunEventKind.TRANSITION,
                data="request-1",
                meta={
                    "occurrence_id": "occ-1",
                    "capability_key": "chat:local",
                    "phase": "verifying",
                },
            )
        )

    asyncio.run(_seed())

    response = altar_client.get(f"/api/v1/bridge/runs/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["occurrence_id"] == "occ-1"
    assert body["dispatch_occurrence_id"] == "occ-1"
    assert body["grant_id"] == "grant-1"
    assert body["capability_key"] == "chat:local"
    assert body["transition_occurrence_id"] == "occ-1"
    assert body["transition_request_id"] == "request-1"
    assert body["transition_phase"] == "verifying"


def test_run_snapshot_uses_boot_catalogue_for_loom_link(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)

    async def _seed() -> None:
        await fake_services.ledger.create(
            Intent(session_id=session.id, run_id="run-registry-mismatch", prompt="raise", source="bridge"),
            workflow_name=BRIDGE_CHAT.name,
            pattern_manifest=BRIDGE_CHAT.manifest.snapshot(),
            queue_name="runs",
            priority=70,
        )

    asyncio.run(_seed())
    fake_services.workflows = BuiltinWorkflowRegistry(workflows=(DELEGATED_RITE,))

    response = altar_client.get("/api/v1/bridge/runs/run-registry-mismatch")

    assert response.status_code == 200
    assert response.json()["loom_path"] is None


def test_run_snapshot_requires_full_pattern_equality_for_loom_link(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    manifest = {**BRIDGE_CHAT.manifest.snapshot(), "unregistered_field": "drift"}

    async def _seed() -> None:
        await fake_services.ledger.create(
            Intent(session_id=session.id, run_id="run-full-pattern-mismatch", prompt="raise", source="bridge"),
            workflow_name=BRIDGE_CHAT.name,
            pattern_manifest=manifest,
            queue_name="runs",
            priority=70,
        )

    asyncio.run(_seed())

    response = altar_client.get("/api/v1/bridge/runs/run-full-pattern-mismatch")

    assert response.status_code == 200
    assert response.json()["loom_path"] is None


def test_run_snapshot_reconstructs_delegated_crossing(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    run_id = "run_delegate_crossing"

    async def _seed() -> str:
        await fake_services.ledger.create(
            Intent(
                session_id=session.id,
                run_id=run_id,
                prompt="/delegate inspect",
                source="bridge",
            ),
            workflow_name="delegated_rite",
            queue_name="runs",
            priority=70,
        )
        await fake_services.ledger.set_status(run_id, RunStatus.RUNNING)
        job = await fake_services.delegates.submit(
            DelegatedAgentRequest(
                request_id="request-crossing",
                run_id=run_id,
                step_id="dispatch_delegate",
                runtime="reference",
                profile=DelegatedAgentProfile.READ,
                prompt="inspect",
            )
        )
        await fake_services.ledger.append_event(
            RunEvent(
                run_id=run_id,
                seq=0,
                kind=RunEventKind.NODE,
                data="dispatch_delegate",
                meta={
                    "phase": "waiting",
                    "occurrence_id": "occ-delegate",
                    "delegated_job_id": job.job_id,
                    "delegated_runtime": "reference",
                },
            )
        )
        await fake_services.ledger.set_status(run_id, RunStatus.AWAITING_DELEGATE)
        return job.job_id

    job_id = asyncio.run(_seed())
    jobs_for_run = fake_services.delegates.jobs_for_run
    bounds: list[tuple[int | None, int | None]] = []

    async def record_bounded_read(
        correlated_run_id: str,
        *,
        limit: int | None = None,
        event_limit: int | None = None,
    ) -> tuple[Any, ...]:
        bounds.append((limit, event_limit))
        return await jobs_for_run(correlated_run_id, limit=limit, event_limit=event_limit)

    fake_services.delegates.jobs_for_run = record_bounded_read
    response = altar_client.get(f"/api/v1/bridge/runs/{run_id}")

    assert response.status_code == 200
    assert bounds == [(1, 0)]
    body = response.json()
    assert body["run_status"] == "awaiting_delegate"
    assert body["delegated_job_id"] == job_id
    assert body["delegated_runtime"] == "reference"
    assert body["delegated_profile"] == "read"
    assert body["delegated_status"] == "running"


def test_run_snapshot_preserves_cross_occurrence_correlations(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    """A resumed dispatch must never be presented as the prior transition's occurrence."""
    session = _session(fake_services)
    run_id = "run_cross_occurrence"

    async def _seed() -> None:
        await fake_services.ledger.create(
            Intent(session_id=session.id, run_id=run_id, prompt="raise", source="bridge"),
            workflow_name="bridge_chat",
            queue_name="runs",
            priority=70,
        )
        await fake_services.ledger.set_status(run_id, RunStatus.RUNNING)
        for event in (
            RunEvent(
                run_id=run_id,
                seq=0,
                kind=RunEventKind.TRANSITION,
                data="request-a",
                meta={"occurrence_id": "occ-a", "capability_key": "chat:local", "phase": "ready"},
            ),
            RunEvent(
                run_id=run_id,
                seq=1,
                kind=RunEventKind.NODE,
                data="converse",
                meta={"occurrence_id": "occ-b"},
            ),
            RunEvent(
                run_id=run_id,
                seq=2,
                kind=RunEventKind.DISPATCH,
                data="chat:local",
                meta={"occurrence_id": "occ-b", "grant_id": "grant-b"},
            ),
        ):
            await fake_services.ledger.append_event(event)

    asyncio.run(_seed())

    body = altar_client.get(f"/api/v1/bridge/runs/{run_id}").json()
    assert body["occurrence_id"] == "occ-b"
    assert body["dispatch_occurrence_id"] == "occ-b"
    assert body["grant_id"] == "grant-b"
    assert body["transition_occurrence_id"] == "occ-a"
    assert body["transition_request_id"] == "request-a"


def test_send_unknown_session_404(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.post(
        "/api/v1/bridge/sessions/nope/messages",
        json={"prompt": "hi", "request_id": _REQUEST_ID},
    )
    assert response.status_code == 404


def test_send_empty_prompt_400(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    response = altar_client.post(
        f"/api/v1/bridge/sessions/{session.id}/messages",
        json={"prompt": "   ", "request_id": _REQUEST_ID},
    )
    assert response.status_code == 400


def test_send_happy_path(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    response = altar_client.post(
        f"/api/v1/bridge/sessions/{session.id}/messages",
        json={"prompt": "raise the dead", "request_id": _REQUEST_ID},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"]
    assert body["pattern_id"] == "bridge_chat"
    assert body["pattern_revision"] == "1"
    assert body["loom_path"] == "/loom/bridge_chat/1"
    assert body["orb_path"] == f"/orb/{body['run_id']}"
    assert body["evidence_capture"] == "process_local"
    assert body["turn"]["content"] == "raise the dead"
    assert body["turn"]["role"] == "user"
    assert len(fake_services.run_engine.submitted) == 1
    assert fake_services.run_engine.submitted[0].prompt == "raise the dead"
    assert fake_services.run_engine.submitted[0].sigil_name
    assert fake_services.run_engine.submitted[0].sigil_scopes
    assert fake_services.run_engine.exclusive_session_submissions == [True]


def test_send_replay_returns_one_run_and_one_retained_turn(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    path = f"/api/v1/bridge/sessions/{session.id}/messages"
    payload = {"prompt": "raise exactly once", "request_id": _REQUEST_ID}

    first = altar_client.post(path, json=payload)
    replay = altar_client.post(path, json=payload)
    restored = altar_client.get(f"/api/v1/bridge/sessions/{session.id}")

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["run_id"] == first.json()["run_id"]
    assert replay.json()["turn"] == first.json()["turn"]
    assert len(fake_services.run_engine.submitted) == 1
    user_turns = [turn for turn in restored.json()["session"]["turns"] if turn["role"] == "user"]
    assert len(user_turns) == 1


def test_inspector_returns_context(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    response = altar_client.get(
        f"/api/v1/bridge/sessions/{session.id}/inspector",
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": session.id,
        "title": session.title,
        "turn_count": 0,
        "pending_count": 0,
    }
