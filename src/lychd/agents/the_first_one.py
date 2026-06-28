"""THE_FIRST_ONE — the Bridge agent specification (§5.3).

A static Specification Class: no model and no tools are hardcoded (Late-Binding
law). The model and toolsets arrive per-run via the resolved `CapabilityGrant`.
Layer-1 identity is the static `instructions`; layers 2-4 arrive through the
dynamic `@instructions` hook reading the run's assembled floor.
"""

from __future__ import annotations

from pydantic_ai import Agent, DeferredToolRequests, ModelRetry, RunContext

from lychd.agents.deps import LychDDeps
from lychd.agents.workflows.bridge_chat import BridgeReply
from lychd.domain.cortex.context import IDENTITY_BLOCK_TEXT

# `DeferredToolRequests` is a mandated output member: pydantic-ai rejects an
# approval-required tool unless the agent can output it (that is the deferred
# path the Seat of Consent resumes from). See `request_coven_swap` below.
THE_FIRST_ONE: Agent[LychDDeps, BridgeReply | DeferredToolRequests] = Agent(
    deps_type=LychDDeps,
    output_type=[BridgeReply, DeferredToolRequests],
    retries=2,
    instructions=IDENTITY_BLOCK_TEXT,
)


@THE_FIRST_ONE.instructions
def stable_floor(ctx: RunContext[LychDDeps]) -> str:
    """Layers 2-4 of the assembled floor, deterministic given the block key set."""
    return ctx.deps.context.floor_text(ctx.deps.run_id)


@THE_FIRST_ONE.tool(requires_approval=True)
async def request_coven_swap(ctx: RunContext[LychDDeps], capability_key: str, reason: str) -> str:
    """Propose a hardware coven swap; the Magus disposes (runs only post-approval).

    `requires_approval=True` means the model calling this tool yields a
    `DeferredToolRequests`; this body executes only after the Seat of Consent
    resumes the run with an approval.
    """
    from lychd.agents.workflows.bridge_chat import require_orchestrator

    if "nexus:swap" not in ctx.deps.sigil.scopes:
        msg = "This sigil lacks the nexus:swap scope; a coven swap may not be proposed."
        raise ModelRetry(msg)

    orchestrator = require_orchestrator()
    plan = await orchestrator.calculate_transition_plan(capability_key)
    await orchestrator.request_transition(capability_key, priority=50.0)
    return (
        f"transition to {capability_key} executed "
        f"(action {plan.action_type}, cost {plan.total_metabolic_cost}); reason: {reason}"
    )
