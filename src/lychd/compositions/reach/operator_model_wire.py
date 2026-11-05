"""Closed values for one operator-selected local model and static voice, not Mirror."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Annotated, Any, Literal, cast
from uuid import UUID

from pydantic import AfterValidator, Field, field_validator, model_validator

from lychd.compositions.reach.decision_format import (
    DECISION_PHASES,
    DECISION_SCHEMA_BUNDLE_SHA256,
    DecisionPhase,
    DecisionVariant,
    decision_format_phase,
    decision_phase,
    decision_response_format,
)
from lychd.compositions.reach.expressions import ConversationExpressions
from lychd.compositions.reach.operator_trace import TraceCorrelation
from lychd.compositions.reach.operator_wire import strict_json
from lychd.compositions.reach.research_wire import ResearchOptions
from lychd.compositions.reach.schemas import PolicyDigest, Record

MAX_MODEL_PAYLOAD_BYTES = 1_048_576
DECISION_SCHEMA_VERSION = 4


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
    adaptive_context: bool = False
    enable_thinking: bool = False
    thinking_phases: tuple[DecisionPhase, ...] = Field(default=(), max_length=len(DECISION_PHASES))
    json_object_output: bool = False
    decision_schema_version: Literal[4] = 4
    checkback: bool = False
    checkback_invalid_retry: bool = Field(default=False, strict=True)
    request_goals: bool = False
    context_projection_version: Literal[1, 2] = 1
    expressions: ConversationExpressions = Field(default_factory=ConversationExpressions)
    research: ResearchOptions = Field(default_factory=ResearchOptions)
    max_context: int = Field(default=16_384, ge=4096, le=262_144)
    max_tokens: int = Field(default=384, ge=32, le=4096)
    temperature: float = Field(default=0.6, ge=0, le=1)
    max_input_chars: int = Field(default=20_000, ge=1000, le=210_000)
    timeout_seconds: int = Field(default=60, ge=5, le=300)

    @field_validator("decision_schema_version", mode="before")
    @classmethod
    def original_decision_schema_version(cls, value: object) -> object:
        if type(value) is not int or value != DECISION_SCHEMA_VERSION:
            msg = "decision_schema_version"
            raise ValueError(msg)
        return value

    @field_validator("context_projection_version", mode="before")
    @classmethod
    def original_context_projection_version(cls, value: object) -> object:
        if type(value) is not int:
            msg = "context_projection_version"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def expressions_require_decisions(self) -> OperatorConversationProfile:
        if len(set(self.thinking_phases)) != len(self.thinking_phases) or (
            self.thinking_phases and not self.json_object_output
        ):
            msg = "model_thinking_phases"
            raise ValueError(msg)
        if self.max_tokens >= self.max_context:
            msg = "model_completion_context"
            raise ValueError(msg)
        if self.checkback_invalid_retry and not self.checkback:
            msg = "checkback_invalid_retry_requires_checkback"
            raise ValueError(msg)
        if self.request_goals and not self.checkback:
            msg = "request_goals_require_checkback"
            raise ValueError(msg)
        if self.json_object_output and not self.adaptive_context:
            msg = "json_object_output_requires_adaptive_context"
            raise ValueError(msg)
        if (self.expressions.enabled or self.research.enabled or self.checkback) and not self.adaptive_context:
            msg = "expressions_require_adaptive_context"
            raise ValueError(msg)
        if (self.request_goals or self.json_object_output) and "decision_schema_version" not in self.model_fields_set:
            msg = "decision_schema_version_required"
            raise ValueError(msg)
        if self.context_projection_version != 1 and not (self.request_goals and self.adaptive_context):
            msg = "context_projection_requires_interpretation"
            raise ValueError(msg)
        return self

    @property
    def digest(self) -> str:
        values = self.model_dump(mode="json")
        if self.context_projection_version == 1:
            values.pop("context_projection_version")
        if self.checkback_invalid_retry is False:
            values.pop("checkback_invalid_retry")
        if not self.thinking_phases:
            values.pop("thinking_phases")
        if self.enable_thinking is False:
            values.pop("enable_thinking")
        if self.json_object_output is False:
            values.pop("json_object_output")
            values.pop("decision_schema_version")
        else:
            values["decision_schema_bundle_sha256"] = DECISION_SCHEMA_BUNDLE_SHA256
        return sha256(canonical_json(values).encode()).hexdigest()

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
    correlation: TraceCorrelation | None = None

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
    content: str = Field(min_length=1, max_length=210_000)


class _Generation(Record):
    model: Literal["Qwen3.8-27B"]
    messages: tuple[_Message, ...] = Field(min_length=1, max_length=60)
    max_tokens: int = Field(ge=1, le=4096)
    temperature: float = Field(ge=0, le=1)
    stream: Literal[False] = False
    chat_template_kwargs: dict[Literal["enable_thinking"], bool]
    structured_outputs: dict[Literal["grammar"], str] | None = None

    @field_validator("chat_template_kwargs")
    @classmethod
    def exact_thinking(cls, value: dict[str, bool]) -> dict[str, bool]:
        if set(value) != {"enable_thinking"} or type(value["enable_thinking"]) is not bool:
            msg = "model_thinking"
            raise ValueError(msg)
        return value


def generation_format(profile: OperatorConversationProfile, *, phase: DecisionVariant) -> dict[str, Any]:
    """Return only the syntax constraint frozen in the private model binding."""
    if phase in {"checkback_goals", "checkback_public_goals"} and not profile.request_goals:
        msg = "model_generation_binding"
        raise ValueError(msg)
    if phase in {"checkback", "checkback_public"} and profile.request_goals:
        phase = "checkback_public_goals" if phase == "checkback_public" else "checkback_goals"
    return {"structured_outputs": decision_response_format(phase)} if profile.json_object_output else {}


def generation_thinking(profile: OperatorConversationProfile, *, phase: DecisionVariant | None) -> bool:
    """Map the trusted carrier variant to the private semantic-phase thinking policy."""
    if profile.thinking_phases and phase is None:
        msg = "model_generation_binding"
        raise ValueError(msg)
    return profile.enable_thinking or (phase is not None and decision_phase(phase) in profile.thinking_phases)


def _validate_format_binding(profile: OperatorConversationProfile, payload_json: str) -> DecisionVariant | None:
    raw = strict_json(payload_json.encode())
    if not isinstance(raw, dict):
        msg = "model_generation_binding"
        raise ValueError(msg)  # noqa: TRY004 - decoded protocol values retain the existing ValueError boundary
    body = cast("dict[str, Any]", raw)
    present = "structured_outputs" in body
    phase = decision_format_phase(body["structured_outputs"]) if present else None
    if "response_format" in body or present != profile.json_object_output or (present and phase is None):
        msg = "model_generation_binding"
        raise ValueError(msg)
    if (phase in {"checkback", "checkback_public"} and profile.request_goals) or (
        phase in {"checkback_goals", "checkback_public_goals"} and not profile.request_goals
    ):
        msg = "model_generation_binding"
        raise ValueError(msg)
    return phase


def validate_generation_payload(profile: OperatorConversationProfile, payload_json: str) -> dict[str, Any]:
    """Recheck the same closed request at native and host transport boundaries."""
    _payload(payload_json)
    phase = _validate_format_binding(profile, payload_json)
    value = _Generation.model_validate_json(payload_json)
    if (
        value.model != profile.model_id
        or value.chat_template_kwargs != {"enable_thinking": generation_thinking(profile, phase=phase)}
        or ("structured_outputs" in value.model_fields_set) != profile.json_object_output
        or (profile.json_object_output and value.structured_outputs is None)
        or value.max_tokens != profile.max_tokens
        or value.temperature != profile.temperature
        or sum(len(message.content) for message in value.messages) > profile.max_input_chars
        or value.messages[0].role != "system"
        or any(message.role == "system" for message in value.messages[1:])
    ):
        msg = "model_generation_binding"
        raise ValueError(msg)
    return value.model_dump(mode="json", exclude_none=True)
