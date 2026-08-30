from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from litestar import Litestar
from litestar.datastructures import State

from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.orchestration.arbiter import TransitionDeclined
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan
from lychd.interface.api.orchestrator import OrchestratorController
from lychd.interface.web.deps import web_dependencies


class _RecordingOrchestrator(OrchestratorManager):
    """Small HTTP-boundary collaborator with observable transition requests."""

    def __init__(self) -> None:
        self._contained_reason = None
        self.worker_broker = None
        self.planned_targets: list[str] = []
        self.transition_requests: list[tuple[str, float]] = []

    def list_capability_statuses(self) -> list[dict[str, object]]:
        return [
            {
                "capability_key": "test-cap",
                "animator_name": "test-animator",
                "family": "chat",
                "runtime": "reference",
                "source_kind": "soulstone",
                "is_dynamic": True,
                "phase": "warm",
                "model_id": "test-model",
                "is_static": False,
                "is_active": True,
                "is_available": True,
                "warm": True,
                "health": "ok",
                "reason": None,
                "checked_at": None,
                "dedicated": True,
                "persistent_resident": False,
            }
        ]

    async def calculate_transition_plan(self, target_capability_key: str) -> TransitionPlan:
        self.planned_targets.append(target_capability_key)
        return TransitionPlan(
            total_metabolic_cost=50.0,
            evict_coven_ids=["old-relic"],
            launch_coven_ids=[target_capability_key],
            action_type="HARD_SWAP",
        )

    async def request_transition(
        self,
        target_capability_key: str,
        priority: float,
        *,
        trace: object | None = None,
    ) -> TransitionPlan:
        _ = trace
        self.transition_requests.append((target_capability_key, priority))
        return TransitionPlan(
            total_metabolic_cost=10.0,
            evict_coven_ids=[],
            launch_coven_ids=[target_capability_key],
            action_type="SOFT_SWAP",
        )


def _app(orchestrator: OrchestratorManager) -> Litestar:
    services = SimpleNamespace(orchestrator=orchestrator, leases=LeaseLedger())
    return Litestar(
        route_handlers=[OrchestratorController],
        dependencies=web_dependencies,
        middleware=[sigil_auth_middleware()],
        state=State({"services": services}),
    )


@pytest.mark.asyncio
async def test_get_status() -> None:
    transport = httpx.ASGITransport(app=_app(_RecordingOrchestrator()))  # pyright: ignore[reportArgumentType]
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver.local") as client:
        response = await client.get("/orchestrator/status")

    assert response.status_code == 200
    data = response.json()
    assert data["active_capabilities"] == ["test-cap"]
    assert data["all_capabilities"][0]["phase"] == "warm"
    assert data["mutation_containment"] is None


@pytest.mark.asyncio
async def test_get_plan() -> None:
    orchestrator = _RecordingOrchestrator()
    transport = httpx.ASGITransport(app=_app(orchestrator))  # pyright: ignore[reportArgumentType]
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver.local") as client:
        response = await client.get("/orchestrator/solver/plan", params={"target": "new-relic"})

    assert response.status_code == 200
    data = response.json()
    assert data["total_metabolic_cost"] == 50.0
    assert data["action_type"] == "HARD_SWAP"
    assert data["evict_coven_ids"] == ["old-relic"]
    assert orchestrator.planned_targets == ["new-relic"]


@pytest.mark.parametrize("failure", ["missing-substrate", "queue-info"])
@pytest.mark.asyncio
async def test_queues_reports_unavailable_truth(
    failure: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import lychd.interface.api.orchestrator as api

    if failure == "missing-substrate":

        def unavailable() -> object:
            message = "not published"
            raise RuntimeError(message)

        monkeypatch.setattr(api, "get_run_substrate", unavailable)
    else:

        class BrokenQueue:
            async def info(self) -> dict[str, int]:
                message = "broker offline"
                raise OSError(message)

        monkeypatch.setattr(
            api,
            "get_run_substrate",
            lambda: SimpleNamespace(queues={"runs": BrokenQueue()}),
        )

    transport = httpx.ASGITransport(app=_app(_RecordingOrchestrator()))  # pyright: ignore[reportArgumentType]
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver.local") as client:
        response = await client.get("/orchestrator/queues")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_activate_manual_override() -> None:
    orchestrator = _RecordingOrchestrator()
    transport = httpx.ASGITransport(app=_app(orchestrator))  # pyright: ignore[reportArgumentType]
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver.local") as client:
        response = await client.post("/orchestrator/activate", params={"target": "target-relic"})

    assert response.status_code == 202
    assert response.json()["action_type"] == "SOFT_SWAP"
    assert orchestrator.transition_requests == [("target-relic", 100)]


class _GatingOrchestrator(OrchestratorManager):
    """A gating orchestrator: HARD_SWAP declined below priority 40 (subclasses for DI validation)."""

    def __init__(self) -> None:
        self.worker_broker = None

    async def request_transition(
        self,
        target_capability_key: str,
        priority: float,
        *,
        trace: object | None = None,
    ) -> TransitionPlan:
        _ = trace
        plan = TransitionPlan(
            total_metabolic_cost=1.0,
            evict_coven_ids=["old-relic"],
            launch_coven_ids=[target_capability_key],
            action_type="HARD_SWAP",
        )
        if priority < 40:
            raise TransitionDeclined(plan, priority, 40)
        return plan


def _gating_app() -> Litestar:
    return _app(_GatingOrchestrator())


@pytest.mark.asyncio
async def test_activate_low_priority_hard_swap_returns_409() -> None:
    """POST /activate?priority=25 against a HARD_SWAP → 409 carrying the plan + threshold."""
    transport = httpx.ASGITransport(app=_gating_app())  # pyright: ignore[reportArgumentType]
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver.local") as client:
        resp = await client.post("/orchestrator/activate", params={"target": "titan", "priority": 25})
    assert resp.status_code == 409
    body = resp.json()
    assert body["threshold"] == 40
    assert body["priority"] == 25
    assert body["plan"]["action_type"] == "HARD_SWAP"


@pytest.mark.parametrize("priority", [-1, 101])
@pytest.mark.asyncio
async def test_activate_rejects_priority_outside_doctrine(priority: int) -> None:
    transport = httpx.ASGITransport(app=_gating_app())  # pyright: ignore[reportArgumentType]
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver.local") as client:
        response = await client.post(
            "/orchestrator/activate",
            params={"target": "titan", "priority": priority},
        )

    assert response.status_code == 400
