"""Selected-Run Orb projection with explicit capture and gaps."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from lychd.agents.router import Intent
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT
from lychd.domain.cortex.events import RunEvent, RunEventKind
from lychd.domain.cortex.runs import RunStatus

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient


def _seed(services: SimpleNamespace, run_id: str) -> None:
    async def seed() -> None:
        run = await services.ledger.create(
            Intent(session_id="session-1", run_id=run_id, prompt="secret prompt", source="bridge"),
            workflow_name=BRIDGE_CHAT.name,
            pattern_manifest=BRIDGE_CHAT.manifest.snapshot(),
            queue_name="runs",
            priority=70,
        )
        await services.ledger.set_status(run.run_id, RunStatus.RUNNING)
        await services.ledger.append_event(RunEvent(run_id=run.run_id, seq=0, kind=RunEventKind.STATUS, data="running"))
        await services.ledger.append_event(
            RunEvent(
                run_id=run.run_id,
                seq=2,
                kind=RunEventKind.NODE,
                data="converse",
                meta={
                    "phase": "entered",
                    "occurrence_id": "occurrence-1",
                    "pattern_id": BRIDGE_CHAT.manifest.key,
                    "pattern_revision": BRIDGE_CHAT.manifest.revision,
                },
            )
        )
        await services.ledger.append_event(
            RunEvent(
                run_id=run.run_id,
                seq=3,
                kind=RunEventKind.LOG,
                data="raw secret that must not be projected",
                meta={"level": "warning"},
            )
        )

    asyncio.run(seed())


def test_selected_run_projects_exact_pattern_and_honest_gap(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    _seed(fake_services, "run-orb")

    response = altar_client.get("/api/v1/orb/runs/run-orb")

    assert response.status_code == 200
    body = response.json()
    assert body["run"]["run_id"] == "run-orb"
    assert body["pattern"]["exact"] is True
    assert body["pattern"]["loom_path"] == "/loom/bridge_chat/1?run=run-orb"
    assert body["capture"] == "process_local"
    assert body["live_tail"] == "not_available"
    assert body["ledger_head_seq"] == 3
    assert body["page_end_seq"] == 3
    assert body["has_more"] is False
    assert body["gaps"] == [{"start_seq": 1, "end_seq": 1, "classification": "unknown_or_omitted"}]
    assert body["evidence"][1]["occurrence_id"] == "occurrence-1"
    assert body["evidence"][1]["subject_key"] == "converse"
    assert "raw secret" not in response.text
    assert "Token deltas" in body["known_omissions"][0]


def test_selected_run_is_bounded_and_unknown_is_404(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    _seed(fake_services, "run-page")

    first = altar_client.get("/api/v1/orb/runs/run-page?limit=1")

    assert first.status_code == 200
    assert len(first.json()["evidence"]) == 1
    assert first.json()["has_more"] is True
    assert first.json()["page_end_seq"] == 0
    assert first.json()["next_after_seq"] == 0
    assert altar_client.get("/api/v1/orb/runs/missing").status_code == 404
    assert altar_client.get("/api/v1/scrying/runs/run-page").status_code == 404
