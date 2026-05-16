from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.schema import TransitionPlan
from lychd.interface.api.orchestrator import OrchestratorController


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    return MagicMock(spec=OrchestratorManager)


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
