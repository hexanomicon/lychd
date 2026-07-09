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
    short_spec = replace(THE_FIRST_ONE_SPEC, max_tokens=1024)
    forge.register(short_spec.name, build_the_first_one)
    assert forge.agent_for(THE_FIRST_ONE_SPEC) is not forge.agent_for(short_spec)


def test_minimal_spec_binds_no_lifecycle_tool() -> None:
    """The default First One has no in-lease hardware transition capability."""
    agent = build_the_first_one(THE_FIRST_ONE_SPEC)
    assert "request_coven_swap" not in _function_tool_names(agent)


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


def test_reference_and_production_models_share_one_profile() -> None:
    """Reference (`build_local_model`) and production (`get_model`) build the SAME profile.

    Guards the divergence that shipped once: the reference carried the inline-defs /
    no-strict-tools profile and the production connector built a bare model, so tool-call
    JSON schemas differed between tests and the running daemon.
    """
    from lychd.domain.animation.links import Link
    from lychd.domain.animation.model_factory import LOCAL_COMPAT_PROFILE
    from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector

    reference = build_local_model(model_id="qwen", base_url="http://localhost:8080/v1")
    assert reference.profile is LOCAL_COMPAT_PROFILE

    connector = OpenAICompatibleConnector(
        kind="openai_compat",
        link=Link(up=True, activatable=False),
        base_url="http://localhost:8080/v1",
        default_model_id="qwen",
    )
    production = connector.get_model()
    assert production.profile is LOCAL_COMPAT_PROFILE
