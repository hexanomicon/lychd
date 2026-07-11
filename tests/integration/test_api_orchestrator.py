from __future__ import annotations

# Litestar's create_test_client callback surface contains third-party Unknowns.
# pyright: reportUnknownVariableType=false
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from litestar.testing import create_test_client

from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.orchestration.arbiter import TransitionDeclined
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan
from lychd.interface.api.orchestrator import OrchestratorController
from lychd.interface.web.deps import web_dependencies

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar import Litestar


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    orchestrator = MagicMock(spec=OrchestratorManager)
    orchestrator.containment_reason = None
    return orchestrator


@pytest.mark.asyncio
async def test_get_status(mock_orchestrator: MagicMock) -> None:
    mock_orchestrator.list_capability_statuses.return_value = [
        {
            "capability_key": "test-cap",
            "is_active": True,
            "evict_cost": 10,
            "matrix_sets": ["set1"],
            "dedicated": True,
            "persistent_resident": False,
        }
    ]

    data = await OrchestratorController.get_status.fn(None, mock_orchestrator)

    assert "test-cap" in data["active_capabilities"]
    assert data["all_capabilities"][0]["capability_key"] == "test-cap"
    assert data["all_capabilities"][0]["evict_cost"] == 10
    assert data["mutation_containment"] is None


@pytest.mark.asyncio
async def test_get_plan(mock_orchestrator: MagicMock) -> None:
    plan = TransitionPlan(
        total_metabolic_cost=50.0,
        evict_coven_ids=["old-relic"],
        launch_coven_ids=["new-relic"],
        action_type="HARD_SWAP",
    )
    mock_orchestrator.calculate_transition_plan = AsyncMock(return_value=plan)

    data = await OrchestratorController.get_transition_plan.fn(None, mock_orchestrator, target="new-relic")

    assert data.total_metabolic_cost == 50.0
    assert data.action_type == "HARD_SWAP"
    assert "old-relic" in data.evict_coven_ids
    mock_orchestrator.calculate_transition_plan.assert_called_once_with("new-relic")


@pytest.mark.asyncio
async def test_activate_manual_override(mock_orchestrator: MagicMock) -> None:
    plan = TransitionPlan(
        total_metabolic_cost=10.0,
        evict_coven_ids=[],
        launch_coven_ids=["target-relic"],
        action_type="SOFT_SWAP",
    )
    mock_orchestrator.request_transition = AsyncMock(return_value=plan)

    data = await OrchestratorController.activate_capability.fn(None, mock_orchestrator, target="target-relic")

    assert data.action_type == "SOFT_SWAP"
    mock_orchestrator.request_transition.assert_called_once_with("target-relic", priority=100.0)


class _GatingOrchestrator(OrchestratorManager):
    """A gating orchestrator: HARD_SWAP declined below priority 40 (subclasses for DI validation)."""

    def __init__(self) -> None:
        self.worker_broker = None

    async def request_transition(self, target_capability_key: str, priority: float) -> TransitionPlan:
        plan = TransitionPlan(
            total_metabolic_cost=1.0,
            evict_coven_ids=["old-relic"],
            launch_coven_ids=[target_capability_key],
            action_type="HARD_SWAP",
        )
        if priority < 40:
            raise TransitionDeclined(plan, priority, 40)
        return plan


def _gating_client() -> Any:
    services = SimpleNamespace(orchestrator=_GatingOrchestrator(), leases=LeaseLedger())

    @asynccontextmanager
    async def _lifespan(app: Litestar) -> AsyncIterator[None]:
        app.state.services = services
        yield

    return create_test_client(
        route_handlers=[OrchestratorController],
        dependencies=web_dependencies,
        lifespan=[_lifespan],
        middleware=[sigil_auth_middleware()],
    )


def test_activate_low_priority_hard_swap_returns_409() -> None:
    """POST /activate?priority=25 against a HARD_SWAP → 409 carrying the plan + threshold."""
    with _gating_client() as client:
        resp = client.post("/orchestrator/activate", params={"target": "titan", "priority": 25})
    assert resp.status_code == 409
    body = resp.json()
    assert body["threshold"] == 40
    assert body["priority"] == 25
    assert body["plan"]["action_type"] == "HARD_SWAP"


def test_activate_high_priority_hard_swap_returns_202() -> None:
    """POST /activate?priority=70 proceeds → 202 with the plan."""
    with _gating_client() as client:
        resp = client.post("/orchestrator/activate", params={"target": "titan", "priority": 70})
    assert resp.status_code == 202
    assert resp.json()["action_type"] == "HARD_SWAP"
