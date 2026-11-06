"""Run one private, headless Reach turn through the networkless native OCI worker.

Only the audience plan-delivery receipt is simulated. Cognition and document
reads remain in the worker; the existing host broker contacts the fixed local
Qwen endpoint. No Discord connection, web acquisition or model lifecycle control occurs.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import signal
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, NoReturn, cast
from uuid import uuid4

from pydantic import Field, model_validator
from pydantic_ai.profiles import DEFAULT_THINKING_TAGS

from lychd.compositions.reach.checkback import (
    CheckbackEnvelope,
    InvalidCheckbackOutputError,
    checkback_retry_control,
    checkback_retry_digest,
    effective_checkback,
)
from lychd.compositions.reach.conversation_references import (
    REFERENCE_PARSER_VERSION,
    reference_digest,
    reference_payload,
    reference_selectors,
)
from lychd.compositions.reach.conversation_workflow import persona_text
from lychd.compositions.reach.decision_format import decision_format_phase
from lychd.compositions.reach.documents import (
    LEGACY_MAX_CORPUS_BYTES,
    MAX_CORPUS_BYTES,
    MAX_CORPUS_MANIFEST_BYTES,
    MAX_DOCUMENT_BYTES,
    PublicCorpus,
    parse_corpus_manifest,
    project_research_source,
    read_research_document,
    research_projection_mode,
    verify_corpus,
)
from lychd.compositions.reach.expressions import GifId
from lychd.compositions.reach.operator_diagnostics import parse_diagnostic
from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    OperatorModelRequest,
    OperatorModelResponse,
    canonical_json,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_observation import ReachPatternObservation
from lychd.compositions.reach.operator_trace import ReachTraceEvent, TraceCorrelation
from lychd.compositions.reach.operator_wire import (
    MAX_WIRE_BYTES,
    ReachHistoryEntry,
    ReachWorkerReady,
    ReachWorkerRequest,
    ReachWorkerResult,
    ReachWorkerStatus,
    protocol_bytes,
    strict_json,
)
from lychd.compositions.reach.request_goals import (
    CONTEXT_PROJECTION_VERSION,
    TaskRequirements,
    parse_request_goals,
    request_goals_digest,
    request_goals_prompt,
    resolved_required_context,
)
from lychd.compositions.reach.research import (
    MAX_RESEARCH_FOCUS_CHARS,
    ResearchPlan,
    SynthesisProjection,
    model_research_source,
    research_catalogue,
    synthesis_projection,
)
from lychd.compositions.reach.research_wire import OperatorResearchRequest, OperatorResearchResponse, SourceId
from lychd.compositions.reach.schemas import ReachEvent, ReachPolicy, ReachRule, Record

if __package__:
    from scripts import reach_operator as operator
    from scripts import reach_operator_transport as transport
    from scripts.reach_model_broker import OperatorModelBroker
    from scripts.reach_podman_model import PodmanModelTransport
    from scripts.reach_trace_archive import TraceArchive
    from scripts.reach_trace_capture import TraceCapture
else:
    import reach_operator as operator
    import reach_operator_transport as transport
    from reach_model_broker import OperatorModelBroker
    from reach_podman_model import PodmanModelTransport
    from reach_trace_archive import TraceArchive
    from reach_trace_capture import TraceCapture

MAX_STDOUT_FRAMES = 64
MAX_DIAGNOSTIC_FRAMES = 2048
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_MODEL_CALLS = 12
MAX_CHECKBACKS = 3
MAX_ASSERTION_CHARS = 2000
MAX_DEBUG_CHARS = 24_000
MAX_TIMEOUT_SECONDS = 480
_REASONING_FIELDS = ("reasoning", "reasoning_content")
_FINISH_REASONS = frozenset({"stop", "length", "tool_calls", "function_call", "content_filter"})
_REVIEW_TRACE_FIELDS = ("review_attempt", "retry_ordinal", "invalid_review_reason", "review_retry_digest")
SYNTHETIC = {
    "platform": "discord",
    "account_id": "900000000000000001",
    "agent_subject_id": "900000000000000002",
    "space_id": "900000000000000003",
    "conversation_id": "900000000000000004",
    "subject_id": "900000000000000005",
    "event_id": "900000000000000006",
}


class ProbeError(ValueError):
    """A fixed local code, never a rendered provider or persona exception."""


def refuse(code: str) -> NoReturn:
    raise ProbeError(code)


class HistoryItem(Record):
    text: str = Field(min_length=1, max_length=2000, repr=False)
    speaker: Literal["operator", "agent"] = "operator"
    age_seconds: int = Field(default=1, ge=1, le=600)
    event_id: str | None = Field(default=None, pattern=r"^[1-9][0-9]{0,19}$")


class Scenario(Record):
    """One bounded private question and optional assertions about observable results."""

    question: str = Field(min_length=1, max_length=2000, repr=False)
    direct: bool = False
    history: tuple[HistoryItem, ...] = Field(default=(), max_length=20, repr=False)
    plan_delivery: Literal["succeeded", "rejected", "unknown"] = "succeeded"
    expected_status: ReachWorkerStatus | None = None
    required_source_ids: tuple[SourceId, ...] = Field(default=(), max_length=4)
    expected_gif_id: GifId | None = None
    trigger: Literal["reply", "followup"] | None = None
    reply_to_history_index: int | None = Field(default=None, ge=0, le=19)
    continuation_to_history_index: int | None = Field(default=None, ge=0, le=19)
    required_text: tuple[str, ...] = Field(default=(), max_length=32)
    prohibited_text: tuple[str, ...] = Field(default=(), max_length=32)
    text_case: Literal["sensitive", "casefold"] = "sensitive"
    event_sequence: int = Field(default=0, ge=0, le=99)

    @model_validator(mode="after")
    def exact_anchor(self) -> Scenario:
        indices = (self.reply_to_history_index, self.continuation_to_history_index)
        if self.direct and self.trigger is not None:
            msg = "probe_direct_trigger"
            raise ValueError(msg)
        if self.trigger == "reply" and self.reply_to_history_index is None:
            msg = "probe_reply_anchor"
            raise ValueError(msg)
        if (self.trigger == "followup") != (self.continuation_to_history_index is not None):
            msg = "probe_continuation_anchor"
            raise ValueError(msg)
        if all(index is not None for index in indices):
            msg = "probe_ambiguous_anchor"
            raise ValueError(msg)
        for index in indices:
            if index is not None and (index >= len(self.history) or self.history[index].speaker != "agent"):
                msg = "probe_history_anchor"
                raise ValueError(msg)
        for term in self.required_text + self.prohibited_text:
            if not term or len(term) > MAX_ASSERTION_CHARS:
                msg = "probe_text_assertion"
                raise ValueError(msg)
        return self


def make_request(scenario: Scenario, now: datetime) -> tuple[ReachPolicy, ReachWorkerRequest]:
    """Bind synthetic identities explicitly, including a distinct opted-in DM place."""
    place = "900000000000000007" if scenario.direct else SYNTHETIC["conversation_id"]
    policy = ReachPolicy(
        platform="discord",
        account_id=SYNTHETIC["account_id"],
        agent_subject_id=SYNTHETIC["agent_subject_id"],
        space_id=SYNTHETIC["space_id"],
        allowed_conversation_ids=(SYNTHETIC["conversation_id"],),
        allowed_direct_subject_ids=(SYNTHETIC["subject_id"],),
        allowed_reply_conversation_ids=(SYNTHETIC["conversation_id"],),
        allowed_adjacent_followup_conversation_ids=(SYNTHETIC["conversation_id"],),
        rules=(ReachRule(name="headless_probe", subject_ids=(SYNTHETIC["subject_id"],), actions=("converse",)),),
        context_message_limit=20,
        context_max_age_seconds=600,
        event_ttl_seconds=600,
    )
    anchor_index = (
        scenario.continuation_to_history_index if scenario.trigger == "followup" else scenario.reply_to_history_index
    )
    related = scenario.history[anchor_index] if anchor_index is not None and scenario.trigger is not None else None
    related_id = (
        related.event_id or str(900000000000000100 + anchor_index)
        if related is not None and anchor_index is not None
        else None
    )
    event = ReachEvent(
        platform="discord",
        account_id=SYNTHETIC["account_id"],
        event_id=str(int(SYNTHETIC["event_id"]) + scenario.event_sequence * 1000),
        space_id=None if scenario.direct else SYNTHETIC["space_id"],
        conversation_id=place,
        subject_id=SYNTHETIC["subject_id"],
        subject_label="Probe operator",
        mention_subject_ids=() if scenario.direct or scenario.trigger is not None else (SYNTHETIC["agent_subject_id"],),
        trigger=scenario.trigger or ("message" if scenario.direct else "mention"),
        related_event_id=related_id,
        related_subject_id=SYNTHETIC["agent_subject_id"] if related is not None else None,
        related_occurred_at=now - timedelta(seconds=related.age_seconds) if related is not None else None,
        action="converse",
        question=scenario.question,
        occurred_at=now,
    )
    history = tuple(
        ReachHistoryEntry(
            subject_id=SYNTHETIC["agent_subject_id" if item.speaker == "agent" else "subject_id"],
            subject_label="Probe agent" if item.speaker == "agent" else "Probe operator",
            event_id=item.event_id or str(900000000000000100 + index),
            conversation_id=place,
            text=item.text,
            occurred_at=now - timedelta(seconds=item.age_seconds),
        )
        for index, item in enumerate(scenario.history)
    )
    reply = history[scenario.reply_to_history_index] if scenario.reply_to_history_index is not None else None
    continuation = (
        history[scenario.continuation_to_history_index] if scenario.continuation_to_history_index is not None else None
    )
    return policy, ReachWorkerRequest(
        request_id=str(uuid4()),
        event=event,
        history=tuple(item for item in history if item is not reply and item is not continuation),
        reply_to_event_id=reply.event_id if reply is not None else None,
        reply_anchor=reply,
        continuation_anchor=continuation,
    )


def content_assertions(scenario: Scenario, text: str) -> list[str]:
    """Evaluate literal acceptance criteria separately from source and Run success."""
    normalize = str.casefold if scenario.text_case == "casefold" else str
    actual = normalize(text)
    return [
        *(f"required_text_{i}" for i, term in enumerate(scenario.required_text) if normalize(term) not in actual),
        *(f"prohibited_text_{i}" for i, term in enumerate(scenario.prohibited_text) if normalize(term) in actual),
    ]


def freeze_corpus(directory: Path, output: Path) -> PublicCorpus:
    """Verify the entire selected export, then mount only its detached exact bytes."""
    operator.external_path(directory)
    raw = operator.read_regular(directory / "manifest.json", MAX_CORPUS_MANIFEST_BYTES)
    manifest = parse_corpus_manifest(raw)
    contents: list[bytes] = []
    total = 0
    limit = LEGACY_MAX_CORPUS_BYTES if manifest.schema_version == 1 else MAX_CORPUS_BYTES
    for item in manifest.documents:
        raw_document = operator.read_regular(directory / item.file, MAX_DOCUMENT_BYTES)
        total += len(raw_document)
        if total > limit:
            refuse("probe_corpus_budget")
        contents.append(raw_document)
    corpus = verify_corpus(manifest, tuple(contents))
    operator.private_directory(output)
    operator.write_private(output / "manifest.json", raw)
    for item, content in zip(manifest.documents, contents, strict=True):
        operator.write_private(output / item.file, content)
    return corpus


def object_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        refuse("probe_protocol")
    return cast("dict[str, Any]", value)


def validate_evidence_scope(value: object) -> dict[str, str]:
    """Require the closed host context independently from model or source claims."""
    expected = {
        "version": "public-text-v1",
        "source_authority": "public_reference_text",
        "successful_read_proves": "source_bytes_obtained",
        "operator_runtime_observation": "not_supplied",
    }
    if not isinstance(value, dict) or value != expected:
        refuse("probe_evidence_scope")
    return expected


def completion_finish_reason(choice: dict[str, Any]) -> str:
    """Normalize provider completion metadata without retaining arbitrary provider words."""
    if "finish_reason" not in choice:
        return "missing"
    value = choice["finish_reason"]
    if value is None:
        return "null"
    if value == "":
        return "empty"
    return value if isinstance(value, str) and value in _FINISH_REASONS else "unknown"


def reasoning_field_observation(message: dict[str, Any], field: str) -> dict[str, str | int]:
    """Retain presence and character counts only for the two recognized reasoning fields."""
    if field not in message:
        return {"state": "missing"}
    value = message[field]
    if value is None:
        return {"state": "null"}
    if isinstance(value, str):
        return {"state": "text", "chars": len(value)}
    return {"state": "invalid"}


class Turn:
    """One finite protocol state machine; it cannot invent acquisition evidence."""

    def __init__(
        self,
        scenario: Scenario,
        policy: ReachPolicy,
        request: ReachWorkerRequest,
        profile: OperatorConversationProfile,
        corpus: PublicCorpus,
        archive: TraceArchive,
        *,
        capture_model_output: bool = False,
    ) -> None:
        """Pin inputs and archive custody before the child is started."""
        self.scenario, self.policy, self.request = scenario, policy, request
        self.profile, self.corpus = profile, corpus
        self.archive = archive
        self.events: list[ReachTraceEvent] = []
        self.trace_failed = False
        self.capture = TraceCapture(
            self.observe,
            source_ids=frozenset(f"doc:{d.path}" for d in corpus.manifest.documents),
        )
        self.capture_model_output = capture_model_output
        self.ready: ReachWorkerReady | None = None
        self.result: ReachWorkerResult | None = None
        self.run_id: str | None = None
        self.plan: str | None = None
        self.proposed_plan: str | None = None
        self.focus: str | None = None
        self.proposed_focus: str | None = None
        self.proposed_focus_valid = False
        self.plan_call_id: str | None = None
        self.planned_ids: tuple[str, ...] = ()
        self.offered_ids: frozenset[str] = frozenset()
        self.offered_sources: list[dict[str, str]] = []
        self.reads: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self.debug: list[str] = []
        self.synthesis = 0
        self.synthesis_correlation: TraceCorrelation | None = None
        self.total_bytes = 0
        self.stdout_frames = 0
        self.diagnostic_frames = 0
        self.unstructured_diagnostics = 0
        self.seen_call_ids: set[str] = set()
        self.patterns: dict[str, Any] | None = None
        self.cleanup: dict[str, Any] = {
            "process_retired": False,
            "container_removed": False,
            "container_id": None,
        }
        self.projection: dict[str, Any] = {}
        self.evidence_scope: dict[str, str] | None = None
        self.formation_context: dict[str, Any] | None = None
        self.candidate: dict[str, Any] | None = None
        self.checkbacks: list[dict[str, Any]] = []
        self.checkback_controls: list[dict[str, Any]] = []
        self.review_claims: list[tuple[str, ...] | None] = []
        self.corrections = 0
        self.invalid_review_retry_used = False
        self.requirements: TaskRequirements | None = None
        self.goals: tuple[str, ...] = ()
        self.interpretations = 0

    @property
    def projection_mode(self) -> Literal["balanced", "complete_quotes"]:
        """Use the admitted enum when enabled; preserve the literal-question legacy path."""
        if self.profile.request_goals:
            if self.requirements is None:
                refuse("probe_objectives_binding")
            return self.requirements.projection_mode
        return research_projection_mode(self.request.event.question)

    def observe(self, event: ReachTraceEvent) -> None:
        """Retain finite structural metadata independently of best-effort emitter semantics."""
        if len(self.events) >= MAX_DIAGNOSTIC_FRAMES or (
            event.producer == "core"
            and event.source_id is not None
            and event.source_id not in (self.capture.source_ids or frozenset())
        ):
            self.trace_failed = True
            return
        if (
            event.producer == "core"
            and event.name == "source_read"
            and (
                self.plan is None
                or self.scenario.plan_delivery != "succeeded"
                or event.request_id != self.request.request_id
                or event.run_id != self.run_id
            )
        ):
            self.trace_failed = True
        self.events.append(event)
        self.archive.emit(event)

    def correlation(self, value: TraceCorrelation | None) -> dict[str, Any]:
        if (
            value is None
            or self.ready is None
            or value.generation != self.ready.generation
            or value.request_id != self.request.request_id
            or (self.run_id is not None and self.run_id != value.run_id)
        ):
            refuse("probe_correlation")
        self.run_id = value.run_id
        return value.model_dump(exclude_none=True)

    def before_model(self, frame: OperatorModelRequest) -> dict[str, Any]:
        """Bind native order and the profile-selected review carrier before local inference."""
        if len(self.calls) >= MAX_MODEL_CALLS or frame.call_id in self.seen_call_ids:
            refuse("probe_model_budget")
        if frame.binding_digest != self.profile.digest:
            refuse("probe_binding")
        if self.ready is None:
            if frame.operation != "probe" or frame.correlation is not None or self.calls:
                refuse("probe_bootstrap_binding")
        else:
            self.correlation(frame.correlation)
        self.seen_call_ids.add(frame.call_id)
        prompt: dict[str, Any] = {}
        phase = "probe"
        observation: dict[str, Any] = {}
        if frame.operation == "generate":
            generation = validate_generation_payload(self.profile, frame.payload_json)
            messages = cast("list[dict[str, Any]]", generation["messages"])
            prompt = object_value(strict_json(cast("str", messages[-1]["content"]).encode()))
            schema_phase = decision_format_phase(generation.get("structured_outputs"))
            if prompt.get("phase") == "checkback" and self.profile.json_object_output:
                public = (
                    self.formation_context is not None
                    and self.formation_context.get("research_phase") == "synthesis"
                    and bool(self.formation_context.get("research_sources"))
                )
                expected = "checkback_public" if public else "checkback"
                if self.profile.request_goals:
                    expected += "_goals"
                if schema_phase != expected:
                    refuse("probe_checkback_schema")
            phase = self.generation_phase(prompt)
            self.synthesis_correlation = frame.correlation if phase == "synthesis" else self.synthesis_correlation
            if phase in {"planning", "answer"}:
                observation["research_source_kinds"] = [
                    kind
                    for kind in ("doc", "web")
                    if any(source_id.startswith(f"{kind}:") for source_id in self.offered_ids)
                ]
            observation["enable_thinking"] = generation["chat_template_kwargs"]["enable_thinking"]
            observation["response_format"] = "structured_json" if "structured_outputs" in generation else "omitted"
            observation["decision_schema_phase"] = schema_phase
        self.calls.append(
            {
                "call_id": frame.call_id,
                "operation": frame.operation,
                "phase": phase,
                **observation,
            }
        )
        return prompt

    def capture_addressing(self, prompt: dict[str, Any]) -> str:
        """Bind the independent addressing posture before any answer context."""
        anchor = self.request.reply_anchor or self.request.continuation_anchor
        if (
            anchor is None
            or prompt.get("request_id") != self.request.request_id
            or prompt.get("question") != self.request.event.question
            or prompt.get("trigger") != self.request.event.trigger
            or canonical_json(prompt.get("anchor")) != canonical_json(anchor.model_dump(mode="json"))
            or self.plan is not None
            or any(call["phase"] == "addressing" for call in self.calls)
        ):
            refuse("probe_addressing_binding")
        return "addressing"

    def generation_phase(self, prompt: dict[str, Any]) -> str:
        if prompt.get("conversation_phase") == "addressing":
            return self.capture_addressing(prompt)
        if prompt.get("phase") in {"checkback", "correction"}:
            return self.capture_checkback(prompt)
        if prompt.get("phase") == "interpretation":
            return self.capture_interpretation(prompt)
        phase = str(prompt.get("research_phase", "answer"))
        if prompt.get("reference_hints", []) != reference_payload(self.request):
            refuse("probe_references_binding")
        if prompt.get("question") != self.request.event.question:
            refuse("probe_question_binding")
        self.validate_requirements(prompt)
        if phase == "synthesis":
            self.capture_synthesis(prompt)
        elif self.plan is not None or phase not in {"planning", "answer"}:
            refuse("probe_phase")
        else:
            offered = prompt.get("available_research_sources", [])
            expected = research_catalogue(self.profile, self.corpus, self.request)
            if not isinstance(offered, list) or canonical_json(offered) != canonical_json(expected):
                refuse("probe_catalogue")
            self.offered_sources = [dict(item) for item in expected]
            self.offered_ids = frozenset(item["id"] for item in expected)
        self.formation_context = prompt
        return phase

    def capture_interpretation(self, prompt: dict[str, Any]) -> str:
        """Admit one independently formed requirements object before any answer context."""
        if (
            not self.profile.request_goals
            or self.interpretations
            or self.formation_context is not None
            or canonical_json(prompt) != request_goals_prompt(self.profile, self.request)
        ):
            refuse("probe_interpretation_binding")
        self.interpretations += 1
        return "interpretation"

    def validate_requirements(self, prompt: dict[str, Any]) -> None:
        """Bind the full interpretation and the host-resolved attributed context."""
        if self.profile.request_goals and (self.requirements is None or self.goals != self.requirements.goals):
            refuse("probe_objectives_binding")
        expected = self.requirements.model_dump(mode="json") if self.requirements else None
        context = (
            resolved_required_context(
                self.requirements,
                self.request,
                self.profile,
                agent_subject_id=self.policy.agent_subject_id,
            )
            if self.requirements
            else ()
        )
        essential_ids = {object_value(item["entry"])["event_id"] for item in context}
        essential_handles = {object_value(item["entry"])["event_id"]: item["handle"] for item in context}
        anchors: dict[str, object] = {}
        if self.profile.request_goals:
            for name, anchor in (
                ("reply_anchor", self.request.reply_anchor),
                ("continuation_anchor", self.request.continuation_anchor),
            ):
                if anchor is None:
                    anchors[name] = None
                elif anchor.event_id in essential_handles:
                    anchors[name] = {"required_context_handle": essential_handles[anchor.event_id]}
                else:
                    entry = anchor.model_dump(mode="json")
                    if anchor.subject_id == self.policy.agent_subject_id:
                        entry["subject_label"] = self.profile.persona_name
                    anchors[name] = entry
        recent = prompt.get("recent_messages", [])
        if (
            prompt.get("request_goals", []) != []
            or (
                self.profile.context_projection_version == CONTEXT_PROJECTION_VERSION
                and (
                    type(prompt.get("context_projection_version")) is not int
                    or prompt["context_projection_version"] != CONTEXT_PROJECTION_VERSION
                )
            )
            or (self.profile.context_projection_version == 1 and "context_projection_version" in prompt)
            or canonical_json(prompt.get("task_requirements")) != canonical_json(expected)
            or canonical_json(prompt.get("required_context", [])) != canonical_json(context)
            or not isinstance(recent, list)
            or any(object_value(item).get("event_id") in essential_ids for item in cast("list[Any]", recent))
            or any(canonical_json(prompt.get(name)) != canonical_json(value) for name, value in anchors.items())
        ):
            refuse("probe_objectives_binding")

    def capture_checkback(self, prompt: dict[str, Any]) -> str:
        """Bind review and repair to the exact previously admitted candidate and evidence."""
        phase = str(prompt["phase"])
        context = object_value(prompt.get("context"))
        candidate = object_value(prompt.get("candidate"))
        expected = CheckbackEnvelope.prepare(
            self.request,
            canonical_json(context),
            persona_name=self.profile.persona_name,
        ).bindings(canonical_json(candidate))
        if (
            self.formation_context is None
            or self.candidate is None
            or canonical_json(context) != canonical_json(self.formation_context)
            or canonical_json(candidate) != canonical_json(self.candidate)
            or prompt.get("approved_persona_name") != self.profile.persona_name
            or prompt.get("task") != self.request.event.question
            or any(key in prompt for key in expected)
        ):
            refuse("probe_checkback_binding")
        if context.get("research_phase") == "synthesis":
            self.validate_source_projections(context)
        if phase == "correction":
            if (
                self.corrections
                or not self.checkbacks
                or "review_retry" in prompt
                or not self.checkback_controls
                or self.checkback_controls[-1].get("review_attempt", len(self.checkback_controls) - 1)
                != len(self.checkbacks) - 1
                or self.checkback_controls[-1].get("effective_verdict") != "revise"
            ):
                refuse("probe_correction_order")
            control = self.checkback_controls[-1]
            expected_observation = {
                key: value for key, value in control.items() if key not in {*expected, "attempt", *_REVIEW_TRACE_FIELDS}
            }
            if (
                prompt.get("issues") != control["effective_issues"]
                or prompt.get("correction_control") != expected_observation
            ):
                refuse("probe_correction_binding")
            claims = self.review_claims[-1]
            if ("current_runtime_claims" in prompt) != (claims is not None) or (
                claims is not None and prompt["current_runtime_claims"] != list(claims)
            ):
                refuse("probe_runtime_claims_binding")
            self.corrections += 1
        else:
            self.capture_review_call(prompt, expected)
        return phase

    def capture_review_call(self, prompt: dict[str, Any], bindings: dict[str, Any]) -> None:
        """Admit one bounded re-review only after the prior candidate's typed parsing failure."""
        if len(self.checkbacks) >= MAX_CHECKBACKS:
            refuse("probe_checkback_order")
        reason = None
        if "review_retry" in prompt:
            previous = self.checkbacks[-1] if self.checkbacks else {}
            reason = previous.get("invalid_review_reason")
            if (
                not self.profile.checkback_invalid_retry
                or self.invalid_review_retry_used
                or reason not in {"review_shape", "coverage_binding"}
                or "verdict" in previous
                or previous.get("attempt") != self.corrections
                or any(previous.get(key) != value for key, value in bindings.items())
                or canonical_json(prompt["review_retry"]) != canonical_json(checkback_retry_control(reason))
            ):
                refuse("probe_checkback_retry_binding")
            envelope = CheckbackEnvelope.prepare(
                self.request, canonical_json(self.formation_context), persona_name=self.profile.persona_name
            )
            if canonical_json(prompt) != envelope.prompt(canonical_json(self.candidate), retry_reason=reason):
                refuse("probe_checkback_retry_binding")
            self.invalid_review_retry_used = True
        elif self.checkbacks:
            previous = self.checkbacks[-1]
            if previous.get("attempt", len(self.checkbacks) - 1) != self.corrections - 1 or "verdict" not in previous:
                refuse("probe_checkback_order")
        elif self.corrections:
            refuse("probe_checkback_order")
        self.checkbacks.append(
            {
                **bindings,
                "attempt": self.corrections,
                "review_attempt": len(self.checkbacks),
                "retry_ordinal": int(reason is not None),
                "invalid_review_reason": reason,
                "review_retry_digest": checkback_retry_digest(reason) if reason is not None else None,
            }
        )

    def capture_synthesis(self, prompt: dict[str, Any]) -> None:
        if (
            self.plan is None
            or self.scenario.plan_delivery != "succeeded"
            or self.synthesis
            or prompt.get("research_plan") != self.plan
        ):
            refuse("probe_synthesis_binding")
        reads = self.validate_source_projections(prompt)
        omitted = prompt.get("omitted_recent_messages")
        if type(omitted) is not int or not 0 <= omitted <= len(self.request.history):
            refuse("probe_history_metadata")
        self.synthesis += 1
        self.reads.extend(reads)
        self.evidence_scope = validate_evidence_scope(prompt.get("evidence_scope"))
        self.projection = {
            "omitted_recent_messages": omitted,
            "source_count": len(self.reads),
        }

    def validate_source_projections(self, prompt: dict[str, Any]) -> list[dict[str, Any]]:
        if self.plan is None or self.scenario.plan_delivery != "succeeded" or prompt.get("research_plan") != self.plan:
            refuse("probe_synthesis_binding")
        validate_evidence_scope(prompt.get("evidence_scope"))
        if self.profile.context_projection_version == CONTEXT_PROJECTION_VERSION:
            expected = self.reconstruct_synthesis()
            if canonical_json(prompt) != expected.prompt:
                refuse("probe_synthesis_binding")
            return [self.projection_metadata(item) for item in expected.full_projections]
        if (
            prompt.get("research_request_id") != self.request.request_id
            or prompt.get("research_focus") != self.focus
            or prompt.get("corpus_digest") != self.corpus.digest
        ):
            refuse("probe_synthesis_binding")
        sources = prompt.get("research_sources")
        if not isinstance(sources, list):
            refuse("probe_source_metadata")
        records = [object_value(item) for item in cast("list[Any]", sources)]
        if tuple(item.get("id") for item in records) != self.planned_ids:
            refuse("probe_source_binding")
        return [self.read_projection(item) for item in records]

    def reconstruct_synthesis(self) -> SynthesisProjection:
        """Rebuild the compact model envelope solely from bound host inputs and exact local reads."""
        if self.plan is None or self.scenario.plan_delivery != "succeeded" or not self.planned_ids:
            refuse("probe_synthesis_binding")
        if any(not source_id.startswith("doc:") for source_id in self.planned_ids):
            refuse("probe_web_refused")
        sources = tuple(
            read_research_document(
                self.corpus,
                source_id,
                question=self.request.event.question,
                focus=self.focus or self.plan,
                reference_labels=reference_selectors(self.request),
                projection_mode=self.projection_mode,
            )
            for source_id in self.planned_ids
        )
        plan = ResearchPlan(kind="research", text=self.plan, focus=self.focus, source_ids=self.planned_ids)
        return synthesis_projection(
            self.profile,
            self.corpus,
            self.request,
            plan,
            sources,
            instructions=persona_text(self.profile),
            agent_subject_id=self.policy.agent_subject_id,
            task_requirements=self.requirements,
        )

    @staticmethod
    def projection_metadata(projection: dict[str, object]) -> dict[str, Any]:
        """Retain complete host proof fields without storing the transient evidence body in reports."""
        return {
            **{key: value for key, value in projection.items() if key != "text"},
            "projected_chars": len(cast("str", projection["text"])),
        }

    def read_projection(self, item: dict[str, Any]) -> dict[str, Any]:
        """Verify exact metadata and the actual transient projection against frozen source bytes."""
        source_id = item.get("id")
        if not isinstance(source_id, str) or not source_id.startswith("doc:"):
            refuse("probe_web_refused")
        if self.profile.context_projection_version == CONTEXT_PROJECTION_VERSION:
            receipt = self.reconstruct_synthesis()
            for projection in receipt.full_projections:
                if projection["id"] == source_id:
                    if canonical_json(item) != canonical_json(
                        model_research_source(projection, version=CONTEXT_PROJECTION_VERSION)
                    ):
                        refuse("probe_source_metadata")
                    return self.projection_metadata(projection)
            refuse("probe_source_binding")
        source = read_research_document(
            self.corpus,
            source_id,
            question=self.request.event.question,
            focus=self.focus or self.plan or "",
            reference_labels=reference_selectors(self.request),
            projection_mode=self.projection_mode,
        )
        expected = source.model_dump(mode="json", exclude={"text"})
        budget = item.get("projection_budget")
        if type(budget) is not int or not 0 <= budget <= len(source.text):
            refuse("probe_source_metadata")
        mode = self.projection_mode
        if item.get("projection_mode") != mode:
            refuse("probe_source_metadata")
        projection = project_research_source(source, budget, projection_mode=mode)
        text = item.get("text")
        if (
            not isinstance(text, str)
            or canonical_json(item) != canonical_json(model_research_source(projection))
            or (mode == "complete_quotes" and source.status == "ok" and not text.strip())
        ):
            refuse("probe_source_metadata")
        return {
            **expected,
            "projection_digest": projection["projection_digest"],
            "projection_truncated": projection["projection_truncated"],
            "projection_budget": budget,
            "projection_mode": mode,
            "projection_spans": projection["projection_spans"],
            "projected_chars": len(text),
        }

    def capture_completion(self, payload: str) -> str:
        """Observe bounded provider metadata while returning only final content for cognition capture."""
        value = object_value(strict_json(payload.encode()))
        choices = value.get("choices")
        if not isinstance(choices, list) or len(cast("list[Any]", choices)) != 1:
            refuse("probe_completion_metadata")
        choice = object_value(cast("list[Any]", choices)[0])
        message = object_value(choice.get("message"))
        content = message.get("content")
        if not isinstance(content, str):
            refuse("probe_completion_metadata")
        reasoning = {field: reasoning_field_observation(message, field) for field in _REASONING_FIELDS}
        self.calls[-1].update(
            {
                "finish_reason": completion_finish_reason(choice),
                "reasoning_fields": reasoning,
            }
        )
        if any(field["state"] == "invalid" for field in reasoning.values()):
            refuse("probe_reasoning_metadata")
        if any(marker in content for marker in DEFAULT_THINKING_TAGS):
            refuse("probe_reasoning_content")
        return content

    def after_model(self, frame: OperatorModelRequest, response: OperatorModelResponse) -> None:
        self.calls[-1].update({"status": response.status, "reason": response.reason})
        if response.status != "ok" or frame.operation != "generate":
            return
        content = self.capture_completion(response.payload_json)
        if self.capture_model_output:
            if sum(map(len, self.debug)) + len(content) > MAX_DEBUG_CHARS:
                refuse("probe_debug_budget")
            self.debug.append(content)
        phase = self.calls[-1]["phase"]
        if phase == "checkback":
            self.capture_review_completion(content)
            return
        try:
            decision = object_value(strict_json(content.encode()))
        except (ValueError, UnicodeError, RecursionError):
            return  # Native validation owns model output; no permissive repair here.
        if phase == "interpretation":
            with suppress(ValueError):
                self.requirements = parse_request_goals(content, request=self.request, profile=self.profile)
                self.goals = self.requirements.goals
            return
        if phase != "addressing" and decision.get("kind") in {"answer", "clarify"}:
            self.candidate = decision
        if decision.get("kind") == "research":
            ids = decision.get("source_ids")
            if isinstance(ids, list) and all(isinstance(item, str) for item in cast("list[Any]", ids)):
                self.planned_ids = tuple(cast("list[str]", ids))
                self.calls[-1]["selected_source_ids"] = self.planned_ids
                text = decision.get("text")
                self.proposed_plan = text.strip() if isinstance(text, str) else None
                focus = decision.get("focus")
                self.proposed_focus_valid = focus is None or (
                    isinstance(focus, str) and bool(focus.strip()) and len(focus) <= MAX_RESEARCH_FOCUS_CHARS
                )
                self.proposed_focus = focus.strip() if isinstance(focus, str) else None

    @staticmethod
    def claim_metadata(candidate_digest: str, claims: tuple[str, ...] | None) -> dict[str, Any]:
        """Compute a candidate-bound structural receipt without persisting exact observed clauses."""
        if claims is None:
            return {}
        return {
            "runtime_claim_count": len(claims),
            "runtime_claim_digest": sha256(
                canonical_json(
                    {
                        "candidate_digest": candidate_digest,
                        "current_runtime_claims": claims,
                    }
                ).encode()
            ).hexdigest(),
        }

    def capture_review_completion(self, content: str) -> None:
        """Only a completion admitted by the native finish gate may reach review parsing."""
        finish = self.calls[-1].get("finish_reason")
        if finish != "length" and (not self.calls[-1].get("enable_thinking") or finish == "stop"):
            self.capture_review(content)

    def capture_review(self, content: str) -> None:
        """Accept only the same strict coverage and evidence binding as native Core."""
        envelope = CheckbackEnvelope.prepare(
            self.request, canonical_json(self.formation_context), persona_name=self.profile.persona_name
        )
        try:
            judgment = envelope.parse(
                content, canonical_json(self.candidate), classify_invalid=self.profile.checkback_invalid_retry
            )
        except InvalidCheckbackOutputError as failure:
            self.checkbacks[-1]["invalid_review_reason"] = failure.reason
            self.checkbacks[-1]["invalid_review_output"] = True
            return
        except ValueError:
            return  # The native strict parser owns malformed model output.
        control = effective_checkback(
            self.request,
            canonical_json(self.candidate),
            judgment,
            context_json=canonical_json(self.formation_context),
        )
        self.review_claims.append(judgment.current_runtime_claims)
        self.checkback_controls.append(
            {
                **envelope.bindings(canonical_json(self.candidate)),
                "attempt": self.checkbacks[-1].get("attempt", len(self.checkbacks) - 1),
                **{
                    key: self.checkbacks[-1].get(
                        key,
                        len(self.checkbacks) - 1 if key == "review_attempt" else 0 if key == "retry_ordinal" else None,
                    )
                    for key in _REVIEW_TRACE_FIELDS
                },
                **control.observation(),
            }
        )
        self.checkbacks[-1].update(
            {
                "verdict": judgment.verdict,
                "issues": list(judgment.issues),
                **self.claim_metadata(judgment.candidate_digest, judgment.current_runtime_claims),
                "coverage": [
                    {"goal": item.goal, "status": item.status}
                    for item in sorted(judgment.coverage, key=lambda item: item.goal)
                ],
            }
        )

    def research(self, frame: OperatorResearchRequest) -> OperatorResearchResponse:
        """Simulate exactly one audience receipt; never pretend to acquire web material."""
        binding = self.correlation(frame.correlation)
        if (
            frame.binding_digest != self.profile.digest
            or frame.request_id != self.request.request_id
            or frame.event != self.request.event
            or frame.call_id in self.seen_call_ids
            or self.plan is not None
            or frame.plan != self.proposed_plan
            or not self.proposed_focus_valid
            or not self.planned_ids
            or any(item not in self.offered_ids for item in self.planned_ids)
        ):
            refuse("probe_research_binding")
        self.seen_call_ids.add(frame.call_id)
        self.plan, self.focus, self.plan_call_id = (
            frame.plan,
            self.proposed_focus,
            frame.call_id,
        )
        self.capture.host.record(
            "research_plan",
            status=self.scenario.plan_delivery,
            call_id=frame.call_id,
            **binding,
        )
        web = frame.source_ids or any(not item.startswith("doc:") for item in self.planned_ids)
        accepted = self.scenario.plan_delivery == "succeeded" and not web
        response = OperatorResearchResponse(
            call_id=frame.call_id,
            request_id=frame.request_id,
            binding_digest=frame.binding_digest,
            status="ok" if accepted else "refused",
            reason=None if accepted else "probe_web_refused" if web else "probe_plan_not_delivered",
        )
        self.capture.host.record("research_call", status=response.status, call_id=frame.call_id, **binding)
        if web:
            refuse("probe_web_refused")
        return response

    def accept_ready(self, ready: ReachWorkerReady) -> None:
        """Stamp the synthetic invocation after worker startup while retaining its request identity."""
        if self.ready is not None or (
            ready.policy_digest,
            ready.corpus_digest,
            ready.model_binding_digest,
            ready.adaptive_context,
            ready.research_enabled,
            ready.expressions,
        ) != (
            self.policy.digest,
            self.corpus.digest,
            self.profile.digest,
            self.profile.adaptive_context,
            self.profile.research.enabled,
            self.profile.expressions,
        ):
            refuse("probe_ready_binding")
        if self.patterns is not None and self.patterns["generation"] != ready.generation:
            refuse("probe_pattern_binding")
        policy, request = make_request(self.scenario, max(datetime.now(UTC), ready.started_at))
        if policy.digest != self.policy.digest:
            refuse("probe_policy_binding")
        self.request = request.model_copy(update={"request_id": self.request.request_id})
        self.ready = ready
        self.capture.ready(ready)

    def accept_result(self, result: ReachWorkerResult) -> None:
        if (
            self.ready is None
            or self.result is not None
            or result.request_id != self.request.request_id
            or result.policy_digest != self.policy.digest
            or result.corpus_digest != self.corpus.digest
            or result.model_binding_digest != self.profile.digest
            or (self.run_id is not None and result.run_id != self.run_id)
        ):
            refuse("probe_result_binding")
        self.result = result
        self.capture.result(result)

    def account(self, raw: bytes, *, diagnostic: bool) -> None:
        self.total_bytes += len(raw)
        if diagnostic:
            self.diagnostic_frames += 1
        else:
            self.stdout_frames += 1
        if (
            len(raw) > MAX_WIRE_BYTES
            or self.total_bytes > MAX_TOTAL_BYTES
            or self.stdout_frames > MAX_STDOUT_FRAMES
            or self.diagnostic_frames > MAX_DIAGNOSTIC_FRAMES
        ):
            refuse("probe_frame_budget")

    async def diagnostics(self, reader: asyncio.StreamReader) -> None:
        """Consume Core-only typed observations; foreign stderr never enters artifacts."""
        while raw := await read_line(reader):
            self.account(raw, diagnostic=True)
            if not raw.startswith(b"{"):
                self.unstructured_diagnostics += 1
                continue
            value = object_value(strict_json(raw))
            if value.get("kind") == "reach_trace":
                event = ReachTraceEvent.model_validate_json(raw)
                if event.producer != "core":
                    refuse("probe_trace_custody")
                if event.request_id is not None and event.request_id != self.request.request_id:
                    refuse("probe_trace_binding")
                self.capture.child(event, "core")
            elif value.get("kind") == "operation_observation":
                # Existing typed parser verifies this metadata without retaining foreign fields.
                if not transport.capture_structured(raw, "core", self.capture):
                    refuse("probe_diagnostic_protocol")
            else:
                parse_diagnostic(raw)

    def oracle(self) -> list[str]:
        """Judge explicit scenario assertions independently from native Run success."""
        failures = self.result_assertions()
        failures.extend(self.evidence_assertions())
        return failures

    def result_assertions(self) -> list[str]:
        failures: list[str] = []
        result = self.result
        if result is None:
            failures.append("missing_result")
        elif self.scenario.expected_status is not None and result.status != self.scenario.expected_status:
            failures.append("expected_status")
        elif (
            self.scenario.expected_status is None
            and result.status in {"error", "refused"}
            and (self.scenario.plan_delivery == "succeeded" or self.plan is None)
        ):
            failures.append("native_failure")
        if self.scenario.expected_gif_id is not None and (
            result is None or result.gif_id != self.scenario.expected_gif_id
        ):
            failures.append("expected_gif_id")
        failures.extend(content_assertions(self.scenario, result.text if result is not None else ""))
        read_ids = {item.source_id for item in self.events if item.name == "source_read" and item.status == "ok"}
        if not set(self.scenario.required_source_ids) <= read_ids:
            failures.append("required_source_ids")
        return failures

    def evidence_assertions(self) -> list[str]:
        failures: list[str] = []
        if self.scenario.plan_delivery != "succeeded":
            if self.plan is None:
                failures.append("missing_plan")
            if self.reads or self.synthesis or any(item.name == "source_read" for item in self.events):
                failures.append("read_before_delivery")
        if any(item.get("status") != "ok" for item in self.calls):
            failures.append("model_unavailable")
        if not any(item["operation"] == "generate" for item in self.calls):
            failures.append("missing_real_generation")
        if self.trace_failed:
            failures.append("trace_budget")
        if self.ready is not None and any(
            (item.generation is not None and item.generation != self.ready.generation)
            or (item.run_id is not None and item.run_id != (self.result.run_id if self.result else self.run_id))
            or (item.request_id is not None and item.request_id != self.request.request_id)
            for item in self.events
            if item.producer == "core"
        ):
            failures.append("trace_binding")
        if self.patterns is None or not any(item.name == "native_node" for item in self.events):
            failures.append("missing_native_trace")
        failures.extend(self.checkback_assertions())
        failures.extend(self.source_projection_assertions())
        failures.extend(self.goal_assertions())
        failures.extend(self.reference_assertions())
        return failures

    def source_projection_assertions(self) -> list[str]:
        """Match reconstructed source proofs to late-arriving native observations after capture drains."""
        if self.profile.context_projection_version != CONTEXT_PROJECTION_VERSION:
            return []
        observed = [event for event in self.events if event.producer == "core" and event.name == "source_projection"]
        if not self.synthesis:
            return ["source_projection_trace_binding"] if observed else []
        if len(observed) != len(self.reads):
            return ["source_projection_capture_gap"]
        if self.synthesis_correlation is None:
            return ["source_projection_trace_binding"]
        for event, proof in zip(observed, self.reads, strict=True):
            expected = {
                "source_id": proof["id"],
                "source_digest": proof["source_digest"],
                "text_digest": proof["text_digest"],
                "projection_budget": proof["projection_budget"],
                "projection_mode": proof["projection_mode"],
                "projection_chars": proof["projected_chars"],
                "projection_truncated": proof["projection_truncated"],
                "projection_digest": proof["projection_digest"],
                "projection_span_count": len(proof["projection_spans"]),
                "projection_spans_digest": sha256(canonical_json(proof["projection_spans"]).encode()).hexdigest(),
            }
            if (
                event.status != proof["status"]
                or any(
                    canonical_json(getattr(event, name)) != canonical_json(value) for name, value in expected.items()
                )
                or (event.generation is not None and event.generation != self.synthesis_correlation.generation)
                or any(
                    getattr(event, name) != getattr(self.synthesis_correlation, name)
                    for name in ("request_id", "run_id", "occurrence_id")
                )
            ):
                return ["source_projection_trace_binding"]
        return []

    def source_projection_proof_origin(self) -> str:
        """Describe reconstruction separately from independently observed native projection metadata."""
        if self.synthesis and not self.source_projection_assertions():
            return "native_trace_matched_reconstruction"
        return "reconstruction_only_native_trace_unmatched" if self.synthesis else "not_observed"

    def goal_assertions(self) -> list[str]:
        """Correlate the frozen independent interpretation without retaining goal text in trace."""
        observed = [
            event
            for event in self.events
            if event.producer == "core" and event.name == "interpretation" and event.status == "ok"
        ]
        if (
            self.result is None
            or self.result.status not in {"conversation", "clarify"}
            or not self.profile.request_goals
        ):
            return []
        if (
            self.interpretations != 1
            or self.requirements is None
            or self.goals != self.requirements.goals
            or len(observed) != 1
            or observed[0].request_id != self.request.request_id
            or observed[0].run_id != self.run_id
            or observed[0].goal_count != len(self.goals)
            or observed[0].requirements_version != self.requirements.version
            or observed[0].constraint_count != len(self.requirements.constraints)
            or observed[0].required_context_count != len(self.requirements.required_context)
            or observed[0].quotation_presentation != self.requirements.quotation_presentation
            or observed[0].objective_digest
            != request_goals_digest(self.requirements, request=self.request, profile=self.profile)
        ):
            return ["interpretation_trace_binding"]
        return []

    def reference_assertions(self) -> list[str]:
        """Bind observed hint metadata independently from model goal interpretation."""
        observed = [event for event in self.events if event.name == "reference_hints" and event.status == "ok"]
        if self.formation_context is None:
            return [] if not observed else ["reference_trace_binding"]
        if (
            len(observed) != 1
            or observed[0].producer != "core"
            or observed[0].request_id != self.request.request_id
            or observed[0].run_id != self.run_id
            or observed[0].reference_version != REFERENCE_PARSER_VERSION
            or observed[0].reference_count != len(reference_payload(self.request))
            or observed[0].reference_digest != reference_digest(self.request)
        ):
            return ["reference_trace_binding"]
        return []

    def checkback_assertions(self) -> list[str]:
        """Require raw judgments and independent effective controls for the exact adopted bytes."""
        reviews = [event for event in self.events if event.name == "checkback" and event.status == "ok"]
        controls = [event for event in self.events if event.name == "checkback_control" and event.status == "ok"]
        parsed = [item for item in self.checkbacks if "verdict" in item]
        failures = self.failed_checkback_assertions()
        if len(reviews) != len(parsed):
            failures.append("missing_checkback_trace")
        if len(controls) != len(self.checkback_controls):
            failures.append("missing_checkback_control")
        for index, event in enumerate(reviews):
            if (
                index >= len(parsed)
                or not self.review_trace_matches(event, parsed[index], index)
                or event.issue_codes != tuple(parsed[index].get("issues", ()))
                or (event.goal_coverage or ()) != tuple(item["status"] for item in parsed[index].get("coverage", ()))
                or any(
                    getattr(event, key) != parsed[index].get(key)
                    for key in (
                        "request_digest",
                        "evidence_digest",
                        "candidate_digest",
                        "verdict",
                        "runtime_claim_count",
                        "runtime_claim_digest",
                    )
                )
                or any(
                    getattr(event, key) is not None
                    for key in (
                        "guard_rule",
                        "guard_version",
                        "guard_status",
                        "effective_verdict",
                    )
                )
            ):
                failures.append("checkback_trace_binding")
        for index, event in enumerate(controls):
            if (
                index >= len(self.checkback_controls)
                or event.producer != "core"
                or event.request_id != self.request.request_id
                or event.run_id != self.run_id
                or event.verdict is not None
                or event.issue_codes is not None
                or event.goal_coverage is not None
                or any(
                    getattr(event, key) != value
                    for key, value in self.review_trace_metadata(self.checkback_controls[index], index).items()
                )
                or any(
                    getattr(event, key) != self.checkback_controls[index].get(key)
                    for key in (
                        "request_digest",
                        "evidence_digest",
                        "candidate_digest",
                        "attempt",
                        "guard_rule",
                        "guard_version",
                        "guard_status",
                        "effective_verdict",
                        "runtime_claim_count",
                        "runtime_claim_digest",
                    )
                )
            ):
                failures.append("checkback_control_binding")
        if self.result is not None and self.result.status == "conversation" and self.profile.checkback:
            final_digest = (
                CheckbackEnvelope.prepare(
                    self.request,
                    canonical_json(self.formation_context),
                    persona_name=self.profile.persona_name,
                ).bindings(canonical_json(self.candidate))["candidate_digest"]
                if self.candidate is not None and self.formation_context is not None
                else None
            )
            if (
                not parsed
                or parsed[-1].get("verdict") != "accept"
                or not self.checkback_controls
                or self.checkback_controls[-1].get("effective_verdict") != "accept"
                or parsed[-1].get("candidate_digest") != final_digest
                or self.checkback_controls[-1].get("candidate_digest") != final_digest
            ):
                failures.append("missing_accepted_checkback")
        return failures

    def failed_checkback_assertions(self) -> list[str]:
        observed = [event for event in self.events if event.name == "checkback" and event.status == "failed"]
        invalid = [item for item in self.checkbacks if "verdict" not in item]
        failures: list[str] = []
        if len(observed) != len(invalid):
            failures.append("missing_failed_checkback_trace")
        for index, event in enumerate(observed):
            if (
                index >= len(invalid)
                or not self.review_trace_matches(event, invalid[index], index)
                or any(
                    getattr(event, key) is not None
                    for key in (
                        "verdict",
                        "issue_codes",
                        "goal_coverage",
                        "runtime_claim_count",
                        "runtime_claim_digest",
                    )
                )
            ):
                failures.append("failed_checkback_trace_binding")
        return failures

    def review_trace_matches(self, event: ReachTraceEvent, record: dict[str, Any], index: int) -> bool:
        """Bind candidate revision separately from global review/retry metadata, including failed attempts."""
        return (
            event.producer == "core"
            and event.request_id == self.request.request_id
            and event.run_id == self.run_id
            and event.attempt == record.get("attempt", index)
            and all(getattr(event, key) == value for key, value in self.review_trace_metadata(record, index).items())
            and all(
                getattr(event, key) == record.get(key)
                for key in ("request_digest", "evidence_digest", "candidate_digest")
            )
        )

    def review_trace_metadata(self, record: dict[str, Any], index: int) -> dict[str, Any]:
        if not self.profile.checkback_invalid_retry:
            return dict.fromkeys(_REVIEW_TRACE_FIELDS)
        return {
            key: record.get(key, index if key == "review_attempt" else 0 if key == "retry_ordinal" else None)
            for key in _REVIEW_TRACE_FIELDS
        }


