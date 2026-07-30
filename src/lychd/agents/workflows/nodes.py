"""Shared workflow-node helpers: the streaming pump + the consent park (C3).

`pump_agent_events` streams one agent run (token deltas → `emit.token`, RAW; the
client renders as text), captures the typed output, and returns the JSONABLE message
history. `park_on_consent` serializes the current logical turn into graph STATE and writes the
consent record — but does NOT emit (S4: the `CONSENT` event moves to `perform_run`,
fired only AFTER `set_status(AWAITING_CONSENT)`).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

from pydantic import BaseModel, ConfigDict
from pydantic_ai import RunContext
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
)
from pydantic_ai.run import AgentRunResultEvent
from pydantic_ai.toolsets import CombinedToolset, ToolsetTool, WrapperToolset
from pydantic_ai.usage import UsageLimits

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
CONSENT_EFFECT_ID_KEY: Final[str] = "lychd_effect_id"
CONSENT_EFFECT_REVISION_KEY: Final[str] = "lychd_effect_revision"


@dataclass(frozen=True, slots=True)
class PumpResult[OutputT]:
    """One agent hop split into resumable history and its new durable suffix."""

    output: OutputT
    all_messages: list[Any]
    new_messages: list[Any]


class ConsentToolBinding(BaseModel):
    """Durable binding for the effect revision and tool definition shown for consent."""

    model_config = ConfigDict(frozen=True)

    capability_key: str
    toolset_id: str
    toolset_type: str
    tool_name: str
    effect_id: str
    effect_revision: str
    definition_digest: str


class ConsentToolBindingChangedError(RuntimeError):
    """The currently granted tool no longer matches the effect shown for consent."""


@dataclass
class _ConsentBindingToolset(WrapperToolset[Any]):
    """Capture and verify prepared approval definitions before tool dispatch."""

    capability_key: str
    expected: ConsentToolBinding | None = None
    captured: dict[str, ConsentToolBinding] = field(default_factory=dict)

    async def get_tools(self, ctx: RunContext[Any]) -> dict[str, ToolsetTool[Any]]:
        tools = await super().get_tools(ctx)
        current = {
            name: binding
            for name, tool in tools.items()
            if tool.tool_def.kind == "unapproved" and (binding := _tool_binding(self.capability_key, tool)) is not None
        }
        if self.expected is not None:
            actual = current.get(self.expected.tool_name)
            if actual != self.expected:
                msg = f"approved tool binding changed for '{self.expected.tool_name}'"
                raise ConsentToolBindingChangedError(msg)
        self.captured.update(current)
        return tools

    def binding_for(self, tool_name: str) -> ConsentToolBinding | None:
        """Return the captured binding for one approval-required tool."""
        return self.captured.get(tool_name)


__all__ = [
    "CONSENT_EFFECT_ID_KEY",
    "CONSENT_EFFECT_REVISION_KEY",
    "MAX_CONSENT_ROUNDS",
    "ConsentToolBinding",
    "ConsentToolBindingChangedError",
    "PumpResult",
    "bind_consent_toolsets",
    "is_single_approval",
    "new_step_id",
    "park_on_consent",
    "pump_agent_events",
]


def _tool_binding(capability_key: str, tool: ToolsetTool[Any]) -> ConsentToolBinding | None:
    """Build a restart-stable binding from project-owned and Pydantic AI identities."""
    toolset_id = tool.toolset.id
    if toolset_id is None:
        return None
    toolset_type = f"{type(tool.toolset).__module__}.{type(tool.toolset).__qualname__}"
    tool_def = tool.tool_def
    metadata = tool_def.metadata
    if not isinstance(metadata, dict):
        return None
    effect_id = metadata.get(CONSENT_EFFECT_ID_KEY)
    effect_revision = metadata.get(CONSENT_EFFECT_REVISION_KEY)
    if (
        not isinstance(effect_id, str)
        or not effect_id.strip()
        or not isinstance(effect_revision, str)
        or not effect_revision.strip()
    ):
        return None
    definition = {
        "description": tool_def.description,
        "kind": tool_def.kind,
        "metadata": metadata,
        "name": tool_def.name,
        "parameters_json_schema": tool_def.parameters_json_schema,
        "sequential": tool_def.sequential,
        "strict": tool_def.strict,
    }
    try:
        encoded = json.dumps(definition, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    except (TypeError, ValueError):
        return None
    return ConsentToolBinding(
        capability_key=capability_key,
        toolset_id=toolset_id,
        toolset_type=toolset_type,
        tool_name=tool_def.name,
        effect_id=effect_id,
        effect_revision=effect_revision,
        definition_digest=hashlib.sha256(encoded).hexdigest(),
    )


def bind_consent_toolsets(
    toolsets: Sequence[Any],
    *,
    capability_key: str,
    expected: ConsentToolBinding | None = None,
    require_expected: bool = False,
) -> _ConsentBindingToolset:
    """Wrap one grant's toolsets so approval identity is captured and fail-closed."""
    if require_expected and expected is None:
        msg = "parked approval has no durable tool binding"
        raise ConsentToolBindingChangedError(msg)
    if expected is not None and expected.capability_key != capability_key:
        msg = f"approved capability changed from '{expected.capability_key}' to '{capability_key}'"
        raise ConsentToolBindingChangedError(msg)
    return _ConsentBindingToolset(
        wrapped=CombinedToolset(toolsets),
        capability_key=capability_key,
        expected=expected,
    )


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


async def pump_agent_events[OutputT](
    agent: Agent[Any, OutputT],
    prompt: str | None,
    *,
    deps: LychDDeps,
    model: Any,
    model_settings: Any,
    toolsets: Sequence[Any],
    emit: RunEmitter,
    message_history: list[Any] | None = None,
    deferred_tool_results: Any = None,
    usage_limits: UsageLimits | None = None,
) -> PumpResult[OutputT]:
    """Stream one agent run and return typed output plus serialized message scopes.

    Token deltas are emitted raw (`emit.token`); clients must render them as text.
    """
    result_event: AgentRunResultEvent[OutputT] | None = None
    async for event in agent.run_stream_events(
        prompt,
        deps=deps,
        model=model,
        model_settings=model_settings,
        toolsets=list(toolsets),
        message_history=message_history,
        deferred_tool_results=deferred_tool_results,
        usage_limits=usage_limits,
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
    return PumpResult(
        output=result.output,
        all_messages=list(ModelMessagesTypeAdapter.dump_python(result.all_messages(), mode="json")),
        new_messages=list(ModelMessagesTypeAdapter.dump_python(result.new_messages(), mode="json")),
    )


async def park_on_consent(
    ctx: GraphRunContext[BridgeChatState, WorkflowServices],
    requests: DeferredToolRequests,
    messages: list[Any],
    binding: ConsentToolBinding,
) -> ConsentDecision:
    """C3 step-2 park: serialize the pause into STATE and write the consent record.

    `messages` is only the indivisible current LychD turn suffix. Settled history is
    re-bounded under the grant acquired on resume, then prepended to this chain.
    S4: writes the row but does NOT emit — the `CONSENT` event fires in `perform_run`
    after `set_status(AWAITING_CONSENT)`, so a fast verdict can never beat the guard.
    """
    calls = requests.approvals
    first = calls[0]
    ctx.state.paused_messages = messages
    ctx.state.pending_call_ids = tuple(c.tool_call_id for c in calls)
    ctx.state.pending_consent_tool_name = first.tool_name
    ctx.state.pending_consent_tool_binding = binding
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
