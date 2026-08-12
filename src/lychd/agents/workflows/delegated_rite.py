"""A reference Pattern proving durable delegation without a provider call.

The Pattern deliberately targets the inert ``reference`` runtime.  It exercises the
same AgentJob, checkpoint, resume, evidence, and projection paths that effectful CLI
adapters use, but it has no network, subprocess, workspace, or credential authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelRequest, ModelResponse, TextPart
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from lychd.agents.services import WorkflowServices
from lychd.agents.workflows.base import (
    DelegatedAgentNode,
    PatternEdge,
    PatternManifest,
    PatternNode,
    Trigger,
    Workflow,
)
from lychd.domain.cortex.priority import PRIORITY_DEFAULT
from lychd.domain.delegation.models import (
    TERMINAL_DELEGATED_AGENT_STATUSES,
    DelegatedAgentJobStatus,
    DelegatedAgentProfile,
    DelegatedAgentRequest,
)
from lychd.domain.delegation.signals import DelegatedAgentPending
from lychd.domain.web.schemas import BridgeTurn

__all__ = [
    "DELEGATED_RITE",
    "DELEGATED_RITE_GRAPH",
    "DelegatedRiteState",
    "DispatchDelegate",
    "ProjectDelegatedReply",
]

_COMMAND = "/delegate"
_REFERENCE_RUNTIME = "reference"
_REFERENCE_PROFILE = DelegatedAgentProfile.READ


class DelegatedRiteState(BaseModel):
    """Replay-safe state retained across the delegated AgentJob park."""

    session_id: str
    run_id: str
    prompt: str
    priority: int = PRIORITY_DEFAULT
    request_id: str = ""
    job_id: str | None = None
    reply: str | None = None


def _delegated_prompt(prompt: str) -> str:
    stripped = prompt.strip()
    if stripped.lower() == _COMMAND:
        return "Prove the sealed delegated-agent path."
    return stripped[len(_COMMAND) :].strip()


def _matches_delegate_command(prompt: str) -> bool:
    """Match the slash command as one token, not as an arbitrary prefix."""
    tokens = prompt.strip().split(maxsplit=1)
    return bool(tokens) and tokens[0].lower() == _COMMAND


@dataclass
class DispatchDelegate(DelegatedAgentNode, BaseNode[DelegatedRiteState, WorkflowServices, str]):
    """Submit once, then resume this same station from durable AgentJob truth."""

    async def run(
        self,
        ctx: GraphRunContext[DelegatedRiteState, WorkflowServices],
    ) -> ProjectDelegatedReply:
        delegates = ctx.deps.delegates
        if delegates is None:
            msg = "Delegated labor is unavailable: the composition root did not bind a coordinator."
            raise RuntimeError(msg)

        if ctx.state.job_id is None:
            request = DelegatedAgentRequest(
                request_id=ctx.state.request_id,
                run_id=ctx.state.run_id,
                step_id="dispatch_delegate",
                runtime=_REFERENCE_RUNTIME,
                profile=_REFERENCE_PROFILE,
                prompt=_delegated_prompt(ctx.state.prompt),
            )
            job = await delegates.submit(request)
            ctx.state.job_id = job.job_id
            raise DelegatedAgentPending(job)

        job = await delegates.get(ctx.state.job_id)
        if job is None:
            msg = f"Delegated AgentJob {ctx.state.job_id!r} disappeared from its authoritative store."
            raise RuntimeError(msg)
        if job.status not in TERMINAL_DELEGATED_AGENT_STATUSES:
            raise DelegatedAgentPending(job.ref)
        if job.status is not DelegatedAgentJobStatus.SUCCEEDED or job.result is None:
            msg = f"Delegated AgentJob {job.ref.job_id} settled {job.status.value}."
            raise RuntimeError(msg)
        ctx.state.reply = job.result.output or "The delegated AgentJob succeeded without textual output."
        return ProjectDelegatedReply()


@dataclass
class ProjectDelegatedReply(BaseNode[DelegatedRiteState, WorkflowServices, str]):
    """Return the bounded adopted result through the ordinary Bridge turn ledger."""

    async def run(self, ctx: GraphRunContext[DelegatedRiteState, WorkflowServices]) -> End[str]:
        reply = ctx.state.reply or "The delegated AgentJob settled without a reply."
        messages = ModelMessagesTypeAdapter.dump_python(
            [
                ModelRequest.user_text_prompt(ctx.state.prompt),
                ModelResponse(parts=[TextPart(reply)]),
            ],
            mode="json",
        )
        bound_messages: list[Any] = []
        for message in cast("list[Any]", messages):
            payload = cast("dict[str, Any]", message) if isinstance(message, dict) else {}
            if payload.get("kind") in {"request", "response"}:
                bound_messages.append({**payload, "run_id": ctx.state.run_id})
            else:
                bound_messages.append(message)
        await ctx.deps.turns.settle_agent_turn(
            ctx.state.session_id,
            BridgeTurn(
                role="agent",
                content=reply,
                run_id=ctx.state.run_id,
                state="settled",
            ),
            new_messages=bound_messages,
        )
        ctx.deps.events.emitter(ctx.state.run_id).status("settling")
        return End(reply)


DELEGATED_RITE_GRAPH: Graph[DelegatedRiteState, WorkflowServices, str] = Graph(
    nodes=(DispatchDelegate, ProjectDelegatedReply),
    name="delegated_rite",
)


def _make_state(intent: Any) -> DelegatedRiteState:
    return DelegatedRiteState(
        session_id=intent.session_id,
        run_id=intent.run_id or "",
        prompt=intent.prompt,
        priority=intent.priority if intent.priority is not None else PRIORITY_DEFAULT,
        request_id=str(uuid4()),
    )


DELEGATED_RITE = Workflow(
    name="delegated_rite",
    title="Delegated Rite",
    description="Pass bounded work through one sealed AgentJob and resume from durable truth.",
    trigger=Trigger(
        hint="Bridge prompts using the /delegate command",
        match=lambda intent: intent.source == "bridge" and _matches_delegate_command(intent.prompt),
    ),
    graph=DELEGATED_RITE_GRAPH,
    start_node=DispatchDelegate,
    make_state=_make_state,
    manifest=PatternManifest(
        key="delegated_rite",
        revision="1",
        implementation_revision="py.1",
        checkpoint_schema="delegated-rite-state-v1",
        entry_node="dispatch_delegate",
        nodes=(
            PatternNode(
                key="dispatch_delegate",
                label="Delegate sealed labor",
                kind="delegate",
                implementation=DispatchDelegate,
            ),
            PatternNode(
                key="project_reply",
                label="Project adopted result",
                implementation=ProjectDelegatedReply,
            ),
            PatternNode(key="end", label="End", kind="terminal"),
        ),
        edges=(
            PatternEdge(key="delegate-waits", source="dispatch_delegate", target="dispatch_delegate"),
            PatternEdge(key="delegate-to-project", source="dispatch_delegate", target="project_reply"),
            PatternEdge(key="project-to-end", source="project_reply", target="end"),
        ),
    ),
)
