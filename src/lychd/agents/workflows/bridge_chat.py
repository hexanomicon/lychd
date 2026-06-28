"""The `bridge_chat` workflow: WeaveContext -> Converse -> ProjectReply (§5.3).

Three stations over the woven Stable Floor. The grant is acquired inside
`Converse` (the per-step lease); a `HardwareTransitionRequired` raised there
propagates out of `graph.iter()` for `GraphRunner` to catch and resolve — that is
Live Stasis, and no node handles hardware.

Module-level singletons (`_DISPATCHER`, `_ORCHESTRATOR`, `_CONTEXT`,
`_FRAGMENTS`, `_SESSIONS`) are injected once by `wire(...)` so nodes stay
import-clean and testable with fakes.
"""

from __future__ import annotations

import html
import json
import uuid
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPart, TextPartDelta
from pydantic_ai.run import AgentRunResultEvent
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from lychd.agents.deps import LychDDeps, Sigil
from lychd.agents.workflows.base import Trigger, Workflow

if TYPE_CHECKING:
    from lychd.agents.router import Intent
    from lychd.domain.cortex.context import ContextOrchestrator
    from lychd.domain.cortex.dispatcher import Dispatcher
    from lychd.domain.orchestration.manager import OrchestratorManager
    from lychd.domain.web.fragments import FragmentRegistry, ValidatedFragment
    from lychd.domain.web.sessions import BridgeSessionStore


# ---------------------------------------------------------------------------
# Typed state and output (Buddhi's contract)
# ---------------------------------------------------------------------------


class FragmentCall(BaseModel):
    """A generative-UI request: a registry key plus its params (never markup)."""

    fragment: str
    params: dict[str, Any] = Field(default_factory=dict)


class BridgeReply(BaseModel):
    """The First One's settled turn output."""

    answer: str
    fragments: list[FragmentCall] = Field(default_factory=list)


class Bottleneck(BaseModel):
    """A typed non-completion (ADR 20)."""

    kind: Literal["contradiction", "missing_input", "policy_block", "dependency_unavailable"]
    detail: str


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
# Wired singletons
# ---------------------------------------------------------------------------

_dispatcher: Dispatcher | None = None
_orchestrator: OrchestratorManager | None = None
_context: ContextOrchestrator | None = None
_fragments: FragmentRegistry | None = None
_sessions: BridgeSessionStore | None = None

_DEFAULT_SIGIL = Sigil(name="magus", scopes=frozenset({"bridge:send", "nexus:swap", "consent:grant"}))


def default_sigil() -> Sigil:
    """Return the process default Sigil (v1 single-identity stand-in for the Ward)."""
    return _DEFAULT_SIGIL


def wire(
    *,
    dispatcher: Dispatcher,
    orchestrator: OrchestratorManager,
    context: ContextOrchestrator,
    fragments: FragmentRegistry,
    sessions: BridgeSessionStore,
) -> None:
    """Inject the runtime singletons the nodes and the consent tool depend on."""
    global _dispatcher, _orchestrator, _context, _fragments, _sessions  # noqa: PLW0603
    _dispatcher = dispatcher
    _orchestrator = orchestrator
    _context = context
    _fragments = fragments
    _sessions = sessions


def require_dispatcher() -> Dispatcher:
    """Return the wired dispatcher or raise if `wire()` was never called."""
    return _require(_dispatcher, "dispatcher")


def require_orchestrator() -> OrchestratorManager:
    """Return the wired orchestrator (used by the consent tool in the_first_one)."""
    return _require(_orchestrator, "orchestrator")


def require_context() -> ContextOrchestrator:
    """Return the wired context orchestrator."""
    return _require(_context, "context")


def require_fragments() -> FragmentRegistry:
    """Return the wired fragment registry."""
    return _require(_fragments, "fragments")


def require_sessions() -> BridgeSessionStore:
    """Return the wired session store."""
    return _require(_sessions, "sessions")