async def read_line(reader: asyncio.StreamReader) -> bytes:
    try:
        return await reader.readuntil(b"\n")
    except asyncio.IncompleteReadError as error:
        if error.partial:
            refuse("probe_truncated_frame")
        return b""
    except asyncio.LimitOverrunError:
        refuse("probe_frame_budget")


async def worker_response(
    turn: Turn, raw: bytes, writer: asyncio.StreamWriter, broker: OperatorModelBroker
) -> bytes | None:
    """Handle one closed worker control frame after the outer exchange admits its budget and phase."""
    kind = object_value(strict_json(raw)).get("kind")
    if kind == "reach_pattern_observation":
        if turn.patterns is not None or turn.ready is not None:
            refuse("probe_pattern_order")
        turn.patterns = ReachPatternObservation.model_validate_json(raw).model_dump(mode="json")
    elif kind == "ready":
        turn.accept_ready(ReachWorkerReady.model_validate_json(raw))
        turn.capture.request(turn.request)
        return protocol_bytes(turn.request)
    elif kind == "model_request":
        frame = OperatorModelRequest.model_validate_json(raw)
        turn.before_model(frame)
        model = await broker.handle(frame)
        turn.after_model(frame, model)
        return model.model_dump_json().encode() + b"\n"
    elif kind == "research_request":
        return turn.research(OperatorResearchRequest.model_validate_json(raw)).model_dump_json().encode() + b"\n"
    elif kind == "result":
        turn.accept_result(ReachWorkerResult.model_validate_json(raw))
        writer.close()
    else:
        refuse("probe_core_frame")
    return None


