"""Strict A2A v1.0.1 public-text JSON-RPC shapes, without effects or authority."""

from __future__ import annotations

import json
import re
from typing import cast

from lychd.domain.intercom.transport import (
    MAX_REQUEST_BODY_BYTES,
    MAX_RESPONSE_BODY_BYTES,
    IntercomCode,
    IntercomError,
    IntercomRemoteError,
    TaskMethod,
    TaskObservation,
)

_ID = re.compile(r"[\x21-\x7e]{1,128}")
_STATES = frozenset(
    f"TASK_STATE_{state}"
    for state in (
        "UNSPECIFIED",
        "SUBMITTED",
        "WORKING",
        "COMPLETED",
        "FAILED",
        "CANCELED",
        "INPUT_REQUIRED",
        "REJECTED",
        "AUTH_REQUIRED",
    )
)
_TERMINALS = frozenset(f"TASK_STATE_{state}" for state in ("COMPLETED", "FAILED", "CANCELED", "REJECTED"))
_MAX_PARTS = 8
_MAX_ARTIFACTS = 8


def visible_id(value: object) -> str:
    """Admit one opaque profile identifier without controls or Unicode ambiguity."""
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise IntercomError(IntercomCode.PROTOCOL)
    return value


def _object(value: object, *, required: set[str], optional: set[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise IntercomError(IntercomCode.PROTOCOL)
    result = cast("dict[str, object]", value)
    if not required <= result.keys() or result.keys() - required - optional:
        raise IntercomError(IntercomCode.PROTOCOL)
    return result


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise IntercomError(IntercomCode.PROTOCOL)
        result[key] = value
    return result


def _invalid_constant(value: str) -> object:
    del value
    raise IntercomError(IntercomCode.PROTOCOL)


def _decoded(raw: bytes) -> object:
    try:
        return cast(
            "object", json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_invalid_constant)
        )
    except (ValueError, UnicodeError, RecursionError):
        raise IntercomError(IntercomCode.PROTOCOL) from None


def send_params(text: str, message_id: str) -> dict[str, object]:
    """Construct only the initial single user text part and asynchronous options."""
    visible_id(message_id)
    if type(text) is not str or not text:
        raise IntercomError(IntercomCode.INPUT)
    try:
        if len(text.encode("utf-8")) > MAX_REQUEST_BODY_BYTES:
            raise IntercomError(IntercomCode.INPUT)
    except UnicodeError:
        raise IntercomError(IntercomCode.INPUT) from None
    return {
        "message": {"messageId": message_id, "role": "ROLE_USER", "parts": [{"text": text, "mediaType": "text/plain"}]},
        "configuration": {"returnImmediately": True, "historyLength": 0, "acceptedOutputModes": ["text/plain"]},
    }


def task_params(method: TaskMethod, foreign_task_id: str) -> dict[str, object]:
    """Construct an exact known-task poll or cancellation request."""
    visible_id(foreign_task_id)
    if method == "GetTask":
        return {"id": foreign_task_id, "historyLength": 0}
    if method == "CancelTask":
        return {"id": foreign_task_id}
    raise IntercomError(IntercomCode.INPUT)


def encode_request(method: TaskMethod, local_task_id: str, params: dict[str, object]) -> bytes:  # noqa: C901
    """Seal an exact supported operation; caller identity is not a receiver task id."""
    visible_id(local_task_id)
    if method == "SendMessage":
        value = _object(params, required={"message", "configuration"}, optional=set())
        message = _object(value["message"], required={"messageId", "role", "parts"}, optional=set())
        visible_id(message["messageId"])
        parts = message["parts"]
        if not isinstance(parts, list):
            raise IntercomError(IntercomCode.PROTOCOL)
        parts = cast("list[object]", parts)
        if len(parts) != 1:
            raise IntercomError(IntercomCode.PROTOCOL)
        part = _object(parts[0], required={"text", "mediaType"}, optional=set())
        config = _object(
            value["configuration"],
            required={"returnImmediately", "historyLength", "acceptedOutputModes"},
            optional=set(),
        )
        if type(config["returnImmediately"]) is not bool or type(config["historyLength"]) is not int:
            raise IntercomError(IntercomCode.PROTOCOL)
        if message["role"] != "ROLE_USER" or params != send_params(
            cast("str", part["text"]), cast("str", message["messageId"])
        ):
            raise IntercomError(IntercomCode.PROTOCOL)
    elif method in {"GetTask", "CancelTask"}:
        if method == "GetTask" and type(params.get("historyLength")) is not int:
            raise IntercomError(IntercomCode.PROTOCOL)
        if params != task_params(method, visible_id(params.get("id"))):
            raise IntercomError(IntercomCode.PROTOCOL)
    else:
        raise IntercomError(IntercomCode.INPUT)
    try:
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": local_task_id, "method": method, "params": params},
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (ValueError, UnicodeError, TypeError):
        raise IntercomError(IntercomCode.INPUT) from None
    if len(raw) > MAX_REQUEST_BODY_BYTES:
        raise IntercomError(IntercomCode.LIMIT)
    return raw


def _parts(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise IntercomError(IntercomCode.PROTOCOL)
    value = cast("list[object]", value)
    if not 1 <= len(value) <= _MAX_PARTS:
        raise IntercomError(IntercomCode.PROTOCOL)
    texts: list[str] = []
    for item in value:
        part = _object(item, required={"text"}, optional={"mediaType"})
        text = part["text"]
        if not isinstance(text, str) or part.get("mediaType", "text/plain") != "text/plain":
            raise IntercomError(IntercomCode.PROTOCOL)
        try:
            text.encode("utf-8")
        except UnicodeError:
            raise IntercomError(IntercomCode.PROTOCOL) from None
        texts.append(text)
    return tuple(texts)


def _message(value: object, foreign_id: str, context_id: str | None) -> tuple[str, ...]:
    message = _object(value, required={"messageId", "role", "parts"}, optional={"taskId", "contextId"})
    visible_id(message["messageId"])
    if (
        message["role"] != "ROLE_AGENT"
        or message.get("taskId", foreign_id) != foreign_id
        or message.get("contextId", context_id) != context_id
    ):
        raise IntercomError(IntercomCode.PROTOCOL)
    return _parts(message["parts"])


def decode_response(  # noqa: C901 - This is the complete closed Task/profile validation boundary.
    raw: bytes,
    *,
    method: TaskMethod,
    local_task_id: str,
    expected_task_id: str | None,
    expected_context_id: str | None,
    response_nonce: str,
) -> TaskObservation:
    """Validate an already authenticated response into inert quarantined task facts."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RESPONSE_BODY_BYTES:
        raise IntercomError(IntercomCode.LIMIT)
    body = _object(_decoded(raw), required={"jsonrpc", "id"}, optional={"result", "error"})
    if body["jsonrpc"] != "2.0" or body["id"] != local_task_id or ("result" in body) == ("error" in body):
        raise IntercomError(IntercomCode.PROTOCOL)
    if "error" in body:
        error = _object(body["error"], required={"code", "message"}, optional={"data"})
        code = error["code"]
        if type(code) is not int or not -(2**31) <= code < 2**31 or not isinstance(error["message"], str):
            raise IntercomError(IntercomCode.PROTOCOL)
        raise IntercomRemoteError(code)
    value = body["result"]
    if method == "SendMessage":
        value = _object(value, required={"task"}, optional=set())["task"]
    task = _object(value, required={"id", "status"}, optional={"contextId", "artifacts", "history"})
    foreign_id = visible_id(task["id"])
    context = visible_id(task["contextId"]) if "contextId" in task else None
    if method != "SendMessage" and (foreign_id != expected_task_id or context != expected_context_id):
        raise IntercomError(IntercomCode.PROTOCOL)
    if task.get("history", []) != []:
        raise IntercomError(IntercomCode.PROTOCOL)
    status = _object(task["status"], required={"state"}, optional={"message", "timestamp"})
    state = status["state"]
    if (
        not isinstance(state, str)
        or state not in _STATES
        or ("timestamp" in status and not isinstance(status["timestamp"], str))
    ):
        raise IntercomError(IntercomCode.PROTOCOL)
    texts = list(_message(status["message"], foreign_id, context)) if "message" in status else []
    artifacts = task.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise IntercomError(IntercomCode.PROTOCOL)
    artifacts = cast("list[object]", artifacts)
    if len(artifacts) > _MAX_ARTIFACTS:
        raise IntercomError(IntercomCode.PROTOCOL)
    identities: set[str] = set()
    for item in artifacts:
        artifact = _object(item, required={"artifactId", "parts"}, optional={"name", "description"})
        identity = visible_id(artifact["artifactId"])
        if identity in identities or any(
            not isinstance(artifact[key], str) for key in ("name", "description") if key in artifact
        ):
            raise IntercomError(IntercomCode.PROTOCOL)
        identities.add(identity)
        texts.extend(_parts(artifact["parts"]))
    return TaskObservation(foreign_id, context, state, tuple(texts), state in _TERMINALS, response_nonce)