def _require[T](value: T | None, name: str) -> T:
    if value is None:
        msg = f"bridge_chat.wire() has not bound '{name}'."
        raise RuntimeError(msg)
    return value


# ---------------------------------------------------------------------------
# RunChannel emitters (server-side event payloads)
# ---------------------------------------------------------------------------


def emit_status(run_id: str, status: str) -> None:
    """Emit a status chip keyword (e.g. weaving/thinking/settling)."""
    require_sessions().channel(run_id).emit("status", status)


def emit_token(run_id: str, text: str) -> None:
    """Emit an escaped token delta appended to the streaming turn body."""
    if text:
        require_sessions().channel(run_id).emit("token", html.escape(text))


def emit_fragment(run_id: str, fragment: ValidatedFragment) -> None:
    """Emit a validated generative-UI fragment as `{key, params}` JSON."""
    payload = json.dumps({"key": fragment.key, "params": fragment.params.model_dump(mode="json")})
    require_sessions().channel(run_id).emit("fragment", payload)


def emit_consent(run_id: str, consent_id: str) -> None:
    """Emit the id of a parked consent awaiting the Magus's verdict."""
    require_sessions().channel(run_id).emit("consent", consent_id)


def emit_done(run_id: str) -> None:
    """Emit the terminal event that settles the turn and closes the SSE stream."""
    require_sessions().channel(run_id).emit("done", run_id)


# ---------------------------------------------------------------------------
# Node helpers
# ---------------------------------------------------------------------------


def new_step_id() -> str:
    """Return a fresh per-step id."""
    return f"step_{uuid.uuid4().hex[:12]}"


def build_user_prompt(state: BridgeChatState) -> str:
    """Return the query as the user prompt; the woven floor rides in `instructions`."""
    return state.prompt


def _session_history(session_id: str) -> list[dict[str, str]]:
    session = require_sessions().get_session(session_id)
    if session is None:
        return []
    return [{"role": turn.role, "content": turn.content} for turn in session.turns]


def consent_placeholder() -> BridgeReply:
    """Return the placeholder reply for a turn that parked on consent."""
    return BridgeReply(answer="Consent sought — the Magus must decide before I may proceed.")


def park_consent(state: BridgeChatState, requests: DeferredToolRequests) -> str:
    """Park the first approval-required tool call and return its consent id."""
    call = requests.approvals[0]
    return require_sessions().park_consent(
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
) -> None:
    """Write the settled agent turn to the session store and close the run."""
    from lychd.domain.web.schemas import BridgeTurn

    sessions = require_sessions()
    sessions.add_turn(
        state.session_id,
        BridgeTurn(
            role="agent",
            content=reply.answer,
            run_id=state.run_id,
            state="settled",
            fragments=tuple(fragment.key for fragment in validated),
        ),
    )
    sessions.set_run_status(state.run_id, "done")
    require_context().release(state.run_id)


def fail_run(*, run_id: str, session_id: str, message: str) -> None:
    """Terminate a run that raised before settling: record a failed turn, close the stream.

    The background run guard in ``router.submit`` calls this so a failed run still
    emits a terminal ``done`` event — otherwise the SSE stream and its streaming
    slot would hang forever (the turn would stay ``aria-busy``).
    """
    from lychd.domain.web.schemas import BridgeTurn

    sessions = require_sessions()
    sessions.add_turn(
        session_id,
        BridgeTurn(role="agent", content=message, run_id=run_id, state="failed"),
    )
    sessions.set_run_status(run_id, "failed")
    with suppress(RuntimeError):
        require_context().release(run_id)
    sessions.channel(run_id).emit("done", run_id)


# ---------------------------------------------------------------------------
# The graph nodes
# ---------------------------------------------------------------------------


