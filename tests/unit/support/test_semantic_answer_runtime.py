"""Inert transport-fence controls; these never send a model request or launch resources."""

# ruff: noqa: INP001 - existing tests/unit/support namespace
# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx2
import pytest
from pydantic import ValidationError
from pydantic_ai.messages import (
    CompactionPart,
    ModelMessagesTypeAdapter,
    ModelResponse,
    NativeToolCallPart,
    NativeToolReturnPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
)
from scripts.local_model_probe import ProbeProfile

import tests.integration.test_semantic_answer_native_runtime as answer

pytestmark = pytest.mark.asyncio


def boundary(case: str = "A") -> answer._AnswerBoundary:
    result = answer._AnswerBoundary(
        ProbeProfile(
            base_url="http://127.0.0.1:32123/v1",
            model_id="Qwen3.8-27B",
            source_revision="31b39d03c389f09bbfe5d918f5f532cf636eb35b",
        )
    )
    result.admitted = True
    result.deadline = time.monotonic() + 10
    result.case = case
    result.run_id = "public-inert-run"
    result.receipt = receipt()
    result.previous_answer = "Previous public answer: 14:20."
    return result


def receipt() -> dict[str, Any]:
    return {name: 2 if name == "schema_version" else "inert-public-fixture" for name in answer._WIRE_RECEIPT_FIELDS}


def payload(case: str = "A") -> dict[str, Any]:
    items = (
        [
            {
                "text": answer._SOURCE,
                "selection": {
                    "source_key": answer._SOURCE_KEY,
                    "source_revision": answer._SOURCE_REVISION,
                },
            }
        ]
        if case == "A"
        else []
    )
    envelope = {
        "kind": "archive_semantic_recall",
        "instruction_authority": "none",
        "receipt": receipt(),
        "items": items,
    }
    return {
        "model": "Qwen3.8-27B",
        "stream": True,
        "max_tokens": 256,
        "messages": [{"role": "user", "content": json.dumps(envelope)}, {"role": "user", "content": answer._QUESTION}],
    }


def request(body: dict[str, Any], *, url: str = "http://127.0.0.1:32123/v1/chat/completions") -> httpx2.Request:
    return httpx2.Request("POST", url, json=body)


async def test_inert_supported_body_is_observed_without_transport() -> None:
    observer = boundary()
    await observer.check(request(payload()))
    assert observer.posts == 1
    assert observer.observations[0]["case"] == "A"


@pytest.mark.parametrize(
    "mutation", ["tools", "model", "stream", "output", "endpoint", "case_B", "case_C", "second_post", "third_post"]
)
async def test_inert_transport_fence_refuses_before_send(mutation: str) -> None:
    observer = boundary()
    body = payload()
    url = "http://127.0.0.1:32123/v1/chat/completions"
    if mutation == "tools":
        body["tools"] = [{"type": "function", "function": {"name": "final_result"}}]
    elif mutation == "model":
        body["model"] = "different-model"
    elif mutation == "stream":
        body["stream"] = False
    elif mutation == "output":
        body["max_tokens"] = 257
    elif mutation == "endpoint":
        url = "http://127.0.0.1:32124/v1/chat/completions"
    elif mutation == "case_B":
        observer.case = "B"
    elif mutation == "case_C":
        observer.case = "C"
        body = payload("C")
    elif mutation == "second_post":
        observer.posts = 1
    else:
        observer.posts = 2
    before = observer.posts
    with pytest.raises(AssertionError, match="semantic_answer_model_post_refused"):
        await observer.check(request(body, url=url))
    assert observer.posts == before
    assert observer.observations == []


async def test_inert_empty_case_refuses_before_transport_even_with_no_prior_answer() -> None:
    observer = boundary("C")
    observer.previous_answer = None
    with pytest.raises(AssertionError, match="semantic_answer_model_post_refused"):
        await observer.check(request(payload("C")))
    assert observer.posts == 0
    assert observer.observations == []


