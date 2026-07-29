"""Selected-Run Orb projection with explicit capture and gaps."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from lychd.agents.router import Intent
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT
from lychd.domain.cortex.events import RunEvent, RunEventKind
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.delegation.models import DelegatedAgentProfile, DelegatedAgentRequest

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


def test_selected_run_projects_prompt_free_delegated_job_evidence(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    _seed(fake_services, "run-delegated")

    async def seed_job() -> None:
        ref = await fake_services.delegates.submit(
            DelegatedAgentRequest(
                request_id="request-secret",
                run_id="run-delegated",
                step_id="dispatch_delegate",
                runtime="reference",
                profile=DelegatedAgentProfile.READ,
                prompt="private delegated prompt",
            )
        )
        await fake_services.delegates.refresh(ref.job_id)

    asyncio.run(seed_job())

    response = altar_client.get("/api/v1/orb/runs/run-delegated")

    assert response.status_code == 200
    jobs = response.json()["delegated_jobs"]
    assert len(jobs) == 1
    assert jobs[0]["runtime"] == "reference"
    assert jobs[0]["profile"] == "read"
    assert jobs[0]["status"] == "succeeded"
    assert jobs[0]["output_present"] is True
    assert [event["status"] for event in jobs[0]["events"]] == [
        "queued",
        "admitted",
        "preparing",
        "running",
        "succeeded",
    ]
    assert "private delegated prompt" not in response.text
    assert "Reference delegate completed" not in response.text


def test_selected_run_bounds_delegated_job_cardinality(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    _seed(fake_services, "run-many-delegates")

    async def seed_jobs() -> None:
        for index in range(33):
            await fake_services.delegates.submit(
                DelegatedAgentRequest(
                    request_id=f"request-many-{index:02d}",
                    run_id="run-many-delegates",
                    step_id=f"delegate-{index:02d}",
                    runtime="reference",
                    profile=DelegatedAgentProfile.READ,
                    prompt="bounded private prompt",
                )
            )

    asyncio.run(seed_jobs())

    body = altar_client.get("/api/v1/orb/runs/run-many-delegates").json()

    assert len(body["delegated_jobs"]) == 32
    assert body["delegated_jobs"][0]["request_id"] == "request-many-01"
    assert body["delegated_jobs"][-1]["request_id"] == "request-many-32"
    assert any("1 older delegated job" in omission for omission in body["known_omissions"])
