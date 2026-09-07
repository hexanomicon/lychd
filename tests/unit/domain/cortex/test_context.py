"""Bounded, grant-aware context assembly.

White-box cache assertions prove active-run ownership and release bounds.
"""

from copy import deepcopy
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
    def __init__(self) -> None:
        self.states: list[Any] = []

    def list_capability_states(self) -> list[Any]:
        return self.states


def _grant(*, generation_window: int = 1024, spec_window: int = 2048) -> CapabilityGrant:
    return cast(
        "CapabilityGrant",
        SimpleNamespace(
            spec=SimpleNamespace(
                key="chat:local",
                max_context=spec_window,
                generation_profile=SimpleNamespace(max_context=generation_window),
            ),
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


def _environment(assembled: Any) -> Any:
    return next(block for block in assembled.blocks if block.layer == 3)


def _retained_environment_cache_sizes(context: ContextOrchestrator) -> tuple[int, int]:
    internals = cast("Any", context)
    return len(internals._env_snapshots), len(internals._env_snapshot_key_by_run)


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


@pytest.mark.parametrize("turn_window", [0, -1])
def test_nonpositive_history_window_preserves_only_required_continuation(turn_window: int) -> None:
    history = [*_exchange("settled-1", "old", "old reply"), *_exchange("settled-2", "new", "new reply")]
    continuation = _exchange("current", "current", "tool call")
    context = ContextOrchestrator(registry=cast("Any", _Registry()), turn_window=turn_window)

    assembled = context.assemble(
        run_id="run",
        session_id="session",
        query="query",
        history=history,
        continuation=continuation,
    )

    assert assembled.state_window == []
    assert assembled.continuation == continuation
    assert assembled.model_history() == continuation


def test_context_detaches_input_history_and_required_continuation() -> None:
    history = _exchange("settled", "old", "old reply")
    continuation = _exchange("current", "current", "tool call")
    expected_history = deepcopy(history)
    expected_continuation = deepcopy(continuation)
    context = ContextOrchestrator(registry=cast("Any", _Registry()))
    assembled = context.assemble(
        run_id="run",
        session_id="session",
        query="query",
        history=history,
        continuation=continuation,
    )
    state_block = next(block.text for block in assembled.blocks if block.layer == 5)

    history[0]["parts"][0]["content"] = "x" * context.char_cap
    continuation[0]["parts"][0]["content"] = "changed after admission"

    assert assembled.state_window == expected_history
    assert assembled.continuation == expected_continuation
    assert next(block.text for block in assembled.blocks if block.layer == 5) == state_block
    assert assembled.model_history() == [*expected_history, *expected_continuation]


def test_context_detaches_every_cached_projection_and_model_history() -> None:
    history = _exchange("settled", "old", "old reply")
    continuation = _exchange("current", "current", "tool call")
    expected_history = deepcopy(history)
    expected_continuation = deepcopy(continuation)
    context = ContextOrchestrator(registry=cast("Any", _Registry()))
    assembled = context.assemble(
        run_id="run",
        session_id="session",
        query="query",
        history=history,
        continuation=continuation,
    )

    projected = assembled.model_history()
    projected[0]["parts"][0]["content"] = "changed model history"
    projected[-1]["parts"][0]["content"] = "changed model continuation"
    assert assembled.state_window == expected_history
    assert assembled.continuation == expected_continuation

    assembled.state_window[0]["parts"][0]["content"] = "changed admission view"
    assembled.continuation.clear()
    cached = context.get("run")
    assert cached is not None
    assert cached.state_window == expected_history
    assert cached.continuation == expected_continuation
    cached.state_window.clear()
    cached.continuation[0]["parts"][0]["content"] = "changed cache view"

    retained = context.get("run")
    assert retained is not None
    assert retained.state_window == expected_history
    assert retained.continuation == expected_continuation


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


def test_environment_snapshot_is_shared_until_every_referencing_run_releases() -> None:
    registry = _Registry()
    context = ContextOrchestrator(registry=cast("Any", registry))

    first = context.assemble(run_id="run-a", session_id="session", query="first")
    second = context.assemble(run_id="run-b", session_id="session", query="second")
    first_environment = _environment(first)
    assert _environment(second) is first_environment

    context.release("run-a")
    registry.states = [SimpleNamespace(capability_key="chat:warm", warm=True, is_active=False)]
    rebound = context.assemble(run_id="run-b", session_id="session", query="again")
    assert _environment(rebound) is first_environment
    assert "warm coven: none" in rebound.floor_text()

    context.release("run-b")
    assert _retained_environment_cache_sizes(context) == (0, 0)

    refreshed = context.assemble(run_id="run-c", session_id="session", query="fresh")
    assert _environment(refreshed) is not first_environment
    assert "warm coven: chat:warm" in refreshed.floor_text()

    # A duplicate late release from the old generation cannot evict the new owner.
    context.release("run-b")
    registry.states = []
    still_fresh = context.assemble(run_id="run-c", session_id="session", query="still fresh")
    assert _environment(still_fresh) is _environment(refreshed)
    assert "warm coven: chat:warm" in still_fresh.floor_text()


def test_release_bounds_environment_snapshots_across_many_epochs() -> None:
    context = ContextOrchestrator(registry=cast("Any", _Registry()))

    for index in range(1_000):
        context.assemble(
            run_id="long-run",
            session_id="session",
            grant_epoch=index,
            query="hello",
        )

    assert _retained_environment_cache_sizes(context) == (1, 1)
    context.release("long-run")
    assert context.get("long-run") is None
    assert _retained_environment_cache_sizes(context) == (0, 0)


def test_failed_assembly_does_not_retain_an_environment_snapshot() -> None:
    context = ContextOrchestrator(registry=cast("Any", _Registry()), char_cap=1)

    with pytest.raises(ContextBudgetExceededError):
        context.assemble(run_id="run", session_id="session", query="hello")

    assert _retained_environment_cache_sizes(context) == (0, 0)


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