async def test_inert_unavailable_case_refuses_previous_answer_injection() -> None:
    observer = boundary("C")
    body = payload("C")
    body["messages"].append({"role": "assistant", "content": observer.previous_answer})
    with pytest.raises(AssertionError):
        await observer.check(request(body))
    assert observer.posts == 0
    assert observer.observations == []


async def test_inert_generated_answer_consumes_entire_current_post_allowance() -> None:
    observer = boundary()
    await observer.check(request(payload()))
    observed = list(observer.observations)
    with pytest.raises(AssertionError, match="semantic_answer_model_post_refused"):
        await observer.check(request(payload()))
    assert observer.posts == 1
    assert observer.observations == observed


async def test_inert_supported_case_refuses_changed_source_projection() -> None:
    observer = boundary()
    body = payload()
    envelope = json.loads(body["messages"][0]["content"])
    envelope["items"][0]["text"] = "Changed source bytes."
    body["messages"][0]["content"] = json.dumps(envelope)
    with pytest.raises(AssertionError):
        await observer.check(request(body))
    assert observer.posts == 0


@pytest.mark.parametrize("mutation", ["missing_key", "extra_key", "public_mode", "symlink", "wrong_deadline"])
async def test_inert_profile_refuses_incomplete_or_unowned_declaration(tmp_path: Path, mutation: str) -> None:
    profile = boundary().profile.model_dump()
    if mutation == "missing_key":
        profile.pop("max_tokens")
    elif mutation == "extra_key":
        profile["thinking"] = True
    elif mutation == "wrong_deadline":
        profile["deadline_seconds"] = 29
    location = tmp_path / "chat-profile.json"
    location.write_text(json.dumps(profile))
    location.chmod(0o600)
    if mutation == "public_mode":
        location.chmod(0o644)
    elif mutation == "symlink":
        linked = tmp_path / "alias.json"
        linked.symlink_to(location)
        location = linked
    with pytest.raises(AssertionError):
        answer._chat_profile(location)


async def test_inert_exact_warm_inventory_get_is_separate_from_inference() -> None:
    profile = boundary().profile
    journal: list[dict[str, Any]] = []
    entry = answer._warm_inventory(httpx2.Request("GET", profile.base_url + "/models"), profile, journal)
    assert journal == [entry]
    assert entry["method"] == "GET"


@pytest.mark.parametrize(
    ("method", "path"), [("POST", "/models"), ("GET", "/chat/completions"), ("GET", "/models?changed=1")]
)
async def test_inert_warm_inventory_refuses_post_or_other_endpoint(method: str, path: str) -> None:
    profile = boundary().profile
    journal: list[dict[str, Any]] = []
    with pytest.raises(AssertionError):
        answer._warm_inventory(httpx2.Request(method, profile.base_url + path), profile, journal)
    assert journal == []


async def test_inert_warm_inventory_sixth_get_is_refused() -> None:
    profile = boundary().profile
    journal: list[dict[str, Any]] = []
    for _ in range(5):
        answer._warm_inventory(httpx2.Request("GET", profile.base_url + "/models"), profile, journal)
    with pytest.raises(AssertionError, match="warm_inventory_budget"):
        answer._warm_inventory(httpx2.Request("GET", profile.base_url + "/models"), profile, journal)
    assert len(journal) == 5


@pytest.mark.parametrize("failure_stage", ["none", "disconnect", "dispose", "cancel"])
async def test_inert_sql_disposal_stays_on_owner_loop_after_disconnect(failure_stage: str) -> None:
    loop = asyncio.get_running_loop()
    events: list[str] = []
    observation: dict[str, Any] = {
        "calls": 0,
        "status": "not_observed",
        "service_id": 1,
        "service_close": {"status": "returned", "service_id": 1, "loop_id": id(loop)},
    }
    failure = asyncio.CancelledError() if failure_stage == "cancel" else RuntimeError("inert teardown failure")

    async def disconnect(queues: object) -> None:
        assert queues == ("owned",)
        assert asyncio.get_running_loop() is loop
        events.append("disconnect")
        if failure_stage == "disconnect":
            raise failure

    async def dispose() -> None:
        assert events == ["disconnect"]
        assert asyncio.get_running_loop() is loop
        events.append("dispose")
        if failure_stage in {"dispose", "cancel"}:
            raise failure

    async def close() -> None:
        await answer._disconnect_and_dispose(
            ("owned",), disconnect=disconnect, dispose=dispose, observation=observation
        )

    if failure_stage == "none":
        await close()
        assert observation["status"] == "dispose_returned"
        with pytest.raises(AssertionError, match="single_app_sql_disposal_required"):
            await close()
    else:
        with pytest.raises(type(failure)) as caught:
            await close()
        assert caught.value is failure
        assert observation["status"] == ("disconnecting" if failure_stage == "disconnect" else "disposing")
        assert observation["error_type"] == type(failure).__name__
    assert events == (["disconnect"] if failure_stage == "disconnect" else ["disconnect", "dispose"])
    assert observation["calls"] == 1
    assert observation["loop_id"] == id(loop)


