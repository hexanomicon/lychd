"""THE_FIRST_ONE — the Bridge agent specification (A5 §4).

The process-scoped forge caches the agent by its complete specification. No model
and no tools are hardcoded: both arrive per run via the resolved capability grant.
Layer-1 identity retains admitted forms of address; layers 2-4 arrive through the
dynamic instruction hook.

The minimal agent intentionally exposes no lifecycle-transition tool.  A model run
holds its model grant lease; asking the Orchestrator to replace that substrate from a
tool body can make the transition wait on its own lease.  Lifecycle control remains a
Vessel/control-plane concern until it has an external, post-lease execution path.
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast

from pydantic_ai import Agent, DeferredToolRequests, RunContext

from lychd.agents.deps import LychDDeps
from lychd.agents.factory import AgentForge, AgentSpec, build_agent
from lychd.agents.outputs import BridgeReply
from lychd.domain.cortex.context import IDENTITY_BLOCK_KEY, IDENTITY_BLOCK_TEXT, naming_identity_block
from lychd.domain.naming import NamingSnapshot

type BridgeAgentOutput = BridgeReply | DeferredToolRequests

THE_FIRST_ONE_SPEC = AgentSpec(
    name="the_first_one",
    instructions_key=IDENTITY_BLOCK_KEY,
    instructions=IDENTITY_BLOCK_TEXT,
    output_types=(BridgeReply, DeferredToolRequests),
)


def named_agent_spec(spec: AgentSpec, naming: NamingSnapshot | None) -> AgentSpec:
    """Bind the same admitted naming text used by Context, preserving profile rules."""
    if naming is None:
        return spec
    if not spec.instructions.startswith(IDENTITY_BLOCK_TEXT):
        msg = "Named Bridge agent must retain its known identity instruction prefix."
        raise ValueError(msg)
    block = naming_identity_block(naming)
    return replace(
        spec,
        instructions_key=f"{spec.instructions_key}:{block.key}",
        instructions=block.text + spec.instructions.removeprefix(IDENTITY_BLOCK_TEXT),
    )


async def stable_floor(ctx: RunContext[LychDDeps]) -> str:
    """Return layers 2-4 without routing a trivial lookup through a worker thread."""
    return ctx.deps.context.floor_text(ctx.deps.run_id)


def build_the_first_one(spec: AgentSpec) -> Agent[LychDDeps, BridgeAgentOutput]:
    """Construct the minimal late-bound agent with no lifecycle-mutating tools."""
    return cast(
        "Agent[LychDDeps, BridgeAgentOutput]",
        build_agent(spec, toolset_factories={}, instruction_hooks=(stable_floor,)),
    )


def default_forge() -> AgentForge:
    """Build a forge with The First One registered."""
    forge = AgentForge()
    forge.register(THE_FIRST_ONE_SPEC.name, build_the_first_one)
    return forge


__all__ = [
    "THE_FIRST_ONE_SPEC",
    "build_the_first_one",
    "default_forge",
    "named_agent_spec",
    "stable_floor",
]