async def exchange(turn: Turn, process: asyncio.subprocess.Process, broker: OperatorModelBroker) -> None:
    if process.stdin is None or process.stdout is None:
        refuse("probe_child_pipe")
    while raw := await read_line(process.stdout):
        turn.account(raw, diagnostic=False)
        if turn.result is not None:
            refuse("probe_after_result")
        response = await worker_response(turn, raw, process.stdin, broker)
        if response is not None:
            turn.account(response, diagnostic=False)
            process.stdin.write(response)
            await process.stdin.drain()
    if turn.result is None:
        refuse("probe_core_eof")


async def finish_task[T](task: asyncio.Task[T]) -> tuple[T, bool]:
    """Join an owned operation through repeated cancellation without abandoning its handle."""
    interrupted = False
    while True:
        try:
            return await asyncio.shield(task), interrupted
        except asyncio.CancelledError:
            interrupted = True
            if task.done():
                return task.result(), interrupted


async def cleanup_owned(
    turn: Turn, process: asyncio.subprocess.Process | None, cidfile: Path, engine: str, tasks: list[asyncio.Task[Any]]
) -> None:
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    try:
        if process is not None:
            await transport.retire(process)
        turn.cleanup["process_retired"] = True
    finally:
        try:
            if await asyncio.to_thread(cidfile.exists):
                identity = (await asyncio.to_thread(operator.read_regular, cidfile, 128)).decode("ascii").strip()
                if operator.CONTAINER_ID.fullmatch(identity) is None:
                    refuse("probe_container_identity")
                turn.cleanup["container_id"] = identity
            elif process is not None:
                refuse("probe_container_identity_missing")
            await transport.remove_owned(engine, cidfile, read_identity=operator.read_regular)
            turn.cleanup["container_removed"] = True
        finally:
            if not turn.cleanup["process_retired"] or not turn.cleanup["container_removed"]:
                turn.cleanup["retained_workspace"] = str(cidfile.parent)


