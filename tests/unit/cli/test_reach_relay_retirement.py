"""Retired private responses remain inert without widening the shared worker pipe dialect."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

import pytest
from scripts.reach_worker import PipeModelRelay, build_runtime, serve

from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    OperatorModelResponse,
    canonical_json,
)
from lychd.compositions.reach.operator_wire import MAX_WIRE_BYTES
from lychd.compositions.reach.research_wire import OperatorResearchRequest, OperatorResearchResponse, ResearchOptions
from lychd.domain.cortex.runs import RunStatus
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_policy, make_request


def profile() -> OperatorConversationProfile:
    return OperatorConversationProfile(
        persona_name="Nadir",
        persona_instructions="Use attributed public evidence.",
        adaptive_context=True,
        research=ResearchOptions(enabled=True),
    )


def research_request(binding: OperatorConversationProfile) -> OperatorResearchRequest:
    return OperatorResearchRequest(
        call_id=str(uuid4()),
        request_id="request:retired-research",
        binding_digest=binding.digest,
        event=make_request(action="converse").event,
        plan="I will compare the supplied public evidence.",
        source_ids=(),
    )


def research_response(request: OperatorResearchRequest) -> OperatorResearchResponse:
    return OperatorResearchResponse(
        call_id=request.call_id,
        request_id=request.request_id,
        binding_digest=request.binding_digest,
        status="ok",
    )


def line(value: OperatorModelResponse | OperatorResearchResponse) -> bytes:
    return value.model_dump_json().encode("utf-8") + b"\n"


async def retire_research(relay: PipeModelRelay, request: OperatorResearchRequest, *, via_deadline: bool) -> None:
    if via_deadline:
        with pytest.raises(TimeoutError):
            async with asyncio.timeout(0):
                await relay.research(request)
    else:
        task = asyncio.create_task(relay.research(request))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert not relay.lock.locked()


@pytest.mark.parametrize("via_deadline", [False, True])
@pytest.mark.asyncio
async def test_late_research_after_cancel_or_timeout_does_not_poison_next_model_exchange(*, via_deadline: bool) -> None:
    binding = profile()
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    writes: list[dict[str, Any]] = []

    def write(raw: bytes) -> None:
        frame = json.loads(raw)
        writes.append(frame)
        if frame["kind"] == "model_request":
            reader.feed_data(
                line(
                    OperatorModelResponse(
                        call_id=frame["call_id"],
                        binding_digest=binding.digest,
                        status="ok",
                        payload_json=canonical_json({"answer": "fresh"}),
                    )
                )
            )

    relay = PipeModelRelay(binding, reader, write)
    request = research_request(binding)
    await retire_research(relay, request, via_deadline=via_deadline)
    assert [frame["kind"] for frame in writes] == ["research_request"]
    reader.feed_data(line(research_response(request)))
    assert await relay("probe", "{}") == canonical_json({"answer": "fresh"})
    assert [frame["kind"] for frame in writes] == ["research_request", "model_request"]
    assert relay.pending_inputs == []
    assert not relay.lock.locked()


@pytest.mark.asyncio
async def test_partial_late_response_survives_cancelled_read_and_is_discarded_when_completed() -> None:
    binding = profile()
    request = research_request(binding)
    late = line(research_response(request))
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)

    def write(raw: bytes) -> None:
        frame = json.loads(raw)
        if frame["kind"] == "research_request":
            reader.feed_data(late[: len(late) // 2])
        else:
            reader.feed_data(
                line(
                    OperatorModelResponse(
                        call_id=frame["call_id"], binding_digest=binding.digest, status="ok", payload_json="{}"
                    )
                )
            )

    relay = PipeModelRelay(binding, reader, write)
    await retire_research(relay, request, via_deadline=False)
    reader.feed_data(late[len(late) // 2 :])
    assert await relay("probe", "{}") == "{}"
    assert relay.pending_inputs == []


@pytest.mark.parametrize("change", ["kind", "request", "binding", "extra", "body"])
@pytest.mark.asyncio
async def test_retired_uuid_does_not_grant_foreign_or_malformed_frames_a_discard_bypass(change: str) -> None:
    binding = profile()
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    writes: list[bytes] = []
    relay = PipeModelRelay(binding, reader, writes.append)
    request = research_request(binding)
    await retire_research(relay, request, via_deadline=False)
    value = research_response(request).model_dump(mode="json")
    if change == "kind":
        raw = line(OperatorModelResponse(call_id=request.call_id, binding_digest=binding.digest, status="ok"))
    else:
        if change == "request":
            value["request_id"] = "request:foreign"
        elif change == "binding":
            value["binding_digest"] = "0" * 64
        elif change == "extra":
            value["operation"] = "execute"
        else:
            value["sources"] = [{"id": "web:invented", "text": "foreign body"}]
        raw = json.dumps(value).encode("utf-8") + b"\n"
    with pytest.raises(
        ValueError, match=r"retired_response_binding|research_response_binding|OperatorResearchResponse"
    ):
        relay.discard_late(raw)
    assert relay.discard_late(line(research_response(request)))
    assert len(writes) == 1


@pytest.mark.asyncio
async def test_unrecognized_uuid_is_never_discarded_just_because_its_binding_matches() -> None:
    binding = profile()
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    relay = PipeModelRelay(binding, reader, lambda _raw: None)
    request = research_request(binding)
    await retire_research(relay, request, via_deadline=False)
    unrelated = research_response(request).model_copy(update={"call_id": str(uuid4())})
    assert not relay.discard_late(line(unrelated))


@pytest.mark.asyncio
async def test_foreign_early_response_retires_the_actual_call_before_the_next_exchange() -> None:
    binding = profile()
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    writes: list[dict[str, Any]] = []

    def write(raw: bytes) -> None:
        frame = json.loads(raw)
        writes.append(frame)
        observed_call = str(uuid4()) if len(writes) == 1 else frame["call_id"]
        reader.feed_data(
            line(
                OperatorModelResponse(
                    call_id=observed_call,
                    binding_digest=binding.digest,
                    status="ok",
                    payload_json=canonical_json({"answer": "fresh"}),
                )
            )
        )

    relay = PipeModelRelay(binding, reader, write)
    with pytest.raises(ValueError, match="model_response_binding"):
        await relay("probe", "{}")
    reader.feed_data(
        line(
            OperatorModelResponse(
                call_id=writes[0]["call_id"],
                binding_digest=binding.digest,
                status="ok",
                payload_json=canonical_json({"answer": "late"}),
            )
        )
    )
    assert await relay("probe", "{}") == canonical_json({"answer": "fresh"})
    assert len(writes) == 2
    assert relay.pending_inputs == []


@pytest.mark.asyncio
async def test_completed_response_duplicate_is_inert_before_another_model_exchange() -> None:
    binding = profile()
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    responses: list[OperatorModelResponse] = []

    def write(raw: bytes) -> None:
        frame = json.loads(raw)
        response = OperatorModelResponse(
            call_id=frame["call_id"],
            binding_digest=binding.digest,
            status="ok",
            payload_json=canonical_json({"sequence": len(responses)}),
        )
        responses.append(response)
        reader.feed_data(line(response))

    relay = PipeModelRelay(binding, reader, write)
    assert await relay("probe", "{}") == canonical_json({"sequence": 0})
    reader.feed_data(line(responses[0]))
    assert await relay("probe", "{}") == canonical_json({"sequence": 1})
    assert len(responses) == 2


@pytest.mark.parametrize("via_deadline", [False, True])
@pytest.mark.asyncio
async def test_serve_discards_retired_research_before_admitting_a_new_native_request(*, via_deadline: bool) -> None:
    binding = profile()
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    outbound: list[bytes] = []
    relay = PipeModelRelay(binding, reader, outbound.append)
    retired = research_request(binding)
    await retire_research(relay, retired, via_deadline=via_deadline)
    runtime = build_runtime(make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW)
    runtime.pending_inputs = relay.pending_inputs
    runtime.late_response_filter = relay.discard_late
    request = make_request()
    reader.feed_data(line(research_response(retired)) + request.model_dump_json().encode() + b"\n")
    reader.feed_eof()
    results: list[bytes] = []
    try:
        await serve(runtime, reader, results.append)
        decoded = [json.loads(raw) for raw in results]
        assert [frame["kind"] for frame in decoded] == ["ready", "result"]
        assert decoded[1]["request_id"] == request.request_id
        assert decoded[1]["status"] == "docs"
        assert len(await runtime.substrate.ledger.list_by_status(RunStatus.DONE)) == 1
        assert len(outbound) == 1
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("foreign", ["unhashable_id", "wrong_request", "wrong_kind", "unknown_id"])
@pytest.mark.asyncio
async def test_serve_refuses_foreign_frames_without_losing_the_following_native_request(foreign: str) -> None:
    binding = profile()
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    relay = PipeModelRelay(binding, reader, lambda _raw: None)
    retired = research_request(binding)
    await retire_research(relay, retired, via_deadline=False)
    value = research_response(retired).model_dump(mode="json")
    if foreign == "unhashable_id":
        value["call_id"] = []
    elif foreign == "wrong_request":
        value["request_id"] = "request:foreign"
    elif foreign == "wrong_kind":
        value = OperatorModelResponse(call_id=retired.call_id, binding_digest=binding.digest, status="ok").model_dump(
            mode="json"
        )
    else:
        value["call_id"] = str(uuid4())
    runtime = build_runtime(make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW)
    runtime.pending_inputs = relay.pending_inputs
    runtime.late_response_filter = relay.discard_late
    request = make_request()
    reader.feed_data(json.dumps(value).encode() + b"\n" + request.model_dump_json().encode() + b"\n")
    reader.feed_eof()
    results: list[bytes] = []
    try:
        await serve(runtime, reader, results.append)
        decoded = [json.loads(raw) for raw in results]
        assert [frame["kind"] for frame in decoded] == ["ready", "result", "result"]
        assert (decoded[1]["request_id"], decoded[1]["reason"]) == ("invalid", "invalid_request")
        assert (decoded[2]["request_id"], decoded[2]["status"]) == (request.request_id, "docs")
        assert len(await runtime.substrate.ledger.list_by_status(RunStatus.DONE)) == 1
    finally:
        await runtime.aclose()
