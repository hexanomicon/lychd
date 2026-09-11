"""Bridge chat: assemble context, converse, optionally await consent, settle reply.

Nodes read collaborators from ``ctx.deps`` and lease capabilities only while using
them. GraphRunner owns hardware waits; AwaitConsent owns the consent continuation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Self, cast
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator
from pydantic_ai import DeferredToolRequests, DeferredToolResults
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
)
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from lychd.agents.context_limits import ContextWindowModel
from lychd.agents.deps import LychDDeps
from lychd.agents.outputs import Bottleneck, BridgeReply
from lychd.agents.services import WorkflowServices
from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC
from lychd.agents.workflows.base import Gate, PatternEdge, PatternManifest, PatternNode, Trigger, Workflow
from lychd.agents.workflows.nodes import (
    MAX_CONSENT_ROUNDS,
    ConsentToolBinding,
    ConsentToolBindingChangedError,
    bind_consent_toolsets,
    bind_messages_to_logical_run,
    is_single_approval,
    park_on_consent,
    pump_agent_events,
)
from lychd.domain.cortex.context import ContextBudgetExceededError
from lychd.domain.cortex.graph import build_serial_graph
from lychd.domain.cortex.graph_runner import HardwareResumeBudget
from lychd.domain.cortex.priority import PRIORITY_DEFAULT
from lychd.domain.cortex.runs import ConsentPending

if TYPE_CHECKING:
    from lychd.agents.router import Intent
    from lychd.agents.services import TurnLedgerPort
    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.web.fragments import FragmentRegistry, ValidatedFragment

__all__ = [
    "BRIDGE_CHAT",
    "BRIDGE_CHAT_BOUND",
    "BRIDGE_CHAT_BOUND_GRAPH",
    "BRIDGE_CHAT_GRAPH",
    "AwaitConsent",
    "BoundBridgeChatState",
    "BridgeChatState",
    "Converse",
    "ProjectReply",
    "WeaveContext",
]


class BridgeChatState(BaseModel):
    """Rolling state for one Bridge turn (GraphRunner binds `StateT: BaseModel`)."""

    session_id: str
    run_id: str
    prompt: str
    priority: int = PRIORITY_DEFAULT
    capability_key: str | None = None
    hardware_resume_budget: HardwareResumeBudget = Field(default_factory=HardwareResumeBudget)
    history: list[Any] = Field(default_factory=list)
    new_messages: list[Any] = Field(default_factory=list)
    reply: BridgeReply | None = None
    pending_consent_id: str | None = None
    bottleneck: Bottleneck | None = None
    # Persist only the current turn's JSON suffix. Re-bound completed history under
    # the new grant on resume; never checkpoint live DeferredToolRequests.
    paused_messages: list[Any] | None = None
    pending_call_ids: tuple[str, ...] = ()
    pending_consent_tool_name: str | None = None  # Lets the worker emit without another consent read.
    pending_consent_tool_binding: ConsentToolBinding | None = None
    consent_rounds: int = 0  # bounded by MAX_CONSENT_ROUNDS


class BoundBridgeChatState(BridgeChatState):
    """Revision 2 requires its admitted binding even when decoding a parked graph."""

    @model_validator(mode="after")
    def require_binding(self) -> Self:
        """Refuse a revision 2 resume that has lost its admitted binding."""
        if self.capability_key is None or not self.capability_key.strip():
            msg = "bridge_chat@2 requires its admitted exact capability key."
            raise ValueError(msg)
        return self


async def _session_history(session_id: str, turns: TurnLedgerPort) -> list[Any]:
    """Return only completed Pydantic AI history, never optimistic display turns."""
    session = await turns.get_session(session_id)
    if session is None:
        return []
    return list(getattr(session, "message_history", []))


def _fallback_reply(state: BridgeChatState) -> BridgeReply:
    """Honest non-completion prose when a bottleneck settled the turn without a reply."""
    if state.bottleneck is not None:
        return BridgeReply(answer=f"The turn settled without the action: {state.bottleneck.detail}")
    return BridgeReply(answer="The turn settled without a reply.")


def _agent_deps(ctx: GraphRunContext[BridgeChatState, WorkflowServices], grant: CapabilityGrant) -> LychDDeps:
    """Bind fresh identity and step correlation inside the current grant's lease."""
    return LychDDeps(
        sigil=ctx.deps.sigil_provider(),
        grant=grant,
        dispatcher=ctx.deps.dispatcher,
        orchestrator=ctx.deps.orchestrator,
        context=ctx.deps.context,
        run_id=ctx.state.run_id,
        step_id=f"step_{uuid4().hex[:12]}",
        priority=ctx.state.priority,
    )


