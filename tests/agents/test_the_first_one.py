"""THE_FIRST_ONE typed outputs, offline (A5 §4/§10)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.deps import LychDDeps
from lychd.agents.outputs import BridgeReply
from lychd.agents.services import default_sigil
from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC, default_forge
from lychd.domain.cortex.context import ContextOrchestrator
from tests.agents.fakes import FakeDispatcher, FakeGrant, FakeOrchestrator, FakeRegistry

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilityGrant


def _deps() -> LychDDeps:
    return LychDDeps(
        sigil=default_sigil(),
        grant=cast("CapabilityGrant", FakeGrant(model=None)),
        dispatcher=FakeDispatcher(model=None),  # unused by the direct-run tests
        orchestrator=FakeOrchestrator(),
        context=ContextOrchestrator(registry=FakeRegistry()),
        run_id="run_1",
        step_id="step_1",
        priority=50,
    )


@pytest.mark.asyncio
async def test_yields_bridge_reply_when_no_tool_called() -> None:
    """With tools suppressed, the typed output is a `BridgeReply`."""
    agent = default_forge().agent_for(THE_FIRST_ONE_SPEC)
    model = TestModel(custom_output_args={"answer": "greetings, Magus", "fragments": []}, call_tools=[])
    result = await agent.run("hello", deps=_deps(), model=model)
    assert isinstance(result.output, BridgeReply)
    assert result.output.answer == "greetings, Magus"


def test_minimal_agent_does_not_expose_coven_transition_tool() -> None:
    """The leased minimal agent cannot request a transition of its own substrate."""
    agent = default_forge().agent_for(THE_FIRST_ONE_SPEC)
    names = {name for toolset in agent.toolsets if isinstance(toolset, FunctionToolset) for name in toolset.tools}
    assert "request_coven_swap" not in names
