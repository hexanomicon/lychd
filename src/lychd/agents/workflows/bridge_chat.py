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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from pydantic_ai import DeferredToolRequests, DeferredToolResults
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from lychd.agents.deps import LychDDeps
from lychd.agents.outputs import Bottleneck, BridgeReply, FragmentCall
from lychd.agents.services import WorkflowServices, default_sigil
from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC
from lychd.agents.workflows.base import Gate, Trigger, Workflow
from lychd.agents.workflows.nodes import MAX_CONSENT_ROUNDS, new_step_id, park_on_consent, pump_agent_events
from lychd.domain.cortex.runs import ConsentPending

if TYPE_CHECKING:
    from lychd.agents.router import Intent
    from lychd.agents.services import TurnLedgerPort
    from lychd.domain.web.fragments import ValidatedFragment

# Re-exported for backward-compatible imports (domain/web/fragments,
# interface/web/bridge) without re-introducing the old import cycle.
__all__ = [
    "BRIDGE_CHAT",
    "BRIDGE_CHAT_GRAPH",
    "AwaitConsent",
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
    priority: int = 50
    history: list[dict[str, str]] = Field(default_factory=list)
    prefix_digest: str | None = None
    reply: BridgeReply | None = None
    pending_consent_id: str | None = None
    bottleneck: Bottleneck | None = None
    # Consent park state (4C-2 contract; wired in 4C-4). `paused_messages` is stored
    # JSONABLE (`to_jsonable_python(result.all_messages())`) so every snapshot — durable
    # file included — round-trips with no custom serializers. NEVER store DeferredToolRequests.
    paused_messages: list[Any] | None = None
    pending_call_ids: tuple[str, ...] = ()
    pending_consent_tool_name: str | None = None  # S4: remembered so perform_run emits without a codex read
    consent_rounds: int = 0  # bounded by MAX_CONSENT_ROUNDS


# ---------------------------------------------------------------------------
# Node helpers (pure; every collaborator is an explicit argument)
# ---------------------------------------------------------------------------


def build_user_prompt(state: BridgeChatState) -> str:
    """Return the query as the user prompt; the woven floor rides in `instructions`."""
    return state.prompt


async def _session_history(session_id: str, turns: TurnLedgerPort) -> list[dict[str, str]]:
    session = await turns.get_session(session_id)
    if session is None:
        return []
    return [{"role": turn.role, "content": turn.content} for turn in session.turns]


def _fallback_reply(state: BridgeChatState) -> BridgeReply:
    """Honest non-completion prose when a bottleneck settled the turn without a reply."""
    if state.bottleneck is not None:
        return BridgeReply(answer=f"The turn settled without the action: {state.bottleneck.detail}")
    return BridgeReply(answer="The turn settled without a reply.")


async def settle_turn(
    state: BridgeChatState,
    reply: BridgeReply,
    validated: list[ValidatedFragment],
    *,
    turns: TurnLedgerPort,
    context: Any,
) -> None:
    """Write the settled agent turn to the turn ledger and release the context floor."""
    from lychd.domain.web.schemas import BridgeTurn

    await turns.add_turn(
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
            history=await _session_history(ctx.state.session_id, ctx.deps.turns),
        )
        ctx.state.prefix_digest = assembled.prefix_digest
        ctx.state.history = assembled.state_window
        return Converse()


@dataclass
class Converse(BaseNode[BridgeChatState, WorkflowServices]):
    """The thinking station. The grant is acquired HERE — the per-step lease."""

    async def run(self, ctx: GraphRunContext[BridgeChatState, WorkflowServices]) -> ProjectReply | AwaitConsent:
        """Lease the grant (per-step), stream The First One, capture reply or park.

        The pump runs INSIDE the lease CM; `park_on_consent` runs AFTER the CM exits,
        so the lease is released before the park is recorded (no-lease-across-park at
        the Converse hop too). A ``HardwareTransitionRequired`` raised by the decision
        table propagates BEFORE lease acquisition by construction (Live Stasis).
        """
        emit = ctx.deps.events.emitter(ctx.state.run_id)
        async with ctx.deps.dispatcher.lease_grant(
            family="chat",
            run_id=ctx.state.run_id,
            priority=ctx.state.priority,
        ) as grant:
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
            output, messages = await pump_agent_events(
                agent,
                build_user_prompt(ctx.state),
                deps=deps,
                model=grant.model,
                model_settings=grant.model_settings(),
                toolsets=list(grant.toolsets),
                emit=emit,
            )
        if isinstance(output, DeferredToolRequests):
            await park_on_consent(ctx, output, messages)  # S4: records the row; does NOT emit
            return AwaitConsent()
        ctx.state.reply = output if isinstance(output, BridgeReply) else None
        return ProjectReply()


@dataclass
class AwaitConsent(Gate, BaseNode[BridgeChatState, WorkflowServices]):
    """The Seat of Consent: check the verdict; park (raise) if pending, else resume.

    A `Gate` — its presence assigns bridge_chat the Durable Stasis tier. The verdict
    check PRECEDES grant acquisition (no lease across the park, S6).
    """

    async def run(self, ctx: GraphRunContext[BridgeChatState, WorkflowServices]) -> ProjectReply | AwaitConsent:
        """Read the verdict; suspend on pending; else resume the deferred tool run."""
        consent_id = ctx.state.pending_consent_id
        if consent_id is None:  # defensive: a Gate entered without a park is a bug
            ctx.state.bottleneck = Bottleneck(kind="policy_block", detail="gate reached without a parked consent")
            return ProjectReply()
        verdict = await ctx.deps.consents.verdict(consent_id)
        if verdict is None:  # THE park signal — the run suspends, it does not fail
            raise ConsentPending(consent_id, ctx.state.run_id, ctx.state.pending_consent_tool_name or "")

        # Parked-context guard (design risk 7): a durable resume lost the in-memory floor.
        if ctx.deps.context.get(ctx.state.run_id) is None:
            ctx.deps.context.assemble(
                run_id=ctx.state.run_id,
                session_id=ctx.state.session_id,
                query=ctx.state.prompt,
                history=ctx.state.history,
            )
        results = DeferredToolResults(approvals=dict.fromkeys(ctx.state.pending_call_ids, verdict))
        history = ModelMessagesTypeAdapter.validate_python(ctx.state.paused_messages)
        emit = ctx.deps.events.emitter(ctx.state.run_id)
        async with ctx.deps.dispatcher.lease_grant(
            family="chat",
            run_id=ctx.state.run_id,
            priority=ctx.state.priority,
        ) as grant:
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
            output, messages = await pump_agent_events(
                agent,
                None,
                deps=deps,
                model=grant.model,
                model_settings=grant.model_settings(),
                toolsets=list(grant.toolsets),
                emit=emit,
                message_history=history,
                deferred_tool_results=results,
            )
        ctx.state.pending_consent_id = None
        ctx.state.paused_messages = None
        ctx.state.pending_call_ids = ()
        ctx.state.pending_consent_tool_name = None
        if isinstance(output, DeferredToolRequests):  # the tool chained another approval
            ctx.state.consent_rounds += 1
            if ctx.state.consent_rounds >= MAX_CONSENT_ROUNDS:
                ctx.state.bottleneck = Bottleneck(kind="policy_block", detail="consent round limit reached")
                return ProjectReply()
            await park_on_consent(ctx, output, messages)
            return AwaitConsent()  # self-edge
        ctx.state.reply = output if isinstance(output, BridgeReply) else None
        return ProjectReply()


@dataclass
class ProjectReply(BaseNode[BridgeChatState, WorkflowServices, BridgeReply]):
    """Validate FragmentCalls against the Vessel-owned registry, settle the turn."""

    async def run(self, ctx: GraphRunContext[BridgeChatState, WorkflowServices]) -> End[BridgeReply]:
        """Validate fragments and settle. Reached only with a settled reply OR a bottleneck.

        A park now leaves the graph via `ConsentPending` raised out of `AwaitConsent`
        and NEVER reaches here. Run status is the ledger's — never written here.
        """
        emit = ctx.deps.events.emitter(ctx.state.run_id)
        emit.status("settling")
        reply = ctx.state.reply or _fallback_reply(ctx.state)
        validated = ctx.deps.fragments.validate_calls(reply.fragments)
        for fragment in validated:
            emit.fragment(fragment.key, fragment.params.model_dump(mode="json"))
        await settle_turn(ctx.state, reply, validated, turns=ctx.deps.turns, context=ctx.deps.context)
        return End(reply)


# ---------------------------------------------------------------------------
# The workflow
# ---------------------------------------------------------------------------

BRIDGE_CHAT_GRAPH: Graph[BridgeChatState, WorkflowServices, BridgeReply] = Graph(
    nodes=(WeaveContext, Converse, AwaitConsent, ProjectReply),
    name="bridge_chat",
)


def _make_state(intent: Intent) -> BridgeChatState:
    # S3: `perform_run` rebuilds the intent from the run row via `RunRecord.to_intent`,
    # so `intent.run_id` here is always the canonical ledger id; the `or ""` only
    # satisfies the type for the advisory-None client-correlation shape.
    # C6: per-run data (priority) lives in graph State, never deps.
    return BridgeChatState(
        session_id=intent.session_id,
        run_id=intent.run_id or "",
        prompt=intent.prompt,
        priority=intent.priority if intent.priority is not None else 50,
    )


BRIDGE_CHAT = Workflow(
    name="bridge_chat",
    title="Bridge Chat",
    description="Converse with The First One over the woven Stable Floor.",
    trigger=Trigger(hint="default — any Bridge prompt", match=lambda intent: intent.source == "bridge"),
    graph=BRIDGE_CHAT_GRAPH,
    start_node=WeaveContext,
    make_state=_make_state,
)