def _request_policy(context_window: int | None, grant: Any) -> tuple[Model | None, UsageLimits | None]:
    """Bind per-request context capacity while preserving aggregate usage accounting."""
    model = cast("Model | None", grant.model)
    if context_window is None:
        return model, None
    output_reserve = grant.spec.generation_profile.max_tokens or THE_FIRST_ONE_SPEC.max_tokens or 0
    if output_reserve >= context_window:
        msg = (
            f"Output reserve {output_reserve} leaves no input budget inside the {context_window}-token context window."
        )
        raise ContextBudgetExceededError(msg)
    limits = UsageLimits(
        count_tokens_before_request=model is not None and type(model).count_tokens is not Model.count_tokens,
    )
    if model is None:
        return None, limits
    return ContextWindowModel(model, input_tokens_limit=context_window - output_reserve), limits


async def settle_turn(
    state: BridgeChatState,
    reply: BridgeReply,
    validated: list[ValidatedFragment],
    *,
    turns: TurnLedgerPort,
    fragments: FragmentRegistry,
) -> None:
    """Atomically settle the visible reply and completed model-history suffix."""
    from lychd.domain.web.schemas import BridgeTurn

    new_messages = state.new_messages
    if state.bottleneck is not None:
        synthetic: list[ModelMessage] = [
            ModelRequest.user_text_prompt(state.prompt),
            ModelResponse(parts=[TextPart(reply.answer)]),
        ]
        new_messages = list(ModelMessagesTypeAdapter.dump_python(synthetic, mode="json"))
    new_messages = bind_messages_to_logical_run(new_messages, state.run_id)
    await turns.settle_agent_turn(
        state.session_id,
        BridgeTurn(
            role="agent",
            content=reply.answer,
            run_id=state.run_id,
            state="settled",
            fragments=tuple(fragments.descriptor(fragment) for fragment in validated),
        ),
        new_messages=new_messages,
    )


@dataclass
class WeaveContext(BaseNode[BridgeChatState, WorkflowServices]):
    """Assemble completed session history and the keyed-block Stable Floor."""

    async def run(self, ctx: GraphRunContext[BridgeChatState, WorkflowServices]) -> Converse:
        """Retain the bounded history for the capability-bound context assembly."""
        emit = ctx.deps.events.emitter(ctx.state.run_id)
        emit.status("weaving")
        assembled = ctx.deps.context.assemble(
            run_id=ctx.state.run_id,
            session_id=ctx.state.session_id,
            query=ctx.state.prompt,
            history=await _session_history(ctx.state.session_id, ctx.deps.turns),
        )
        ctx.state.history = assembled.state_window
        return Converse()


