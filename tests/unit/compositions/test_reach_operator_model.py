"""The exact local model wire rejects expanded payloads and mismatched replies."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from scripts.reach_worker import PipeModelRelay

from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    OperatorModelRequest,
    OperatorModelResponse,
    canonical_json,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_wire import MAX_WIRE_BYTES


def profile() -> OperatorConversationProfile:
    return OperatorConversationProfile(persona_name="Example", persona_instructions="Be useful.")


def body() -> dict[str, Any]:
    binding = profile()
    return {
        "model": binding.model_id,
        "messages": [{"role": "system", "content": "Be useful."}, {"role": "user", "content": "Hello"}],
        "max_tokens": binding.max_tokens,
        "temperature": binding.temperature,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }


def test_closed_generation_payload_and_static_binding() -> None:
    binding = profile()
    assert validate_generation_payload(binding, canonical_json(body()))["model"] == binding.model_id
    assert binding.digest != binding.model_copy(update={"persona_name": "Changed"}).digest
    patches: tuple[dict[str, Any], ...] = (
        {"tools": []},
        {"model": "other"},
        {"max_tokens": 769},
        {"stream": True},
        {"chat_template_kwargs": {"enable_thinking": True}},
    )
    for patch in patches:
        with pytest.raises(ValueError, match=r"model_|validation"):
            validate_generation_payload(binding, canonical_json(body() | patch))
    with pytest.raises(ValueError, match="model_probe_payload"):
        OperatorModelRequest(
            call_id=str(uuid4()), binding_digest=binding.digest, operation="probe", payload_json='{"x":1}'
        )
    with pytest.raises(ValidationError):
        OperatorModelRequest.model_validate_json(
            canonical_json(
                {
                    "call_id": str(uuid4()),
                    "binding_digest": binding.digest,
                    "operation": "delete",
                    "payload_json": "{}",
                }
            )
        )


@pytest.mark.asyncio
async def test_pipe_rejects_mismatched_binding_without_repeating_request() -> None:
    binding = profile()
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    writes: list[bytes] = []

    def write(raw: bytes) -> None:
        writes.append(raw)
        frame = json.loads(raw)
        response = OperatorModelResponse(
            call_id=frame["call_id"],
            binding_digest="a" * 64,
            status="ok",
            payload_json=canonical_json({"healthy": True, "model_ids": [binding.model_id]}),
        )
        reader.feed_data(response.model_dump_json().encode() + b"\n")

    relay = PipeModelRelay(binding, reader, write)
    with pytest.raises(ValueError, match="model_response_binding"):
        await relay("probe", "{}")
    assert len(writes) == 1


@pytest.mark.asyncio
async def test_pipe_cancellation_does_not_retransmit() -> None:
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    writes: list[bytes] = []
    relay = PipeModelRelay(profile(), reader, writes.append)
    task = asyncio.create_task(relay("probe", "{}"))
    await asyncio.sleep(0)
    assert len(writes) == 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(writes) == 1
    assert not relay.lock.locked()
