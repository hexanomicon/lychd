"""THE_FIRST_ONE — the Bridge agent specification (A5 §4).

Built through the `AgentForge`, not a bare module constant: nodes fetch the agent
via `ctx.deps.forge.agent_for(THE_FIRST_ONE_SPEC)` (cached once per process). No
model and no tools are hardcoded (Late-Binding law) — the model and grant-carried
toolsets arrive per-run via the resolved `CapabilityGrant`. Layer-1 identity is
the static `instructions`; layers 2-4 arrive through the dynamic `@instructions`
hook reading the run's assembled floor.

The consent tool reads `ctx.deps.orchestrator` (a `TransitionPort`) — no reach
back into the workflow module, so the historical import cycle is dead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai import Agent, DeferredToolRequests, ModelRetry, RunContext
from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.deps import LychDDeps
from lychd.agents.factory import AgentForge, AgentSpec, build_agent
from lychd.agents.outputs import BridgeReply
from lychd.domain.codex.scopes import scopes_satisfied
from lychd.domain.cortex.context import IDENTITY_BLOCK_KEY, IDENTITY_BLOCK_TEXT

if TYPE_CHECKING:
    from pydantic_ai.toolsets import AbstractToolset

# The `coven` toolset is mutating (it enacts a hardware transition) and
# approval-required (the model calling it yields a `DeferredToolRequests`).
_COVEN_TOOLSET = "coven"

THE_FIRST_ONE_SPEC = AgentSpec(
    name="the_first_one",
    instructions_key=IDENTITY_BLOCK_KEY,
    instructions=IDENTITY_BLOCK_TEXT,
    output_kind="bridge_reply",
    toolset_names=(_COVEN_TOOLSET,),
    writes=True,
)


def stable_floor(ctx: RunContext[LychDDeps]) -> str:
    """Layers 2-4 of the assembled floor, deterministic given the block key set."""
    return ctx.deps.context.floor_text(ctx.deps.run_id)


async def request_coven_swap(ctx: RunContext[LychDDeps], capability_key: str, reason: str) -> str:
    """Propose a hardware coven swap; the Magus disposes (runs only post-approval).

    The tool is registered `requires_approval=True`, so the model calling it yields
    a `DeferredToolRequests`; this body executes only after the Seat of Consent
    resumes the run with an approval.
    """
    if not scopes_satisfied(ctx.deps.sigil.scopes, ("orchestrator:transition",)):
        msg = "This sigil lacks orchestrator:transition; a coven swap may not be proposed."
        raise ModelRetry(msg)

    plan = await ctx.deps.orchestrator.calculate_transition_plan(capability_key)
    await ctx.deps.orchestrator.request_transition(capability_key, priority=50.0)
    return (
        f"transition to {capability_key} executed "
        f"(action {plan.action_type}, cost {plan.total_metabolic_cost}); reason: {reason}"
    )


def coven_toolset() -> AbstractToolset[LychDDeps]:
    """Build the approval-required coven-swap toolset."""
    toolset: FunctionToolset[LychDDeps] = FunctionToolset()
    toolset.add_function(request_coven_swap, requires_approval=True)
    return toolset


def build_the_first_one(spec: AgentSpec) -> Agent[LychDDeps, object]:
    """Construct The First One through the factory (no model bound: Late-Binding)."""
    return build_agent(
        spec,
        output_type=[BridgeReply, DeferredToolRequests],
        toolset_factories={_COVEN_TOOLSET: coven_toolset},
        mutating=frozenset({_COVEN_TOOLSET}),
        instruction_hooks=(stable_floor,),
    )


def default_forge() -> AgentForge:
    """Return an `AgentForge` with The First One's builder registered."""
    forge = AgentForge()
    forge.register(THE_FIRST_ONE_SPEC.name, build_the_first_one)
    return forge


__all__ = [
    "THE_FIRST_ONE_SPEC",
    "build_the_first_one",
    "coven_toolset",
    "default_forge",
    "request_coven_swap",
    "stable_floor",
]