@dataclass
class Converse(BaseNode[BridgeChatState, WorkflowServices]):
    """Run the first inference hop under a fresh capability lease."""

    async def run(self, ctx: GraphRunContext[BridgeChatState, WorkflowServices]) -> ProjectReply | AwaitConsent:
        """Stream a reply or record consent after releasing the capability lease.

        Hardware waits propagate to GraphRunner before lease acquisition.
        """
        emit = ctx.deps.events.emitter(ctx.state.run_id)
        async with ctx.deps.dispatcher.lease_grant(
            family="chat",
            capability_key=ctx.state.capability_key,
            run_id=ctx.state.run_id,
            priority=ctx.state.priority,
            requires_tools=True,
        ) as grant:
            assembled = ctx.deps.context.assemble(
                run_id=ctx.state.run_id,
                session_id=ctx.state.session_id,
                query=ctx.state.prompt,
                history=ctx.state.history,
                grant=grant,
                grant_epoch=grant.lease.grant_id,
            )
            ctx.state.history = assembled.state_window
            agent = ctx.deps.forge.agent_for(THE_FIRST_ONE_SPEC)
            deps = _agent_deps(ctx, grant)
            emit.status("thinking")
            bound_toolset = bind_consent_toolsets(grant.toolsets, capability_key=grant.spec.key)
            model, usage_limits = _request_policy(assembled.context_window, grant)
            pumped = await pump_agent_events(
                agent,
                ctx.state.prompt,
                deps=deps,
                model=model,
                model_settings=grant.model_settings(),
                toolsets=[bound_toolset],
                emit=emit,
                message_history=ModelMessagesTypeAdapter.validate_python(ctx.state.history) or None,
                usage_limits=usage_limits,
            )
        output = pumped.output
        ctx.state.new_messages = pumped.new_messages
        if isinstance(output, DeferredToolRequests):
            if not is_single_approval(output):
                ctx.state.bottleneck = Bottleneck(
                    kind="policy_block", detail="multiple tool approvals in one turn are not yet supported"
                )
                return ProjectReply()
            tool_name = output.approvals[0].tool_name
            binding = bound_toolset.binding_for(tool_name)
            if binding is None:
                ctx.state.bottleneck = Bottleneck(
                    kind="policy_block",
                    detail=f"approval tool '{tool_name}' has no durable effect identity",
                )
                return ProjectReply()
            await park_on_consent(ctx, output, ctx.state.new_messages, binding)
            return AwaitConsent()
        ctx.state.reply = output
        return ProjectReply()


