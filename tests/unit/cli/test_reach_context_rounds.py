"""Exact continuation admission before any fixture session or fresh native Run exists."""

from __future__ import annotations

from datetime import timedelta

import pytest
from scripts import reach_worker as worker

from lychd.compositions.reach import conversation_session
from lychd.compositions.reach.operator_wire import (
    ReachHistoryEntry,
    ReachWorkerRequest,
    ReachWorkerResult,
    ReachWorkerStatus,
)
from tests.unit.compositions.test_reach_conversation import profile
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_policy, make_request


def entry(event_id: str, seconds: int = 2) -> ReachHistoryEntry:
    return ReachHistoryEntry(
        subject_id="person:two",
        event_id=event_id,
        conversation_id="channel:one",
        text=f"Quoted message {event_id}",
        occurred_at=NOW - timedelta(seconds=seconds),
    )


def request(context_round: int = 0, history: tuple[ReachHistoryEntry, ...] = ()) -> ReachWorkerRequest:
    return make_request(action="converse").model_copy(
        update={
            "context_round": context_round,
            "history_state": "more",
            "history": history,
            "reply_to_event_id": "anchor",
            "reply_anchor": entry("anchor", 10),
        }
    )


def result(request: ReachWorkerRequest, status: ReachWorkerStatus = "need_context") -> ReachWorkerResult:
    return ReachWorkerResult(
        request_id=request.request_id,
        run_id="run:round",
        status=status,
        policy_digest=make_policy().digest,
        corpus_digest=make_corpus().digest,
    )


def admit(rounds: conversation_session.ContextRounds, request: ReachWorkerRequest) -> None:
    digest = conversation_session.request_digest(request)
    assert rounds.reason(request, digest, adaptive=True) is None
    rounds.admit(request, digest)


def awaiting() -> tuple[conversation_session.ContextRounds, ReachWorkerRequest, ReachWorkerRequest]:
    rounds = conversation_session.ContextRounds()
    first = request(history=(entry("recent"),))
    admit(rounds, first)
    rounds.settled(first, result(first), adaptive=True)
    second = request(1, (entry("older", 3), *first.history))
    return rounds, first, second


@pytest.mark.parametrize("context_round", [1, 2])
def test_initial_request_cannot_skip_round_zero(context_round: int) -> None:
    rounds = conversation_session.ContextRounds()
    candidate = request(context_round)
    assert rounds.reason(candidate, conversation_session.request_digest(candidate), adaptive=True) == "context_round"
    assert rounds.admitted == 0
    assert rounds.events == {}


def test_only_settled_need_context_opens_exact_next_round() -> None:
    rounds = conversation_session.ContextRounds()
    first = request(history=(entry("recent"),))
    second = request(1, (entry("older", 3), *first.history))
    admit(rounds, first)
    assert rounds.reason(second, conversation_session.request_digest(second), adaptive=True) == "context_continuation"
    rounds.settled(first, result(first), adaptive=True)
    skipped = second.model_copy(update={"context_round": 2})
    assert rounds.reason(skipped, conversation_session.request_digest(skipped), adaptive=True) == "context_round"
    admit(rounds, second)
    third = request(2, (entry("oldest", 4), *second.history))
    assert rounds.reason(third, conversation_session.request_digest(third), adaptive=True) == "context_continuation"
    rounds.settled(second, result(second), adaptive=True)
    admit(rounds, third)
    rounds.settled(third, result(third), adaptive=True)
    assert rounds.events[rounds.identity(third)].expected_round is None
    assert rounds.admitted == 3


@pytest.mark.parametrize("status", ["conversation", "clarify", "docs", "context", "empty", "refused", "error"])
def test_terminal_results_cannot_open_a_continuation(status: ReachWorkerStatus) -> None:
    rounds = conversation_session.ContextRounds()
    first = request(history=(entry("recent"),))
    admit(rounds, first)
    rounds.settled(first, result(first, status), adaptive=True)
    second = request(1, (entry("older", 3), *first.history))
    assert rounds.reason(second, conversation_session.request_digest(second), adaptive=True) == "context_continuation"


@pytest.mark.parametrize("history_state", ["disabled", "exhausted", "budget", "unavailable"])
def test_need_context_does_not_open_a_round_without_more_history(history_state: str) -> None:
    rounds = conversation_session.ContextRounds()
    first = request().model_copy(update={"history_state": history_state})
    admit(rounds, first)
    rounds.settled(first, result(first), adaptive=True)
    second = request(1, (entry("older", 3),))
    assert rounds.reason(second, conversation_session.request_digest(second), adaptive=True) == "context_continuation"


def test_profile_must_opt_in_when_opening_and_using_a_continuation() -> None:
    rounds, first, second = awaiting()
    assert rounds.reason(second, conversation_session.request_digest(second), adaptive=False) == "context_continuation"
    disabled = conversation_session.ContextRounds()
    admit(disabled, first)
    disabled.settled(first, result(first), adaptive=False)
    assert disabled.reason(second, conversation_session.request_digest(second), adaptive=True) == "context_continuation"