async def test_inert_body_failure_retains_original_exception_identity() -> None:
    failures: list[BaseException] = []
    failure = RuntimeError("inert original workflow failure")
    with pytest.raises(RuntimeError) as caught, answer._remember_body_failure(failures):
        raise failure
    assert caught.value is failure
    assert failures == [failure]


@pytest.mark.parametrize("change", ["absent", "failed", "wrong_service", "wrong_loop"])
async def test_inert_sql_disposal_requires_exact_successful_service_close(change: str) -> None:
    loop = asyncio.get_running_loop()
    observation: dict[str, Any] = {
        "calls": 0,
        "status": "not_observed",
        "service_id": 1,
        "service_close": {"status": "returned", "service_id": 1, "loop_id": id(loop)},
    }
    if change == "absent":
        observation.pop("service_close")
    elif change == "failed":
        observation["service_close"]["status"] = "failed"
    elif change == "wrong_service":
        observation["service_close"]["service_id"] = 2
    else:
        observation["service_close"]["loop_id"] = -1
    calls: list[str] = []

    async def disconnect(_queues: object) -> None:
        calls.append("disconnect")

    async def dispose() -> None:
        calls.append("dispose")

    await answer._disconnect_and_dispose((), disconnect=disconnect, dispose=dispose, observation=observation)
    assert calls == ["disconnect"]
    assert observation["status"] == "services_unsettled"


_RESPONSE_TEXT = "Public synthetic answer."


def _response_history(parts: list[Any], **changes: Any) -> list[Any]:
    response = ModelResponse(
        parts=parts,
        model_name="Qwen3.8-27B",
        provider_response_id="offline-response",
        provider_details={"finish_reason": "stop"},
        finish_reason="stop",
        run_id="offline-run",
    )
    for field, value in changes.items():
        setattr(response, field, value)
    return ModelMessagesTypeAdapter.dump_python([response], mode="json")


@pytest.mark.parametrize(
    "shape",
    [
        "text",
        "thinking_then_text",
        "text_then_thinking",
        "thinking_between_text",
        "adjacent_text",
        "empty_fragment",
        "space_fragment",
    ],
)
async def test_inert_semantic_response_separates_visible_answer_from_thinking(shape: str) -> None:
    parts: list[Any] = [TextPart(_RESPONSE_TEXT)]
    if shape == "thinking_then_text":
        parts.insert(0, ThinkingPart("opaque synthetic metadata"))
    elif shape == "text_then_thinking":
        parts.append(ThinkingPart("opaque synthetic metadata"))
    elif shape == "adjacent_text":
        parts = [TextPart("Public "), TextPart("synthetic answer.")]
    elif shape == "thinking_between_text":
        parts = [TextPart("Public "), ThinkingPart("opaque synthetic metadata"), TextPart("synthetic answer.")]
    elif shape == "empty_fragment":
        parts.insert(0, TextPart(""))
    elif shape == "space_fragment":
        parts = [
            TextPart("Public"),
            TextPart(" "),
            ThinkingPart("opaque synthetic metadata"),
            TextPart("synthetic answer."),
        ]
    observed: dict[str, Any] = {}
    assert (
        answer._response(
            _response_history(parts), boundary().profile, "offline-run", answer=_RESPONSE_TEXT, observed=observed
        )
        is observed
    )
    assert observed["response_count"] == 1
    assert "opaque synthetic metadata" not in json.dumps(observed)