@dataclass
class AwaitConsent(Gate, BaseNode[BridgeChatState, WorkflowServices]):
    """Resume an approved or refused call; a pending verdict parks without a lease.

    The Gate marker makes this workflow use durable checkpoints.
    """

    async def run(self, ctx: GraphRunContext[BridgeChatState, WorkflowServices]) -> ProjectReply | AwaitConsent:
        """Read the verdict; suspend on pending; else resume the deferred tool run."""
        consent_id = ctx.state.pending_consent_id
        if consent_id is None:
            ctx.state.bottleneck = Bottleneck(kind="policy_block", detail="gate reached without a parked consent")
            return ProjectReply()
        verdict = await ctx.deps.consents.verdict(consent_id)
        if verdict is None:
            raise ConsentPending(consent_id, ctx.state.run_id, ctx.state.pending_consent_tool_name or "")

        expected_binding = ctx.state.pending_consent_tool_binding
        results = DeferredToolResults(approvals=dict.fromkeys(ctx.state.pending_call_ids, verdict))
        continuation = list(ctx.state.paused_messages or [])
        emit = ctx.deps.events.emitter(ctx.state.run_id)
        async with ctx.deps.dispatcher.lease_grant(
            family="chat",
            capability_key=ctx.state.capability_key,
            run_id=ctx.state.run_id,
            priority=ctx.state.priority,
            requires_tools=True,
        ) as grant:
            assembled = ctx.deps.context.assemble(
                run_id=ctx.state.run_id,
                session_id=ctx.state.session_id,
                query=ctx.state.prompt,
                history=ctx.state.history,
                continuation=continuation,
                grant=grant,
                grant_epoch=grant.lease.grant_id,
            )
            ctx.state.history = assembled.state_window
            history = ModelMessagesTypeAdapter.validate_python(assembled.model_history())
            agent = ctx.deps.forge.agent_for(THE_FIRST_ONE_SPEC)
            deps = _agent_deps(ctx, grant)
            emit.status("thinking")
            try:
                bound_toolset = bind_consent_toolsets(
                    grant.toolsets,
                    capability_key=grant.spec.key,
                    expected=expected_binding,
                    require_expected=True,
                )
                model, usage_limits = _request_policy(assembled.context_window, grant)
                pumped = await pump_agent_events(
                    agent,
                    None,
                    deps=deps,
                    model=model,
                    model_settings=grant.model_settings(),
                    toolsets=[bound_toolset],
                    emit=emit,
                    message_history=history,
                    deferred_tool_results=results,
                    usage_limits=usage_limits,
                )
            except ConsentToolBindingChangedError:
                ctx.state.bottleneck = Bottleneck(
                    kind="policy_block",
                    detail="the approved tool or capability changed while consent was parked; fresh consent is required",
                )
                return ProjectReply()
        output = pumped.output
        ctx.state.new_messages.extend(pumped.new_messages)
        ctx.state.pending_consent_id = None
        ctx.state.paused_messages = None
        ctx.state.pending_call_ids = ()
        ctx.state.pending_consent_tool_name = None
        ctx.state.pending_consent_tool_binding = None
        if isinstance(output, DeferredToolRequests):  # the tool chained another approval
            if not is_single_approval(output):
                ctx.state.bottleneck = Bottleneck(
                    kind="policy_block", detail="multiple tool approvals in one turn are not yet supported"
                )
                return ProjectReply()
            ctx.state.consent_rounds += 1
            if ctx.state.consent_rounds >= MAX_CONSENT_ROUNDS:
                ctx.state.bottleneck = Bottleneck(kind="policy_block", detail="consent round limit reached")
                return ProjectReply()
            tool_name = output.approvals[0].tool_name
            binding = bound_toolset.binding_for(tool_name)
            if binding is None:
                ctx.state.bottleneck = Bottleneck(
                    kind="policy_block",
                    detail=f"approval tool '{tool_name}' has no durable effect identity",
                )
            else:
                await park_on_consent(ctx, output, ctx.state.new_messages, binding)
                return AwaitConsent()  # self-edge
        ctx.state.reply = output if isinstance(output, BridgeReply) else None
        return ProjectReply()


@dataclass
class ProjectReply(BaseNode[BridgeChatState, WorkflowServices, BridgeReply]):
    """Validate FragmentCalls against the Vessel-owned registry, settle the turn."""

    async def run(self, ctx: GraphRunContext[BridgeChatState, WorkflowServices]) -> End[BridgeReply]:
        """Settle the reply or bottleneck; the worker owns terminal Run status."""
        emit = ctx.deps.events.emitter(ctx.state.run_id)
        emit.status("settling")
        reply = ctx.state.reply or _fallback_reply(ctx.state)
        validated = ctx.deps.fragments.validate_calls(reply.fragments)
        for fragment in validated:
            emit.fragment(fragment.key, fragment.params.model_dump(mode="json"))
        await settle_turn(
            ctx.state,
            reply,
            validated,
            turns=ctx.deps.turns,
            fragments=ctx.deps.fragments,
        )
        return End(reply)


BRIDGE_CHAT_GRAPH: Graph[
    BridgeChatState, WorkflowServices, BaseNode[BridgeChatState, WorkflowServices, BridgeReply], BridgeReply
] = build_serial_graph(
    nodes=(WeaveContext, Converse, AwaitConsent, ProjectReply),
    state_type=BridgeChatState,
    deps_type=WorkflowServices,
    output_type=BridgeReply,
    name="bridge_chat",
)


def _make_state(intent: Intent) -> BridgeChatState:
    # Worker execution reconstructs Intent from the admitted Run, including its
    # canonical id and priority. Direct test construction may omit the id.
    return BridgeChatState(
        session_id=intent.session_id,
        run_id=intent.run_id or "",
        prompt=intent.prompt,
        priority=intent.priority if intent.priority is not None else PRIORITY_DEFAULT,
    )


