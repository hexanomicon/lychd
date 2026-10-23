"""One explicitly admitted public task, durable sovereign wait and attributed reply."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.base import PatternEdge, PatternManifest, PatternNode, PeerTaskNode, Trigger, Workflow
from lychd.domain.cortex.graph import build_serial_graph
from lychd.domain.cortex.graph_runner import HardwareResumeBudget
from lychd.domain.intercom.native import PeerRunBinding, PeerTaskPending, PeerTaskRef
from lychd.domain.web.schemas import BridgeTurn

if TYPE_CHECKING:
    from lychd.agents.router import Intent


class NativePublicPeerState(BaseModel):
    """Checkpoint only exact local ownership, never a marker, socket or foreign plan."""

    session_id: str
    run_id: str
    prompt: str = Field(repr=False)
    binding: PeerRunBinding
    hardware_resume_budget: HardwareResumeBudget = Field(default_factory=HardwareResumeBudget)
    peer_task: PeerTaskRef | None = None


@dataclass
class WaitPublicPeer(PeerTaskNode, BaseNode[NativePublicPeerState, WorkflowServices, str]):
    """Prepare before parking; consume only a freshly authorized terminal successor."""

    async def run(self, ctx: GraphRunContext[NativePublicPeerState, WorkflowServices]) -> End[str]:
        peer = ctx.deps.peer
        if peer is None:
            msg = "Native peer workflow has no host-owned peer service."
            raise RuntimeError(msg)
        state = ctx.state
        if state.peer_task is None:
            state.peer_task = await peer.prepare(run_id=state.run_id, binding=state.binding, station="peer_wait")
            raise PeerTaskPending(state.peer_task)
        reply = await peer.result(run_id=state.run_id, binding=state.binding, ref=state.peer_task)
        # Foreign text is the result of this opaque station. It is never parsed as
        # a tool, command, Companion action or additional Graph instruction.
        await ctx.deps.turns.settle_agent_turn(
            state.session_id,
            BridgeTurn(role="agent", content=reply, run_id=state.run_id, state="settled"),
            new_messages=[],
        )
        return End(reply)


NATIVE_PUBLIC_PEER_GRAPH = build_serial_graph(
    nodes=(WaitPublicPeer,),
    state_type=NativePublicPeerState,
    deps_type=WorkflowServices,
    output_type=str,
    name="native_public_peer",
)


def _make_state(intent: Intent) -> NativePublicPeerState:
    if intent.run_id is None or intent.admitted_peer is None or intent.source != "peer_public":
        msg = "Native public peer requires real server-owned Run admission."
        raise ValueError(msg)
    return NativePublicPeerState(
        session_id=intent.session_id,
        run_id=intent.run_id,
        prompt=intent.prompt,
        binding=intent.admitted_peer,
    )


def _validate_state(intent: Intent, state: BaseModel) -> None:
    if (
        not isinstance(state, NativePublicPeerState)
        or state.run_id != intent.run_id
        or state.session_id != intent.session_id
        or state.prompt != intent.prompt
        or state.binding != intent.admitted_peer
        or intent.source != "peer_public"
    ):
        msg = "Native peer checkpoint differs from its immutable admission."
        raise ValueError(msg)
    ref = state.peer_task
    if ref is not None and (
        ref.run_id != state.run_id
        or ref.station != "peer_wait"
        or ref.request_id != state.binding.request_id
        or ref.binding_digest != state.binding.digest
    ):
        msg = "Native peer checkpoint task differs from its exact owner."
        raise ValueError(msg)


NATIVE_PUBLIC_PEER = Workflow(
    name="native_public_peer",
    title="Public peer task",
    description="Await one explicitly authored public task and return attributed sovereign data.",
    trigger=Trigger(
        hint="Explicit authenticated public peer admission", match=lambda intent: intent.source == "peer_public"
    ),
    graph=NATIVE_PUBLIC_PEER_GRAPH,
    start_node=WaitPublicPeer,
    make_state=_make_state,
    validate_state=_validate_state,
    manifest=PatternManifest(
        key="native_public_peer",
        revision="1",
        implementation_revision="py.1",
        checkpoint_schema="native-public-peer-state-v1",
        entry_node="peer_wait",
        nodes=(
            PatternNode(key="peer_wait", label="Await public peer result", kind="peer", implementation=WaitPublicPeer),
            PatternNode(key="settled", label="Return attributed foreign data", kind="terminal"),
        ),
        edges=(
            PatternEdge(key="peer_reentry", source="peer_wait", target="peer_wait"),
            PatternEdge(key="peer_result", source="peer_wait", target="settled"),
        ),
    ),
)
