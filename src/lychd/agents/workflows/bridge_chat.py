"""The `bridge_chat` workflow: WeaveContext -> Converse -> ProjectReply (A5 §5).

Three stations over the woven Stable Floor. The grant is acquired inside
`Converse` (the per-step lease); a `HardwareTransitionRequired` raised there
propagates out of `graph.iter()` for `GraphRunner` to catch and resolve — that is
Live Stasis, and no node handles hardware.

No module-level mutable state: every collaborator is read from `ctx.deps`
(a `WorkflowServices`), threaded in as `graph.iter(..., deps=services)`. The
typed outputs (`BridgeReply`, `FragmentCall`, `Bottleneck`) live in
`lychd.agents.outputs` and are re-exported here for backward-compatible imports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPart, TextPartDelta
from pydantic_ai.run import AgentRunResultEvent
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from lychd.agents.deps import LychDDeps
from lychd.agents.outputs import Bottleneck, BridgeReply, FragmentCall
from lychd.agents.services import WorkflowServices, default_sigil
from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC
from lychd.agents.workflows.base import Trigger, Workflow

if TYPE_CHECKING:
    from lychd.agents.router import Intent
    from lychd.agents.services import ConsentLedgerPort, TurnLedgerPort
    from lychd.domain.web.fragments import ValidatedFragment

# Re-exported for backward-compatible imports (domain/web/fragments,
# interface/web/bridge) without re-introducing the old import cycle.
__all__ = [
    "BRIDGE_CHAT",
    "BRIDGE_CHAT_GRAPH",
    "Bottleneck",
    "BridgeChatState",
    "BridgeReply",
    "Converse",
    "FragmentCall",
    "ProjectReply",
    "WeaveContext",
    "default_sigil",
]


# ---------------------------------------------------------------------------
# Typed state (workflow-private; outputs live in lychd.agents.outputs)
# ---------------------------------------------------------------------------


class BridgeChatState(BaseModel):
    """Rolling state for one Bridge turn (GraphRunner binds `StateT: BaseModel`)."""

    session_id: str
    run_id: str
    prompt: str
    history: list[dict[str, str]] = Field(default_factory=list)
    prefix_digest: str | None = None
    reply: BridgeReply | None = None
    pending_consent_id: str | None = None
    bottleneck: Bottleneck | None = None


# ---------------------------------------------------------------------------
# Node helpers (pure; every collaborator is an explicit argument)
# ---------------------------------------------------------------------------


def new_step_id() -> str:
    """Return a fresh per-step id."""
    return f"step_{uuid.uuid4().hex[:12]}"


def build_user_prompt(state: BridgeChatState) -> str:
    """Return the query as the user prompt; the woven floor rides in `instructions`."""
    return state.prompt


def _session_history(session_id: str, turns: TurnLedgerPort) -> list[dict[str, str]]:
    session = turns.get_session(session_id)
    if session is None:
        return []
    return [{"role": turn.role, "content": turn.content} for turn in session.turns]


def consent_placeholder() -> BridgeReply:
    """Return the placeholder reply for a turn that parked on consent."""
    return BridgeReply(answer="Consent sought — the Magus must decide before I may proceed.")


def park_consent(state: BridgeChatState, requests: DeferredToolRequests, consents: ConsentLedgerPort) -> str:
    """Park the first approval-required tool call and return its consent id."""
    call = requests.approvals[0]
    return consents.park_consent(
        run_id=state.run_id,
        session_id=state.session_id,
        tool_name=call.tool_name,
        args=call.args_as_dict(),
        requests=requests,
    )


def settle_turn(
    state: BridgeChatState,
    reply: BridgeReply,
    validated: list[ValidatedFragment],
    *,
    turns: TurnLedgerPort,
    context: Any,
) -> None:
    """Write the settled agent turn to the turn ledger and release the context floor."""
    from lychd.domain.web.schemas import BridgeTurn

    turns.add_turn(
        state.session_id,
        BridgeTurn(
            role="agent",
            content=reply.answer,
            run_id=state.run_id,
            state="settled",
            fragments=tuple(fragment.key for fragment in validated),
        ),
    )
    context.release(state.run_id)


# ---------------------------------------------------------------------------
# The graph nodes
# ---------------------------------------------------------------------------


@dataclass
class WeaveContext(BaseNode[BridgeChatState, WorkflowServices]):
    """The Archivist step: assemble the keyed-block Stable Floor (ADR 28 §2, ADR 21)."""

    async def run(self, ctx: GraphRunContext[BridgeChatState, WorkflowServices]) -> Converse:
        """Assemble the floor, stamp the prefix digest, and hand off to Converse."""
        emit = ctx.deps.events.emitter(ctx.state.run_id)
        emit.status("weaving")
        assembled = ctx.deps.context.assemble(
            run_id=ctx.state.run_id,
            session_id=ctx.state.session_id,
            query=ctx.state.prompt,
            history=_session_history(ctx.state.session_id, ctx.deps.turns),
        )
        ctx.state.prefix_digest = assembled.prefix_digest
        ctx.state.history = assembled.state_window
        return Converse()


@dataclass
class Converse(BaseNode[BridgeChatState, WorkflowServices]):
    """The thinking station. The grant is acquired HERE — the per-step lease."""

    async def run(self, ctx: GraphRunContext[BridgeChatState, WorkflowServices]) -> ProjectReply:
        """Resolve the grant, stream The First One, and capture reply or consent."""
        emit = ctx.deps.events.emitter(ctx.state.run_id)
        grant = ctx.deps.dispatcher.resolve_capability_grant("chat")
        agent = ctx.deps.forge.agent_for(THE_FIRST_ONE_SPEC)
        deps = LychDDeps(
            sigil=ctx.deps.sigil_provider(),
            grant=grant,
            dispatcher=ctx.deps.dispatcher,
            orchestrator=ctx.deps.orchestrator,
            context=ctx.deps.context,
            run_id=ctx.state.run_id,
            step_id=new_step_id(),
        )
        emit.status("thinking")

        result_event: AgentRunResultEvent[Any] | None = None
        async for event in agent.run_stream_events(
            build_user_prompt(ctx.state),
            deps=deps,
            model=grant.model,
            toolsets=list(grant.toolsets),
        ):
            if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                emit.token(event.delta.content_delta)
            elif isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
                emit.token(event.part.content)
            elif isinstance(event, AgentRunResultEvent):
                result_event = event

        output = result_event.result.output if result_event is not None else None
        if isinstance(output, DeferredToolRequests):
            ctx.state.pending_consent_id = park_consent(ctx.state, output, ctx.deps.consents)
            tool_name = output.approvals[0].tool_name if output.approvals else ""
            emit.consent(ctx.state.pending_consent_id, tool_name=tool_name)
        elif isinstance(output, BridgeReply):
            ctx.state.reply = output
        return ProjectReply()


@dataclass
class ProjectReply(BaseNode[BridgeChatState, WorkflowServices, BridgeReply]):
    """Validate FragmentCalls against the Vessel-owned registry, settle the turn."""

    async def run(self, ctx: GraphRunContext[BridgeChatState, WorkflowServices]) -> End[BridgeReply]:
        """Validate fragments and settle — unless a consent parked the turn.

        When a consent is parked the run does NOT settle or emit ``done``: the live
        consent card must stay actionable in the streaming slot (a ``done`` event
        OOB-replaces the whole slot and would destroy the card). The ghoul
        (`perform_run`) sees the parked consent and ends the run AWAITING_CONSENT,
        emitting no ``DONE``. Run status is the ledger's — never written here.
        Honest deferred-tool resume is a later wave (spec-00-FINAL C3).
        """
        if ctx.state.pending_consent_id is not None:
            return End(consent_placeholder())
        emit = ctx.deps.events.emitter(ctx.state.run_id)
        emit.status("settling")
        reply = ctx.state.reply or consent_placeholder()
        validated = ctx.deps.fragments.validate_calls(reply.fragments)
        for fragment in validated:
            emit.fragment(fragment.key, fragment.params.model_dump(mode="json"))
        settle_turn(ctx.state, reply, validated, turns=ctx.deps.turns, context=ctx.deps.context)
        return End(reply)


# ---------------------------------------------------------------------------
# The workflow
# ---------------------------------------------------------------------------

BRIDGE_CHAT_GRAPH: Graph[BridgeChatState, WorkflowServices, BridgeReply] = Graph(
    nodes=(WeaveContext, Converse, ProjectReply),
    name="bridge_chat",
)


def _make_state(intent: Intent) -> BridgeChatState:
    # S3: `perform_run` rebuilds the intent from the run row via `RunRecord.to_intent`,
    # so `intent.run_id` here is always the canonical ledger id; the `or ""` only
    # satisfies the type for the advisory-None client-correlation shape.
    return BridgeChatState(session_id=intent.session_id, run_id=intent.run_id or "", prompt=intent.prompt)


BRIDGE_CHAT = Workflow(
    name="bridge_chat",
    title="Bridge Chat",
    description="Converse with The First One over the woven Stable Floor.",
    trigger=Trigger(hint="default — any Bridge prompt", match=lambda intent: intent.source == "bridge"),
    graph=BRIDGE_CHAT_GRAPH,
    start_node=WeaveContext,
    make_state=_make_state,
)