def _validate_state(intent: Intent, state: BaseModel) -> None:
    """Bind every Bridge revision's checkpoint to its admitted input and identity."""
    expected_priority = intent.priority if intent.priority is not None else PRIORITY_DEFAULT
    if not isinstance(state, BridgeChatState) or (
        state.run_id,
        state.session_id,
        state.prompt,
        state.capability_key,
        state.priority,
    ) != (intent.run_id, intent.session_id, intent.prompt, intent.admitted_capability_key, expected_priority):
        msg = "bridge_chat checkpoint does not match its admitted Run."
        raise ValueError(msg)


BRIDGE_CHAT = Workflow(
    name="bridge_chat",
    title="Bridge Chat",
    description="Converse with The First One over the woven Stable Floor.",
    trigger=Trigger(hint="default — any Bridge prompt", match=lambda intent: intent.source == "bridge"),
    graph=BRIDGE_CHAT_GRAPH,
    start_node=WeaveContext,
    make_state=_make_state,
    validate_state=_validate_state,
    manifest=PatternManifest(
        key="bridge_chat",
        revision="1",
        implementation_revision="py.1",
        checkpoint_schema="bridge-chat-state-v1",
        entry_node="weave_context",
        nodes=(
            PatternNode(key="weave_context", label="Weave context", implementation=WeaveContext),
            PatternNode(key="converse", label="Converse", implementation=Converse),
            PatternNode(key="await_consent", label="Await consent", kind="gate", implementation=AwaitConsent),
            PatternNode(key="project_reply", label="Project reply", implementation=ProjectReply),
            PatternNode(key="end", label="End", kind="terminal"),
        ),
        edges=(
            PatternEdge(key="weave-to-converse", source="weave_context", target="converse"),
            PatternEdge(key="converse-to-consent", source="converse", target="await_consent"),
            PatternEdge(key="converse-to-project", source="converse", target="project_reply"),
            PatternEdge(key="consent-waits", source="await_consent", target="await_consent"),
            PatternEdge(key="consent-to-project", source="await_consent", target="project_reply"),
            PatternEdge(key="project-to-end", source="project_reply", target="end"),
        ),
    ),
)


def _make_bound_state(intent: Intent) -> BoundBridgeChatState:
    """Use only the binding persisted at admission, never current configuration."""
    values = _make_state(intent).model_dump()
    values["capability_key"] = intent.admitted_capability_key
    return BoundBridgeChatState.model_validate(values)


def _validate_bound_state(intent: Intent, state: BaseModel) -> None:
    """Refuse checkpoint drift from the Run's admitted input and execution identity."""
    if not isinstance(state, BoundBridgeChatState) or intent.admitted_capability_key is None:
        msg = "bridge_chat@2 requires its admitted Run binding."
        raise ValueError(msg)
    _validate_state(intent, state)


BRIDGE_CHAT_BOUND_GRAPH: Graph[
    BridgeChatState, WorkflowServices, BaseNode[BridgeChatState, WorkflowServices, BridgeReply], BridgeReply
] = build_serial_graph(
    nodes=(WeaveContext, Converse, AwaitConsent, ProjectReply),
    state_type=BoundBridgeChatState,
    deps_type=WorkflowServices,
    output_type=BridgeReply,
    name="bridge_chat",
)

BRIDGE_CHAT_BOUND = replace(
    BRIDGE_CHAT,
    description="Converse with The First One using the exact capability selected at admission.",
    graph=BRIDGE_CHAT_BOUND_GRAPH,
    make_state=_make_bound_state,
    validate_state=_validate_bound_state,
    manifest=replace(
        BRIDGE_CHAT.manifest,
        revision="2",
        implementation_revision="py.2",
        checkpoint_schema="bridge-chat-state-v2",
    ),
)