async def supervise(
    turn: Turn, arguments: list[str], cidfile: Path, *, engine: str, model_transport: str, budget_seconds: float
) -> None:
    """Retire the one owned process and exact CID on every terminal path, without retries."""
    process: asyncio.subprocess.Process | None = None
    tasks: list[asyncio.Task[Any]] = []
    loop = asyncio.get_running_loop()
    current = asyncio.current_task()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, current.cancel if current is not None else lambda: None)
    try:
        async with asyncio.timeout(budget_seconds):
            spawning = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    *arguments,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    limit=MAX_WIRE_BYTES,
                    env=operator.safe_environment(engine),
                )
            )
            try:
                spawned = await asyncio.shield(spawning)
                process = spawned
            except asyncio.CancelledError:
                # A successful OS spawn must never lose its process handle at cancellation.
                process, _interrupted = await finish_task(spawning)
                raise
            if spawned.stderr is None:
                refuse("probe_child_pipe")
            broker = OperatorModelBroker(
                turn.profile,
                transport=PodmanModelTransport() if model_transport == "podman" else None,
                trace=turn.capture.host,
            )
            tasks = [
                asyncio.create_task(exchange(turn, spawned, broker)),
                asyncio.create_task(turn.diagnostics(spawned.stderr)),
            ]
            await asyncio.gather(*tasks)
            if await spawned.wait() != 0:
                refuse("probe_core_exit")
    finally:
        cleanup = asyncio.create_task(cleanup_owned(turn, process, cidfile, engine, tasks))
        try:
            _settled, interrupted = await finish_task(cleanup)
            if interrupted:
                raise asyncio.CancelledError
        finally:
            for signum in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(signum)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        self.exit(2, "reach_probe_arguments_refused\n")