@dataclass
class WeaveContext(BaseNode[BridgeChatState]):
    """The Archivist step: assemble the keyed-block Stable Floor (ADR 28 §2, ADR 21)."""

    async def run(self, ctx: GraphRunContext[BridgeChatState]) -> Converse:
        """Assemble the floor, stamp the prefix digest, and hand off to Converse."""
        emit_status(ctx.state.run_id, "weaving")
        assembled = require_context().assemble(
            run_id=ctx.state.run_id,
            session_id=ctx.state.session_id,
            query=ctx.state.prompt,
            history=_session_history(ctx.state.session_id),
        )
        ctx.state.prefix_digest = assembled.prefix_digest
        ctx.state.history = assembled.state_window
        return Converse()


@dataclass
class Converse(BaseNode[BridgeChatState]):
    """The thinking station. The grant is acquired HERE — the per-step lease."""

    async def run(self, ctx: GraphRunContext[BridgeChatState]) -> ProjectReply:
        """Resolve the grant, stream The First One, and capture reply or consent."""
        from lychd.agents.the_first_one import THE_FIRST_ONE

        grant = require_dispatcher().resolve_capability_grant("chat")
        deps = LychDDeps(
            sigil=_DEFAULT_SIGIL,
            grant=grant,
            dispatcher=require_dispatcher(),
            phylactery=None,
            context=require_context(),
            run_id=ctx.state.run_id,
            step_id=new_step_id(),
        )
        emit_status(ctx.state.run_id, "thinking")

        result_event: AgentRunResultEvent[Any] | None = None
        async for event in THE_FIRST_ONE.run_stream_events(
            build_user_prompt(ctx.state),
            deps=deps,
            model=grant.model,
            toolsets=list(grant.toolsets),
        ):
            if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                emit_token(ctx.state.run_id, event.delta.content_delta)
            elif isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
                emit_token(ctx.state.run_id, event.part.content)
            elif isinstance(event, AgentRunResultEvent):
                result_event = event

        output = result_event.result.output if result_event is not None else None
        if isinstance(output, DeferredToolRequests):
            ctx.state.pending_consent_id = park_consent(ctx.state, output)
            emit_consent(ctx.state.run_id, ctx.state.pending_consent_id)
        elif isinstance(output, BridgeReply):
            ctx.state.reply = output
        return ProjectReply()


@dataclass
class ProjectReply(BaseNode[BridgeChatState, None, BridgeReply]):
    """Validate FragmentCalls against the Vessel-owned registry, settle the turn."""

    async def run(self, ctx: GraphRunContext[BridgeChatState]) -> End[BridgeReply]:
        """Validate fragments and settle — unless a consent parked the turn.

        When a consent is parked the run does NOT settle or emit ``done``: the live
        consent card must stay actionable in the streaming slot (a ``done`` event
        OOB-replaces the whole slot and would destroy the card). Honest deferred-tool
        resume and a clean non-destructive terminal are P2/M2.1 work.
        """
        if ctx.state.pending_consent_id is not None:
            require_sessions().set_run_status(ctx.state.run_id, "awaiting_consent")
            return End(consent_placeholder())
        emit_status(ctx.state.run_id, "settling")
        reply = ctx.state.reply or consent_placeholder()
        validated = require_fragments().validate_calls(reply.fragments)
        for fragment in validated:
            emit_fragment(ctx.state.run_id, fragment)
        settle_turn(ctx.state, reply, validated)
        emit_done(ctx.state.run_id)
        return End(reply)


# ---------------------------------------------------------------------------
# The workflow
# ---------------------------------------------------------------------------

BRIDGE_CHAT_GRAPH: Graph[BridgeChatState, None, BridgeReply] = Graph(
    nodes=(WeaveContext, Converse, ProjectReply),
    name="bridge_chat",
)


def _make_state(intent: Intent) -> BridgeChatState:
    return BridgeChatState(session_id=intent.session_id, run_id=intent.run_id, prompt=intent.prompt)


BRIDGE_CHAT = Workflow(
    name="bridge_chat",
    title="Bridge Chat",
    description="Converse with The First One over the woven Stable Floor.",
    trigger=Trigger(hint="default — any Bridge prompt", match=lambda intent: intent.source == "bridge"),
    graph=BRIDGE_CHAT_GRAPH,
    start_node=WeaveContext,
    make_state=_make_state,
)
