"""THE_FIRST_ONE typed outputs, offline (A5 §4/§10)."""

from __future__ import annotations

from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC, default_forge


def test_minimal_agent_does_not_expose_coven_transition_tool() -> None:
    """The leased minimal agent cannot request a transition of its own substrate."""
    agent = default_forge().agent_for(THE_FIRST_ONE_SPEC)
    names = {name for toolset in agent.toolsets if isinstance(toolset, FunctionToolset) for name in toolset.tools}
    assert "request_coven_swap" not in names
