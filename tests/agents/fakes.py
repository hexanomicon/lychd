"""In-process fakes for the offline agent/graph suite (A5 §10).

Each fake is a thin, dict/list-backed stand-in for a `WorkflowServices` port.
None of them touches the network or a model — the whole suite runs with
`ALLOW_MODEL_REQUESTS = False` (see `conftest.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import DeferredToolRequests


@dataclass
class FakeGrant:
    """A minimal `CapabilityGrant` stand-in: nodes only read `model`/`toolsets`."""

    model: Any
    toolsets: tuple[Any, ...] = ()


@dataclass
class FakeDispatcher:
    """`GrantPort` fake: hands back a grant carrying the injected TestModel."""

    model: Any
    toolsets: tuple[Any, ...] = ()
    calls: list[str] = field(default_factory=list)

    def resolve_capability_grant(self, intent_type: str) -> FakeGrant:
        self.calls.append(intent_type)
        return FakeGrant(model=self.model, toolsets=self.toolsets)


@dataclass
class _Plan:
    action_type: str = "NO_OP"
    total_metabolic_cost: float = 0.0


@dataclass
class FakeOrchestrator:
    """`TransitionPort` fake: records calculate/request calls for assertions."""

    calls: list[tuple[str, ...]] = field(default_factory=list)

    async def calculate_transition_plan(self, target_capability_key: str) -> _Plan:
        self.calls.append(("calculate", target_capability_key))
        return _Plan()

    async def request_transition(self, target_capability_key: str, priority: float) -> _Plan:
        self.calls.append(("request", target_capability_key, str(priority)))
        return _Plan()


@dataclass
class _FakeChannel:
    parent: FakeEvents
    run_id: str

    def emit(self, kind: str, payload: str) -> None:
        self.parent.events.append((self.run_id, kind, payload))


@dataclass
class FakeEvents:
    """`RunEventPort` fake: flat list of `(run_id, kind, payload)` tuples."""

    events: list[tuple[str, str, str]] = field(default_factory=list)

    def channel(self, run_id: str) -> _FakeChannel:
        return _FakeChannel(self, run_id)

    def kinds(self) -> list[str]:
        return [kind for _, kind, _ in self.events]


@dataclass
class _FakeSession:
    turns: list[Any] = field(default_factory=list)


@dataclass
class FakeTurns:
    """`TurnLedgerPort` fake: records added turns, run statuses, and known sessions."""

    added: list[tuple[str, Any]] = field(default_factory=list)
    statuses: dict[str, str] = field(default_factory=dict)
    sessions: dict[str, _FakeSession] = field(default_factory=dict)

    def add_turn(self, session_id: str, turn: Any) -> None:
        self.added.append((session_id, turn))

    def set_run_status(self, run_id: str, status: str) -> None:
        self.statuses[run_id] = status

    def get_session(self, session_id: str) -> _FakeSession | None:
        return self.sessions.get(session_id)


@dataclass
class FakeConsents:
    """`ConsentLedgerPort` fake: dict-backed park with a deterministic id."""

    parked: list[dict[str, Any]] = field(default_factory=list)

    def park_consent(
        self,
        *,
        run_id: str,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        requests: DeferredToolRequests,
    ) -> str:
        consent_id = f"consent_{len(self.parked)}"
        self.parked.append(
            {
                "id": consent_id,
                "run_id": run_id,
                "session_id": session_id,
                "tool_name": tool_name,
                "args": args,
                "requests": requests,
            }
        )
        return consent_id


class FakeRegistry:
    """Minimal registry for a real `ContextOrchestrator` (no warm capabilities)."""

    def list_capability_states(self) -> list[Any]:
        return []
