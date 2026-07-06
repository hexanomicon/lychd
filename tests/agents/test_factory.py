"""AgentForge / AgentSpec / build_agent / build_local_model (A5 §4, FINAL C6)."""

from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.factory import AgentForge, build_local_model
from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC, build_the_first_one, default_forge


def _function_tool_names(agent: object) -> list[str]:
    """Return the names of every function tool bound on the agent."""
    names: list[str] = []
    for toolset in agent.toolsets:  # type: ignore[attr-defined]
        if isinstance(toolset, FunctionToolset):
            names.extend(toolset.tools.keys())
    return names


def test_forge_caches_per_spec() -> None:
    """A forge returns the same agent instance for an identical spec (cache hit)."""
    forge = default_forge()
    first = forge.agent_for(THE_FIRST_ONE_SPEC)
    second = forge.agent_for(THE_FIRST_ONE_SPEC)
    assert first is second


def test_forge_distinct_specs_distinct_agents() -> None:
    """A changed spec is a distinct cache key -> a distinct agent."""
    forge = default_forge()
    read_only_spec = replace(THE_FIRST_ONE_SPEC, writes=False)
    forge.register(read_only_spec.name, build_the_first_one)
    assert forge.agent_for(THE_FIRST_ONE_SPEC) is not forge.agent_for(read_only_spec)


def test_write_gate_binds_mutating_tool_by_absence() -> None:
    """`writes=True` binds the coven tool; `writes=False` drops it entirely."""
    writing = build_the_first_one(THE_FIRST_ONE_SPEC)
    read_only = build_the_first_one(replace(THE_FIRST_ONE_SPEC, writes=False))
    assert "request_coven_swap" in _function_tool_names(writing)
    assert "request_coven_swap" not in _function_tool_names(read_only)


def test_forge_unknown_spec_raises() -> None:
    """`agent_for` on an unregistered spec name fails loudly."""
    forge = AgentForge()
    with pytest.raises(KeyError):
        forge.agent_for(THE_FIRST_ONE_SPEC)


def test_build_local_model_uses_base_url() -> None:
    """`build_local_model` constructs an OpenAIChatModel at the given base_url (no network)."""
    model = build_local_model(model_id="qwen", base_url="http://localhost:8080/v1")
    assert isinstance(model, OpenAIChatModel)
    assert str(model.client.base_url).rstrip("/") == "http://localhost:8080/v1"
