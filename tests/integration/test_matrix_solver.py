import pytest
from unittest.mock import AsyncMock, MagicMock
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.extensions.protocols import CapabilityProtocol

@pytest.mark.asyncio
async def test_matrix_solver_lowest_cost_path():
    """
    THE MATRIX SOLVER CRUCIBLE.
    Verifies that the Orchestrator picks the lowest-cost transition path
    by evaluating concurrent Matrix Sets and eviction costs.
    """
    
    # 1. Setup Capabilities
    # Titan: Heavy model, expensive to evict
    titan = MagicMock(spec=CapabilityProtocol)
    titan.identifier = "titan-70b"
    titan.evict_cost = 100
    titan.matrix_sets = ["titan_set"]
    titan.is_active = True
    
    # Coding: Lite model, part of both 'lite' and 'coding' sets
    coding = MagicMock(spec=CapabilityProtocol)
    coding.identifier = "coding-8b"
    coding.evict_cost = 10
    coding.matrix_sets = ["lite_set", "coding_set"]
    coding.is_active = True
    
    # Vision: Target model, part of 'lite' and 'vision' sets
    vision = MagicMock(spec=CapabilityProtocol)
    vision.identifier = "vision-8b"
    vision.evict_cost = 10
    vision.matrix_sets = ["lite_set", "vision_set"]
    vision.is_active = False
    
    # Current Active Models: [titan-70b, coding-8b]
    
    # Scenario: Activate "vision-8b"
    
    # Candidate Set 1: "lite_set" -> contains [coding-8b, vision-8b]
    # To transition: Evict [titan-70b] -> Cost 100
    
    # Candidate Set 2: "vision_set" -> contains [vision-8b]
    # To transition: Evict [titan-70b, coding-8b] -> Cost 110
    
    manager = OrchestratorManager(MagicMock(), [titan, coding, vision])
    
    # 2. Execution
    to_stop, to_start = await manager._solve_matrix(vision)
    
    # 3. Assertions
    # Should pick "lite_set" (Cost 100) over "vision_set" (Cost 110)
    assert "titan-70b" in to_stop
    assert "coding-8b" not in to_stop  # Should be kept alive!
    assert "vision-8b" in to_start

@pytest.mark.asyncio
async def test_matrix_solver_no_eviction_required():
    """Verifies that if the target is already in a compatible set, cost is 0."""
    coding = MagicMock(spec=CapabilityProtocol)
    coding.identifier = "coding-8b"
    coding.evict_cost = 10
    coding.matrix_sets = ["lite_set"]
    coding.is_active = True
    
    vision = MagicMock(spec=CapabilityProtocol)
    vision.identifier = "vision-8b"
    vision.evict_cost = 10
    vision.matrix_sets = ["lite_set"]
    vision.is_active = True
    
    manager = OrchestratorManager(MagicMock(), [coding, vision])
    
    to_stop, to_start = await manager._solve_matrix(vision)
    
    assert len(to_stop) == 0
    assert len(to_start) == 0
