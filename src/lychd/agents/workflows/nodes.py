"""Shared workflow-node helpers: the streaming pump + the consent park (C3).

`pump_agent_events` streams one agent run (token deltas → `emit.token`, RAW; the
Projector escapes), captures the typed output, and returns the JSONABLE message
history. `park_on_consent` serializes the pause into graph STATE and writes the
consent record — but does NOT emit (S4: the `CONSENT` event moves to `perform_run`,
fired only AFTER `set_status(AWAITING_CONSENT)`).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Final

from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPart, TextPartDelta
from pydantic_ai.run import AgentRunResultEvent
from pydantic_core import to_jsonable_python

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic_ai import Agent, DeferredToolRequests
    from pydantic_graph import GraphRunContext

    from lychd.agents.deps import LychDDeps
    from lychd.agents.services import WorkflowServices
    from lychd.agents.workflows.bridge_chat import BridgeChatState
    from lychd.domain.codex.schemas import ConsentDecision
    from lychd.domain.cortex.events import RunEmitter

MAX_CONSENT_ROUNDS: Final[int] = 3

__all__ = [
    "MAX_CONSENT_ROUNDS",
    "is_single_approval",
    "new_step_id",
    "park_on_consent",
    "pump_agent_events",
]


def new_step_id() -> str:
    """Return a fresh per-step id."""
    return f"step_{uuid.uuid4().hex[:12]}"


def is_single_approval(requests: DeferredToolRequests) -> bool:
    """Whether a park is honestly representable today: exactly one approval, no external calls.

    One consent record = one card = one tri-state verdict. pydantic-ai requires a
    result for EVERY deferred call on resume, so a turn that raises >1 approval (or any
    external deferred `call`) cannot be resolved from a single card without silently
    applying one seen verdict to unseen calls (finding 5). Until per-call cards land,
    the caller degrades such a turn to a bottleneck instead of parking it. Today only
    `coven` is approval-gated, so a well-behaved turn always yields exactly one.
    """
    return len(requests.approvals) == 1 and not requests.calls


async def pump_agent_events(
    agent: Agent[Any, Any],
    prompt: str | None,
    *,
    deps: LychDDeps,
    model: Any,
    model_settings: Any,
    toolsets: Sequence[Any],
    emit: RunEmitter,
    message_history: list[Any] | None = None,
    deferred_tool_results: Any = None,
) -> tuple[Any, list[Any]]:
    """Stream one agent run; return (typed output, jsonable all_messages()).

    Token deltas are emitted RAW (`emit.token`); the Projector is the sole escaper.
    """
    result_event: AgentRunResultEvent[Any] | None = None
    async for event in agent.run_stream_events(
        prompt,
        deps=deps,
        model=model,
        model_settings=model_settings,
        toolsets=list(toolsets),
        message_history=message_history,
        deferred_tool_results=deferred_tool_results,
    ):
        if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
            emit.token(event.delta.content_delta)
        elif isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
            emit.token(event.part.content)
        elif isinstance(event, AgentRunResultEvent):
            result_event = event
    if result_event is None:
        msg = "agent run produced no result event"
        raise RuntimeError(msg)
    result = result_event.result
    return result.output, to_jsonable_python(result.all_messages())


async def park_on_consent(
    ctx: GraphRunContext[BridgeChatState, WorkflowServices],
    requests: DeferredToolRequests,
    messages: list[Any],
) -> ConsentDecision:
    """C3 step-2 park: serialize the pause into STATE and write the consent record.

    S4: writes the row but does NOT emit — the `CONSENT` event fires in `perform_run`
    after `set_status(AWAITING_CONSENT)`, so a fast verdict can never beat the guard.
    """
    calls = requests.approvals
    first = calls[0]
    ctx.state.paused_messages = messages
    ctx.state.pending_call_ids = tuple(c.tool_call_id for c in calls)
    ctx.state.pending_consent_tool_name = first.tool_name
    decision = await ctx.deps.consents.park(
        run_id=ctx.state.run_id,
        tool_name=first.tool_name,
        tool_call_id=first.tool_call_id,
        call_ids=ctx.state.pending_call_ids,
        args=first.args_as_dict(),
        sigil=ctx.deps.sigil_provider(),
    )
    ctx.state.pending_consent_id = decision.consent_id
    return decision