@pytest.mark.parametrize(
    "change",
    ["question", "subject", "conversation", "occurred_at", "reply_id", "reply_anchor", "missing_anchor"],
)
def test_continuation_pins_entire_event_and_reply_metadata(change: str) -> None:
    rounds, _, second = awaiting()
    changes = {
        "question": {"event": second.event.model_copy(update={"question": "Changed question"})},
        "subject": {"event": second.event.model_copy(update={"subject_id": "person:other"})},
        "conversation": {"event": second.event.model_copy(update={"conversation_id": "channel:other"})},
        "occurred_at": {"event": second.event.model_copy(update={"occurred_at": NOW})},
        "reply_id": {"reply_to_event_id": "other"},
        "reply_anchor": {"reply_anchor": entry("anchor", 11)},
        "missing_anchor": {"reply_anchor": None},
    }
    candidate = second.model_copy(update=changes[change])
    assert rounds.reason(candidate, conversation_session.request_digest(candidate), adaptive=True) == "context_binding"
    assert rounds.admitted == 1
    assert rounds.reason(second, conversation_session.request_digest(second), adaptive=True) is None


@pytest.mark.parametrize(
    "change",
    ["unchanged", "removed", "edited", "newer", "appended", "unsorted", "duplicate_id", "foreign"],
)
def test_continuation_requires_exact_cumulative_history_and_older_progress(change: str) -> None:
    rounds, first, second = awaiting()
    recent, older = first.history[0], second.history[0]
    histories = {
        "unchanged": first.history,
        "removed": (older,),
        "edited": (older, recent.model_copy(update={"text": "Changed quotation"})),
        "newer": (entry("newer", 1), recent),
        "appended": (recent, older),
        "unsorted": (older, entry("oldest", 4), recent),
        "duplicate_id": (recent.model_copy(update={"occurred_at": older.occurred_at}), recent),
        "foreign": (older.model_copy(update={"conversation_id": "channel:other"}), recent),
    }
    candidate = second.model_copy(update={"history": histories[change]})
    assert rounds.reason(candidate, conversation_session.request_digest(candidate), adaptive=True) == "context_history"
    assert rounds.admitted == 1
    assert rounds.reason(second, conversation_session.request_digest(second), adaptive=True) is None


def test_same_timestamp_uses_event_id_total_order_for_older_progress() -> None:
    rounds = conversation_session.ContextRounds()
    first = request(history=(entry("message:m"),))
    admit(rounds, first)
    rounds.settled(first, result(first), adaptive=True)
    second = request(1, (entry("message:a"), *first.history))
    admit(rounds, second)
    assert rounds.admitted == 2


def test_empty_initial_history_can_gain_strictly_older_entries() -> None:
    rounds = conversation_session.ContextRounds()
    first = request()
    admit(rounds, first)
    rounds.settled(first, result(first), adaptive=True)
    admit(rounds, request(1, (entry("older"),)))
    assert rounds.admitted == 2


def test_all_admitted_rounds_keep_legacy_duplicate_and_conflict_codes() -> None:
    rounds, first, second = awaiting()
    admit(rounds, second)
    for seen in (first, second):
        duplicate = seen.model_copy(update={"request_id": "another:request"})
        assert rounds.reason(duplicate, conversation_session.request_digest(duplicate), adaptive=True) == "duplicate"
        changed = seen.model_copy(update={"history_state": "exhausted"})
        assert (
            rounds.reason(changed, conversation_session.request_digest(changed), adaptive=True) == "duplicate_conflict"
        )
    assert rounds.admitted == 2


def test_each_admitted_round_consumes_the_generation_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(conversation_session, "MAX_REQUESTS", 2)
    rounds, first, second = awaiting()
    admit(rounds, second)
    rounds.settled(second, result(second), adaptive=True)
    third = request(2, (entry("oldest", 4), *second.history))
    assert rounds.reason(third, conversation_session.request_digest(third), adaptive=True) == "generation_budget"
    other = request().model_copy(update={"event": first.event.model_copy(update={"event_id": "event:other"})})
    assert rounds.reason(other, conversation_session.request_digest(other), adaptive=True) == "generation_budget"
    assert rounds.reason(first, conversation_session.request_digest(first), adaptive=True) == "duplicate"
    assert rounds.admitted == 2


@pytest.mark.parametrize("adaptive", [None, False, True])
@pytest.mark.asyncio
async def test_ready_advertises_only_the_selected_profiles_adaptive_capability(*, adaptive: bool | None) -> None:
    async def relay(_operation: str, _payload: str) -> str:
        pytest.fail("Ready construction must not request the model")

    selected = profile().model_copy(update={"adaptive_context": adaptive}) if adaptive is not None else None
    runtime = worker.build_runtime(
        make_policy(),
        make_corpus(),
        profile=selected,
        model_relay=relay if selected is not None else None,
        started_at=STARTED,
        clock=lambda: NOW,
    )
    try:
        assert runtime.ready.adaptive_context is (adaptive is True)
        assert runtime.ready.model_binding_digest == (selected.digest if selected is not None else None)
    finally:
        await runtime.aclose()
