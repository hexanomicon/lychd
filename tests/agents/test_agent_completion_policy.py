"""A dependency upgrade must not execute extra tools alongside a final output."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from pydantic import BaseModel
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import DeltaToolCall, FunctionModel
from pydantic_ai.run import AgentRunResultEvent
from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.deps import LychDDeps
from lychd.agents.factory import AgentSpec, build_agent

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.models.function import AgentInfo


class _Answer(BaseModel):
    answer: str


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming", [False, True])
async def test_final_output_does_not_execute_sibling_effect(*, streaming: bool) -> None:
    effects: list[str] = []
    toolset: FunctionToolset[LychDDeps] = FunctionToolset(id="completion-policy")

    async def write_candidate() -> str:
        effects.append("written")
        return "written"

    toolset.add_function(write_candidate)

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        assert messages
        return ModelResponse(
            parts=[
                ToolCallPart("write_candidate", {}, tool_call_id="effect"),
                ToolCallPart(info.output_tools[0].name, {"answer": "finished"}, tool_call_id="output"),
            ]
        )

    async def respond_stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[dict[int, DeltaToolCall]]:
        assert messages
        yield {
            0: DeltaToolCall(name="write_candidate", json_args="{}", tool_call_id="effect"),
            1: DeltaToolCall(name=info.output_tools[0].name, json_args='{"answer":"finished"}', tool_call_id="output"),
        }

    agent = build_agent(
        AgentSpec(
            name="completion-policy",
            instructions_key="completion-policy-v1",
            instructions="Return the answer; the test supplies the model response.",
            output_types=(_Answer,),
            toolset_names=("writer",),
            writes=True,
        ),
        toolset_factories={"writer": lambda: toolset},
        mutating=frozenset({"writer"}),
    )
    model = FunctionModel(respond, stream_function=respond_stream)
    # This tool has no context argument; policy must refuse it without reading dependencies.
    deps = cast("LychDDeps", object())
    if streaming:
        result = None
        async with agent.run_stream_events("complete", model=model, deps=deps) as stream:
            async for event in stream:
                if isinstance(event, AgentRunResultEvent):
                    result = event.result
        assert result is not None
    else:
        result = await agent.run("complete", model=model, deps=deps)

    assert result.output == _Answer(answer="finished")
    assert effects == []
