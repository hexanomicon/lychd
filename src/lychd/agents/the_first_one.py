"""THE_FIRST_ONE — the Bridge agent specification (A5 §4).

Built through the `AgentForge`, not a bare module constant: nodes fetch the agent
via `ctx.deps.forge.agent_for(THE_FIRST_ONE_SPEC)` (cached once per process). No
model and no tools are hardcoded (Late-Binding law) — the model and grant-carried
toolsets arrive per-run via the resolved `CapabilityGrant`. Layer-1 identity is
the static `instructions`; layers 2-4 arrive through the dynamic `@instructions`
hook reading the run's assembled floor.

The minimal agent intentionally exposes no lifecycle-transition tool.  A model run
holds its model grant lease; asking the Orchestrator to replace that substrate from a
tool body can make the transition wait on its own lease.  Lifecycle control remains a
Vessel/control-plane concern until it has an external, post-lease execution path.
"""

from __future__ import annotations

from pydantic_ai import Agent, DeferredToolRequests, RunContext

from lychd.agents.deps import LychDDeps
from lychd.agents.factory import AgentForge, AgentSpec, build_agent
from lychd.agents.outputs import BridgeReply
from lychd.domain.cortex.context import IDENTITY_BLOCK_KEY, IDENTITY_BLOCK_TEXT

THE_FIRST_ONE_SPEC = AgentSpec(
    name="the_first_one",
    instructions_key=IDENTITY_BLOCK_KEY,
    instructions=IDENTITY_BLOCK_TEXT,
    output_types=(BridgeReply, DeferredToolRequests),
    toolset_names=(),
    writes=False,
)


async def stable_floor(ctx: RunContext[LychDDeps]) -> str:
    """Return layers 2-4 without routing a trivial lookup through a worker thread."""
    return ctx.deps.context.floor_text(ctx.deps.run_id)


def build_the_first_one(spec: AgentSpec) -> Agent[LychDDeps, object]:
    """Construct the minimal late-bound agent with no lifecycle-mutating tools."""
    return build_agent(
        spec,
        toolset_factories={},
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
    "default_forge",
    "stable_floor",
]
