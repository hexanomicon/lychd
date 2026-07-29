"""Core contracts for replay-safe work delegated to isolated agent runtimes."""

from lychd.domain.delegation.models import (
    LEGAL_DELEGATED_AGENT_TRANSITIONS,
    TERMINAL_DELEGATED_AGENT_STATUSES,
    DelegatedAgentEvent,
    DelegatedAgentEventKind,
    DelegatedAgentJob,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentProfile,
    DelegatedAgentRequest,
    DelegatedAgentResult,
)
from lychd.domain.delegation.ports import (
    DelegatedAgentCoordinatorPort,
    DelegatedAgentJobStore,
    DelegatedAgentRuntime,
)
from lychd.domain.delegation.services import (
    DelegatedAgentCoordinator,
    IllegalDelegatedAgentTransitionError,
    InMemoryDelegatedAgentJobStore,
)
from lychd.domain.delegation.signals import DelegatedAgentParked, DelegatedAgentPending

__all__ = [
    "LEGAL_DELEGATED_AGENT_TRANSITIONS",
    "TERMINAL_DELEGATED_AGENT_STATUSES",
    "DelegatedAgentCoordinator",
    "DelegatedAgentCoordinatorPort",
    "DelegatedAgentEvent",
    "DelegatedAgentEventKind",
    "DelegatedAgentJob",
    "DelegatedAgentJobRef",
    "DelegatedAgentJobStatus",
    "DelegatedAgentJobStore",
    "DelegatedAgentParked",
    "DelegatedAgentPending",
    "DelegatedAgentProfile",
    "DelegatedAgentRequest",
    "DelegatedAgentResult",
    "DelegatedAgentRuntime",
    "IllegalDelegatedAgentTransitionError",
    "InMemoryDelegatedAgentJobStore",
]
