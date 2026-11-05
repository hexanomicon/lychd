"""Bounded, grant-aware context assembly.

White-box cache assertions prove active-run ownership and release bounds.
"""

import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
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


def _legacy_messages(messages: list[ModelMessage]) -> list[Any]:
    history = json.loads(ModelMessagesTypeAdapter.dump_json(messages))
    for message in history:
        message.pop("run_id", None)
    return history


def _tool_exchange() -> list[ModelMessage]:
    return [
        ModelRequest.user_text_prompt("look up the answer"),
        ModelResponse(parts=[ToolCallPart("lookup", {"query": "answer"}, tool_call_id="call-1")]),
        ModelRequest(parts=[ToolReturnPart("lookup", "found", tool_call_id="call-1")]),
        ModelResponse(parts=[TextPart("the answer")]),
    ]


def _assert_complete_tool_pairs(history: list[Any]) -> None:
    pending: set[str] = set()
    for message in ModelMessagesTypeAdapter.validate_python(history):
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                assert part.tool_call_id not in pending
                pending.add(part.tool_call_id)
            elif isinstance(part, ToolReturnPart):
                assert part.tool_call_id in pending, f"orphan tool result: {part.tool_call_id}"
                pending.remove(part.tool_call_id)
    assert not pending, f"unanswered tool calls: {pending}"


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


def test_default_context_window_keeps_twenty_complete_legacy_exchanges() -> None:
    history = _legacy_messages(_tool_exchange())
    for index in range(19):
        history.extend(
            _legacy_messages(
                [ModelRequest.user_text_prompt(f"question {index}"), ModelResponse(parts=[TextPart("answer")])],
            ),
        )
    context = ContextOrchestrator(registry=cast("Any", _Registry()))

    assembled = context.assemble(run_id="current", session_id="session", query="next", history=history)

    _assert_complete_tool_pairs(assembled.model_history())
    assert len(assembled.state_window) == 42
    assert assembled.state_window == history


@pytest.mark.parametrize("turn_window", [1, 2])
def test_legacy_tool_rounds_and_retries_remain_one_exchange(turn_window: int) -> None:
    old = _exchange("old", "old question", "old answer")
    latest = _legacy_messages(_tool_exchange()[:2])
    latest.append(
        {
            "kind": "request",
            "parts": [
                {"part_kind": "retry-prompt", "content": "try again", "tool_name": "lookup", "tool_call_id": "call-1"}
            ],
        }
    )
    latest.extend(
        _legacy_messages(
            [
                ModelResponse(parts=[ToolCallPart("lookup", {"query": "again"}, tool_call_id="call-2")]),
                ModelRequest(parts=[ToolReturnPart("lookup", "unavailable", tool_call_id="call-2", outcome="failed")]),
                ModelResponse(parts=[TextPart("invalid answer")]),
            ]
        )
    )
    latest.append(
        {"kind": "request", "parts": [{"part_kind": "retry-prompt", "content": "answer must match the schema"}]}
    )
    latest.extend(_legacy_messages([ModelResponse(parts=[TextPart("valid answer")])]))
    context = ContextOrchestrator(registry=cast("Any", _Registry()), turn_window=turn_window)

    assembled = context.assemble(run_id="current", session_id="session", query="next", history=[*old, *latest])

    _assert_complete_tool_pairs(assembled.model_history())
    assert assembled.state_window == ([*old, *latest] if turn_window == 2 else latest)


@pytest.mark.parametrize("tool_retry", [False, True])
def test_legacy_user_prompt_with_tool_result_remains_a_continuation(*, tool_retry: bool) -> None:
    history = _legacy_messages(_tool_exchange())
    result = (
        {"part_kind": "retry-prompt", "content": "try again", "tool_name": "lookup", "tool_call_id": "call-1"}
        if tool_retry
        else history[2]["parts"][0]
    )
    history[2]["parts"] = [result, {"part_kind": "user-prompt", "content": "continue with this result"}]
    context = ContextOrchestrator(registry=cast("Any", _Registry()), turn_window=1)

    assembled = context.assemble(run_id="current", session_id="session", query="next", history=history)

    _assert_complete_tool_pairs(assembled.model_history())
    assert assembled.state_window == history