@pytest.mark.parametrize(
    "bad_part",
    [
        ToolCallPart("external", {}),
        NativeToolCallPart("native", {}),
        NativeToolReturnPart("native", "opaque synthetic metadata"),
        CompactionPart("opaque synthetic metadata"),
    ],
)
async def test_inert_semantic_response_rejects_active_or_other_parts(bad_part: Any) -> None:
    observed: dict[str, Any] = {}
    with pytest.raises(AssertionError):
        answer._response(
            _response_history([TextPart(_RESPONSE_TEXT), bad_part]),
            boundary().profile,
            "offline-run",
            answer=_RESPONSE_TEXT,
            observed=observed,
        )
    assert observed["part_types"] == [["text", bad_part.part_kind]]
    assert "opaque synthetic metadata" not in json.dumps(observed)


@pytest.mark.parametrize(
    "mutation",
    [
        "empty",
        "blank",
        "thinking_only",
        "answer_mismatch",
        "missing_response",
        "duplicate_response",
        "malformed_text",
    ],
)
async def test_inert_semantic_response_retains_completion_and_visible_text_fences(mutation: str) -> None:
    history = _response_history([TextPart(_RESPONSE_TEXT)])
    expected = _RESPONSE_TEXT
    if mutation == "empty":
        history = _response_history([TextPart("")])
    elif mutation == "blank":
        history = _response_history([TextPart("  ")])
    elif mutation == "thinking_only":
        history = _response_history([ThinkingPart("opaque synthetic metadata")])
    elif mutation == "answer_mismatch":
        expected = "Different public answer."
    elif mutation == "missing_response":
        history = []
    elif mutation == "duplicate_response":
        history *= 2
    else:
        history[0]["parts"][0]["content"] = 42
    observed: dict[str, Any] = {}
    with pytest.raises((AssertionError, ValidationError)):
        answer._response(history, boundary().profile, "offline-run", answer=expected, observed=observed)
    assert "opaque synthetic metadata" not in json.dumps(observed)


@pytest.mark.parametrize(
    "changes",
    [
        {"model_name": "different-model"},
        {"provider_response_id": None},
        {"state": "incomplete"},
        {"finish_reason": "length"},
        {"provider_details": {"finish_reason": "length"}},
    ],
)
async def test_inert_semantic_response_retains_identity_and_finish_fences(changes: dict[str, Any]) -> None:
    observed: dict[str, Any] = {}
    with pytest.raises(AssertionError):
        answer._response(
            _response_history([TextPart(_RESPONSE_TEXT)], **changes),
            boundary().profile,
            "offline-run",
            answer=_RESPONSE_TEXT,
            observed=observed,
        )
    assert "opaque synthetic metadata" not in json.dumps(observed)


@pytest.mark.parametrize("status", [answer.RunStatus.FAILED, answer.RunStatus.DONE])
async def test_terminal_absent_context_waits_for_observed_release(status: answer.RunStatus) -> None:
    record = SimpleNamespace(status=status)
    releases: list[str] = []

    async def get_run(_run_id: str) -> Any:
        return record

    async def cancel(_run_id: str) -> None:
        pytest.fail("The release observation should arrive before the deadline.")

    def context(_run_id: str) -> None:
        return None

    services = SimpleNamespace(
        ledger=SimpleNamespace(get=get_run),
        substrate=SimpleNamespace(context=SimpleNamespace(get=context)),
        leases=SimpleNamespace(active=list),
        run_engine=SimpleNamespace(cancel=cancel),
    )
    task = asyncio.create_task(
        answer._terminal(services, "inert-refusal", asyncio.get_running_loop().time() + 2, releases)
    )
    try:
        # A refusal or deterministic outcome can be terminal without Context.
        await asyncio.sleep(0)
        assert not task.done()
        releases.append("inert-refusal")
        assert await asyncio.wait_for(task, 0.5) is record
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
