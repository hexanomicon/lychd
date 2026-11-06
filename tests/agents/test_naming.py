"""Pinned names reach actual model instructions and the same budgeted Context block."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, cast

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from lychd.agents.deps import LychDDeps
from lychd.agents.factory import AgentSpec
from lychd.agents.router import Intent
from lychd.agents.the_first_one import THE_FIRST_ONE_SPEC, named_agent_spec
from lychd.agents.workflows import builtin_workflow_registry, resolve_named_workflow
from lychd.agents.workflows.archive_chat import ARCHIVE_AGENT_SPEC
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT, BRIDGE_CHAT_BOUND, BridgeChatState, WeaveContext
from lychd.agents.workflows.scout_chat import SCOUT_AGENT_SPEC
from lychd.agents.workflows.semantic_chat import SEMANTIC_AGENT_SPEC
from lychd.domain.cortex.context import IDENTITY_BLOCK_TEXT, ContextBudgetExceededError, naming_identity_block
from lychd.domain.naming import NamingSnapshot
from tests.agents.conftest import make_services
from tests.agents.fakes import FakeConsents, FakeEvents, FakeOrchestrator, FakeTurns

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.models.function import AgentInfo, DeltaToolCall

    from lychd.agents.workflows.base import Workflow


def _names() -> NamingSnapshot:
    return NamingSnapshot(
        magus_name="Zenith Runeweaver",
        primus_name="Nadir Shadowdancer",
        magus_origin="manual",
        primus_origin="self_chosen",
        revision=1,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("workflow", [BRIDGE_CHAT, BRIDGE_CHAT_BOUND], ids=["bridge-1", "bridge-2"])
async def test_bridge_graph_uses_retained_names_in_actual_model_instructions(workflow: Workflow) -> None:
    instructions: list[str | None] = []

    async def answer(_messages: list[ModelMessage], info: AgentInfo) -> AsyncGenerator[str | dict[int, DeltaToolCall]]:
        from pydantic_ai.models.function import DeltaToolCall

        instructions.append(info.instructions)
        yield {
            0: DeltaToolCall(
                name=info.output_tools[0].name, json_args='{"answer":"hello","fragments":[]}', tool_call_id="output"
            )
        }

    services = make_services(
        model=FunctionModel(stream_function=answer),
        events=FakeEvents(),
        turns=FakeTurns(),
        consents=FakeConsents(),
        orchestrator=FakeOrchestrator(),
    )
    intent = Intent(
        session_id="session",
        run_id="run",
        prompt="hello",
        admitted_naming=_names(),
        admitted_capability_key="chat:test" if workflow is BRIDGE_CHAT_BOUND else None,
    )
    workflow = resolve_named_workflow(builtin_workflow_registry(), workflow)
    state = cast("BridgeChatState", workflow.make_state(intent))
    # Restore through JSON as a parked worker does; no live naming store is present.
    state = type(state).model_validate_json(state.model_dump_json())
    async with workflow.graph.iter(inputs=WeaveContext(), state=state, deps=services) as run:
        async for _ in run:
            pass
    expected = naming_identity_block(_names())
    assert instructions
    assert all(expected.text in (value or "") for value in instructions)
    assert all("You are The First One" not in (value or "") for value in instructions)
    assembled = services.context.get("run")
    assert assembled is not None
    assert assembled.blocks[0] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("spec", [THE_FIRST_ONE_SPEC, ARCHIVE_AGENT_SPEC, SCOUT_AGENT_SPEC, SEMANTIC_AGENT_SPEC])
async def test_every_bridge_profile_preserves_rules_and_sends_named_instruction(spec: AgentSpec) -> None:
    captured: list[str | None] = []

    async def answer(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        captured.append(info.instructions)
        if info.output_tools:
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"answer": "hello", "fragments": []})])
        return ModelResponse(parts=[TextPart("hello")])

    model = FunctionModel(answer)
    services = make_services(
        model=model,
        events=FakeEvents(),
        turns=FakeTurns(),
        consents=FakeConsents(),
        orchestrator=FakeOrchestrator(),
    )
    naming = _names()
    selected = named_agent_spec(spec, naming)
    base = naming_identity_block(naming)
    assert selected.name == spec.name
    assert selected.instructions == base.text + spec.instructions.removeprefix(IDENTITY_BLOCK_TEXT)
    async with services.dispatcher.lease_grant(family="chat", run_id="run") as grant:
        services.context.assemble(run_id="run", session_id="session", query="hello", naming=naming, grant=grant)
        deps = LychDDeps(
            sigil=services.sigil_provider(),
            grant=grant,
            dispatcher=services.dispatcher,
            orchestrator=services.orchestrator,
            context=services.context,
            run_id="run",
            step_id="step",
            priority=50,
        )
        await services.forge.agent_for(selected).run("hello", model=model, deps=deps)
    assert captured
    assert all(selected.instructions in (value or "") for value in captured)
    assert named_agent_spec(spec, None) is spec


def test_naming_values_are_json_literals_and_have_revision_specific_keys() -> None:
    names = _names()
    first = naming_identity_block(names)
    assert json.dumps(names.magus_name) in first.text
    assert json.dumps(names.primus_name) in first.text
    assert naming_identity_block(names.model_copy(update={"revision": 2})).key != first.key
    assert naming_identity_block(names.model_copy(update={"primus_name": "Aster Runeweaver"})).key != first.key


def test_named_identity_counts_against_actual_context_budget() -> None:
    services = make_services(
        model=None,
        events=FakeEvents(),
        turns=FakeTurns(),
        consents=FakeConsents(),
        orchestrator=FakeOrchestrator(),
    )
    services.context.char_cap = len(IDENTITY_BLOCK_TEXT) + 200
    services.context.assemble(run_id="old", session_id="session", query="hello")
    with pytest.raises(ContextBudgetExceededError):
        services.context.assemble(run_id="named", session_id="session", query="hello", naming=_names())


@pytest.mark.parametrize("change", [{"revision": 0}, {"primus_name": "x" * 97}, {"magus_name": "name\ncommand"}])
def test_unchecked_naming_copy_cannot_enter_model_instruction(change: dict[str, object]) -> None:
    invalid = _names().model_copy(update=change)
    with pytest.raises(ValidationError):
        named_agent_spec(THE_FIRST_ONE_SPEC, invalid)
