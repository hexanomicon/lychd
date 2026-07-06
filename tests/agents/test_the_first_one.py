"""THE_FIRST_ONE typed outputs, offline (A5 §4/§10)."""

from __future__ import annotations

import pytest
from pydantic_ai import DeferredToolRequests
from pydantic_ai.models.test import TestModel

from lychd.agents.deps import LychDDeps
from lychd.agents.outputs import BridgeReply
from lychd.agents.services import default_sigil
from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC, default_forge
from lychd.domain.cortex.context import ContextOrchestrator
from tests.agents.fakes import FakeGrant, FakeOrchestrator, FakeRegistry


def _deps() -> LychDDeps:
    return LychDDeps(
        sigil=default_sigil(),
        grant=FakeGrant(model=None),
        dispatcher=object(),  # unused by the direct-run tests
        orchestrator=FakeOrchestrator(),
        context=ContextOrchestrator(registry=FakeRegistry()),
        run_id="run_1",
        step_id="step_1",
    )


@pytest.mark.asyncio
async def test_yields_bridge_reply_when_no_tool_called() -> None:
    """With tools suppressed, the typed output is a `BridgeReply`."""
    agent = default_forge().agent_for(THE_FIRST_ONE_SPEC)
    model = TestModel(custom_output_args={"answer": "greetings, Magus", "fragments": []}, call_tools=[])
    result = await agent.run("hello", deps=_deps(), model=model)
    assert isinstance(result.output, BridgeReply)
    assert result.output.answer == "greetings, Magus"


@pytest.mark.asyncio
async def test_approval_tool_yields_deferred_requests() -> None:
    """Calling the approval-required coven tool yields a `DeferredToolRequests`."""
    agent = default_forge().agent_for(THE_FIRST_ONE_SPEC)
    # TestModel calls every bound tool by default; the coven tool requires approval.
    result = await agent.run("swap the coven", deps=_deps(), model=TestModel())
    assert isinstance(result.output, DeferredToolRequests)
    assert result.output.approvals[0].tool_name == "request_coven_swap"
