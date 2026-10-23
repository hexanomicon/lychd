from __future__ import annotations

import json
from typing import cast

import pytest

from lychd.domain.intercom.codec import decode_response, encode_request, send_params, task_params
from lychd.domain.intercom.transport import IntercomError, IntercomRemoteError, TaskMethod, TaskObservation


def _task(state: str = "COMPLETED") -> dict[str, object]:
    return {
        "id": "receiver-task",
        "contextId": "receiver-context",
        "status": {"state": f"TASK_STATE_{state}"},
        "artifacts": [{"artifactId": "artifact-1", "parts": [{"text": "foreign result", "mediaType": "text/plain"}]}],
    }


def _decode(value: object, method: TaskMethod = "GetTask") -> TaskObservation:
    return decode_response(
        json.dumps({"jsonrpc": "2.0", "id": "local-1", "result": value}).encode(),
        method=method,
        local_task_id="local-1",
        expected_task_id="receiver-task",
        expected_context_id="receiver-context",
        response_nonce="a" * 32,
    )


@pytest.mark.parametrize("method", ["SendMessage", "GetTask", "CancelTask"])
def test_exact_v1_operation_shapes(method: TaskMethod) -> None:
    params = (
        send_params("public text", "message-1") if method == "SendMessage" else task_params(method, "receiver-task")
    )
    value = json.loads(encode_request(method, "local-1", params))
    assert value == {"jsonrpc": "2.0", "id": "local-1", "method": method, "params": params}
    if method == "SendMessage":
        assert "taskId" not in value["params"]["message"]


def test_submit_task_and_poll_terminal_remain_inert_observations() -> None:
    first = _decode({"task": _task("SUBMITTED")}, "SendMessage")
    final = _decode(_task())
    assert first.terminal is False
    assert final.terminal is True
    assert final.text == ("foreign result",)
    assert "foreign result" not in repr(final)


@pytest.mark.parametrize("state", ["FAILED", "CANCELED", "REJECTED", "INPUT_REQUIRED", "AUTH_REQUIRED", "WORKING"])
def test_protocol_state_meaning_is_preserved(state: str) -> None:
    result = _decode(_task(state))
    assert result.state == f"TASK_STATE_{state}"
    assert result.terminal == (state in {"FAILED", "CANCELED", "REJECTED"})


@pytest.mark.parametrize(
    "mutation",
    [
        "foreign-id",
        "context",
        "extra",
        "url",
        "raw",
        "data",
        "legacy",
        "history",
        "duplicate-artifact",
        "too-many",
        "bad-id",
    ],
)
def test_unsafe_or_uncorrelated_task_refuses(mutation: str) -> None:
    task = _task()
    if mutation == "foreign-id":
        task["id"] = "different"
    elif mutation == "context":
        task["contextId"] = "different"
    elif mutation == "extra":
        task["metadata"] = {"scope": "admin"}
    elif mutation in {"url", "raw", "data"}:
        task["artifacts"] = [{"artifactId": "artifact-1", "parts": [{mutation: "unsafe"}]}]
    elif mutation == "legacy":
        task["status"] = {"state": "completed"}
    elif mutation == "history":
        task["history"] = [{"parts": [{"text": "unexpected"}]}]
    elif mutation == "duplicate-artifact":
        task["artifacts"] = cast("list[object]", task["artifacts"]) * 2
    elif mutation == "too-many":
        task["artifacts"] = [{"artifactId": str(i), "parts": [{"text": "x"}]} for i in range(9)]
    else:
        task["id"] = "non-ascii-č"
    with pytest.raises(IntercomError):
        _decode(task)


@pytest.mark.parametrize(
    "value",
    [{"message": {"messageId": "m", "role": "ROLE_AGENT", "parts": [{"text": "x"}]}}, {"task": {}, "message": {}}, {}],
)
def test_direct_message_and_multiple_result_alternatives_refuse(value: object) -> None:
    with pytest.raises(IntercomError):
        _decode(value, "SendMessage")


@pytest.mark.parametrize(
    "raw", [b'{"jsonrpc":"2.0","jsonrpc":"2.0","id":"local-1","result":{}}', b"[]", b'{"x":NaN}', b"x" * 65537]
)
def test_malformed_duplicate_or_oversized_json_refuses(raw: bytes) -> None:
    with pytest.raises(IntercomError):
        decode_response(
            raw,
            method="GetTask",
            local_task_id="local-1",
            expected_task_id="receiver-task",
            expected_context_id=None,
            response_nonce="a" * 32,
        )


def test_authenticated_remote_error_preserves_only_integer_code() -> None:
    raw = b'{"jsonrpc":"2.0","id":"local-1","error":{"code":-32001,"message":"foreign secret"}}'
    with pytest.raises(IntercomRemoteError) as caught:
        decode_response(
            raw,
            method="GetTask",
            local_task_id="local-1",
            expected_task_id="receiver-task",
            expected_context_id=None,
            response_nonce="a" * 32,
        )
    assert caught.value.remote_code == -32001
    assert "foreign secret" not in str(caught.value)


def test_request_forbids_push_followup_unknown_fields_and_boolean_history() -> None:
    invalid: tuple[dict[str, object], ...] = (
        {"id": "receiver-task", "historyLength": False},
        {"id": "receiver-task", "historyLength": 0, "metadata": {}},
    )
    for params in invalid:
        with pytest.raises(IntercomError):
            encode_request("GetTask", "local-1", params)
    params = send_params("public", "message-1")
    cast("dict[str, object]", params["message"])["taskId"] = "pretend-new-task"
    with pytest.raises(IntercomError):
        encode_request("SendMessage", "local-1", params)
