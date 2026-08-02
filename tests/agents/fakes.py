"""In-process fakes for the offline agent/graph suite (A5 §10).

Each fake is a thin, dict/list-backed stand-in for a `WorkflowServices` port.
None of them touches the network or a model — the whole suite runs with
`ALLOW_MODEL_REQUESTS = False` (see `conftest.py`).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from pydantic_ai import RunContext

from lychd.agents.deps import LychDDeps
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.codex.schemas import ConsentDecision
from lychd.domain.cortex.events import RunChannel, RunChannelSnapshot, RunEmitter, RunEvent
from lychd.domain.orchestration.schema import TransitionPlan

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lychd.domain.animation.capabilities import CapabilityGrant, CapabilityState
    from lychd.domain.animation.schemas.capability_family import CapabilityFamily
    from lychd.domain.cortex.priority import Priority


@dataclass
class FakeGrant:
    """A minimal `CapabilityGrant` stand-in: nodes only read `model`/`toolsets`."""

    model: Any
    toolsets: tuple[Any, ...] = ()
    settings: Any = None
    key: str = "chat:test"
    spec: Any = field(
        default_factory=lambda: SimpleNamespace(
            key="chat:test",
            animator_name="test-animator",
            family=SimpleNamespace(value="chat"),
            model_id="test-model",
            max_context=4096,
        )
    )
    state: Any = field(default_factory=lambda: SimpleNamespace(phase=SimpleNamespace(value="warm")))
    generation: Any = field(default_factory=lambda: SimpleNamespace(max_context=8192, max_tokens=512))
    lease: Any = field(default_factory=lambda: SimpleNamespace(grant_id="grant-test"))

    def model_settings(self) -> Any:
        """Return the recordable model_settings sentinel (None unless one was injected)."""
        return self.settings


@dataclass
class FakeDispatcher:
    """`GrantPort` fake: leases a grant carrying the injected TestModel (C1 CM shape)."""

    model: Any
    toolsets: tuple[Any, ...] = ()
    settings: Any = None
    key: str = "chat:test"
    calls: list[str] = field(default_factory=list)
    requires_tools_calls: list[bool] = field(default_factory=list)

    @asynccontextmanager
    async def lease_grant(
        self,
        *,
        family: CapabilityFamily | str,
        model_name: str | None = None,
        run_id: str,
        priority: int = 50,
        require_modalities: tuple[str, ...] = (),
        requires_tools: bool = False,
    ) -> AsyncIterator[CapabilityGrant]:
        _ = (model_name, run_id, priority, require_modalities)
        self.calls.append(str(family))
        self.requires_tools_calls.append(requires_tools)
        # The graph deliberately consumes only the grant surface represented by
        # ``FakeGrant``.  The cast keeps that test double honest at the concrete
        # production seam without constructing live animator/model handles.
        yield cast(
            "CapabilityGrant",
            FakeGrant(model=self.model, toolsets=self.toolsets, settings=self.settings, key=self.key),
        )


@dataclass
class FakeOrchestrator:
    """`TransitionPort` fake: records calculate/request calls for assertions."""

    calls: list[tuple[str, ...]] = field(default_factory=list)

    async def calculate_transition_plan(self, target_capability_key: str) -> TransitionPlan:
        self.calls.append(("calculate", target_capability_key))
        return TransitionPlan(
            total_metabolic_cost=0.0,
            evict_coven_ids=[],
            launch_coven_ids=[],
            action_type="NO_OP",
        )

    async def request_transition(self, target_capability_key: str, priority: Priority) -> TransitionPlan:
        self.calls.append(("request", target_capability_key, str(priority)))
        return TransitionPlan(
            total_metabolic_cost=0.0,
            evict_coven_ids=[],
            launch_coven_ids=[],
            action_type="NO_OP",
        )


@dataclass
class FakeEvents:
    """`RunEventBus` fake: real `RunEmitter`/`RunChannel`, recording a flat event list.

    Exercises the real event plane (the emitter pushes to a real `RunChannel`) while
    teeing every event into `events` as `(run_id, kind, data)` tuples for assertions.
    """

    events: list[tuple[str, str, str]] = field(default_factory=list)
    _channels: dict[str, RunChannel] = field(default_factory=dict)

    def open(self, run_id: str, *, from_seq: int | None = None) -> RunChannel:
        """Return the run channel, seeding a newly restored stream when requested."""
        channel = self._channels.get(run_id)
        if channel is None:
            channel = RunChannel(run_id=run_id, _seq=from_seq or 0)
            self._channels[run_id] = channel
        return channel

    def emitter(self, run_id: str) -> RunEmitter:
        return RunEmitter(channel=self.open(run_id), persist=self._record)

    def subscribe(self, run_id: str, *, from_seq: int | None = None) -> AsyncIterator[RunEvent]:
        return self.open(run_id).subscribe(from_seq)

    def snapshot(self, run_id: str) -> RunChannelSnapshot | None:
        channel = self._channels.get(run_id)
        return channel.snapshot() if channel is not None else None

    def close(self, run_id: str) -> None:
        channel = self._channels.pop(run_id, None)
        if channel is not None:
            channel.mark_closed()

    async def wait_persisted(self, run_id: str) -> None:
        """The recording fake persists synchronously in ``_record``."""
        _ = run_id

    def _record(self, event: RunEvent) -> None:
        self.events.append((event.run_id, str(event.kind), event.data))

    def kinds(self) -> list[str]:
        return [kind for _, kind, _ in self.events]


@dataclass
class _FakeSession:
    turns: list[Any] = field(default_factory=list)
    message_history: list[Any] = field(default_factory=list)


@dataclass
class FakeTurns:
    """`TurnLedgerPort` fake: records added turns, run statuses, and known sessions."""

    added: list[tuple[str, Any]] = field(default_factory=list)
    statuses: dict[str, str] = field(default_factory=dict)
    sessions: dict[str, _FakeSession] = field(default_factory=dict)

    def seed_session(
        self,
        session_id: str,
        *,
        turns: list[Any],
        message_history: list[Any],
    ) -> None:
        self.sessions[session_id] = _FakeSession(
            turns=list(turns),
            message_history=list(message_history),
        )

    async def add_turn(self, session_id: str, turn: Any) -> None:
        self.added.append((session_id, turn))
        self.sessions.setdefault(session_id, _FakeSession()).turns.append(turn)

    async def settle_agent_turn(
        self,
        session_id: str,
        turn: Any,
        *,
        new_messages: list[Any],
    ) -> None:
        self.added.append((session_id, turn))
        session = self.sessions.setdefault(session_id, _FakeSession())
        session.turns.append(turn)
        session.message_history.extend(new_messages)

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


class FakeRegistry(AnimatorRegistry):
    """Minimal registry for a real `ContextOrchestrator` (no warm capabilities)."""

    def __init__(self) -> None:
        """Bypass the production registry's runtime-adapter construction."""

    def list_capability_states(self) -> list[CapabilityState]:
        return []


def approval_test_toolset() -> Any:
    """Return the test-only approval tool used to exercise generic consent resume.

    Production's minimal First One deliberately has no coven transition tool.  The
    consent substrate still needs an approval-required function in offline tests, so
    it is injected through the fake capability grant instead of the agent spec.
    """
    from pydantic_ai.toolsets import FunctionToolset

    from lychd.agents.workflows.nodes import CONSENT_EFFECT_ID_KEY, CONSENT_EFFECT_REVISION_KEY

    async def request_coven_swap(ctx: RunContext[LychDDeps], capability_key: str, reason: str) -> str:
        plan = await ctx.deps.orchestrator.request_transition(capability_key, priority=ctx.deps.priority)
        return (
            f"transition to {capability_key} executed "
            f"(action {plan.action_type}, cost {plan.total_metabolic_cost}); reason: {reason}"
        )

    toolset: FunctionToolset[LychDDeps] = FunctionToolset(id="test-coven-transition")
    toolset.add_function(
        request_coven_swap,
        requires_approval=True,
        metadata={
            CONSENT_EFFECT_ID_KEY: "coven.transition",
            CONSENT_EFFECT_REVISION_KEY: "test-v1",
        },
    )
    return toolset
