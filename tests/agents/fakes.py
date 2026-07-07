"""In-process fakes for the offline agent/graph suite (A5 §10).

Each fake is a thin, dict/list-backed stand-in for a `WorkflowServices` port.
None of them touches the network or a model — the whole suite runs with
`ALLOW_MODEL_REQUESTS = False` (see `conftest.py`).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lychd.domain.codex.schemas import ConsentDecision

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass
class FakeGrant:
    """A minimal `CapabilityGrant` stand-in: nodes only read `model`/`toolsets`."""

    model: Any
    toolsets: tuple[Any, ...] = ()
    settings: Any = None

    def model_settings(self) -> Any:
        """Return the recordable model_settings sentinel (None unless one was injected)."""
        return self.settings


@dataclass
class FakeDispatcher:
    """`GrantPort` fake: leases a grant carrying the injected TestModel (C1 CM shape)."""

    model: Any
    toolsets: tuple[Any, ...] = ()
    settings: Any = None
    calls: list[str] = field(default_factory=list)

    @asynccontextmanager
    async def lease_grant(
        self,
        *,
        family: Any,
        model_name: Any = None,
        run_id: str,
        priority: int = 50,
        require_modalities: tuple[str, ...] = (),
    ) -> AsyncIterator[FakeGrant]:
        _ = (model_name, run_id, priority, require_modalities)
        self.calls.append(str(family))
        yield FakeGrant(model=self.model, toolsets=self.toolsets, settings=self.settings)


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
class FakeEvents:
    """`RunEventBus` fake: real `RunEmitter`/`RunChannel`, recording a flat event list.

    Exercises the real event plane (the emitter pushes to a real `RunChannel`) while
    teeing every event into `events` as `(run_id, kind, data)` tuples for assertions.
    """

    events: list[tuple[str, str, str]] = field(default_factory=list)
    _channels: dict[str, Any] = field(default_factory=dict)

    def emitter(self, run_id: str) -> Any:
        from lychd.domain.cortex.events import RunEmitter

        return RunEmitter(channel=self._channel(run_id), persist=self._record)

    def _channel(self, run_id: str) -> Any:
        from lychd.domain.cortex.events import RunChannel

        channel = self._channels.get(run_id)
        if channel is None:
            channel = RunChannel(run_id=run_id)
            self._channels[run_id] = channel
        return channel

    def _record(self, event: Any) -> None:
        self.events.append((event.run_id, str(event.kind), event.data))

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

    async def add_turn(self, session_id: str, turn: Any) -> None:
        self.added.append((session_id, turn))

    def set_run_status(self, run_id: str, status: str) -> None:
        self.statuses[run_id] = status

    async def get_session(self, session_id: str) -> _FakeSession | None:
        return self.sessions.get(session_id)


@dataclass
class FakeConsents:
    """`ConsentLedgerPort` v2 fake: async park/verdict with a scriptable verdict map."""

    parked: list[dict[str, Any]] = field(default_factory=list)
    verdicts: dict[str, bool | None] = field(default_factory=dict)

    async def park(
        self,
        *,
        run_id: str,
        tool_name: str,
        tool_call_id: str,
        call_ids: tuple[str, ...],
        args: dict[str, Any],
        sigil: Any,
    ) -> ConsentDecision:
        _ = sigil
        consent_id = f"consent_{len(self.parked)}"
        self.parked.append(
            {
                "id": consent_id,
                "run_id": run_id,
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "call_ids": call_ids,
                "args": args,
            }
        )
        return ConsentDecision(status="pending", consent_id=consent_id)

    async def verdict(self, consent_id: str) -> bool | None:
        return self.verdicts.get(consent_id)


class FakeRegistry:
    """Minimal registry for a real `ContextOrchestrator` (no warm capabilities)."""

    def list_capability_states(self) -> list[Any]:
        return []
