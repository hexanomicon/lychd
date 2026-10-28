"""Closed values for one operator-selected local model and static voice, not Mirror."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AfterValidator, Field, field_validator, model_validator

from lychd.compositions.reach.operator_wire import strict_json
from lychd.compositions.reach.schemas import PolicyDigest, Record

MAX_MODEL_PAYLOAD_BYTES = 49_152


def canonical_json(value: Any) -> str:
    """Encode exact JSON values without nonfinite numbers or ambiguous key order."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _payload(value: str) -> str:
    if len(value.encode("utf-8")) > MAX_MODEL_PAYLOAD_BYTES or canonical_json(strict_json(value.encode())) != value:
        msg = "model_payload"
        raise ValueError(msg)
    return value


def _call_id(value: str) -> str:
    if str(UUID(value)) != value:
        msg = "model_call_id"
        raise ValueError(msg)
    return value


type ModelPayload = Annotated[str, Field(repr=False), AfterValidator(_payload)]
type ModelCallId = Annotated[str, AfterValidator(_call_id)]


class OperatorConversationProfile(Record):
    """Immutable development binding; no memory, revision lineage, tools or lifecycle authority."""

    schema_version: Literal[1] = 1
    persona_name: str = Field(min_length=1, max_length=80)
    persona_instructions: str = Field(min_length=1, max_length=8000, repr=False)
    animator_id: Literal["night-qwen38"] = "night-qwen38"
    model_id: Literal["Qwen3.8-27B"] = "Qwen3.8-27B"
    max_context: int = Field(default=16_384, ge=4096, le=32_768)
    max_tokens: int = Field(default=384, ge=32, le=768)
    temperature: float = Field(default=0.6, ge=0, le=1)
    max_input_chars: int = Field(default=20_000, ge=1000, le=24_000)
    timeout_seconds: int = Field(default=60, ge=5, le=60)

    @property
    def digest(self) -> str:
        return sha256(canonical_json(self.model_dump(mode="json")).encode()).hexdigest()

    @property
    def capability_key(self) -> str:
        return f"{self.animator_id}:chat:{self.model_id}"


class OperatorModelRequest(Record):
    """Only exact readiness or bounded text formation may cross to the trusted host."""

    kind: Literal["model_request"] = "model_request"
    call_id: ModelCallId
    binding_digest: PolicyDigest
    operation: Literal["probe", "generate"]
    payload_json: ModelPayload

    @model_validator(mode="after")
    def probe_is_empty(self) -> OperatorModelRequest:
        if self.operation == "probe" and self.payload_json != "{}":
            msg = "model_probe_payload"
            raise ValueError(msg)
        return self


class OperatorModelResponse(Record):
    """One correlated result; errors never contain provider bodies or source text."""

    kind: Literal["model_response"] = "model_response"
    call_id: ModelCallId
    binding_digest: PolicyDigest
    status: Literal["ok", "unavailable", "error"]
    payload_json: ModelPayload = "{}"
    reason: Literal["model_unavailable", "model_timeout", "model_refused", "model_protocol", "model_failed"] | None = (
        None
    )

    @model_validator(mode="after")
    def coherent_response(self) -> OperatorModelResponse:
        if (self.status == "ok") != (self.reason is None) or (self.status != "ok" and self.payload_json != "{}"):
            msg = "model_response"
            raise ValueError(msg)
        return self


class OperatorModelProbe(Record):
    """Actual health and exact live inventory observation; configuration is not warmth."""

    healthy: bool
    model_ids: tuple[str, ...] = Field(max_length=32)


class _Message(Record):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=24_000)


class _Generation(Record):
    model: Literal["Qwen3.8-27B"]
    messages: tuple[_Message, ...] = Field(min_length=1, max_length=60)
    max_tokens: int = Field(ge=1, le=768)
    temperature: float = Field(ge=0, le=1)
    stream: Literal[False] = False
    chat_template_kwargs: dict[Literal["enable_thinking"], Literal[False]]

    @field_validator("chat_template_kwargs")
    @classmethod
    def exact_thinking(cls, value: dict[str, bool]) -> dict[str, bool]:
        if value != {"enable_thinking": False}:
            msg = "model_thinking"
            raise ValueError(msg)
        return value


def validate_generation_payload(profile: OperatorConversationProfile, payload_json: str) -> dict[str, Any]:
    """Recheck the same closed request at native and host transport boundaries."""
    _payload(payload_json)
    value = _Generation.model_validate_json(payload_json)
    if (
        value.model != profile.model_id
        or value.max_tokens != profile.max_tokens
        or value.temperature != profile.temperature
        or sum(len(message.content) for message in value.messages) > profile.max_input_chars
        or value.messages[0].role != "system"
        or any(message.role == "system" for message in value.messages[1:])
    ):
        msg = "model_generation_binding"
        raise ValueError(msg)
    return value.model_dump(mode="json")