@pytest.mark.parametrize("has_newer_exchange", [False, True])
@pytest.mark.parametrize("tool_exchange_fits", [False, True])
def test_grant_budget_keeps_or_drops_whole_legacy_tool_exchange(
    *,
    has_newer_exchange: bool,
    tool_exchange_fits: bool,
) -> None:
    tool_history = _legacy_messages(_tool_exchange())
    newer = _exchange("newer", "new question", "new answer") if has_newer_exchange else []
    context = ContextOrchestrator(registry=cast("Any", _Registry()))
    floor = context.assemble(run_id="current", session_id="session", query="next", grant=_grant())
    fixed_cost = sum(len(block.text) for block in floor.blocks if block.layer < 5) + len("next") + len("[]")
    # A tail-only allowance reproduces the bug: the tool return fits, but its call does not.
    allowed_tool = tool_history if tool_exchange_fits else tool_history[2:]
    history_cost = len(json.dumps(allowed_tool, sort_keys=True, separators=(",", ":")))
    if newer:
        history_cost += len(json.dumps(newer, sort_keys=True, separators=(",", ":")))
    token_window = (fixed_cost + history_cost + (2 if tool_exchange_fits else 0)) // 3

    assembled = context.assemble(
        run_id="current",
        session_id="session",
        query="next",
        history=[*tool_history, *newer],
        grant=_grant(generation_window=token_window),
    )

    _assert_complete_tool_pairs(assembled.model_history())
    assert assembled.state_window == ([*tool_history, *newer] if tool_exchange_fits else newer)


@pytest.mark.parametrize("legacy_is_latest", [False, True])
def test_mixed_legacy_and_identified_exchanges_keep_the_latest_group(*, legacy_is_latest: bool) -> None:
    legacy = _legacy_messages(_tool_exchange())
    identified = _exchange("identified", "new question", "new answer")
    history = [*identified, *legacy] if legacy_is_latest else [*legacy, *identified]
    context = ContextOrchestrator(registry=cast("Any", _Registry()), turn_window=1)

    assembled = context.assemble(run_id="current", session_id="session", query="next", history=history)

    _assert_complete_tool_pairs(assembled.model_history())
    assert assembled.state_window == (legacy if legacy_is_latest else identified)


def test_explicit_run_identity_keeps_multiple_user_requests_together() -> None:
    previous = _exchange("old", "old question", "old answer")
    latest = [*_exchange("latest", "first request", "first answer"), *_exchange("latest", "follow-up", "answer")]
    context = ContextOrchestrator(registry=cast("Any", _Registry()), turn_window=1)

    assembled = context.assemble(run_id="current", session_id="session", query="next", history=[*previous, *latest])

    assert assembled.state_window == latest


def test_legacy_role_messages_keep_user_boundaries() -> None:
    old = [{"role": "user", "content": "old question"}, {"role": "assistant", "content": "old answer"}]
    latest = [{"role": "user", "content": "new question"}, {"role": "assistant", "content": "new answer"}]
    context = ContextOrchestrator(registry=cast("Any", _Registry()), turn_window=1)

    assembled = context.assemble(run_id="current", session_id="session", query="next", history=[*old, *latest])

    assert assembled.state_window == latest


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


def test_transient_projection_is_reserved_without_entering_instructions_or_history() -> None:
    context = ContextOrchestrator(registry=cast("Any", _Registry()))
    baseline = context.assemble(run_id="baseline", session_id="s", query="query")
    fixed = (
        sum(len(block.text) for block in baseline.blocks if block.layer <= 4)
        + len("query")
        + len(json.dumps(baseline.continuation))
    )
    context.char_cap = fixed + 100
    assembled = context.assemble(
        run_id="run",
        session_id="s",
        query="query",
        transient_chars=100,
        history=_exchange("old", "old question", "old answer"),
    )
    assert assembled.state_window == []
    assert assembled.floor_text() == baseline.floor_text()
    assert assembled.query == "query"
    assert baseline.transient_chars == 0
    assert assembled.transient_chars == 100
    cached = context.get("run")
    assert cached is not None
    assert cached.transient_chars == assembled.transient_chars
    with pytest.raises(ContextBudgetExceededError):
        context.assemble(run_id="overflow", session_id="s", query="query", transient_chars=101)
    with pytest.raises(ValueError, match="negative"):
        context.assemble(run_id="negative", session_id="s", query="query", transient_chars=-1)


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
    )
    baseline = context.assemble(run_id="baseline", session_id="session", query="current")
    context.char_cap = (
        sum(len(block.text) for block in baseline.blocks if block.layer < 5)
        + len("current")
        + len(json.dumps(continuation, sort_keys=True, separators=(",", ":")))
    )

    assembled = context.assemble(
        run_id="run-current",
        session_id="session",
        query="current",
        history=old,
        continuation=continuation,
    )

    assert assembled.continuation == continuation
    assert assembled.state_window == []
    assert assembled.model_history()[-len(continuation) :] == continuation
    context.char_cap -= 1
    with pytest.raises(ContextBudgetExceededError):
        context.assemble(run_id="one-character-short", session_id="session", query="current", continuation=continuation)


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
