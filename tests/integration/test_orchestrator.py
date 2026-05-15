import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.cortex.dispatcher import HardwareTransitionRequired

@pytest.mark.asyncio
async def test_orchestrator_hard_swap_decision():
    """
    Verifies that the Orchestrator performs a Hard Swap (systemctl start)
    when the target is cold.
    """
    # 1. Setup Mocks
    mock_broker = AsyncMock()
    mock_broker.get_active_worker_count.return_value = 0
    
    mock_animator = AsyncMock()
    mock_animator.identifier = "titan_text"
    
    mock_capability = MagicMock()
    
    exception = HardwareTransitionRequired(
        capability=mock_capability,
        animator=mock_animator
    )
    
    manager = OrchestratorManager(worker_broker=mock_broker)
    
    # 2. Mock Systemd calls
    # We mock create_subprocess_exec to simulate 'is-active' returning 1 (cold)
    # and 'start' returning 0 (success).
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock for is-active (cold)
        mock_is_active_process = AsyncMock()
        mock_is_active_process.wait.return_value = None
        mock_is_active_process.returncode = 1
        
        # Mock for start (success)
        mock_start_process = AsyncMock()
        mock_start_process.wait.return_value = None
        mock_start_process.returncode = 0
        
        mock_exec.side_effect = [mock_is_active_process, mock_start_process]
        
        # 3. Execution (High priority to pass Tipping Point)
        await manager.handle_transition(exception, signal_priority=200.0)
        
        # 4. Assertions
        # Verify Hard Swap sequence (The Drain Protocol)
        mock_broker.pause_queues.assert_called_once()
        mock_broker.broadcast_soft_stop.assert_called_once()
        
        # Verify Systemd calls
        assert mock_exec.call_count == 2
        mock_exec.assert_any_call(
            "systemctl", "--user", "is-active", "lychd-coven-titan_text.target",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        mock_exec.assert_any_call(
            "systemctl", "--user", "start", "lychd-coven-titan_text.target"
        )
        
        # Verify Soft Swap follow-up
        mock_animator.activate_capability.assert_called_once_with(mock_capability)
        
        # Verify Unpause
        mock_broker.unpause_queues.assert_called_once()

@pytest.mark.asyncio
async def test_orchestrator_soft_swap_only_when_warm():
    """
    Verifies that the Orchestrator skips the Hard Swap (and Drain Protocol)
    when the target is already warm.
    """
    # 1. Setup Mocks
    mock_broker = AsyncMock()
    mock_animator = AsyncMock()
    mock_animator.identifier = "vision"
    mock_capability = MagicMock()
    
    exception = HardwareTransitionRequired(
        capability=mock_capability,
        animator=mock_animator
    )
    
    manager = OrchestratorManager(worker_broker=mock_broker)
    
    # 2. Mock Systemd calls (is-active returns 0 -> warm)
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.wait.return_value = None
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        
        # 3. Execution
        await manager.handle_transition(exception, signal_priority=200.0)
        
        # 4. Assertions
        # Should NOT trigger Drain Protocol
        mock_broker.pause_queues.assert_not_called()
        mock_broker.broadcast_soft_stop.assert_not_called()
        
        # Should only call is-active once
        assert mock_exec.call_count == 1
        
        # Should call Soft Swap directly
        mock_animator.activate_capability.assert_called_once_with(mock_capability)
        
        # Unpause should NOT be called since pause wasn't called in the soft-only path
        mock_broker.unpause_queues.assert_not_called()
