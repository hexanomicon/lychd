"""Request decomposition precedes planning and preserves each requested outcome."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic import ValidationError
from pydantic_ai.models import override_allow_model_requests
from scripts.reach_worker import build_runtime

from lychd.compositions.reach.conversation_workflow import make_conversation_intent, reach_conversation_workflow
from lychd.compositions.reach.documents_workflow import DocumentsRefused
from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    canonical_json,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_trace import MAX_TRACE_BYTES, ReachTraceEvent, trace_bytes
from lychd.compositions.reach.operator_wire import ReachHistoryEntry
from lychd.compositions.reach.request_goals import (
    TaskRequirements,
    parse_request_goals,
    request_goals_digest,
    request_goals_prompt,
    resolved_required_context,
)
from lychd.compositions.reach.research_wire import OperatorResearchRequest, OperatorResearchResponse
from tests.unit.compositions.test_reach_addressing import continuation, continuation_policy
from tests.unit.compositions.test_reach_conversation import completion, policy, profile
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_request
from tests.unit.compositions.test_reach_research import answer_json, relay_response, research_profile

GOALS = ("Describe the current supported behavior.", "Describe the future planned behavior.")
QUESTION = "What works today, and what is planned next?"
ANSWER = "Today supports bounded turns. Future work includes durable continuity."
REQUIREMENTS = TaskRequirements(
    version=1,
    goals=GOALS,
    constraints=(),
    quotation_presentation="none",
    required_context=(),
)


def interpreted_profile() -> OperatorConversationProfile:
    return profile().model_copy(
        update={
            "adaptive_context": True,
            "checkback": True,
            "request_goals": True,
            "max_input_chars": 24_000,
        }
    )


@pytest.mark.parametrize(
    "output",
    [
        "{}",
        '{"goals":[]}',
        '{"goals":[" "]}',
        '{"goals":[1]}',
        '{"goals":["same"," same "]}',
        canonical_json({"goals": ["x" * 201]}),
        canonical_json({"goals": [str(index) for index in range(9)]}),
        '{"goals":["one"],"candidate":"forbidden"}',
    ],
)
def test_goals_are_strict_bounded_nonblank_and_unique(output: str) -> None:
    raw = json.loads(output)
    closed = canonical_json({**REQUIREMENTS.model_dump(mode="json"), **raw}) if raw else output
    with pytest.raises(ValidationError):
        parse_request_goals(
            closed,
            request=make_request(action="converse"),
            profile=interpreted_profile(),
        )


def test_goals_profile_is_explicit_and_requires_checkback() -> None:
    assert not profile().request_goals
    value = profile().model_dump(mode="json") | {
        "request_goals": True,
        "adaptive_context": True,
    }
    with pytest.raises(ValidationError):
        OperatorConversationProfile.model_validate_json(canonical_json(value))
    accepted = OperatorConversationProfile.model_validate_json(canonical_json(value | {"checkback": True}))
    assert accepted.request_goals
    assert TaskRequirements.model_validate_json(
        '{"version":1,"goals":[" First outcome ","Second outcome"],"constraints":[],"quotation_presentation":"none","required_context":[]}'
    ).goals == (
        "First outcome",
        "Second outcome",
    )


def test_interpretation_keeps_anchors_and_trims_only_oldest_history_to_budget() -> None:
    history = tuple(
        ReachHistoryEntry(
            subject_id="person:one",
            event_id=f"old:{index}",
            conversation_id="channel:one",
            occurred_at=NOW - timedelta(seconds=10 - index),
            text=f"Message {index} " + "h" * 1200,
        )
        for index in range(3)
    )
    anchor = history[-1].model_copy(update={"event_id": "anchor", "text": "The exact referenced answer."})
    request = make_request(action="converse", question=QUESTION).model_copy(
        update={
            "history": history,
            "reply_anchor": anchor,
        }
    )
    binding = interpreted_profile().model_copy(update={"max_input_chars": 4500})
    prompt = json.loads(request_goals_prompt(binding, request))
    assert set(prompt) == {
        "phase",
        "question",
        "reply_anchor",
        "continuation_anchor",
        "recent_messages",
        "omitted_recent_messages",
    }
    assert prompt["question"] == QUESTION
    assert prompt["reply_anchor"] == {
        "handle": "reply_anchor",
        "entry": anchor.model_dump(mode="json"),
    }
    assert prompt["omitted_recent_messages"] > 0
    assert prompt["recent_messages"]
    assert prompt["recent_messages"] == [
        {"handle": f"history:{index}", "entry": entry.model_dump(mode="json")}
        for index, entry in enumerate(history)
        if index >= prompt["omitted_recent_messages"]
    ]
    oversized = request.model_copy(update={"event": request.event.model_copy(update={"question": "q" * 8192})})
    with pytest.raises(DocumentsRefused, match="conversation_budget"):
        request_goals_prompt(binding, oversized)


def test_goal_checkpoint_rejects_disabled_or_missing_interpretation() -> None:
    binding, corpus = interpreted_profile(), make_corpus()
    request = make_request(action="converse")
    intent = make_conversation_intent(
        policy(),
        corpus,
        binding,
        request,
        session_id="session",
        started_at=STARTED,
        now=NOW,
    ).model_copy(update={"run_id": "run"})
    workflow = reach_conversation_workflow(policy(), corpus, binding, started_at=STARTED, clock=lambda: NOW)
    initial = workflow.make_state(intent)
    assert workflow.manifest.checkpoint_schema == "reach-operator-conversation-v8"
    assert workflow.validate_state is not None
    workflow.validate_state(intent, initial)
    with pytest.raises(DocumentsRefused, match="conversation_checkpoint"):
        workflow.validate_state(intent, initial.model_copy(update={"answer": ANSWER}))
    valid = initial.model_copy(
        update={
            "task_requirements": REQUIREMENTS,
            "answer": ANSWER,
            "task_requirements_digest": request_goals_digest(REQUIREMENTS, request=request, profile=binding),
        }
    )
    workflow.validate_state(intent, valid)
    with pytest.raises(DocumentsRefused, match="conversation_checkpoint"):
        workflow.validate_state(intent, valid.model_copy(update={"task_requirements_digest": "0" * 64}))
    disabled = binding.model_copy(update={"request_goals": False})
    disabled_intent = make_conversation_intent(
        policy(),
        corpus,
        disabled,
        request,
        session_id="session",
        started_at=STARTED,
        now=NOW,
    ).model_copy(update={"run_id": "run"})
    disabled_workflow = reach_conversation_workflow(policy(), corpus, disabled, started_at=STARTED, clock=lambda: NOW)
    assert disabled_workflow.validate_state is not None
    disabled_state = disabled_workflow.make_state(disabled_intent).model_copy(
        update={"task_requirements": REQUIREMENTS}
    )
    with pytest.raises(DocumentsRefused, match="conversation_checkpoint"):
        disabled_workflow.validate_state(disabled_intent, disabled_state)


def accepted_coverage(*, runtime_claims: bool = False) -> str:
    value: dict[str, Any] = {
        "verdict": "accept",
        "issues": [],
        "coverage": [
            {"goal": 0, "status": "complete", "answer_quote": "Today supports bounded turns."},
            {"goal": 1, "status": "complete", "answer_quote": "Future work includes durable continuity."},
        ],
    }
    if runtime_claims:
        value["current_runtime_claims"] = []
    return canonical_json(value)


@pytest.mark.parametrize("research", [False, True])
@pytest.mark.parametrize("projection_version", [1, 2])
@pytest.mark.asyncio
async def test_native_goals_precede_planning_and_reach_the_same_frozen_review_context(
    *, research: bool, projection_version: int
) -> None:
    binding = (
        research_profile(request_goals=True, checkback=True, max_input_chars=24_000)
        if research
        else interpreted_profile()
    )
    binding = OperatorConversationProfile.model_validate_json(
        canonical_json({**binding.model_dump(mode="json"), "context_projection_version": projection_version})
    )
    corpus = make_corpus("# Graph\n" + ANSWER)
    prompts: list[dict[str, Any]] = []
    traces: list[ReachTraceEvent] = []
    acquisitions: list[OperatorResearchRequest] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        body = validate_generation_payload(binding, payload)
        assert "tools" not in body
        prompt = json.loads(body["messages"][-1]["content"])
        prompts.append(prompt)
        if prompt.get("phase") == "interpretation":
            assert len(prompts) == 1
            assert "research_sources" not in prompt
            assert "available_research_sources" not in prompt
            assert "candidate" not in prompt
            return completion(REQUIREMENTS.model_dump_json())
        context = prompt["context"] if prompt.get("phase") == "checkback" else prompt
        assert context["task_requirements"]["goals"] == list(GOALS)
        if prompt.get("phase") == "checkback":
            return completion(accepted_coverage(runtime_claims=research))
        if prompt.get("research_phase") == "planning":
            return completion(
                canonical_json(
                    {
                        "kind": "research",
                        "text": "I will read the public Graph source.",
                        "focus": "Graph",
                        "source_ids": ["doc:docs/graph.md"],
                    }
                )
            )
        return completion(
            answer_json(text=ANSWER, citations=("doc:docs/graph.md",))
            if research
            else canonical_json({"kind": "answer", "text": ANSWER})
        )

    async def acquire(request: OperatorResearchRequest) -> OperatorResearchResponse:
        acquisitions.append(request)
        return relay_response(request, sources=())

    runtime = build_runtime(
        policy(),
        corpus,
        profile=binding,
        model_relay=relay,
        research_relay=acquire if research else None,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=traces.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            result = await runtime.process(
                make_request(action="converse", question=QUESTION).model_copy(update={"request_id": str(uuid4())})
            )
        assert result.status == "conversation"
        assert ANSWER in result.text
        assert len(prompts) == (4 if research else 3)
        assert len(acquisitions) == int(research)
        projections = [event for event in traces if event.name == "source_projection"]
        assert len(projections) == int(research and projection_version == 2)
        for projected in projections:
            assert projected.status == "ok"
            assert projected.projection_mode == "balanced"
            assert projected.projection_span_count == 1
            assert projected.projection_budget == projected.projection_chars
            assert projected.projection_digest is not None
            assert projected.projection_spans_digest is not None
            assert len(trace_bytes(projected)) <= MAX_TRACE_BYTES
            assert ANSWER not in trace_bytes(projected).decode()
        interpreted = [event for event in traces if event.name == "interpretation"]
        assert [event.status for event in interpreted] == ["started", "ok"]
        assert interpreted[-1].goal_count == len(GOALS)
        assert interpreted[-1].objective_digest == request_goals_digest(
            REQUIREMENTS,
            request=make_request(action="converse", question=QUESTION),
            profile=binding,
        )
        assert GOALS[0] not in b"".join(trace_bytes(event) for event in traces).decode()
        assert runtime.substrate.leases.active() == []
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("failure", ["malformed", "cancelled"])
@pytest.mark.asyncio
async def test_bad_interpretation_never_forms_or_adopts_an_answer(failure: str) -> None:
    binding = interpreted_profile()
    prompts: list[dict[str, Any]] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        prompts.append(prompt)
        assert prompt["phase"] == "interpretation"
        if failure == "cancelled":
            raise asyncio.CancelledError
        return completion('{"goals":[]}')

    runtime = build_runtime(
        policy(), make_corpus(), profile=binding, model_relay=relay, started_at=STARTED, clock=lambda: NOW
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            if failure == "cancelled":
                with pytest.raises(asyncio.CancelledError):
                    await runtime.process(make_request(action="converse"))
            else:
                result = await runtime.process(make_request(action="converse"))
                assert result.status == "error"
                assert result.text == ""
        assert len(prompts) == 1
        assert runtime.substrate.leases.active() == []
        for session in await runtime.sessions.list_sessions():
            assert session.message_history == []
            assert all(turn.state == "failed" for turn in session.turns)
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_native_ignore_bypasses_request_decomposition() -> None:
    binding = interpreted_profile()
    prompts: list[dict[str, Any]] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        prompts.append(prompt)
        assert prompt["conversation_phase"] == "addressing"
        return completion(
            canonical_json(
                {"kind": "ignore", "request_id": prompt["request_id"], "anchor_event_id": prompt["anchor"]["event_id"]}
            )
        )

    runtime = build_runtime(
        continuation_policy(), make_corpus(), profile=binding, model_relay=relay, started_at=STARTED, clock=lambda: NOW
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            result = await runtime.process(continuation("followup"))
        assert result.status == "ignore"
        assert result.text == ""
        assert len(prompts) == 1
        assert runtime.substrate.leases.active() == []
    finally:
        await runtime.aclose()


@pytest.mark.parametrize(
    ("presentation", "mode"),
    [("none", "balanced"), ("abbreviated", "balanced"), ("full", "complete_quotes")],
)
def test_typed_quote_intent_never_parses_english_goal_text(presentation: str, mode: str) -> None:
    requirements = TaskRequirements.model_validate_json(
        canonical_json(
            {
                "version": 1,
                "goals": ["Provide the full, untrimmed biblical quote for each week and its method and purpose."],
                "constraints": ["Keep the surrounding explanation short."],
                "quotation_presentation": presentation,
                "required_context": [],
            }
        )
    )
    assert requirements.projection_mode == mode
    assert len(requirements.goals) == 1
    assert requirements.constraints == ("Keep the surrounding explanation short.",)


@pytest.mark.parametrize("handles", [("missing",), ("history:0", "history:0")])
def test_required_context_handles_cannot_be_forged_or_duplicated(
    handles: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match=r"conversation_request_|validation error"):
        parse_request_goals(
            canonical_json(
                {
                    **REQUIREMENTS.model_dump(mode="json"),
                    "required_context": handles,
                }
            ),
            request=make_request(action="converse"),
            profile=interpreted_profile(),
        )


def test_required_attributed_context_survives_history_trimming_and_binds_digest() -> None:
    from lychd.compositions.reach.conversation_workflow import conversation_prompt

    binding = interpreted_profile()
    history = tuple(
        ReachHistoryEntry(
            subject_id="person:one",
            event_id=f"old:{index}",
            conversation_id="channel:one",
            occurred_at=NOW - timedelta(seconds=30 - index),
            text=("Essential method and purpose." if index == 0 else "h" * 1200),
        )
        for index in range(12)
    )
    request = make_request(action="converse", question="Finish that response.").model_copy(update={"history": history})
    requirements = REQUIREMENTS.model_copy(update={"required_context": ("history:0",)})
    required = resolved_required_context(requirements, request, binding)
    assert required[0]["entry"] == history[0].model_dump(mode="json")
    prompt = json.loads(conversation_prompt(binding, make_corpus(), request, task_requirements=requirements))
    assert prompt["question"] == request.event.question
    assert prompt["required_context"] == list(required)
    assert prompt["omitted_recent_messages"] > 0
    assert all(item["event_id"] != history[0].event_id for item in prompt["recent_messages"])
    changed = request.model_copy(
        update={
            "history": (
                history[0].model_copy(update={"text": "Different method."}),
                *history[1:],
            )
        }
    )
    assert request_goals_digest(requirements, request=request, profile=binding) != request_goals_digest(
        requirements, request=changed, profile=binding
    )
    small = binding.model_copy(update={"max_input_chars": 1000})
    with pytest.raises(DocumentsRefused, match="conversation_budget"):
        conversation_prompt(small, make_corpus(), request, task_requirements=requirements)


@pytest.mark.parametrize("version", [True, 1.0, "1", 0, 2])
def test_requirements_version_requires_original_integer_one(version: object) -> None:
    with pytest.raises(ValidationError):
        TaskRequirements.model_validate_json(
            canonical_json({**REQUIREMENTS.model_dump(mode="json"), "version": version})
        )


@pytest.mark.parametrize("anchor_field", ["reply_anchor", "continuation_anchor"])
@pytest.mark.parametrize("phase", ["planning", "synthesis"])
def test_selected_anchor_has_one_persona_attributed_body_within_exact_budget(anchor_field: str, phase: str) -> None:
    from lychd.compositions.reach.checkback import (
        CheckbackEnvelope,
        checkback_reserve,
        checkback_spec,
        model_input_cost,
        validate_checkback_budget,
    )
    from lychd.compositions.reach.conversation_workflow import conversation_prompt, persona_text
    from lychd.compositions.reach.documents import read_research_document
    from lychd.compositions.reach.research import ResearchPlan, synthesis_prompt

    binding = interpreted_profile()
    anchor = ReachHistoryEntry(
        subject_id="agent:one",
        subject_label="Transport agent label",
        event_id="selected-anchor",
        conversation_id="channel:one",
        occurred_at=NOW - timedelta(seconds=5),
        text="The exact selected anchor body preserves its method and purpose. " * 20,
    )
    request = make_request(action="converse", question="Finish that response.").model_copy(
        update={
            anchor_field: anchor,
            "reply_to_event_id": anchor.event_id if anchor_field == "reply_anchor" else None,
        }
    )
    requirements = REQUIREMENTS.model_copy(update={"required_context": (anchor_field,)})
    corpus = make_corpus("# Graph\nThe source preserves the method and purpose.")
    source = read_research_document(corpus, "doc:docs/graph.md", question="Graph")
    plan = ResearchPlan(kind="research", text="Read Graph.", source_ids=(source.id,))

    def render(selected: OperatorConversationProfile) -> str:
        if phase == "planning":
            return conversation_prompt(
                selected, corpus, request, agent_subject_id=anchor.subject_id, task_requirements=requirements
            )
        return synthesis_prompt(
            selected,
            corpus,
            request,
            plan,
            (source,),
            instructions=persona_text(selected),
            agent_subject_id=anchor.subject_id,
            task_requirements=requirements,
        )

    def reserve(selected: OperatorConversationProfile) -> Any:
        return checkback_reserve(
            selected,
            persona_text(selected),
            phase="conversation" if phase == "planning" else "synthesis",
            correction_phase="terminal_correction" if phase == "planning" else "synthesis",
            question=request.event.question,
            runtime_claims=phase == "synthesis",
        )

    prompt = render(binding)
    cost = model_input_cost(
        binding, persona_text(binding), prompt, phase="conversation" if phase == "planning" else "synthesis"
    )
    selected_cap = cost.input_chars + reserve(binding).input_chars + 8
    assert selected_cap <= binding.max_input_chars
    binding = OperatorConversationProfile.model_validate_json(
        canonical_json({**binding.model_dump(mode="json"), "max_input_chars": selected_cap})
    )
    prompt = render(binding)
    context = json.loads(prompt)
    assert context[anchor_field] == {"required_context_handle": anchor_field}
    assert context["required_context"][0]["handle"] == anchor_field
    entry = context["required_context"][0]["entry"]
    assert entry == {**anchor.model_dump(mode="json"), "subject_label": binding.persona_name}
    assert prompt.count(canonical_json(anchor.text)) == 1
    if anchor_field == "reply_anchor":
        assert context["reply_to_event_id"] == anchor.event_id
    actual = model_input_cost(
        binding, persona_text(binding), prompt, phase="conversation" if phase == "planning" else "synthesis"
    )
    assert max(actual.excess(binding, reserve(binding))) <= 0
    duplicate = canonical_json({**context, anchor_field: entry})
    duplicated_cost = model_input_cost(
        binding, persona_text(binding), duplicate, phase="conversation" if phase == "planning" else "synthesis"
    )
    assert duplicated_cost.excess(binding, reserve(binding))[0] > 0
    envelope = CheckbackEnvelope.prepare(request, prompt, persona_name=binding.persona_name)
    review = envelope.prompt(canonical_json({"kind": "answer", "text": "The complete response."}))
    assert json.loads(review)["context"] == context
    assert review.count(canonical_json(anchor.text)) == 1
    validate_checkback_budget(binding, checkback_spec(binding), review, phase=envelope.decision_variant)


def paragraph_profile(**changes: Any) -> OperatorConversationProfile:
    return OperatorConversationProfile.model_validate_json(
        canonical_json(
            {
                **interpreted_profile().model_dump(mode="json"),
                "context_projection_version": 2,
                **changes,
            }
        )
    )


def paragraph_request(text: str) -> Any:
    entry = ReachHistoryEntry(
        subject_id="person:one",
        event_id="paragraph-parent",
        conversation_id="channel:one",
        occurred_at=NOW - timedelta(seconds=5),
        text=text,
    )
    return make_request(action="converse", question="Finish that response and explain the earlier error.").model_copy(
        update={"history": (entry,)}
    )


def test_context_projection_opt_in_preserves_legacy_bindings_and_whole_offers() -> None:
    raw = {"persona_name": "Example", "persona_instructions": "Be useful."}
    omitted = OperatorConversationProfile.model_validate_json(canonical_json(raw))
    explicit = OperatorConversationProfile.model_validate_json(canonical_json(raw | {"context_projection_version": 1}))
    assert omitted.digest == explicit.digest == "150082ac6f4444eb5e577d16215ffdf93ce24ead56887dedf42e90ecec016b15"
    request = paragraph_request("First paragraph.\n\nSecond paragraph.")
    legacy = interpreted_profile()
    prompt = json.loads(request_goals_prompt(legacy, request))
    assert "context_projection_version" not in prompt
    assert prompt["recent_messages"] == [{"handle": "history:0", "entry": request.history[0].model_dump(mode="json")}]
    assert legacy.digest == legacy.model_copy(update={"context_projection_version": 1}).digest
    assert paragraph_profile().digest != legacy.digest


@pytest.mark.parametrize("version", [True, False, 2.0, "2", None, 0, 3])
def test_context_projection_version_is_an_original_supported_integer(version: object) -> None:
    with pytest.raises(ValidationError):
        paragraph_profile(context_projection_version=version)


def test_paragraph_projection_requires_explicit_typed_interpretation() -> None:
    with pytest.raises(ValidationError, match="context_projection_requires_interpretation"):
        paragraph_profile(request_goals=False)


def test_paragraph_offers_show_body_once_and_bind_exact_parent_and_utf8_ranges() -> None:
    from hashlib import sha256

    from lychd.compositions.reach.request_goals import required_context_proofs

    binding = paragraph_profile()
    request = paragraph_request(
        "Caf\N{LATIN SMALL LETTER E WITH ACUTE} \N{SLIGHTLY SMILING FACE} first.\n\nThe earlier answer omitted the ending.\n\nIts purpose remains exact."
    )
    offered = json.loads(request_goals_prompt(binding, request))
    assert offered["context_projection_version"] == 2
    parent = offered["recent_messages"][0]
    assert parent["omitted_paragraphs"] == 0
    assert len(parent["paragraphs"]) == 3
    assert request_goals_prompt(binding, request).count(canonical_json(request.history[0].text)) == 1
    handles = ("history:0:p0", "history:0:p1")
    requirements = parse_request_goals(
        canonical_json({**REQUIREMENTS.model_dump(mode="json"), "required_context": handles}),
        request=request,
        profile=binding,
    )
    selected = cast("tuple[dict[str, Any], ...]", resolved_required_context(requirements, request, binding))
    proofs = cast("tuple[dict[str, Any], ...]", required_context_proofs(requirements, request, binding))
    for unit, proof, span in zip(selected, proofs, parent["paragraphs"][:2], strict=True):
        text = request.history[0].text
        assert unit == {
            "handle": span["handle"],
            "entry": {
                **request.history[0].model_dump(mode="json"),
                "text": text[span["start"] : span["end"]],
            },
            "partial": True,
        }
        assert set(proof) == {
            "handle",
            "event_id",
            "parent_digest",
            "start",
            "end",
            "byte_start",
            "byte_end",
            "text_digest",
            "kind",
        }
        assert proof["start"] == span["start"]
        assert proof["end"] == span["end"]
        assert proof["byte_start"] == len(text[: span["start"]].encode())
        assert proof["byte_end"] == len(text[: span["end"]].encode())
        assert proof["text_digest"] == sha256(unit["entry"]["text"].encode()).hexdigest()
        assert (
            proof["parent_digest"]
            == sha256(canonical_json(request.history[0].model_dump(mode="json")).encode()).hexdigest()
        )
        assert "parent_digest" not in unit
        assert "start" not in unit
    assert proofs[1]["byte_start"] > proofs[1]["start"]
    assert selected[1]["entry"]["text"] == "The earlier answer omitted the ending."
    changed = request.model_copy(
        update={
            "history": (
                request.history[0].model_copy(
                    update={
                        "text": request.history[0].text.replace("purpose", "reason!"),
                    }
                ),
            )
        }
    )
    assert selected == resolved_required_context(requirements, changed, binding)
    assert request_goals_digest(requirements, request=request, profile=binding) != request_goals_digest(
        requirements,
        request=changed,
        profile=binding,
    )


@pytest.mark.parametrize(
    "handles",
    [
        ("history:0", "history:0:p0"),
        ("history:0:p0", "history:0:p0"),
        ("history:0:p9",),
        ("history:0:prefix3",),
        ("history:99:p0",),
    ],
)
def test_unoffered_duplicate_and_whole_plus_paragraph_selections_refuse(handles: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match=r"conversation_request_|validation error"):
        parse_request_goals(
            canonical_json({**REQUIREMENTS.model_dump(mode="json"), "required_context": handles}),
            request=paragraph_request("One.\n\nTwo."),
            profile=paragraph_profile(),
        )


def test_overlapping_host_units_refuse_without_accepting_free_offsets(monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.compositions.reach import request_goals as goal_module

    def overlapping(_text: str) -> tuple[tuple[int, int], ...]:
        return ((0, 20), (10, 30))

    monkeypatch.setattr(goal_module, "_context_paragraphs", overlapping)
    with pytest.raises(ValueError, match="conversation_request_context"):
        parse_request_goals(
            canonical_json(
                {**REQUIREMENTS.model_dump(mode="json"), "required_context": ["history:0:p0", "history:0:p1"]}
            ),
            request=paragraph_request("A complete host parent with more than thirty characters."),
            profile=paragraph_profile(),
        )


def test_only_eight_complete_units_are_offered_and_trimmed_parents_lose_all_handles() -> None:
    binding = paragraph_profile()
    request = paragraph_request("\n\n".join(f"Paragraph {i} stays whole." for i in range(10)))
    offered = json.loads(request_goals_prompt(binding, request))["recent_messages"][0]
    assert len(offered["paragraphs"]) == 8
    assert offered["omitted_paragraphs"] == 2
    requirements = parse_request_goals(
        canonical_json({**REQUIREMENTS.model_dump(mode="json"), "required_context": ["history:0:p7"]}),
        request=request,
        profile=binding,
    )
    entry = cast("dict[str, object]", resolved_required_context(requirements, request, binding)[0]["entry"])
    assert entry["text"] == "Paragraph 7 stays whole."
    with pytest.raises(ValueError, match="conversation_request_context"):
        parse_request_goals(
            canonical_json({**REQUIREMENTS.model_dump(mode="json"), "required_context": ["history:0:p8"]}),
            request=request,
            profile=binding,
        )
    history = tuple(
        request.history[0].model_copy(
            update={
                "event_id": f"entry:{i}",
                "occurred_at": NOW - timedelta(seconds=20 - i),
                "text": f"Entry {i}. " + "x" * 1200,
            }
        )
        for i in range(6)
    )
    request = request.model_copy(update={"history": history})
    binding = paragraph_profile(max_input_chars=7000)
    assert json.loads(request_goals_prompt(binding, request))["omitted_recent_messages"] > 0
    with pytest.raises(ValueError, match="conversation_request_context"):
        parse_request_goals(
            canonical_json({**REQUIREMENTS.model_dump(mode="json"), "required_context": ["history:0:p0"]}),
            request=request,
            profile=binding,
        )


@pytest.mark.parametrize(
    "block",
    [
        "- First item.\n\n- Second item.\n\n  Continued explanation.",
        "> First quotation.\n\n> Second quoted paragraph.",
        "```text\nFirst code paragraph.\n\n*Literal code paragraph.*\n```",
        "~~~text\nFirst code paragraph.\n\nSecond code paragraph.\n~~~",
        "```text\nUnclosed code.\n\nIts remainder is indivisible.",
    ],
)
def test_paragraph_offers_keep_complete_list_quote_and_fenced_blocks(block: str) -> None:
    request = paragraph_request("Introduction.\n\n" + block)
    binding = paragraph_profile()
    offered = json.loads(request_goals_prompt(binding, request))["recent_messages"][0]
    assert len(offered["paragraphs"]) == 2
    selected = parse_request_goals(
        canonical_json({**REQUIREMENTS.model_dump(mode="json"), "required_context": ["history:0:p1"]}),
        request=request,
        profile=binding,
    )
    entry = cast("dict[str, object]", resolved_required_context(selected, request, binding)[0]["entry"])
    assert entry["text"] == block


def test_anchor_events_have_no_paragraph_offers_and_keep_raw_reference_obligations() -> None:
    from lychd.compositions.reach.conversation_references import reference_payload
    from lychd.compositions.reach.conversation_workflow import conversation_prompt

    binding = paragraph_profile()
    request = paragraph_request("An ordinary introduction.\n\nThe actual earlier error.")
    anchor = request.history[0].model_copy(
        update={"event_id": "anchor", "subject_id": "agent:one", "text": "### Week00\nFirst.\n\n### Week01\nSecond."}
    )
    request = request.model_copy(update={"reply_anchor": anchor, "reply_to_event_id": anchor.event_id})
    interpretation = json.loads(request_goals_prompt(binding, request))
    assert "paragraphs" not in interpretation["reply_anchor"]
    selected = parse_request_goals(
        canonical_json({**REQUIREMENTS.model_dump(mode="json"), "required_context": ["history:0:p1"]}),
        request=request,
        profile=binding,
    )
    prompt = json.loads(
        conversation_prompt(
            binding, make_corpus(), request, task_requirements=selected, agent_subject_id=anchor.subject_id
        )
    )
    assert prompt["question"] == request.event.question
    assert prompt["reference_hints"] == reference_payload(request)
    assert prompt["reply_anchor"] == {**anchor.model_dump(mode="json"), "subject_label": binding.persona_name}
    assert prompt["recent_messages"] == []
    assert prompt["required_context"][0]["entry"]["text"] == "The actual earlier error."
    duplicate = request.model_copy(update={"history": (anchor,)})
    assert "paragraphs" not in json.loads(request_goals_prompt(binding, duplicate))["recent_messages"][0]
    with pytest.raises(ValueError, match="conversation_request_context"):
        parse_request_goals(
            canonical_json({**REQUIREMENTS.model_dump(mode="json"), "required_context": ["reply_anchor:p0"]}),
            request=request,
            profile=binding,
        )


def test_selected_whole_parent_overflow_never_silently_becomes_a_paragraph() -> None:
    from lychd.compositions.reach.checkback import checkback_reserve, model_input_cost
    from lychd.compositions.reach.conversation_workflow import conversation_prompt, persona_text

    binding = paragraph_profile()
    request = paragraph_request("Essential referent.\n\n" + "Complete parent narrative. " * 55)
    corpus = make_corpus()
    partial = parse_request_goals(
        canonical_json({**REQUIREMENTS.model_dump(mode="json"), "required_context": ["history:0:p0"]}),
        request=request,
        profile=binding,
    )
    prompt = conversation_prompt(binding, corpus, request, task_requirements=partial)
    reserve = checkback_reserve(
        binding,
        persona_text(binding),
        phase="conversation",
        correction_phase="terminal_correction",
        question=request.event.question,
    )
    cap = (
        model_input_cost(binding, persona_text(binding), prompt, phase="conversation").input_chars
        + reserve.input_chars
        + 8
    )
    assert cap <= binding.max_input_chars
    binding = paragraph_profile(max_input_chars=cap)
    conversation_prompt(binding, corpus, request, task_requirements=partial)
    whole = parse_request_goals(
        canonical_json({**REQUIREMENTS.model_dump(mode="json"), "required_context": ["history:0"]}),
        request=request,
        profile=binding,
    )
    with pytest.raises(DocumentsRefused, match="conversation_budget"):
        conversation_prompt(binding, corpus, request, task_requirements=whole)