def parser() -> argparse.ArgumentParser:
    result = Parser(description=__doc__)
    result.add_argument("--engine", choices=("docker", "podman"), required=True)
    result.add_argument("--core-image", required=True)
    result.add_argument("--conversation-profile", type=Path, required=True)
    result.add_argument("--corpus-dir", type=Path, required=True)
    result.add_argument("--scenario", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--model-transport", choices=("podman", "http"), default="podman")
    result.add_argument("--timeout-seconds", type=int, default=420)
    result.add_argument("--capture-model-output", action="store_true")
    return result


def render_report(report: dict[str, Any], turn: Turn) -> bytes:
    rows = [
        "# Headless Reach probe",
        "",
        f"Outcome: {report['outcome']}",
        f"Native Run: `{report['run_id'] or 'unobserved'}`",
        "",
        "## Native station observations",
        "",
        "| Native sequence | Station | Observation |",
        "| --- | --- | --- |",
    ]
    native = sorted(
        (event for event in turn.events if event.producer == "core" and event.name == "native_node"),
        key=lambda event: (event.native_seq is None, event.native_seq or 0, event.trace_seq),
    )
    rows.extend(
        f"| {event.native_seq if event.native_seq is not None else 'unknown'} | `{event.node}` | {event.status} |"
        for event in native
    )
    rows += ["", "## Model calls in host order", "", "| Call | Status |", "| --- | --- |"]
    rows.extend(f"| {call['operation']} ({call['phase']}) | {call.get('status', 'unknown')} |" for call in turn.calls)
    rows += ["", "## Source and receipt evidence", "", "| Evidence | Status |", "| --- | --- |"]
    if turn.plan is not None:
        rows.append(f"| Synthetic audience plan receipt | {turn.scenario.plan_delivery} |")
    rows.extend(
        f"| Acquired `{event.source_id}` | {event.status} |" for event in turn.events if event.name == "source_read"
    )
    rows.extend(f"| Synthesis projection `{item['id']}` | {item['status']} |" for item in turn.reads)
    rows += [
        f"| Native result | {turn.result.status if turn.result else 'missing'} |",
        "",
        "The plan receipt is synthetic. This probe uses the native OCI worker and fixed local model broker.",
        "Each table keeps its own ordering domain; source projections are captured as metadata only.",
        "This report does not qualify live Discord delivery, web acquisition or the complete host broker.",
        "Source bodies and persona/provider payloads are excluded. See turn.json for the plan and answer.",
        "",
    ]
    return "\n".join(rows).encode()


@contextmanager
def workspace(directory: Path, cleanup: dict[str, Any]) -> Generator[Path]:
    """Keep the exact CID and frozen inputs if retirement or removal remains uncertain."""
    frozen = Path(tempfile.mkdtemp(prefix="input-", dir=directory))
    try:
        yield frozen
    finally:
        if cleanup.get("process_retired") is True and cleanup.get("container_removed") is True:
            shutil.rmtree(frozen)


def execute(args: argparse.Namespace) -> int:
    """Freeze selected inputs outside Git and publish owner-only inspection artifacts."""
    if not 1 <= args.timeout_seconds <= MAX_TIMEOUT_SECONDS or operator.IMAGE_ID.fullmatch(args.core_image) is None:
        refuse("probe_arguments")
    operator.external_path(args.output)
    if args.output.exists():
        refuse("probe_output_exists")
    profile_raw = operator.read_regular(args.conversation_profile, MAX_WIRE_BYTES, private=True)
    strict_json(profile_raw)
    profile = OperatorConversationProfile.model_validate_json(profile_raw)
    scenario_raw = operator.read_regular(args.scenario, MAX_WIRE_BYTES, private=True)
    strict_json(scenario_raw)
    scenario = Scenario.model_validate_json(scenario_raw)
    operator.private_directory(args.output)
    cleanup: dict[str, Any] = {"process_retired": True, "container_removed": True, "container_id": None}
    with workspace(args.output, cleanup) as frozen:
        corpus = freeze_corpus(args.corpus_dir, frozen / "corpus")
        if any(
            item not in {f"doc:{d.path}" for d in corpus.manifest.documents} for item in scenario.required_source_ids
        ):
            refuse("probe_expected_source")
        if scenario.expected_gif_id is not None:
            profile.expressions.validate_selection(None, scenario.expected_gif_id)
        policy, request = make_request(scenario, datetime.now(UTC))
        operator.write_private(frozen / "policy.json", policy.model_dump_json().encode())
        operator.write_private(frozen / "conversation.json", profile.model_dump_json().encode())
        cidfile = frozen / "core.cid"
        arguments = operator.container_arguments(args.engine, args.core_image, cidfile, offline=True)
        arguments += operator.bind(frozen / "policy.json", "/run/reach/policy.json")
        arguments += operator.bind(frozen / "conversation.json", "/run/reach/conversation.json")
        arguments += operator.bind(frozen / "corpus", "/run/reach/corpus")
        arguments += [
            "--entrypoint",
            "python",
            args.core_image,
            "/work/scripts/reach_worker.py",
            "--policy",
            "/run/reach/policy.json",
            "--corpus-dir",
            "/run/reach/corpus",
            "--conversation-profile",
            "/run/reach/conversation.json",
        ]
        archive = TraceArchive(args.output / "traces")
        turn = Turn(scenario, policy, request, profile, corpus, archive, capture_model_output=args.capture_model_output)
        cleanup.update({"process_retired": False, "container_removed": False})
        turn.cleanup = cleanup
        health, failures = run_turn(turn, args, arguments, cidfile)
        return publish_reports(args, turn, profile_raw, scenario_raw, health, failures)


def run_turn(
    turn: Turn, args: argparse.Namespace, arguments: list[str], cidfile: Path
) -> tuple[dict[str, int | bool], list[str]]:
    archive = turn.archive
    error: str | None = None
    try:
        asyncio.run(
            supervise(
                turn,
                arguments,
                cidfile,
                engine=args.engine,
                model_transport=args.model_transport,
                budget_seconds=args.timeout_seconds,
            )
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        error = "probe_cancelled"
    except TimeoutError:
        error = "probe_timeout"
    except ProbeError as failure:
        error = str(failure)
    except Exception:  # noqa: BLE001 - exception values may contain private provider/persona bytes
        error = "probe_failed"
    finally:
        turn.capture.close(0 if error is None else 1)
        flushed = archive.flush()
        closed = archive.close()
    health = archive.health()
    failures = turn.oracle()
    if not flushed or not closed or health["dropped_total"] or health["write_failures"]:
        failures.append("trace_archive_failed")
    if error is not None:
        failures.append(error)
    return health, failures


def publish_reports(
    args: argparse.Namespace,
    turn: Turn,
    profile_raw: bytes,
    scenario_raw: bytes,
    health: dict[str, int | bool],
    failures: list[str],
) -> int:
    profile, corpus, policy, request, scenario = (
        turn.profile,
        turn.corpus,
        turn.policy,
        turn.request,
        turn.scenario,
    )
    report = {
        "schema_version": 1,
        "outcome": "passed" if not failures else "failed",
        "failures": failures,
        "core_image": args.core_image,
        "engine": args.engine,
        "model_transport": args.model_transport,
        "model_id": profile.model_id,
        "profile_digest": profile.digest,
        "profile_file_sha256": sha256(profile_raw).hexdigest(),
        "scenario_file_sha256": sha256(scenario_raw).hexdigest(),
        "corpus_digest": corpus.digest,
        "corpus_manifest": corpus.manifest.model_dump(mode="json"),
        "policy_digest": policy.digest,
        "synthetic_policy": policy.model_dump(mode="json"),
        "synthetic_event_identity": {
            **SYNTHETIC,
            "conversation_id": request.event.conversation_id,
            "space_id": request.event.space_id,
        },
        "audience_plan_receipt": {
            "synthetic": True,
            "status": scenario.plan_delivery,
            "observed": turn.plan is not None,
            "call_id": turn.plan_call_id,
        },
        "request_id": request.request_id,
        "run_id": turn.result.run_id if turn.result else turn.run_id,
        "generation": turn.ready.generation if turn.ready else None,
        "model_calls": turn.calls,
        "checkbacks": turn.checkbacks,
        "checkback_controls": turn.checkback_controls,
        "reference_observation": {
            "parser_version": REFERENCE_PARSER_VERSION,
            "count": len(reference_payload(turn.request)),
            "digest": reference_digest(turn.request),
        },
        "correction_count": turn.corrections,
        "structural_outcome": "failed"
        if any(not item.startswith(("required_text_", "prohibited_text_")) for item in failures)
        else "passed",
        "content_assertions": {
            "case": scenario.text_case,
            "required_count": len(scenario.required_text),
            "prohibited_count": len(scenario.prohibited_text),
            "failures": [item for item in failures if item.startswith(("required_text_", "prohibited_text_"))],
        },
        "semantic_review": "needs_review",
        "real_model_generation_succeeded": any(
            call["operation"] == "generate" and call.get("status") == "ok" for call in turn.calls
        ),
        "native_run_observed": any(item.name == "run_started" for item in turn.events),
        "source_read_count": sum(item.name == "source_read" for item in turn.events),
        "source_projection_capture": "metadata_only",
        **(
            {"source_projection_proof_origin": turn.source_projection_proof_origin()}
            if profile.context_projection_version == CONTEXT_PROJECTION_VERSION
            else {}
        ),
        "evidence_scope": turn.evidence_scope,
        "trace_archive_health": health,
        "unstructured_diagnostic_lines": turn.unstructured_diagnostics,
        "cleanup": turn.cleanup,
        "limits": {
            "timeout_seconds": args.timeout_seconds,
            "model_calls": MAX_MODEL_CALLS,
            "stdout_frames": MAX_STDOUT_FRAMES,
            "diagnostic_frames": MAX_DIAGNOSTIC_FRAMES,
            "frame_bytes": MAX_WIRE_BYTES,
            "total_bytes": MAX_TOTAL_BYTES,
        },
        "claims": {
            "live_discord": False,
            "web_acquisition": False,
            "full_host_broker": False,
        },
    }
    value: dict[str, Any] = {
        "plan": turn.plan,
        "research_focus": turn.focus,
        "request_goals": turn.goals,
        "task_requirements": turn.requirements.model_dump(mode="json") if turn.requirements else None,
        "required_context": resolved_required_context(
            turn.requirements, request, profile, agent_subject_id=policy.agent_subject_id
        )
        if turn.requirements
        else (),
        "selected_source_ids": turn.planned_ids,
        "offered_research_sources": turn.offered_sources,
        "source_reads": turn.reads,
        **(
            {"source_projection_proof_origin": turn.source_projection_proof_origin()}
            if profile.context_projection_version == CONTEXT_PROJECTION_VERSION
            else {}
        ),
        "synthesis_projection": turn.projection,
        "model_calls": turn.calls,
        "evidence_scope": turn.evidence_scope,
        "acquisition_source_reads": [
            item.model_dump(mode="json", exclude_none=True) for item in turn.events if item.name == "source_read"
        ],
        "result": turn.result.model_dump(mode="json") if turn.result else None,
        "patterns": turn.patterns,
    }
    if args.capture_model_output:
        value["model_decision_texts"] = turn.debug
    operator.write_private(args.output / "turn.json", operator.json_bytes(value))
    operator.write_private(args.output / "report.json", operator.json_bytes(report))
    operator.write_private(args.output / "report.md", render_report(report, turn))
    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return execute(args)
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys.stderr.write("reach_probe_cancelled\n")
        return 130
    except Exception:  # noqa: BLE001 - ordinary errors never render selected private input or provider bodies
        sys.stderr.write("reach_probe_refused\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
