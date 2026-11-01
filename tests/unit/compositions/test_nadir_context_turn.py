"""An adaptive Nadir turn settles two native Runs before terminal replay is denied."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import pytest
from pydantic_ai.models import override_allow_model_requests
from scripts.reach_worker import build_runtime

from lychd.compositions.reach.operator_model_wire import canonical_json, validate_generation_payload
from lychd.compositions.reach.operator_wire import ReachHistoryEntry
from lychd.domain.cortex.runs import RunStatus
from tests.unit.compositions.test_reach_conversation import completion, policy, profile
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_request


@pytest.mark.asyncio
async def test_read_more_then_cumulative_history_answers_in_two_distinct_native_runs() -> None:
    binding = profile().model_copy(update={"adaptive_context": True})
    recent = ReachHistoryEntry(
        subject_id="bot:one",
        subject_label="Observed Bot",
        event_id="recent",
        conversation_id="channel:one",
        text="The decision needs an earlier explanation.",
        occurred_at=NOW - timedelta(seconds=2),
    )
    older = recent.model_copy(
        update={
            "event_id": "older",
            "subject_id": "person:one",
            "subject_label": "Current Person",
            "text": "The earlier decision preserves the native Graph boundary.",
            "occurred_at": NOW - timedelta(seconds=3),
        }
    )
    anchor = older.model_copy(update={"event_id": "anchor", "occurred_at": NOW - timedelta(seconds=4)})
    first = make_request(action="converse", subject_label="Current Person").model_copy(
        update={
            "history": (recent,),
            "history_state": "more",
            "context_round": 0,
            "reply_to_event_id": anchor.event_id,
            "reply_anchor": anchor,
        }
    )
    second = first.model_copy(
        update={
            "request_id": "request:round1",
            "context_round": 1,
            "history_state": "exhausted",
            "history": (older, recent),
        }
    )
    prompts: list[dict[str, Any]] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        assert operation == "generate"
        body = validate_generation_payload(binding, payload)
        assert "tools" not in body
        prompts.append(json.loads(body["messages"][-1]["content"]))
        decision = (
            {"kind": "read_more", "text": "Read the earlier explanation."}
            if len(prompts) == 1
            else {"kind": "answer", "text": "It preserves the native Graph boundary."}
        )
        return completion(canonical_json(decision))

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        started_at=STARTED,
        clock=lambda: NOW,
    )
    try:
        assert runtime.ready.adaptive_context
        with override_allow_model_requests(True):  # noqa: FBT003 - explicit third-party model permission
            requested = await runtime.process(first)
            assert requested.status == "need_context"
            answered = await runtime.process(second)
            assert answered.status == "conversation"
            replay = await runtime.process(second.model_copy(update={"request_id": "request:replay"}))
            continuation = await runtime.process(second.model_copy(update={"context_round": 2}))
        assert answered.text == "It preserves the native Graph boundary."
        assert requested.run_id != answered.run_id
        assert len(prompts) == 2
        assert [prompt["context_round"] for prompt in prompts] == [0, 1]
        assert [prompt["history_state"] for prompt in prompts] == ["more", "exhausted"]
        assert [[entry["event_id"] for entry in prompt["recent_messages"]] for prompt in prompts] == [
            ["recent"],
            ["older", "recent"],
        ]
        assert prompts[0]["recent_messages"][0]["subject_label"] == binding.persona_name
        assert all(prompt["reply_to_event_id"] == "anchor" for prompt in prompts)
        assert all(prompt["reply_anchor"]["text"] == anchor.text for prompt in prompts)
        for result in (requested, answered):
            assert result.run_id is not None
            run = await runtime.substrate.ledger.get(result.run_id)
            assert run is not None
            assert run.status is RunStatus.DONE
            assert run.sigil_name == "reach.guest"
            assert run.sigil_scopes == frozenset()
            turn = await runtime.sessions.settled_turn_for_run(run.run_id)
            assert turn is not None
            assert turn.content == result.model_dump_json()
        assert (replay.status, replay.reason, replay.run_id) == ("refused", "duplicate", None)
        assert (continuation.status, continuation.reason, continuation.run_id) == (
            "refused",
            "context_continuation",
            None,
        )
        assert len(await runtime.substrate.ledger.list_by_status(RunStatus.DONE)) == 2
        assert runtime.substrate.leases.active() == []
    finally:
        await runtime.aclose()
