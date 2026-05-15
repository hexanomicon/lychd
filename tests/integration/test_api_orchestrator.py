import pytest
from litestar import Litestar
from litestar.testing import TestClient
from litestar.di import Provide
from lychd.interface.api.orchestrator import OrchestratorController
from lychd.domain.orchestration.manager import OrchestratorManager
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_orchestrator():
    return MagicMock(spec=OrchestratorManager)

@pytest.fixture
def client(mock_orchestrator):
    # We create a minimal app for testing the controller in isolation,
    # following the "unbound controller" pattern.
    app = Litestar(
        route_handlers=[OrchestratorController],
        dependencies={"orchestrator": Provide(lambda: mock_orchestrator)}
    )
    with TestClient(app=app) as client:
        yield client

def test_get_status(client, mock_orchestrator):
    """Verifies the /orchestrator/status endpoint returns valid capability state."""
    # Setup mock capabilities
    cap = MagicMock()
    cap.identifier = "test-cap"
    cap.is_active = True
    cap.evict_cost = 10
    cap.matrix_sets = ["set1"]
    
    mock_orchestrator.all_capabilities = [cap]
    
    response = client.get("/orchestrator/status")
    assert response.status_code == 200
    data = response.json()
    assert "test-cap" in data["active_capabilities"]
    assert data["all_capabilities"][0]["identifier"] == "test-cap"
    assert data["all_capabilities"][0]["evict_cost"] == 10

def test_get_plan(client, mock_orchestrator):
    """Verifies the /orchestrator/solver/plan endpoint returns a TransitionPlan."""
    from lychd.domain.orchestration.schema import TransitionPlan
    
    plan = TransitionPlan(
        total_metabolic_cost=50.0,
        evict_coven_ids=["old-relic"],
        launch_coven_ids=["new-relic"],
        action_type="HARD_SWAP"
    )
    
    # Litestar handles AsyncMock results in dependencies automatically
    mock_orchestrator.calculate_transition_plan = AsyncMock(return_value=plan)
    
    response = client.get("/orchestrator/solver/plan", params={"target": "new-relic"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["total_metabolic_cost"] == 50.0
    assert data["action_type"] == "HARD_SWAP"
    assert "old-relic" in data["evict_coven_ids"]
    
    mock_orchestrator.calculate_transition_plan.assert_called_once_with("new-relic")

def test_activate_manual_override(client, mock_orchestrator):
    """Verifies the /orchestrator/activate endpoint triggers the request_transition physics."""
    from lychd.domain.orchestration.schema import TransitionPlan
    
    plan = TransitionPlan(
        total_metabolic_cost=10.0,
        evict_coven_ids=[],
        launch_coven_ids=["target-relic"],
        action_type="SOFT_SWAP"
    )
    
    mock_orchestrator.request_transition = AsyncMock(return_value=plan)
    
    response = client.post("/orchestrator/activate", params={"target": "target-relic"})
    assert response.status_code == 202
    
    data = response.json()
    assert data["action_type"] == "SOFT_SWAP"
    
    # Priority 100.0 is the manual override default
    mock_orchestrator.request_transition.assert_called_once_with("target-relic", priority=100.0)
