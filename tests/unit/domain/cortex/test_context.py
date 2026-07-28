"""Bounded, grant-aware context assembly."""

from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
)

from lychd.domain.animation.capabilities import CapabilityGrant
from lychd.domain.cortex.context import ContextBudgetExceededError, ContextOrchestrator


class _Registry:
    def list_capability_states(self) -> list[Any]:
        return []


def _grant(*, generation_window: int = 1024, spec_window: int = 2048) -> CapabilityGrant:
    return cast(
        "CapabilityGrant",
        SimpleNamespace(
            spec=SimpleNamespace(key="chat:local", max_context=spec_window),
            generation=SimpleNamespace(max_context=generation_window),
        ),
    )


def _exchange(run_id: str, prompt: str, answer: str) -> list[Any]:
    messages = [
        ModelRequest(
            parts=ModelRequest.user_text_prompt(prompt).parts,
            run_id=run_id,
        ),
        ModelResponse(parts=[TextPart(answer)], run_id=run_id),
    ]
    return list(ModelMessagesTypeAdapter.dump_python(messages, mode="json"))


def test_context_keeps_newest_complete_message_group() -> None:
    first = _exchange("run-1", "old", "old reply")
    second = _exchange("run-2", "new", "new reply")
    context = ContextOrchestrator(
        registry=cast("Any", _Registry()),
        turn_window=1,
    )

    assembled = context.assemble(
        run_id="run-3",
        session_id="session",
        query="current",
        history=[*first, *second],
        grant=_grant(),
    )

    assert assembled.state_window == second


def test_bound_environment_replaces_unbound_floor_and_generation_window_wins() -> None:
    context = ContextOrchestrator(registry=cast("Any", _Registry()))
    unbound = context.assemble(run_id="run", session_id="session", query="hello")
    bound = context.assemble(
        run_id="run",
        session_id="session",
        query="hello",
        grant=_grant(generation_window=1024, spec_window=4096),
    )

    assert "active capability: none" in unbound.floor_text()
    assert "active capability: chat:local" in bound.floor_text()
    assert bound.context_window == 1024


def test_fixed_floor_over_budget_fails_loudly() -> None:
    context = ContextOrchestrator(registry=cast("Any", _Registry()), char_cap=1)

    with pytest.raises(ContextBudgetExceededError):
        context.assemble(run_id="run", session_id="session", query="hello")


def test_required_continuation_is_indivisible_and_rebounds_settled_history() -> None:
    old = _exchange("run-old", "old", "old reply")
    continuation = _exchange("provider-hop-a", "current", "tool call")
    context = ContextOrchestrator(
        registry=cast("Any", _Registry()),
        turn_window=20,
        char_cap=1_350,
    )

    assembled = context.assemble(
        run_id="run-current",
        session_id="session",
        query="current",
        history=old,
        continuation=continuation,
    )

    assert assembled.continuation == continuation
    assert assembled.model_history()[-len(continuation) :] == continuation


def test_required_continuation_over_budget_fails_loudly() -> None:
    context = ContextOrchestrator(registry=cast("Any", _Registry()), char_cap=600)
    continuation = [{"kind": "request", "run_id": "hop", "parts": [{"content": "x" * 1_000}]}]

    with pytest.raises(ContextBudgetExceededError, match="required continuation"):
        context.assemble(
            run_id="run",
            session_id="session",
            query="current",
            continuation=continuation,
        )
