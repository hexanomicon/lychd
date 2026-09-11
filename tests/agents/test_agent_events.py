"""Agent event consumption releases run resources before its grant scope exits."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.workflows.nodes import pump_agent_events

if TYPE_CHECKING:
    from lychd.agents.deps import LychDDeps
    from lychd.domain.cortex.events import RunEmitter


@pytest.mark.asyncio
async def test_event_consumer_failure_closes_agent_toolset_before_return() -> None:
    class ScopedToolset(FunctionToolset[Any]):
        closed = False

        async def __aexit__(self, *args: object) -> None:
            await super().__aexit__(*args)
            self.closed = True

    class FailingEmitter:
        def token(self, _text: str) -> None:
            msg = "projection failed"
            raise RuntimeError(msg)

    toolset = ScopedToolset()
    agent = Agent(output_type=str)
    with pytest.raises(RuntimeError, match="projection failed"):
        await pump_agent_events(
            agent,
            "hello",
            deps=cast("LychDDeps", object()),
            model=TestModel(custom_output_text="hello", call_tools=[]),
            model_settings=None,
            toolsets=[toolset],
            emit=cast("RunEmitter", FailingEmitter()),
        )
    assert toolset.closed, "run toolsets must close before the caller can release the grant model"
