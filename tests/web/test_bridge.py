"""Bridge JSON contract: session creation, message admission, and inspector."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from lychd.agents.router import Intent
from lychd.domain.cortex.events import RunEvent, RunEventKind
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.delegation.models import DelegatedAgentProfile, DelegatedAgentRequest

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient


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


def test_snapshot_reconstructs_selected_process_local_active_runs(
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
    ]


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
    response = altar_client.get(f"/api/v1/bridge/runs/{run_id}")

    assert response.status_code == 200
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
        json={"prompt": "hi"},
    )
    assert response.status_code == 404


def test_send_empty_prompt_400(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    response = altar_client.post(
        f"/api/v1/bridge/sessions/{session.id}/messages",
        json={"prompt": "   "},
    )
    assert response.status_code == 400


def test_send_happy_path(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    session = _session(fake_services)
    response = altar_client.post(
        f"/api/v1/bridge/sessions/{session.id}/messages",
        json={"prompt": "raise the dead"},
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
