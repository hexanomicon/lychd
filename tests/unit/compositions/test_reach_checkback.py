"""Native finite checkback binds exact candidates and keeps source evidence transient."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from typing import Any, Literal, cast
from uuid import uuid4

import pytest
from pydantic import ValidationError
from pydantic_ai.models import override_allow_model_requests
from scripts.reach_worker import build_runtime

from lychd.compositions.reach.checkback import (
    CHECKBACK_CLARIFICATION,
    CHECKBACK_RESERVE_CHARS,
    COMPLETE_QUOTES_RULE,
    GUARD_RULE,
    GUARD_VERSION,
    MAX_RUNTIME_CLAIMS_BYTES,
    PUBLIC_TEXT_EVIDENCE_RULE,
    REFERENCE_GUARD_RULE,
    RUNTIME_GUARD_RULE,
    RUNTIME_GUARD_VERSION,
    CheckbackEnvelope,
    InputBudget,
    InvalidCheckbackOutputError,
    checkback_reserve,
    checkback_retry_control,
    checkback_retry_digest,
    checkback_spec,
    effective_checkback,
    model_input_cost,
    runtime_claim_metadata,
    unchanged_explanation,
    validate_checkback_budget,
)
from lychd.compositions.reach.decision_format import DecisionVariant
from lychd.compositions.reach.documents_workflow import DocumentsRefused
from lychd.compositions.reach.operator_model_wire import (
    MAX_MODEL_PAYLOAD_BYTES,
    OperatorConversationProfile,
    canonical_json,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_trace import ReachTraceEvent, trace_bytes
from lychd.compositions.reach.operator_wire import MAX_WIRE_BYTES, ReachHistoryEntry, ReachWorkerRequest
from lychd.compositions.reach.research import ResearchPlan, synthesis_prompt
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.stasis import InMemoryStasisStore
from tests.unit.compositions.test_reach_conversation import completion, policy, profile
from tests.unit.compositions.test_reach_conversation_references import SUCCESSOR_ANCHOR, SUCCESSOR_QUESTION
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_request
from tests.unit.compositions.test_reach_research import (
    PUBLIC_TEXT_SCOPE,
    RAW_SOURCE_MARKER,
    admitted_source,
    answer_json,
    assert_generation_cost,
    plan_json,
    relay_response,
    research_profile,
)

MISSING_EVIDENCE_QUESTION = "Please quote the missing source passage so I can verify the requested comparison."


def test_review_spotlights_and_binds_the_literal_request_instead_of_an_interpreted_plan() -> None:
    request = make_request(action="converse", question="What comes after the opening period?")
    context = canonical_json({"question": "What comes after labelled period 01?", "research_plan": "Read period 02."})
    envelope = CheckbackEnvelope.prepare(request, context)
    candidate = canonical_json({"kind": "answer", "text": "The next period is 01."})
    prompt = json.loads(envelope.prompt(candidate))
    assert prompt["task"] == request.event.question
    assert prompt["context"] == json.loads(context)
    changed = CheckbackEnvelope.prepare(
        request.model_copy(
            update={
                "event": request.event.model_copy(
                    update={"question": "An unrelated request"},
                )
            }
        ),
        context,
    )
    assert envelope.bindings(candidate)["evidence_digest"] != changed.bindings(candidate)["evidence_digest"]
    assert envelope.bindings(candidate)["request_digest"] != changed.bindings(candidate)["request_digest"]


def test_disabled_goal_interpretation_uses_a_focused_review_and_reserves_the_literal_task() -> None:
    binding = profile().model_copy(update={"checkback": True, "adaptive_context": True})
    assert "answer_quote" not in checkback_spec(binding).instructions
    enabled = binding.model_copy(update={"request_goals": True})
    assert "answer_quote" in checkback_spec(enabled).instructions
    instructions = "Fixed short instructions"
    empty = checkback_reserve(binding, instructions, phase="conversation", correction_phase="terminal_correction")
    unicode_task = checkback_reserve(
        binding, instructions, question="漢" * 100, phase="conversation", correction_phase="terminal_correction"
    )
    assert unicode_task.input_chars - empty.input_chars == 100
    assert unicode_task.payload_bytes - empty.payload_bytes == 300
    assert unicode_task.frame_bytes - empty.frame_bytes == 300
    for selected in (binding, enabled):
        expected = (
            CHECKBACK_RESERVE_CHARS
            + len(canonical_json({"task": ""}))
            + max(len(checkback_spec(selected, correction=correction).instructions) for correction in (False, True))
            - len(instructions)
        )
        assert (
            checkback_reserve(
                selected, instructions, phase="conversation", correction_phase="terminal_correction"
            ).input_chars
            == expected
        )
    assert (
        checkback_reserve(
            enabled, instructions, phase="conversation", correction_phase="terminal_correction"
        ).input_chars
        >= empty.input_chars
    )


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unsupported", "invented_quote"])
def test_frozen_goal_coverage_cannot_accept_an_uncovered_or_unquoted_outcome(mutation: str) -> None:
    request = make_request(action="converse")
    context = canonical_json({"request_goals": ["Explain today", "Explain what follows"]})
    envelope = CheckbackEnvelope.prepare(request, context)
    contract = json.loads(envelope.prompt(canonical_json({"kind": "answer", "text": "Draft"})))[
        "review_output_contract"
    ]
    assert contract["required_keys"] == ["coverage", "verdict", "issues"]
    assert contract["coverage_goal_indices"] == [0, 1]
    candidate = canonical_json({"kind": "answer", "text": "Today we explore. Next week we choose a task."})
    coverage: list[dict[str, Any]] = [
        {"goal": 0, "status": "complete", "answer_quote": "Today we explore."},
        {"goal": 1, "status": "complete", "answer_quote": "Next week we choose a task."},
    ]
    if mutation == "missing":
        coverage.pop()
    elif mutation == "duplicate":
        coverage[1]["goal"] = 0
    elif mutation == "unsupported":
        coverage[1] = {"goal": 1, "status": "missing"}
    else:
        coverage[1]["answer_quote"] = "An invented future claim."
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(canonical_json({"verdict": "accept", "issues": [], "coverage": coverage}), candidate)


def test_missing_outlook_can_request_correction_and_exact_fulfillment_can_be_adopted() -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"), canonical_json({"request_goals": ["Describe today", "Explain the outlook"]})
    )
    original = canonical_json({"kind": "answer", "text": "Today we explore."})
    revision = envelope.parse(
        canonical_json(
            {
                "verdict": "revise",
                "issues": ["missing_component"],
                "coverage": [
                    {"goal": 0, "status": "complete", "answer_quote": "Today we explore."},
                    {"goal": 1, "status": "missing"},
                ],
            }
        ),
        original,
    )
    assert revision.verdict == "revise"
    repair = json.loads(envelope.prompt(original, correction=revision))
    assert repair["prior_coverage"] == [{"goal": 0, "status": "complete"}, {"goal": 1, "status": "missing"}]
    corrected = canonical_json({"kind": "answer", "text": "Today we explore.\nNext week we choose a task."})
    accepted = envelope.parse(
        canonical_json(
            {
                "verdict": "accept",
                "issues": [],
                "coverage": [
                    {"goal": 0, "status": "complete", "answer_quote": "Today we explore."},
                    {"goal": 1, "status": "complete", "answer_quote": "Next week we choose a task."},
                ],
            }
        ),
        corrected,
    )
    assert accepted.verdict == "accept"
    assert accepted.request_digest == revision.request_digest
    assert accepted.evidence_digest == revision.evidence_digest
    assert accepted.candidate_digest != revision.candidate_digest


def test_unsupported_goal_may_identify_the_exact_candidate_phrase_without_becoming_accepted() -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"), canonical_json({"request_goals": ["Name the opening method"]})
    )
    candidate = canonical_json({"kind": "answer", "text": "The opening method is __enter__."})
    value: dict[str, Any] = {
        "verdict": "revise",
        "issues": ["wrong_target"],
        "coverage": [{"goal": 0, "status": "unsupported", "answer_quote": "The opening method is __enter__."}],
    }
    assert envelope.parse(canonical_json(value), candidate).verdict == "revise"
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(canonical_json(value | {"verdict": "accept", "issues": []}), candidate)
    value["coverage"][0]["answer_quote"] = "Invented words."
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(canonical_json(value), candidate)


@pytest.mark.parametrize("quote", ["Walk the Repository: Browse the code.", "Use __new__."])
def test_coverage_accepts_visible_wording_without_markdown_presentation(quote: str) -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"), canonical_json({"request_goals": ["Give the first step"]})
    )
    candidate = canonical_json({"kind": "answer", "text": "**Walk the Repository:** Browse the code. Use `__new__`."})
    value: dict[str, Any] = {
        "verdict": "accept",
        "issues": [],
        "coverage": [{"goal": 0, "status": "complete", "answer_quote": quote}],
    }
    assert envelope.parse(canonical_json(value), candidate).verdict == "accept"
    for changed in ("Use __enter__.", "Use new.", "****"):
        value["coverage"][0]["answer_quote"] = changed
        with pytest.raises(ValueError, match="conversation_checkback_coverage"):
            envelope.parse(canonical_json(value), candidate)


@pytest.mark.parametrize(
    ("text", "quote"),
    [
        ("**Week 00 · `__new__`** introduces the first method.", "Week 00 · `__new__`"),
        ("`**The first method**` is introduced here.", "**The first method**"),
    ],
)
def test_coverage_accepts_exact_excerpts_inside_nested_markdown(text: str, quote: str) -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"), canonical_json({"request_goals": ["Name the first method"]})
    )
    candidate = canonical_json({"kind": "answer", "text": text})
    value: dict[str, Any] = {
        "verdict": "accept",
        "issues": [],
        "coverage": [{"goal": 0, "status": "complete", "answer_quote": quote}],
    }
    assert quote in text
    assert envelope.parse(canonical_json(value), candidate).verdict == "accept"
    for changed in ("An unrelated method.", "The opening technique", "****"):
        value["coverage"][0]["answer_quote"] = changed
        with pytest.raises(ValueError, match="conversation_checkback_coverage"):
            envelope.parse(canonical_json(value), candidate)


def formatting_coverage_case(text: str, quote: str, *, public: bool) -> tuple[CheckbackEnvelope, str, str]:
    context: dict[str, Any] = {"request_goals": ["Describe the opening method."]}
    if public:
        context.update(
            {
                "research_phase": "synthesis",
                "evidence_scope": PUBLIC_TEXT_SCOPE,
                "research_sources": [{"id": "doc:docs/graph.md", "status": "ok", "text": "Public project text."}],
            }
        )
    envelope = CheckbackEnvelope.prepare(make_request(action="converse"), canonical_json(context))
    candidate = canonical_json({"kind": "answer", "text": text})
    output = canonical_json(
        {
            "verdict": "accept",
            "issues": [],
            "coverage": [{"goal": 0, "status": "complete", "answer_quote": quote}],
            **({"current_runtime_claims": []} if public else {}),
        }
    )
    return envelope, candidate, output


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize(
    ("text", "quote"),
    [
        (
            "**00 `__new__` (2\N{EN DASH}8 Nov):** *Let there be light.*",
            "00 `__new__` (2\N{EN DASH}8 Nov): Let there be light.",
        ),
        (
            "**00 `__new__` (2\N{EN DASH}8 Nov):** *Let there be light.*",
            "00 __new__ (2\N{EN DASH}8 Nov): Let there be light.",
        ),
        ("The **first method** is __new__.", "The first method is __new__."),
        ("The *first method* is __new__.", "The first method is __new__."),
        ("Use `__new__` for the first method.", "Use __new__ for the first method."),
        ("Use ``__new__`` for the first method.", "Use __new__ for the first method."),
        ("Use ``a ` b`` for the first method.", "Use a ` b for the first method."),
        ("The **first *method* uses `__new__`** now.", "The first method uses __new__ now."),
        ("The *first **method** uses ``__new__``* now.", "The first method uses __new__ now."),
        ("**First   method:**\nUse `__new__` now.", "First method: Use __new__ now."),
        ("Keep `a *b* c` intact.", "a *b* c"),
    ],
)
def test_coverage_recognizes_only_the_closed_presentation_subset(text: str, quote: str, *, public: bool) -> None:
    envelope, candidate, output = formatting_coverage_case(text, quote, public=public)
    decision = envelope.parse(output, candidate)
    assert decision.verdict == "accept"
    assert decision.coverage[0].answer_quote == quote


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize(
    ("text", "quote"),
    [
        ("Compute a * b * c now.", "Compute a b c now."),
        (r"The a \*b\* c method is ready.", "The a b c method is ready."),
        (r"The **first** method uses a \ path.", r"The first method uses a \ path."),
        ("The `a *b* c` method is ready.", "The a b c method is ready."),
        ("The ``a *b* c`` method is ready.", "The a b c method is ready."),
        ("The **first method is ready.", "The first method is ready."),
        ("The first method** is ready.", "The first method is ready."),
        ("The *first method is ready.", "The first method is ready."),
        ("The `first method is ready.", "The first method is ready."),
        ("The ``first method` is ready.", "The first method is ready."),
        ("The **first *method **uses** code* now**.", "The first method uses code now."),
        ("The **first *method** uses* code.", "The first method uses code."),
        ("The ***first method*** is ready.", "The first method is ready."),
        ("The ****first method**** is ready.", "The first method is ready."),
        ("The a*b*c method is ready.", "The abc method is ready."),
        ("The ** first method** is ready.", "The first method is ready."),
        ("The **first method ** is ready.", "The first method is ready."),
        ("Steps: * First method.", "Steps: First method."),
        ("The ```first method``` is ready.", "The first method is ready."),
        ("The ````first method```` is ready.", "The first method is ready."),
        ("The ~~first method~~ is ready.", "The first method is ready."),
        ("Before\n```\n**first method**\n```\nAfter", "Before first method After"),
        ("Before\n~~~\n**first method**\n~~~\nAfter", "Before first method After"),
        ("Before\n```\n**first method**\nAfter", "Before first method After"),
        ("Before\n~~~\n**first method**\nAfter", "Before first method After"),
        ("```text\n**first**\nThe *second* method.", "The second method."),
    ],
)
def test_coverage_keeps_unsupported_or_ambiguous_presentation_literal(text: str, quote: str, *, public: bool) -> None:
    envelope, candidate, exact_output = formatting_coverage_case(text, text, public=public)
    assert envelope.parse(exact_output, candidate).verdict == "accept"
    _, _, changed_output = formatting_coverage_case(text, quote, public=public)
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(changed_output, candidate)


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize("fence", ["```", "~~~"])
@pytest.mark.parametrize(
    "indent",
    [
        "    ",
        "\t",
        " \t",
        "  \t",
        "   \t",
        "\N{NO-BREAK SPACE}",
        "\N{EM SPACE}",
        " \N{NO-BREAK SPACE}",
    ],
)
def test_coverage_indented_pseudo_closer_keeps_the_remaining_fence_body_literal(
    fence: str, indent: str, *, public: bool
) -> None:
    text = f"{fence}\n{indent}{fence}\nThe *first* method."
    envelope, candidate, exact_output = formatting_coverage_case(text, text, public=public)
    assert envelope.parse(exact_output, candidate).verdict == "accept"
    _, _, changed_output = formatting_coverage_case(text, "The first method.", public=public)
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(changed_output, candidate)


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize("indent", ["    ", "\t", " \t", "  \t", "   \t"])
def test_coverage_indented_code_line_preserves_literal_emphasis_stars(indent: str, *, public: bool) -> None:
    text = f"{indent}The *first* method."
    envelope, candidate, exact_output = formatting_coverage_case(text, text, public=public)
    assert envelope.parse(exact_output, candidate).verdict == "accept"
    _, _, changed_output = formatting_coverage_case(text, "The first method.", public=public)
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(changed_output, candidate)


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize("fence", ["```", "~~~"])
@pytest.mark.parametrize("indent", ["", " ", "  ", "   "])
def test_coverage_valid_fence_closers_allow_presentation_on_following_lines(
    fence: str, indent: str, *, public: bool
) -> None:
    text = f"{fence}\nLiteral fenced text.\n{indent}{fence}\nThe *first* method."
    envelope, candidate, output = formatting_coverage_case(text, "The first method.", public=public)
    assert envelope.parse(output, candidate).verdict == "accept"


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize("indent", ["", " ", "  ", "   "])
def test_coverage_noncode_ascii_indentation_keeps_supported_emphasis(indent: str, *, public: bool) -> None:
    text = f"{indent}The *first* method."
    envelope, candidate, output = formatting_coverage_case(text, "The first method.", public=public)
    assert envelope.parse(output, candidate).verdict == "accept"


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize(
    "quote",
    [
        "00 __enter__ (2\N{EN DASH}8 Nov): Let there be light.",
        "00 new (2\N{EN DASH}8 Nov): Let there be light.",
        "01 __new__ (2\N{EN DASH}8 Nov): Let there be light.",
        "00 __new__ (2-8 Nov): Let there be light.",
        "00 __new__ (2\N{EN DASH}8 Nov); Let there be light.",
        "00 __new__ (2\N{EN DASH}8 Nov): Let there be darkness.",
        "00 __new__ (2\N{EN DASH}8 Nov): let there be light.",
        "00 __new__ (2\N{EN DASH}8 Nov): Let there be light!",
    ],
)
def test_coverage_presentation_never_changes_words_identifiers_digits_punctuation_or_case(
    quote: str, *, public: bool
) -> None:
    text = "**00 `__new__` (2\N{EN DASH}8 Nov):** *Let there be light.*"
    envelope, candidate, output = formatting_coverage_case(text, quote, public=public)
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(output, candidate)


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize(
    ("text", "quote"),
    [
        ("**Café** is ready.", "Cafe\N{COMBINING ACUTE ACCENT} is ready."),
        ("**First method.** Intervening words. *Second method.*", "First method. Second method."),
    ],
)
def test_coverage_keeps_unicode_and_contiguous_candidate_wording_exact(text: str, quote: str, *, public: bool) -> None:
    envelope, candidate, output = formatting_coverage_case(text, quote, public=public)
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(output, candidate)


@pytest.mark.parametrize("public", [False, True])
def test_formatting_cannot_admit_a_phrase_found_only_in_request_history_or_goals(*, public: bool) -> None:
    foreign = "Let there be light."
    request = anchored_request(question=foreign, text=foreign)
    assert request.reply_anchor is not None
    context: dict[str, Any] = {
        "request_goals": [foreign],
        "question": foreign,
        "recent_messages": [request.reply_anchor.model_dump(mode="json")],
    }
    if public:
        context.update(
            {
                "research_phase": "synthesis",
                "evidence_scope": PUBLIC_TEXT_SCOPE,
                "research_sources": [{"id": "doc:docs/graph.md", "status": "ok", "text": "Public project text."}],
            }
        )
    envelope = CheckbackEnvelope.prepare(request, canonical_json(context))
    candidate = canonical_json({"kind": "answer", "text": "**The first method** creates an object."})
    _, _, output = formatting_coverage_case("unused", f"*{foreign}*", public=public)
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(output, candidate)


def test_coverage_presentation_does_not_normalize_runtime_claim_observations() -> None:
    text = "The **first method** is ready."
    quote = "The first method is ready."
    envelope, candidate, output = formatting_coverage_case(text, quote, public=True)
    assert envelope.parse(output, candidate).verdict == "accept"
    changed = json.loads(output)
    changed["current_runtime_claims"] = [quote]
    with pytest.raises(ValueError, match="conversation_checkback_runtime_claims"):
        envelope.parse(canonical_json(changed), candidate)


def test_exact_frozen_goal_names_are_host_mapped_to_closed_indices() -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"), canonical_json({"request_goals": ["Name today", "Name the outlook"]})
    )
    candidate = canonical_json({"kind": "answer", "text": "Today we explore. Next week we choose."})
    value: dict[str, Any] = {
        "verdict": "accept",
        "issues": [],
        "coverage": [
            {"goal": "Name today", "status": "complete", "answer_quote": "Today we explore."},
            {"goal": "Name the outlook", "status": "complete", "answer_quote": "Next week we choose."},
        ],
    }
    assert [item.goal for item in envelope.parse(canonical_json(value), candidate).coverage] == [0, 1]
    for index, item in enumerate(value["coverage"]):
        item["goal"] = str(index)
    assert [item.goal for item in envelope.parse(canonical_json(value), candidate).coverage] == [0, 1]
    for changed in ("Unrequested goal", "name the outlook", " Name the outlook ", "Name today", "01", "1.0", "8"):
        value["coverage"][1]["goal"] = changed
        with pytest.raises(ValueError, match=r"conversation_checkback_coverage|valid integer"):
            envelope.parse(canonical_json(value), candidate)
    ambiguous = CheckbackEnvelope.prepare(
        make_request(action="converse"), canonical_json({"request_goals": ["1", "Name the outlook"]})
    )
    value["coverage"][0]["goal"] = "1"
    value["coverage"][1]["goal"] = 1
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        ambiguous.parse(canonical_json(value), candidate)


@pytest.mark.parametrize(
    ("field", "value"), [("gif_id", "so_it_begins"), ("reaction", "👀"), ("citations", "doc:docs/roadmap.md")]
)
def test_coverage_can_reference_an_exact_structured_output_selection(field: str, value: str) -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"), canonical_json({"request_goals": ["Include the requested output"]})
    )
    candidate = canonical_json(
        {"kind": "answer", "text": "Here you go.", field: [value] if field == "citations" else value}
    )
    decision = envelope.parse(
        canonical_json(
            {
                "verdict": "accept",
                "issues": [],
                "coverage": [{"goal": 0, "status": "complete", "answer_quote": value}],
            }
        ),
        candidate,
    )
    assert decision.verdict == "accept"


def verdict(kind: str, *, claims: tuple[str, ...] | None = None) -> str:
    return canonical_json(
        {
            "verdict": kind,
            "issues": [] if kind == "accept" else ["missing_component"],
            **({"clarification": MISSING_EVIDENCE_QUESTION} if kind == "needs_evidence" else {}),
            **({"current_runtime_claims": claims} if claims is not None else {}),
        }
    )


@pytest.mark.parametrize(
    ("verdicts", "expected", "count"),
    [
        (("accept",), "Original answer.", 2),
        (("revise", "accept"), "Corrected answer.", 4),
        (("revise", "revise"), CHECKBACK_CLARIFICATION, 4),
        (("needs_evidence",), MISSING_EVIDENCE_QUESTION, 2),
    ],
)
@pytest.mark.parametrize("kind", ["answer", "clarify"])
@pytest.mark.asyncio
async def test_native_terminal_checkback_is_bounded_and_settles_once(
    verdicts: tuple[str, ...],
    expected: str,
    count: int,
    kind: str,
) -> None:
    binding = profile().model_copy(
        update={
            "adaptive_context": True,
            "checkback": True,
            "json_object_output": True,
            "thinking_phases": ("checkback",),
        }
    )
    reviews = iter(verdicts)
    prompts: list[dict[str, Any]] = []
    events: list[ReachTraceEvent] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        body = validate_generation_payload(binding, payload)
        assert "tools" not in body
        prompt = json.loads(body["messages"][-1]["content"])
        phase_names: dict[str, DecisionVariant] = {"checkback": "checkback", "correction": "terminal_correction"}
        selected_phase = phase_names.get(prompt.get("phase"), "conversation")
        assert_generation_cost(binding, payload, phase=selected_phase)
        prompts.append(prompt)
        if prompt.get("phase") in {"checkback", "correction"}:
            assert (
                body["messages"][0]["content"]
                == checkback_spec(binding, correction=prompt["phase"] == "correction").instructions
            )
            assert prompt["task"] == prompts[0]["question"]
        if prompt.get("phase") == "checkback":
            assert prompt["context"] == prompts[0]
            return completion(
                verdict(next(reviews), claims=() if prompt.get("context", {}).get("evidence_scope") else None)
            )
        text = "Corrected answer." if prompt.get("phase") == "correction" else "Original answer."
        return completion(canonical_json({"kind": kind, "text": text}))

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=events.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            result = await runtime.process(
                make_request(action="converse", question='Explain "漢" and a path \\ once.').model_copy(
                    update={"request_id": str(uuid4())}
                )
            )
        assert result.text == expected
        assert result.status == (
            "clarify"
            if kind == "clarify" or expected in {CHECKBACK_CLARIFICATION, MISSING_EVIDENCE_QUESTION}
            else "conversation"
        )
        assert len(prompts) == count
        assert runtime.substrate.leases.active() == []
        assert result.run_id is not None
        run = await runtime.substrate.ledger.get(result.run_id)
        assert run is not None
        assert run.status is RunStatus.DONE
        session = await runtime.sessions.session_for_run(result.run_id)
        assert session is not None
        assert len(session.turns) == 1
        assert session.message_history == []
        assert "Original answer." not in session.turns[0].content or expected == "Original answer."
        checks = [event for event in events if event.name == "checkback" and event.status == "ok"]
        assert tuple(event.verdict for event in checks) == verdicts
        assert all(event.review_attempt is None for event in checks)
        assert all("retry_ordinal" not in json.loads(trace_bytes(event)) for event in checks)
        assert len({event.evidence_digest for event in checks}) == 1
        assert len({event.step_id for event in checks}) == 1
        if count == 4:
            assert checks[0].candidate_digest != checks[1].candidate_digest
        captured = b"".join(trace_bytes(event) for event in events).decode()
        assert "Original answer." not in captured
        assert "Corrected answer." not in captured
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("failure", ["foreign_digest", "malformed", "timeout", "cancelled"])
@pytest.mark.asyncio
async def test_bad_review_cannot_adopt_or_persist_candidate(failure: str) -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "checkback": True})
    calls = 0

    async def relay(operation: str, payload: str) -> str:
        nonlocal calls
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        calls += 1
        if calls == 1:
            return completion('{"kind":"answer","text":"Unadopted private candidate."}')
        if failure == "timeout":
            msg = "private error"
            raise TimeoutError(msg)
        if failure == "cancelled":
            raise asyncio.CancelledError
        if failure == "foreign_digest":
            return completion(canonical_json({"verdict": "accept", "issues": [], "candidate_digest": "a" * 64}))
        return completion('{"verdict":"accept"}')

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
        assert calls == 2
        assert runtime.substrate.leases.active() == []
        sessions = await runtime.sessions.list_sessions()
        for item in sessions:
            assert item.message_history == []
            assert all(turn.state == "failed" for turn in item.turns)
            assert all("Unadopted private candidate." not in turn.content for turn in item.turns)
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_correction_cannot_request_context_when_history_is_exhausted() -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "checkback": True})
    prompts: list[dict[str, Any]] = []
    events: list[ReachTraceEvent] = []
    candidate_text = "Unadopted candidate before forbidden context repair."

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        prompts.append(prompt)
        if prompt.get("phase") == "checkback":
            return completion(verdict("revise"))
        if prompt.get("phase") == "correction":
            return completion('{"kind":"read_more","text":"Read earlier history."}')
        assert prompt["history_state"] == "exhausted"
        return completion(canonical_json({"kind": "answer", "text": candidate_text}))

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=events.append,
    )
    request = make_request(action="converse").model_copy(
        update={"request_id": str(uuid4()), "history_state": "exhausted"}
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            result = await runtime.process(request)
        assert result.status == "error"
        assert result.text == ""
        assert len(prompts) == 3
        assert runtime.substrate.leases.active() == []
        checks = [event for event in events if event.name == "checkback" and event.status == "ok"]
        assert len(checks) == 1
        assert any(event.name == "correction" and event.status == "failed" for event in events)
        sessions = await runtime.sessions.list_sessions()
        for session in sessions:
            assert session.message_history == []
            assert all(turn.state == "failed" for turn in session.turns)
            assert all(candidate_text not in turn.content for turn in session.turns)
    finally:
        await runtime.aclose()


def assert_frozen_research_projection(prompts: list[dict[str, Any]], snapshots: list[str]) -> None:
    synthesis = next(prompt for prompt in prompts if prompt.get("research_phase") == "synthesis")
    phases = [prompt for prompt in prompts if "phase" in prompt]
    assert len(phases) == 3
    assert all(prompt["context"] == synthesis for prompt in phases)
    assert synthesis["evidence_scope"] == PUBLIC_TEXT_SCOPE
    assert RAW_SOURCE_MARKER in canonical_json(synthesis["research_sources"])
    assert snapshots
    assert all(RAW_SOURCE_MARKER not in snapshot for snapshot in snapshots)


@pytest.mark.parametrize("json_mode", [False, True])
@pytest.mark.asyncio
async def test_research_repair_reuses_identical_source_projection_without_new_reads(
    monkeypatch: pytest.MonkeyPatch,
    *,
    json_mode: bool,
) -> None:
    binding = research_profile(checkback=True, max_input_chars=24_000, json_object_output=json_mode)
    corpus = make_corpus()
    prompts: list[dict[str, Any]] = []
    snapshots: list[str] = []
    reviews = iter(("revise", "accept"))
    acquisitions = 0
    events: list[ReachTraceEvent] = []
    original_replace = InMemoryStasisStore.replace

    async def capture(store: InMemoryStasisStore, run_id: str, documents: list[Any]) -> None:
        snapshots.append(canonical_json(documents))
        await original_replace(store, run_id, documents)

    monkeypatch.setattr(InMemoryStasisStore, "replace", capture)

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        expected_phase: tuple[DecisionVariant, ...] = (
            "planning",
            "synthesis",
            "checkback_public",
            "synthesis",
            "checkback_public",
        )
        body = assert_generation_cost(binding, payload, phase=expected_phase[len(prompts)])
        prompt = json.loads(body["messages"][-1]["content"])
        prompts.append(prompt)
        if prompt.get("research_phase") == "planning":
            return completion(plan_json())
        if prompt.get("phase") == "checkback":
            return completion(
                verdict(next(reviews), claims=() if prompt.get("context", {}).get("evidence_scope") else None)
            )
        if prompt.get("phase") == "correction":
            return completion(
                canonical_json(
                    {
                        "kind": "answer",
                        "text": "Corrected complete answer.",
                        "citations": ["web:official", "doc:docs/graph.md"],
                    }
                )
            )
        return completion(answer_json())

    async def acquire(request: Any) -> Any:
        nonlocal acquisitions
        acquisitions += 1
        return relay_response(request)

    runtime = build_runtime(
        policy(),
        corpus,
        profile=binding,
        model_relay=relay,
        research_relay=acquire,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=events.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            result = await runtime.process(
                make_request(action="converse").model_copy(update={"request_id": str(uuid4())})
            )
        assert result.status == "conversation"
        assert "Corrected complete answer." in result.text
        assert acquisitions == 1
        assert len(prompts) == 5
        assert_frozen_research_projection(prompts, snapshots)
        assert result.run_id is not None
        session = await runtime.sessions.session_for_run(result.run_id)
        assert session is not None
        assert session.message_history == []
        assert all(RAW_SOURCE_MARKER not in turn.content for turn in session.turns)
        assert RAW_SOURCE_MARKER not in b"".join(trace_bytes(event) for event in events).decode()
        assert len([event for event in events if event.name == "source_read"]) == 1
    finally:
        await runtime.aclose()


def test_checkback_is_explicit_and_binds_exact_host_inputs_without_model_digest_echoes() -> None:
    assert not profile().checkback
    with pytest.raises(ValidationError):
        OperatorConversationProfile(persona_name="Example", persona_instructions="Voice", checkback=True)
    request = make_request(action="converse")
    envelope = CheckbackEnvelope.prepare(request, '{"question":"What?"}')
    candidate = '{"kind":"clarify","text":"Which source?"}'
    review = json.loads(envelope.prompt(candidate))
    bindings = envelope.bindings(candidate)
    assert not set(bindings) & review.keys()
    decision = envelope.parse(verdict("accept"), candidate)
    assert decision.verdict == "accept"
    assert all(getattr(decision, key) == value for key, value in bindings.items())
    changed_candidate = '{"kind":"answer","text":"A different answer."}'
    other = envelope.parse(verdict("accept"), changed_candidate)
    assert decision.candidate_digest != other.candidate_digest
    assert decision.evidence_digest == other.evidence_digest
    changed_request = request.model_copy(update={"request_id": str(uuid4())})
    changed = CheckbackEnvelope.prepare(changed_request, envelope.context_json)
    assert changed.parse(verdict("accept"), candidate).request_digest != decision.request_digest


@pytest.mark.parametrize("key", ["candidate_digest", "evidence_digest", "request_digest", "reasoning"])
def test_model_cannot_supply_host_digests_or_foreign_judgment_fields(key: str) -> None:
    envelope = CheckbackEnvelope.prepare(make_request(action="converse"), '{"question":"What?"}')
    candidate = '{"kind":"answer","text":"Answer."}'
    output = canonical_json({"verdict": "accept", "issues": [], key: "a" * 64})
    with pytest.raises(ValidationError):
        envelope.parse(output, candidate)


def test_approved_persona_identity_is_bound_without_changing_the_frozen_context() -> None:
    request = make_request(action="converse")
    context = '{"question":"Who are you?","research_sources":[]}'
    candidate = '{"kind":"answer","text":"I am Nadir."}'
    nadir = CheckbackEnvelope.prepare(request, context, persona_name="Nadir")
    other = CheckbackEnvelope.prepare(request, context, persona_name="Another")
    prompt = json.loads(nadir.prompt(candidate))
    assert prompt["approved_persona_name"] == "Nadir"
    assert prompt["context"] == json.loads(context)
    assert nadir.bindings(candidate)["evidence_digest"] != other.bindings(candidate)["evidence_digest"]
    assert nadir.parse(verdict("accept"), candidate).verdict == "accept"
    other_decision = other.parse(verdict("accept"), candidate)
    assert other_decision.evidence_digest == other.bindings(candidate)["evidence_digest"]
    assert other_decision.evidence_digest != nadir.parse(verdict("accept"), candidate).evidence_digest


@pytest.mark.parametrize("clarification", [None, " ", "Read https://example.com", "x" * 501])
def test_missing_evidence_requires_a_bounded_public_question(clarification: str | None) -> None:
    envelope = CheckbackEnvelope.prepare(make_request(action="converse"), '{"question":"What?"}')
    candidate = '{"kind":"answer","text":"Unsupported candidate."}'
    output = json.loads(verdict("needs_evidence")) | {"clarification": clarification}
    with pytest.raises(ValidationError):
        envelope.parse(canonical_json(output), candidate)


def test_public_clarification_is_for_missing_evidence_only_and_preserves_its_language() -> None:
    envelope = CheckbackEnvelope.prepare(make_request(action="converse"), '{"question":"Ktorý zdroj?"}')
    candidate = '{"kind":"clarify","text":"Ktorý zdroj?"}'
    question = "Môžete citovať chýbajúci odsek pôvodného zdroja?"
    missing = json.loads(verdict("needs_evidence")) | {"clarification": question}
    assert envelope.parse(canonical_json(missing), candidate).clarification == question
    for kind in ("accept", "revise"):
        invalid = json.loads(verdict(kind)) | {"clarification": question}
        with pytest.raises(ValidationError):
            envelope.parse(canonical_json(invalid), candidate)


@pytest.mark.parametrize("prompt", ["x" * 24_000, "𐍈" * 12_000, "\\" * 21_000])
def test_review_checks_character_utf8_and_escaped_frame_limits(prompt: str) -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "checkback": True, "max_input_chars": 24_000})
    with pytest.raises(DocumentsRefused, match="conversation_budget"):
        validate_checkback_budget(binding, checkback_spec(binding), prompt, phase="checkback")


FIRST_IDEA = "Read the README and roadmap to learn the project's purpose and next steps."
SECOND_IDEA = "Run the test suite or a simple local build to see what the codebase actually does right now."
IDEAS_ANCHOR = f"First: {FIRST_IDEA} Second: {SECOND_IDEA}"
SIMPLIFY_REQUEST = (
    "Explain the second idea in simpler everyday words, in one sentence. "
    "Give the simpler version without repeating the original sentence."
)
PLAINER_IDEA = "Try the project's checks or build it on your computer to find out what works."


def anchored_request(question: str = SIMPLIFY_REQUEST, *, text: str = IDEAS_ANCHOR) -> ReachWorkerRequest:
    request = make_request(action="converse", question=question)
    anchor = ReachHistoryEntry(
        subject_id="bot:one",
        event_id="anchor:one",
        conversation_id=request.event.conversation_id,
        text=text,
        occurred_at=NOW - timedelta(seconds=2),
    )
    return request.model_copy(update={"reply_to_event_id": anchor.event_id, "reply_anchor": anchor})


@pytest.mark.parametrize(
    ("question", "text"),
    [
        (SIMPLIFY_REQUEST, f"Second: {SECOND_IDEA}"),
        ("Can you explain the second idea in simpler words, one sentence?", SECOND_IDEA),
        ("What does the first idea mean in practice? One simple sentence please.", f"First: {FIRST_IDEA}"),
        ("Explain the second idea in simpler words without repeating the original.", f"**Second:** {SECOND_IDEA}"),
        ("Rephrase the second idea.", f'"{SECOND_IDEA}"'),
        ("Simplify the second idea.", SECOND_IDEA.replace(" ", "  ")),
        ("Explain the second sentence in practice.", SECOND_IDEA),
    ],
)
def test_guard_vetoes_complete_unchanged_sentences_for_explicit_transformation(question: str, text: str) -> None:
    request = anchored_request(question)
    candidate = canonical_json({"kind": "answer", "text": text})
    envelope = CheckbackEnvelope.prepare(request, canonical_json({"question": question}))
    raw = envelope.parse(verdict("accept"), candidate)
    control = effective_checkback(request, candidate, raw)
    assert control.guard_status == "unchanged_requested_transformation"
    assert control.effective_verdict == "revise"
    assert control.decision is raw
    assert raw.verdict == "accept"
    assert raw.issues == ()
    assert control.issues == ("missing_component",)
    correction = json.loads(envelope.prompt(candidate, correction=raw, control=control))
    assert correction["issues"] == ["missing_component"]
    assert correction["correction_control"]["origin"] == "core_adoption_guard"
    assert correction["correction_control"]["model_verdict"] == "accept"
    assert correction["correction_control"]["model_issues"] == []


@pytest.mark.parametrize(
    "question",
    [
        "Repeat the second idea exactly; no paraphrase.",
        "Quote the second idea exactly, with no paraphrase.",
        "Explain the second idea in simpler words and repeat the original exactly.",
        'Please follow this instruction: "Explain the second idea in simpler words".',
        '"Explain the second idea in simpler words."',
        "Do not simplify the second idea.",
        "The second idea is simpler. Repeat it.",
        "Can you explain either the first or the second idea in simpler words?",
        "What did the second idea say?",
    ],
)
def test_quoted_conflicting_or_literal_repeat_intent_abstains(question: str) -> None:
    assert (
        unchanged_explanation(anchored_request(question), canonical_json({"kind": "answer", "text": SECOND_IDEA}))
        == "not_applicable"
    )


@pytest.mark.parametrize(
    "text",
    [
        PLAINER_IDEA,
        f"{SECOND_IDEA} Try its checks on your computer and look at the results.",
        "Run the test suite.",
        "Do not run the test suite or a simple local build to see what the codebase actually does right now.",
        SECOND_IDEA.replace("right now", "later"),
        SECOND_IDEA.replace("test suite", "test suite number 2"),
    ],
)
def test_new_explanation_shared_phrases_and_meaningful_changes_pass(text: str) -> None:
    assert unchanged_explanation(anchored_request(), canonical_json({"kind": "answer", "text": text})) == "clear"


@pytest.mark.parametrize(
    "mutation", ["no_anchor", "history_only", "unbound", "both", "wrong_place", "truncated", "ambiguous"]
)
def test_guard_uses_only_one_unambiguous_actual_anchor(mutation: str) -> None:
    request = anchored_request()
    anchor = request.reply_anchor
    assert anchor is not None
    changes: dict[str, Any] = {}
    if mutation in {"no_anchor", "history_only"}:
        changes = {"reply_anchor": None, "reply_to_event_id": None}
        if mutation == "history_only":
            changes["history"] = (anchor,)
    elif mutation == "unbound":
        changes = {"reply_to_event_id": "other"}
    elif mutation == "both":
        changes = {"continuation_anchor": anchor.model_copy(update={"event_id": "other"})}
    elif mutation == "wrong_place":
        changes = {"reply_anchor": anchor.model_copy(update={"conversation_id": "other"})}
    elif mutation == "truncated":
        changes = {"reply_anchor": anchor.model_copy(update={"text": IDEAS_ANCHOR[:-1]})}
    else:
        changes = {
            "reply_anchor": anchor.model_copy(
                update={"text": f"{IDEAS_ANCHOR} Second: Another proposed action goes here."}
            )
        }
    assert (
        unchanged_explanation(
            request.model_copy(update=changes), canonical_json({"kind": "answer", "text": SECOND_IDEA})
        )
        == "not_applicable"
    )


def test_continuation_uses_its_actual_anchor_but_never_later_history() -> None:
    request = anchored_request()
    anchor = request.reply_anchor
    assert anchor is not None
    request = request.model_copy(
        update={
            "reply_anchor": None,
            "reply_to_event_id": None,
            "continuation_anchor": anchor,
            "event": request.event.model_copy(update={"trigger": "followup"}),
            "history": (
                anchor.model_copy(
                    update={"event_id": "later", "text": "A later unrelated answer says something else."}
                ),
            ),
        }
    )
    assert (
        unchanged_explanation(request, canonical_json({"kind": "answer", "text": SECOND_IDEA}))
        == "unchanged_requested_transformation"
    )


@pytest.mark.parametrize("raw_verdict", ["revise", "needs_evidence"])
@pytest.mark.parametrize("text", [PLAINER_IDEA, SECOND_IDEA])
def test_guard_never_promotes_a_model_rejection(raw_verdict: str, text: str) -> None:
    request = anchored_request()
    candidate = canonical_json({"kind": "answer", "text": text})
    raw = CheckbackEnvelope.prepare(request, "{}").parse(verdict(raw_verdict), candidate)
    control = effective_checkback(request, candidate, raw)
    assert control.guard_status == ("unchanged_requested_transformation" if text == SECOND_IDEA else "clear")
    assert raw.verdict == raw_verdict
    assert control.effective_verdict == raw_verdict
    assert control.decision is raw
    assert control.issues == raw.issues


def assert_guard_receipts(events: list[ReachTraceEvent], repair: str, *, research: bool) -> None:
    raw_events = [event for event in events if event.name == "checkback" and event.status == "ok"]
    assert [event.verdict for event in raw_events] == ["accept", "accept"]
    assert all(event.issue_codes == () for event in raw_events)
    assert all(event.runtime_claim_count == (0 if research else None) for event in raw_events)
    assert all((event.runtime_claim_digest is not None) == research for event in raw_events)
    control_events = [event for event in events if event.name == "checkback_control"]
    if repair == "capture_failure":
        assert control_events == []
    else:
        assert [event.effective_verdict for event in control_events] == [
            "revise",
            "revise" if repair == "unchanged" else "accept",
        ]
        for index, (raw, control) in enumerate(zip(raw_events, control_events, strict=True)):
            assert control.attempt == raw.attempt == index
            authority = research and index == 1 and repair == "paraphrase"
            assert control.guard_rule == (RUNTIME_GUARD_RULE if authority else GUARD_RULE)
            assert control.guard_version == (RUNTIME_GUARD_VERSION if authority else GUARD_VERSION)
            expected_status = (
                "no_current_runtime_claim_observed"
                if authority
                else ("unchanged_requested_transformation" if index == 0 or repair == "unchanged" else "clear")
            )
            assert control.guard_status == expected_status
            assert control.runtime_claim_count == raw.runtime_claim_count
            assert control.runtime_claim_digest == raw.runtime_claim_digest
            assert control.request_digest == raw.request_digest
            assert control.evidence_digest == raw.evidence_digest
            assert control.candidate_digest == raw.candidate_digest
            assert control.verdict is None
            assert control.issue_codes is None


SIMPLIFICATION_SOURCE_TITLE = "Fictional reference for the second idea"


def simplification_research_profile() -> OperatorConversationProfile:
    binding: OperatorConversationProfile = research_profile(checkback=True, max_input_chars=24_000)
    source = binding.research.sources[0].model_copy(update={"title": SIMPLIFICATION_SOURCE_TITLE})
    return binding.model_copy(
        update={"research": binding.research.model_copy(update={"sources": (source, *binding.research.sources[1:])})}
    )


@pytest.mark.parametrize("research", [False, True])
@pytest.mark.parametrize("repair", ["paraphrase", "unchanged", "capture_failure"])
@pytest.mark.asyncio
async def test_native_guard_keeps_raw_acceptance_and_uses_only_existing_correction(
    *, research: bool, repair: str
) -> None:
    binding = (
        simplification_research_profile()
        if research
        else profile().model_copy(update={"adaptive_context": True, "checkback": True, "max_input_chars": 24_000})
    )
    request = anchored_request().model_copy(update={"request_id": str(uuid4())})
    prompts: list[dict[str, Any]] = []
    events: list[ReachTraceEvent] = []
    acquisitions = 0

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        prompts.append(prompt)
        if prompt.get("research_phase") == "planning":
            assert "web:official" in {item["id"] for item in prompt["available_research_sources"]}
            return completion(plan_json(("web:official",)))
        if prompt.get("phase") == "checkback":
            assert prompt["task"] == SIMPLIFY_REQUEST
            return completion(verdict("accept", claims=() if research else None))
        text = SECOND_IDEA
        if prompt.get("phase") == "correction":
            assert prompt["correction_control"]["model_verdict"] == "accept"
            assert prompt["correction_control"]["effective_verdict"] == "revise"
            text = SECOND_IDEA if repair == "unchanged" else PLAINER_IDEA
        value: dict[str, Any] = {"kind": "answer", "text": text}
        if research:
            value["citations"] = ["web:official"]
        return completion(canonical_json(value))

    async def acquire(acquisition: Any) -> Any:
        nonlocal acquisitions
        acquisitions += 1
        return relay_response(acquisition, sources=(admitted_source(title=SIMPLIFICATION_SOURCE_TITLE),))

    def capture(event: ReachTraceEvent) -> None:
        if repair == "capture_failure" and event.name == "checkback_control":
            raise asyncio.CancelledError
        events.append(event)

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        research_relay=acquire if research else None,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=capture,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            result = await runtime.process(request)
        assert result.status == ("clarify" if repair == "unchanged" else "conversation")
        assert (CHECKBACK_CLARIFICATION if repair == "unchanged" else PLAINER_IDEA) in result.text
        assert len(prompts) == (5 if research else 4)
        assert acquisitions == int(research)
        assert_guard_receipts(events, repair, research=research)
        context = (
            next(prompt for prompt in prompts if prompt.get("research_phase") == "synthesis")
            if research
            else prompts[0]
        )
        assert all(
            prompt["context"] == context for prompt in prompts if prompt.get("phase") in {"checkback", "correction"}
        )
        assert runtime.substrate.leases.active() == []
        assert SECOND_IDEA not in b"".join(trace_bytes(event) for event in events).decode()
    finally:
        await runtime.aclose()


def test_reference_hints_occur_once_in_frozen_context_without_a_second_reservation() -> None:
    hints: list[dict[str, object]] = [{"origin": "reply_anchor", "label": "Week 01", "position": 2}]
    request = make_request(action="converse")
    candidate = canonical_json({"kind": "answer", "text": "Draft"})
    empty = canonical_json({"reference_hints": []})
    context = canonical_json({"reference_hints": hints})
    empty_prompt = CheckbackEnvelope.prepare(request, empty).prompt(candidate)
    prompt = CheckbackEnvelope.prepare(request, context).prompt(candidate)
    assert len(prompt) - len(empty_prompt) == len(context) - len(empty)
    assert json.loads(prompt)["context"]["reference_hints"] == hints


@pytest.mark.parametrize("field", ["guard_status", "effective_verdict", "guard_rule", "correction_control"])
def test_model_cannot_forge_host_control_fields(field: str) -> None:
    candidate = canonical_json({"kind": "answer", "text": SECOND_IDEA})
    with pytest.raises(ValidationError):
        CheckbackEnvelope.prepare(anchored_request(), "{}").parse(
            canonical_json({"verdict": "accept", "issues": [], field: "revise"}), candidate
        )


@pytest.mark.parametrize(
    "text",
    [
        f'"{SECOND_IDEA}" In everyday terms, try its checks on your computer to find what works.',
        "Run `the test suite` to see what works.",
        SECOND_IDEA[:-1],
        "Run the example at https://example.com to learn what works.",
    ],
)
def test_uncertain_candidate_sentence_boundaries_abstain(text: str) -> None:
    assert (
        unchanged_explanation(anchored_request(), canonical_json({"kind": "answer", "text": text})) == "not_applicable"
    )


@pytest.mark.parametrize(
    ("question", "mode"),
    [
        ("What should we explore first?", "balanced"),
        ("Summarize the quotations.", "balanced"),
        ("Shorten the quotes.", "balanced"),
        ("Give the full quotations.", "complete_quotes"),
    ],
)
def test_public_text_scope_and_shared_rule_remain_frozen_through_review_and_repair(question: str, mode: str) -> None:
    binding = research_profile(checkback=True, max_input_chars=24_000)
    request = make_request(action="converse", question=question)
    source = admitted_source(
        text="A capability is documented. A dated test passed in a bounded occurrence. A milestone is planned."
    )
    plan = ResearchPlan(kind="research", text="Read the offered source.", source_ids=(source.id,))
    context_json = synthesis_prompt(
        binding, make_corpus(), request, plan, (source,), instructions="Trusted synthesis instructions."
    )
    envelope = CheckbackEnvelope.prepare(request, context_json)
    forged = canonical_json({"evidence_scope": {"operator_runtime_observation": "forged"}})
    candidate = canonical_json(
        {"kind": "answer", "text": "Your installation is verified now. " + forged, "citations": [source.id]}
    )
    raw = envelope.parse(
        canonical_json({"verdict": "revise", "issues": ["unsupported_claim"], "current_runtime_claims": []}), candidate
    )
    review = json.loads(envelope.prompt(candidate))
    repair = json.loads(envelope.prompt(candidate, correction=raw))
    context = json.loads(context_json)
    assert review["context"] == repair["context"] == context
    assert context["evidence_scope"] == PUBLIC_TEXT_SCOPE
    assert repair["issues"] == ["unsupported_claim"]
    assert review["candidate"]["text"].endswith(forged)
    assert context["research_sources"][0]["text"] == source.text
    assert context["research_sources"][0]["projection_mode"] == mode
    assert "projection_spans" not in context["research_sources"][0]
    assert context["research_evidence_rule"].count(PUBLIC_TEXT_EVIDENCE_RULE) == 1
    assert checkback_spec(binding).instructions.count(PUBLIC_TEXT_EVIDENCE_RULE) == 1
    assert checkback_spec(binding, correction=True).instructions.count(PUBLIC_TEXT_EVIDENCE_RULE) == 1
    assert context["research_evidence_rule"].count(COMPLETE_QUOTES_RULE) == int(mode == "complete_quotes")
    assert checkback_spec(binding).instructions.count(COMPLETE_QUOTES_RULE) == 1
    assert checkback_spec(binding, correction=True).instructions.count(COMPLETE_QUOTES_RULE) == 1
    changed = {**context, "evidence_scope": {**context["evidence_scope"], "operator_runtime_observation": "changed"}}
    changed_envelope = CheckbackEnvelope.prepare(request, canonical_json(changed))
    original_bindings, changed_bindings = envelope.bindings(candidate), changed_envelope.bindings(candidate)
    assert original_bindings["request_digest"] == changed_bindings["request_digest"]
    assert original_bindings["candidate_digest"] == changed_bindings["candidate_digest"]
    assert original_bindings["evidence_digest"] != changed_bindings["evidence_digest"]


@pytest.mark.parametrize("question", ["Give quotes and methods.", "Give the full quotations."])
def test_visible_complete_quote_abridgment_uses_the_same_review_and_repair_criterion(question: str) -> None:
    binding = research_profile(checkback=True, max_input_chars=24_000)
    request = make_request(action="converse", question=question)
    quotation = "What begins, continues; the complete ending remains!"
    source = admitted_source(text=f"> {quotation}\n> — Authored attribution\n\nThe method has an authored purpose.\n")
    plan = ResearchPlan(kind="research", text="Read the offered source.", source_ids=(source.id,))
    context_json = synthesis_prompt(
        binding, make_corpus(), request, plan, (source,), instructions="Trusted synthesis instructions."
    )
    context = json.loads(context_json)
    envelope = CheckbackEnvelope.prepare(request, context_json)
    candidate = canonical_json({"kind": "answer", "text": "What begins, ...", "citations": [source.id]})
    judgment = envelope.parse(
        canonical_json({"verdict": "revise", "issues": ["quotation_mismatch"], "current_runtime_claims": []}),
        candidate,
    )
    assert quotation not in json.loads(candidate)["text"]
    assert context["research_evidence_rule"].count(COMPLETE_QUOTES_RULE) == 1
    for correction in (False, True):
        prompt = envelope.prompt(candidate, correction=judgment if correction else None)
        value = json.loads(prompt)
        spec = checkback_spec(binding, correction=correction)
        assert value["context"] == context
        assert value["context"]["research_sources"][0]["projection_mode"] == "complete_quotes"
        assert quotation in value["context"]["research_sources"][0]["text"]
        assert "quotation_mismatch" in value["allowed_issues"]
        assert spec.instructions.count(COMPLETE_QUOTES_RULE) == 1
        assert value["issues"] == (["quotation_mismatch"] if correction else [])
        validate_checkback_budget(binding, spec, prompt, phase="synthesis" if correction else "checkback")


RUNTIME_CLAIM = "táto časť je v súčasnosti overená a funguje"
NEGATIVE_RUNTIME_CLAIM = "takže ich ešte nemôžeme bežne skúšať"


def scoped_checkback(
    request: ReachWorkerRequest | None = None, *, source_text: str = "Visible source text."
) -> CheckbackEnvelope:
    return CheckbackEnvelope.prepare(
        request or make_request(action="converse"),
        canonical_json(
            {
                "research_phase": "synthesis",
                "evidence_scope": PUBLIC_TEXT_SCOPE,
                "research_sources": [{"id": "web:official", "status": "ok", "text": source_text}],
            }
        ),
    )


@pytest.mark.parametrize(
    "claims",
    [
        None,
        ("invented clause",),
        ("source only",),
        ("works  now",),
        ("works now", "works now"),
        (" ",),
        ("x" * 241,),
        tuple(str(i) for i in range(5)),
    ],
)
def test_scoped_review_requires_exact_bounded_candidate_claim_observations(claims: tuple[str, ...] | None) -> None:
    envelope = scoped_checkback(source_text="source only")
    candidate = canonical_json({"kind": "answer", "text": "It works now. " + "x" * 241 + " 0 1 2 3 4"})
    with pytest.raises(ValueError, match=r"conversation_checkback_runtime_claims|validation error"):
        envelope.parse(verdict("accept", claims=claims), candidate)


def test_claim_array_has_a_utf8_serialization_cap_and_never_truncates() -> None:
    claims = ("漢" * 100, "界" * 100)
    assert len(canonical_json(claims).encode()) > MAX_RUNTIME_CLAIMS_BYTES
    candidate = canonical_json({"kind": "answer", "text": " ".join(claims)})
    with pytest.raises(ValueError, match="conversation_checkback_runtime_claims"):
        scoped_checkback().parse(verdict("accept", claims=claims), candidate)


@pytest.mark.parametrize("raw_verdict", ["accept", "revise", "needs_evidence"])
def test_authority_veto_preserves_raw_judgment_and_exact_positive_and_negative_claims(raw_verdict: str) -> None:
    candidate = canonical_json({"kind": "answer", "text": RUNTIME_CLAIM + "; " + NEGATIVE_RUNTIME_CLAIM})
    envelope = scoped_checkback()
    raw = envelope.parse(verdict(raw_verdict, claims=(RUNTIME_CLAIM, NEGATIVE_RUNTIME_CLAIM)), candidate)
    control = effective_checkback(make_request(action="converse"), candidate, raw, context_json=envelope.context_json)
    assert raw.verdict == raw_verdict
    assert raw.current_runtime_claims == (RUNTIME_CLAIM, NEGATIVE_RUNTIME_CLAIM)
    assert control.decision is raw
    assert control.guard_rule == RUNTIME_GUARD_RULE
    assert control.guard_status == "current_runtime_claim_without_observation"
    assert control.effective_verdict == "revise"
    assert control.issues == ("unsupported_claim",)
    assert raw.issues == (() if raw_verdict == "accept" else ("missing_component",))
    repair = json.loads(envelope.prompt(candidate, correction=raw, control=control))
    assert repair["current_runtime_claims"] == [RUNTIME_CLAIM, NEGATIVE_RUNTIME_CLAIM]
    assert repair["context"] == json.loads(envelope.context_json)
    metadata = runtime_claim_metadata(raw)
    assert metadata["runtime_claim_count"] == 2
    assert RUNTIME_CLAIM not in canonical_json(control.observation())
    changed = envelope.parse(verdict("accept", claims=(RUNTIME_CLAIM,)), candidate)
    assert runtime_claim_metadata(changed)["runtime_claim_digest"] != metadata["runtime_claim_digest"]


@pytest.mark.parametrize(
    "text",
    [
        "The documented profile supports this capability.",
        "On 21 October the recorded test passed; its mismatch does not qualify this installation.",
        "Voice is planned for December.",
        "If your environment supports it, optionally run the documented check.",
        "I cannot establish the installed state from these documents.",
        "The selected web source was unavailable.",
        "The rejected claim says it works now; the supplied text does not establish that.",
        RUNTIME_CLAIM,
    ],
)
def test_empty_observations_are_not_invented_host_detection_or_proof_of_grounding(text: str) -> None:
    candidate = canonical_json({"kind": "answer", "text": text})
    envelope = scoped_checkback()
    raw = envelope.parse(verdict("accept", claims=()), candidate)
    control = effective_checkback(make_request(action="converse"), candidate, raw, context_json=envelope.context_json)
    assert control.effective_verdict == "accept"
    assert control.guard_status == "no_current_runtime_claim_observed"
    assert runtime_claim_metadata(raw)["runtime_claim_count"] == 0


@pytest.mark.parametrize("raw_verdict", ["accept", "revise", "needs_evidence"])
def test_old_unscoped_observation_is_unrecorded_and_copy_guard_keeps_priority(raw_verdict: str) -> None:
    candidate = canonical_json({"kind": "answer", "text": SECOND_IDEA})
    old = CheckbackEnvelope.prepare(anchored_request(), "{}").parse(verdict("accept"), candidate)
    assert old.current_runtime_claims is None
    assert runtime_claim_metadata(old) == {}
    envelope = scoped_checkback(anchored_request())
    raw = envelope.parse(verdict(raw_verdict, claims=(SECOND_IDEA,)), candidate)
    control = effective_checkback(anchored_request(), candidate, raw, context_json=envelope.context_json)
    assert control.guard_rule == GUARD_RULE
    assert control.effective_verdict == ("revise" if raw_verdict == "accept" else raw_verdict)
    assert control.issues == ("missing_component",)


def test_claim_reservation_covers_accepted_unicode_and_nested_json_escaping() -> None:
    binding = research_profile(checkback=True)
    with_claims = checkback_reserve(
        binding, "", runtime_claims=True, phase="conversation", correction_phase="terminal_correction"
    )
    ordinary = checkback_reserve(binding, "", phase="conversation", correction_phase="terminal_correction")
    extra = InputBudget(
        with_claims.input_chars - ordinary.input_chars,
        with_claims.payload_bytes - ordinary.payload_bytes,
        with_claims.frame_bytes - ordinary.frame_bytes,
    )
    for claims in [
        ("x" * 240, "y" * 240, "z" * 22),
        ("漢" * 100,),
        ("\\" * 240, "\\" * 12),
        ('"' * 240,),
        ("x" + "\n" * 239,),
        (RUNTIME_CLAIM, NEGATIVE_RUNTIME_CLAIM),
    ]:
        assert len(canonical_json(claims).encode()) <= MAX_RUNTIME_CLAIMS_BYTES
        candidate = canonical_json({"kind": "answer", "text": " ".join(claims)})
        envelope = scoped_checkback(make_request(action="converse"))
        assert envelope.parse(verdict("revise", claims=claims), candidate).current_runtime_claims == claims
        repair = canonical_json(
            {
                "current_runtime_claims": claims,
                "correction_control": {
                    "runtime_claim_count": len(claims),
                    "runtime_claim_digest": "f" * 64,
                },
            }
        )
        payload_content = canonical_json(repair)[1:-1]
        frame_content = canonical_json(payload_content)[1:-1]
        assert extra.input_chars >= len(repair)
        assert extra.payload_bytes >= len(payload_content.encode())
        assert extra.frame_bytes >= len(frame_content.encode())
    assert extra.input_chars <= MAX_RUNTIME_CLAIMS_BYTES + 200
    oversized = ("x" * 240, "y" * 240, "z" * 23)
    with pytest.raises(ValueError, match="conversation_checkback_runtime_claims"):
        envelope.parse(
            verdict("revise", claims=oversized), canonical_json({"kind": "answer", "text": " ".join(oversized)})
        )


@pytest.mark.parametrize(
    ("text", "payload_limited", "frame_limited"), [("漢" * 16_384, True, False), ("\\" * 17_000, False, True)]
)
def test_encoded_payload_and_frame_pressure_remain_distinct_from_character_allocation(
    text: str, *, payload_limited: bool, frame_limited: bool
) -> None:
    binding = research_profile(checkback=True, max_input_chars=24_000)
    cost = model_input_cost(binding, "", text, phase="checkback")
    assert cost.input_chars < binding.max_input_chars
    assert (cost.payload_bytes > MAX_MODEL_PAYLOAD_BYTES) is payload_limited
    assert (cost.frame_bytes > MAX_WIRE_BYTES) is frame_limited
    with pytest.raises(DocumentsRefused, match="conversation_budget"):
        validate_checkback_budget(binding, checkback_spec(binding), text, phase="checkback")


@pytest.mark.parametrize(("unit", "payload_axis"), [("漢", True), ("\\", False)])
def test_json_format_overhead_is_admitted_against_exact_byte_and_frame_caps(unit: str, *, payload_axis: bool) -> None:
    legacy = research_profile(checkback=True, max_input_chars=24_000)
    constrained = legacy.model_copy(update={"json_object_output": True})
    spec = checkback_spec(legacy)
    first = model_input_cost(legacy, spec.instructions, unit, phase="checkback")
    second = model_input_cost(legacy, spec.instructions, unit * 2, phase="checkback")
    limit = MAX_MODEL_PAYLOAD_BYTES if payload_axis else MAX_WIRE_BYTES
    first_bytes = first.payload_bytes if payload_axis else first.frame_bytes
    second_bytes = second.payload_bytes if payload_axis else second.frame_bytes
    prompt = unit * (1 + (limit - first_bytes) // (second_bytes - first_bytes))
    old_cost = model_input_cost(legacy, spec.instructions, prompt, phase="checkback")
    new_cost = model_input_cost(constrained, spec.instructions, prompt, phase="checkback")
    assert old_cost.input_chars == new_cost.input_chars
    assert max(old_cost.excess(legacy, InputBudget())) <= 0
    assert (new_cost.payload_bytes if payload_axis else new_cost.frame_bytes) > limit
    validate_checkback_budget(legacy, spec, prompt, phase="checkback")
    with pytest.raises(DocumentsRefused, match="conversation_budget"):
        validate_checkback_budget(constrained, spec, prompt, phase="checkback")


@pytest.mark.parametrize("phase", ["conversation", "planning", "planning_documents", "planning_web", "synthesis"])
def test_frozen_context_reserve_covers_actual_phase_recipe_deltas(phase: DecisionVariant) -> None:
    binding = research_profile(
        checkback=True, max_input_chars=24_000, json_object_output=True, thinking_phases=("checkback",)
    )
    instructions = 'Explain "漢" with a \\ path.'
    correction_phase: Literal["synthesis", "terminal_correction"] = (
        "synthesis" if phase == "synthesis" else "terminal_correction"
    )
    original = model_input_cost(binding, instructions, "", phase=phase)
    review = model_input_cost(binding, checkback_spec(binding).instructions, "", phase="checkback")
    repair = model_input_cost(
        binding, checkback_spec(binding, correction=True).instructions, "", phase=correction_phase
    )
    reserve = checkback_reserve(binding, instructions, phase=phase, correction_phase=correction_phase)
    assert reserve.payload_bytes >= max(
        0, review.payload_bytes - original.payload_bytes, repair.payload_bytes - original.payload_bytes
    )
    assert reserve.frame_bytes >= max(
        0, review.frame_bytes - original.frame_bytes, repair.frame_bytes - original.frame_bytes
    )


MISBOUND_CANDIDATE = "The visible roadmap only covers Stage 00 and Stage 01. Please provide Stage 02 so I can tell you what comes after the first week."
MISBOUND_REVIEW = "The provided excerpt from doc:docs/roadmap.md ends after Stage 01. Please provide the text for Stage 02 or confirm if the document contains further stages."


@pytest.mark.parametrize("source_text", ["The literal target is Stage 01.", "The observed method is __enter__."])
@pytest.mark.parametrize("raw_verdict", ["accept", "revise", "needs_evidence"])
def test_only_visible_exact_successor_can_repair_a_misbound_clarification(source_text: str, raw_verdict: str) -> None:
    request = anchored_request(SUCCESSOR_QUESTION, text=SUCCESSOR_ANCHOR)
    envelope = scoped_checkback(request, source_text=source_text)
    candidate = canonical_json({"kind": "clarify", "text": MISBOUND_CANDIDATE})
    output = json.loads(verdict(raw_verdict, claims=()))
    if raw_verdict == "needs_evidence":
        output["clarification"] = MISBOUND_REVIEW
    raw = envelope.parse(canonical_json(output), candidate)
    control = effective_checkback(request, candidate, raw, context_json=envelope.context_json)
    assert raw.verdict == raw_verdict
    assert control.guard_rule == REFERENCE_GUARD_RULE
    assert control.effective_verdict == "revise"
    assert control.issues == ("wrong_target",)


@pytest.mark.parametrize(
    "text",
    [
        "Please provide Stage 01.",
        "Please provide Stage 02 and Stage 03.",
        "Please provide Week 02.",
        "Please provide Stage 02 and explain the build failure.",
        "Please provide Stage 2.",
        'The user said "Please provide Stage 02."',
        "Please provide Stage 02 if that is the requested target.",
    ],
)
def test_clarification_for_actual_target_or_multiple_ambiguous_targets_keeps_refusal(text: str) -> None:
    request = anchored_request(SUCCESSOR_QUESTION, text=SUCCESSOR_ANCHOR)
    envelope = scoped_checkback(request, source_text="Stage 01 uses __enter__.")
    candidate = canonical_json({"kind": "clarify", "text": text})
    output = json.loads(verdict("needs_evidence", claims=())) | {"clarification": text}
    raw = envelope.parse(canonical_json(output), candidate)
    control = effective_checkback(request, candidate, raw, context_json=envelope.context_json)
    assert control.effective_verdict == "needs_evidence"


@pytest.mark.parametrize(
    "source_text", ["Stage 010 uses __enter__extra.", "Stage 02 is visible.", "The target is omitted."]
)
def test_successor_repair_requires_exact_visible_target_or_observed_alias(source_text: str) -> None:
    request = anchored_request(SUCCESSOR_QUESTION, text=SUCCESSOR_ANCHOR)
    envelope = scoped_checkback(request, source_text=source_text)
    candidate = canonical_json({"kind": "clarify", "text": "Please provide Stage 02."})
    output = json.loads(verdict("needs_evidence", claims=())) | {"clarification": "Please provide Stage 02."}
    raw = envelope.parse(canonical_json(output), candidate)
    assert (
        effective_checkback(request, candidate, raw, context_json=envelope.context_json).effective_verdict
        == "needs_evidence"
    )


def assert_authority_control_receipts(events: list[ReachTraceEvent], *, mode: str, unresolved: bool) -> None:
    raw = [event for event in events if event.name == "checkback" and event.status == "ok"]
    controls = [event for event in events if event.name == "checkback_control"]
    assert len(raw) == len(controls) == 2
    assert raw[0].verdict == ("accept" if mode == "runtime" else "needs_evidence")
    assert controls[0].guard_rule == (RUNTIME_GUARD_RULE if mode == "runtime" else REFERENCE_GUARD_RULE)
    assert [event.effective_verdict for event in controls] == ["revise", "revise" if unresolved else "accept"]
    assert raw[-1].verdict == (raw[0].verdict if unresolved else "accept")
    for before, control in zip(raw, controls, strict=True):
        assert before.candidate_digest == control.candidate_digest
        assert before.evidence_digest == control.evidence_digest
        assert before.runtime_claim_count == control.runtime_claim_count
        assert before.runtime_claim_digest == control.runtime_claim_digest
        assert before.runtime_claim_digest is not None
    assert raw[0].evidence_digest == raw[1].evidence_digest
    if not unresolved:
        assert raw[0].candidate_digest != raw[1].candidate_digest
        assert raw[0].runtime_claim_digest != raw[1].runtime_claim_digest


@pytest.mark.parametrize("mode", ["runtime", "misbound"])
@pytest.mark.parametrize("unresolved", [False, True])
@pytest.mark.asyncio
async def test_claim_veto_and_misbound_refusal_share_existing_single_repair(*, mode: str, unresolved: bool) -> None:
    binding = research_profile(checkback=True, max_input_chars=24_000)
    request = (
        anchored_request(SUCCESSOR_QUESTION + " Use web:official.", text=SUCCESSOR_ANCHOR)
        if mode == "misbound"
        else make_request(action="converse")
    )
    request = request.model_copy(update={"request_id": str(uuid4())})
    bad_text = MISBOUND_CANDIDATE if mode == "misbound" else RUNTIME_CLAIM + "; " + NEGATIVE_RUNTIME_CLAIM
    good_text = (
        "Stage 01 uses __enter__." if mode == "misbound" else "Inspect the documented tests as an optional first step."
    )
    prompts: list[dict[str, Any]] = []
    events: list[ReachTraceEvent] = []
    acquisitions = 0

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        prompts.append(prompt)
        if prompt.get("research_phase") == "planning":
            assert "web:official" in {source["id"] for source in prompt["available_research_sources"]}
            return completion(plan_json(("web:official",)))
        if prompt.get("phase") == "checkback":
            bad = prompt["candidate"]["text"] == bad_text
            output = json.loads(
                verdict(
                    "needs_evidence" if bad and mode == "misbound" else "accept",
                    claims=(RUNTIME_CLAIM, NEGATIVE_RUNTIME_CLAIM) if bad and mode == "runtime" else (),
                )
            )
            if bad and mode == "misbound":
                output["clarification"] = MISBOUND_REVIEW
            return completion(canonical_json(output))
        correcting = prompt.get("phase") == "correction"
        text = bad_text if not correcting or unresolved else good_text
        return completion(
            canonical_json(
                {
                    "kind": "clarify" if text == bad_text and mode == "misbound" else "answer",
                    "text": text,
                    "citations": ["web:official"],
                }
            )
        )

    async def acquire(acquisition: Any) -> Any:
        nonlocal acquisitions
        acquisitions += 1
        return relay_response(acquisition, sources=(admitted_source(text="Stage 01 is documented with __enter__."),))

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        research_relay=acquire,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=events.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            result = await runtime.process(request)
        assert result.status == ("clarify" if unresolved else "conversation")
        assert (CHECKBACK_CLARIFICATION if unresolved else good_text) in result.text
        assert len(prompts) == 5
        assert acquisitions == 1
        assert_authority_control_receipts(events, mode=mode, unresolved=unresolved)
        synthesis = next(prompt for prompt in prompts if prompt.get("research_phase") == "synthesis")
        assert all(
            prompt["context"] == synthesis for prompt in prompts if prompt.get("phase") in {"checkback", "correction"}
        )
        repair = next(prompt for prompt in prompts if prompt.get("phase") == "correction")
        assert repair["current_runtime_claims"] == (
            [RUNTIME_CLAIM, NEGATIVE_RUNTIME_CLAIM] if mode == "runtime" else []
        )
        assert runtime.substrate.leases.active() == []
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("question", ["Please quote the missing source passage.", "Is my installation working now?"])
def test_empty_runtime_claims_preserve_genuine_missing_evidence_clarification(question: str) -> None:
    request = make_request(action="converse", question=question)
    envelope = scoped_checkback(request)
    candidate = canonical_json({"kind": "clarify", "text": MISSING_EVIDENCE_QUESTION})
    raw = envelope.parse(verdict("needs_evidence", claims=()), candidate)
    control = effective_checkback(request, candidate, raw, context_json=envelope.context_json)
    assert control.effective_verdict == "needs_evidence"
    assert control.issues == raw.issues
    assert control.decision.clarification == MISSING_EVIDENCE_QUESTION
    assert control.guard_status == "no_current_runtime_claim_observed"


def authority_refusal_output(prompt: dict[str, Any], bad_text: str) -> str:
    if prompt["candidate"]["text"] != bad_text:
        return verdict("accept", claims=())
    output = json.loads(verdict("needs_evidence", claims=(RUNTIME_CLAIM,)))
    output["issues"] = ["missing_evidence"]
    output["clarification"] = "Please provide proof that the 6,447-test result establishes the current installation."
    return canonical_json(output)


def assert_runtime_refusal_repair_receipts(events: list[ReachTraceEvent], *, unresolved: bool) -> None:
    raw = [event for event in events if event.name == "checkback" and event.status == "ok"]
    controls = [event for event in events if event.name == "checkback_control"]
    assert [event.verdict for event in raw] == ["needs_evidence", "needs_evidence" if unresolved else "accept"]
    assert [event.effective_verdict for event in controls] == ["revise", "revise" if unresolved else "accept"]
    assert raw[0].issue_codes == ("missing_evidence",)
    assert raw[0].runtime_claim_count == 1
    assert raw[1].runtime_claim_count == (1 if unresolved else 0)
    assert all(event.guard_rule == RUNTIME_GUARD_RULE for event in controls)
    assert controls[0].guard_status == "current_runtime_claim_without_observation"
    for review, control in zip(raw, controls, strict=True):
        assert review.runtime_claim_digest == control.runtime_claim_digest
        assert review.candidate_digest == control.candidate_digest
        assert review.evidence_digest == raw[0].evidence_digest == control.evidence_digest


@pytest.mark.parametrize("outcome", ["qualified", "clarify", "unresolved"])
@pytest.mark.asyncio
async def test_extracted_runtime_claim_with_raw_needs_evidence_uses_only_one_same_evidence_repair(outcome: str) -> None:
    binding = research_profile(checkback=True, max_input_chars=24_000)
    question = "Is my installation working now?" if outcome == "clarify" else "Čo máme preskúmať ako prvé?"
    request = make_request(action="converse", question=question + " Use web:official.").model_copy(
        update={"request_id": str(uuid4())}
    )
    bad_text = "Navrhujem začať testami, pretože " + RUNTIME_CLAIM + "."
    final_text = (
        "Please provide a current diagnostic result from your installation so I can assess its state."
        if outcome == "clarify"
        else "Ako voliteľný prvý krok si prečítajme testy a zistime, čo kontrolujú."
    )
    prompts: list[dict[str, Any]] = []
    events: list[ReachTraceEvent] = []
    acquisitions = 0

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        prompts.append(prompt)
        if prompt.get("research_phase") == "planning":
            assert "web:official" in {source["id"] for source in prompt["available_research_sources"]}
            return completion(plan_json(("web:official",)))
        if prompt.get("phase") == "checkback":
            return completion(authority_refusal_output(prompt, bad_text))
        if prompt.get("phase") == "correction":
            assert prompt["issues"] == ["unsupported_claim"]
            assert prompt["correction_control"]["model_verdict"] == "needs_evidence"
            assert prompt["correction_control"]["model_issues"] == ["missing_evidence"]
            assert prompt["current_runtime_claims"] == [RUNTIME_CLAIM]
            return completion(
                canonical_json(
                    {
                        "kind": "clarify" if outcome == "clarify" else "answer",
                        "text": bad_text if outcome == "unresolved" else final_text,
                        "citations": [] if outcome == "clarify" else ["web:official"],
                    }
                )
            )
        return completion(canonical_json({"kind": "answer", "text": bad_text, "citations": ["web:official"]}))

    async def acquire(acquisition: Any) -> Any:
        nonlocal acquisitions
        acquisitions += 1
        return relay_response(
            acquisition,
            sources=(
                admitted_source(
                    text="A dated test occurrence passed with bounded inputs; current installed state was not observed."
                ),
            ),
        )

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        research_relay=acquire,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=events.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            result = await runtime.process(request)
        assert result.status == ("conversation" if outcome == "qualified" else "clarify")
        assert (CHECKBACK_CLARIFICATION if outcome == "unresolved" else final_text) in result.text
        assert bad_text not in result.text
        assert len(prompts) == 5
        assert acquisitions == 1
        assert_runtime_refusal_repair_receipts(events, unresolved=outcome == "unresolved")
        synthesis = next(prompt for prompt in prompts if prompt.get("research_phase") == "synthesis")
        assert all(
            prompt["context"] == synthesis for prompt in prompts if prompt.get("phase") in {"checkback", "correction"}
        )
        assert runtime.substrate.leases.active() == []
    finally:
        await runtime.aclose()


def retry_profile(**changes: Any) -> OperatorConversationProfile:
    return OperatorConversationProfile.model_validate_json(
        canonical_json(
            {
                **profile().model_dump(mode="json"),
                "adaptive_context": True,
                "checkback": True,
                "checkback_invalid_retry": True,
                **changes,
            }
        )
    )


def test_invalid_review_retry_is_explicit_digest_bound_and_strict() -> None:
    original = profile()
    omitted = OperatorConversationProfile.model_validate_json(
        canonical_json(original.model_dump(mode="json", exclude={"checkback_invalid_retry"}))
    )
    explicit = OperatorConversationProfile.model_validate_json(canonical_json(original.model_dump(mode="json")))
    assert omitted.digest == explicit.digest == original.digest
    assert retry_profile().digest != retry_profile(checkback_invalid_retry=False).digest
    with pytest.raises(ValidationError, match="checkback_invalid_retry_requires_checkback"):
        retry_profile(checkback=False)
    for value in (0, 1, "true", None):
        with pytest.raises(ValidationError):
            retry_profile(checkback_invalid_retry=value)
    assert (
        checkback_spec(retry_profile()).instructions
        == checkback_spec(retry_profile(checkback_invalid_retry=False)).instructions
    )


@pytest.mark.parametrize("failure", ["json", "schema", "coverage"])
def test_only_model_review_shape_and_exact_coverage_binding_are_typed_failures(failure: str) -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"), canonical_json({"request_goals": ["Name the method"]})
    )
    candidate = canonical_json(
        {"kind": "answer", "text": "The author\N{RIGHT SINGLE QUOTATION MARK}s method is exact."}
    )
    review: dict[str, Any] = {
        "verdict": "accept",
        "issues": [],
        "coverage": [
            {"goal": 0, "status": "complete", "answer_quote": "The author\N{RIGHT SINGLE QUOTATION MARK}s method"}
        ],
    }
    if failure == "coverage":
        review["coverage"][0]["answer_quote"] = "The author's method"
    output = "{" if failure == "json" else canonical_json(review | ({"foreign": True} if failure == "schema" else {}))
    with pytest.raises(InvalidCheckbackOutputError) as caught:
        envelope.parse(output, candidate, classify_invalid=True)
    assert caught.value.reason == ("coverage_binding" if failure == "coverage" else "review_shape")
    correct = envelope.parse(
        canonical_json(
            {
                "verdict": "accept",
                "issues": [],
                "coverage": [
                    {
                        "goal": 0,
                        "status": "complete",
                        "answer_quote": "The author\N{RIGHT SINGLE QUOTATION MARK}s method",
                    }
                ],
            }
        ),
        candidate,
    )
    assert correct.verdict == "accept"


@pytest.mark.parametrize("claims", ["invalid array", [1], ["Foreign assertion."], None])
def test_runtime_claim_schema_and_excerpt_failures_never_authorize_retry(claims: object) -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"),
        canonical_json({"evidence_scope": PUBLIC_TEXT_SCOPE, "research_phase": "synthesis"}),
    )
    candidate = canonical_json({"kind": "answer", "text": "The documentation describes a method."})
    with pytest.raises(ValueError, match="runtime_claims") as caught:
        envelope.parse(
            canonical_json({"verdict": "accept", "issues": [], "current_runtime_claims": claims}),
            candidate,
            classify_invalid=True,
        )
    assert not isinstance(caught.value, InvalidCheckbackOutputError)


@pytest.mark.parametrize("corruption", ["context", "candidate", "goals", "digest"])
def test_host_envelope_failures_remain_outside_output_retry_classification(corruption: str) -> None:
    context = (
        "{" if corruption == "context" else canonical_json({"request_goals": [None] if corruption == "goals" else []})
    )
    envelope = CheckbackEnvelope.prepare(make_request(action="converse"), context)
    if corruption == "digest":
        envelope = CheckbackEnvelope(context, "bad-host-binding")
    candidate = "{" if corruption == "candidate" else canonical_json({"kind": "answer", "text": "Bound candidate."})
    with pytest.raises(ValueError, match=r"Expecting|conversation_") as caught:
        envelope.parse("{", candidate, classify_invalid=True)
    assert not isinstance(caught.value, InvalidCheckbackOutputError)


@pytest.mark.parametrize("reason", ["review_shape", "coverage_binding"])
def test_retry_control_changes_only_closed_control_with_exact_small_envelope(
    reason: Literal["review_shape", "coverage_binding"],
) -> None:
    from hashlib import sha256

    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"),
        canonical_json({"request_goals": ["Explain the method"]}),
        persona_name="Example",
    )
    candidate = canonical_json({"kind": "answer", "text": "The method\N{RIGHT SINGLE QUOTATION MARK}s exact purpose."})
    normal = json.loads(envelope.prompt(candidate))
    retried = json.loads(envelope.prompt(candidate, retry_reason=reason))
    assert retried.pop("review_retry") == checkback_retry_control(reason)
    assert retried == normal
    serialized = canonical_json({"review_retry": checkback_retry_control(reason)})
    assert len(serialized) <= 160
    assert (
        checkback_retry_digest(reason) == sha256(canonical_json(checkback_retry_control(reason)).encode()).hexdigest()
    )
    decision = envelope.parse(
        canonical_json(
            {"verdict": "revise", "issues": ["missing_component"], "coverage": [{"goal": 0, "status": "missing"}]}
        ),
        candidate,
    )
    with pytest.raises(ValueError, match="conversation_checkback_retry"):
        envelope.prompt(candidate, correction=decision, retry_reason=reason)


@pytest.mark.parametrize("axis", ["input_chars", "payload_bytes", "frame_bytes"])
def test_retry_reserve_accounts_exact_added_control_on_all_axes(axis: str) -> None:
    binding = retry_profile(max_input_chars=24_000)
    disabled = retry_profile(checkback_invalid_retry=False, max_input_chars=24_000)
    envelope = CheckbackEnvelope.prepare(make_request(action="converse"), "{}")
    candidate = canonical_json(
        {"kind": "answer", "text": 'An author\N{RIGHT SINGLE QUOTATION MARK}s "漢" method \\ stays exact.'}
    )
    spec = checkback_spec(binding)
    normal = model_input_cost(binding, spec.instructions, envelope.prompt(candidate), phase="checkback")
    retry = model_input_cost(
        binding, spec.instructions, envelope.prompt(candidate, retry_reason="coverage_binding"), phase="checkback"
    )
    component = canonical_json({"review_retry": checkback_retry_control("coverage_binding")})[1:-1] + ","
    once = canonical_json(component)[1:-1]
    twice = canonical_json(once)[1:-1]
    expected = {"input_chars": len(component), "payload_bytes": len(once.encode()), "frame_bytes": len(twice.encode())}
    assert getattr(retry, axis) - getattr(normal, axis) == expected[axis]
    instructions = "Fixed formation recipe"
    reserved = checkback_reserve(binding, instructions, phase="conversation", correction_phase="terminal_correction")
    legacy = checkback_reserve(disabled, instructions, phase="conversation", correction_phase="terminal_correction")
    review_recipe = model_input_cost(binding, spec.instructions, "", phase="checkback")
    repair_recipe = model_input_cost(
        binding, checkback_spec(binding, correction=True).instructions, "", phase="terminal_correction"
    )
    increase = max(getattr(review_recipe, axis) + expected[axis], getattr(repair_recipe, axis)) - max(
        getattr(review_recipe, axis), getattr(repair_recipe, axis)
    )
    assert getattr(reserved, axis) - getattr(legacy, axis) == increase


def test_actual_retry_budget_rechecked_without_trimming_frozen_context() -> None:
    binding = retry_profile()
    envelope = CheckbackEnvelope.prepare(make_request(action="converse"), "{}")
    candidate = canonical_json({"kind": "answer", "text": "A short exact answer."})
    spec = checkback_spec(binding)
    normal = envelope.prompt(candidate)
    cap = model_input_cost(binding, spec.instructions, normal, phase="checkback").input_chars
    binding = retry_profile(max_input_chars=cap)
    validate_checkback_budget(binding, spec, normal, phase="checkback")
    with pytest.raises(DocumentsRefused, match="conversation_budget"):
        validate_checkback_budget(
            binding, spec, envelope.prompt(candidate, retry_reason="coverage_binding"), phase="checkback"
        )
    assert envelope.context_json == "{}"


@pytest.mark.parametrize(
    ("reviews", "expected", "candidate_attempts", "retry_ordinals"),
    [
        (("malformed", "accept"), "Original answer.", (0, 0), (0, 1)),
        (("revise", "malformed", "accept"), "Corrected answer.", (0, 1, 1), (0, 0, 1)),
        (("malformed", "revise", "accept"), "Corrected answer.", (0, 0, 1), (0, 1, 0)),
        (("malformed", "revise", "malformed"), "", (0, 0, 1), (0, 1, 0)),
        (("malformed", "malformed"), "", (0, 0), (0, 1)),
        (("accept",), "Original answer.", (0,), (0,)),
        (("needs_evidence",), MISSING_EVIDENCE_QUESTION, (0,), (0,)),
        (("revise", "needs_evidence"), MISSING_EVIDENCE_QUESTION, (0, 1), (0, 0)),
        (("revise", "revise"), CHECKBACK_CLARIFICATION, (0, 1), (0, 0)),
    ],
)
@pytest.mark.asyncio
async def test_native_one_malformed_retry_is_shared_across_both_candidate_versions(
    reviews: tuple[str, ...], expected: str, candidate_attempts: tuple[int, ...], retry_ordinals: tuple[int, ...]
) -> None:
    binding = retry_profile()
    pending = iter(reviews)
    prompts: list[dict[str, Any]] = []
    events: list[ReachTraceEvent] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        body = validate_generation_payload(binding, payload)
        prompt = json.loads(body["messages"][-1]["content"])
        prompts.append(prompt)
        if prompt.get("phase") == "checkback":
            selected = next(pending)
            return completion("{" if selected == "malformed" else verdict(selected))
        text = "Corrected answer." if prompt.get("phase") == "correction" else "Original answer."
        return completion(canonical_json({"kind": "answer", "text": text}))

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=events.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted relay
            result = await runtime.process(
                make_request(action="converse").model_copy(update={"request_id": str(uuid4())})
            )
        assert result.text == expected
        assert result.status == (
            "error"
            if not expected
            else "clarify"
            if expected in {CHECKBACK_CLARIFICATION, MISSING_EVIDENCE_QUESTION}
            else "conversation"
        )
        started = [event for event in events if event.name == "checkback" and event.status == "started"]
        assert tuple(event.attempt for event in started) == candidate_attempts
        assert tuple(event.review_attempt for event in started) == tuple(range(len(reviews)))
        assert tuple(event.retry_ordinal for event in started) == retry_ordinals
        assert len({event.evidence_digest for event in started}) == 1
        assert len({event.request_digest for event in started}) == 1
        review_prompts = [prompt for prompt in prompts if prompt.get("phase") == "checkback"]
        assert len(review_prompts) == len(reviews)
        assert sum("review_retry" in prompt for prompt in review_prompts) <= 1
        assert all(prompt["context"] == prompts[0] for prompt in review_prompts)
        for index, ordinal in enumerate(retry_ordinals):
            if ordinal:
                assert review_prompts[index]["candidate"] == review_prompts[index - 1]["candidate"]
                assert started[index].candidate_digest == started[index - 1].candidate_digest
                assert started[index].review_retry_digest == checkback_retry_digest("review_shape")
                assert review_prompts[index]["review_retry"] == checkback_retry_control("review_shape")
        failed = [event for event in events if event.name == "checkback" and event.status == "failed"]
        assert len(failed) == reviews.count("malformed")
        assert all(event.verdict is None for event in failed)
        assert all(event.invalid_review_reason == "review_shape" for event in failed)
        assert runtime.substrate.leases.active() == []
        assert "Original answer." not in b"".join(trace_bytes(event) for event in events).decode()
        assert all(len(trace_bytes(event)) <= 2048 for event in events)
    finally:
        await runtime.aclose()


@pytest.mark.parametrize(
    "failure",
    ["timeout", "cancelled", "transport", "host_typed", "length", "runtime_type", "runtime_excerpt", "runtime_mixed"],
)
@pytest.mark.asyncio
async def test_enabled_retry_does_not_retry_ineligible_failures(failure: str) -> None:
    binding = retry_profile()
    calls = 0

    async def relay(operation: str, payload: str) -> str:
        nonlocal calls
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        calls += 1
        if calls == 1:
            return completion(canonical_json({"kind": "answer", "text": "Unadopted answer."}))
        if failure == "timeout":
            raise TimeoutError
        if failure == "cancelled":
            raise asyncio.CancelledError
        if failure == "transport":
            raise OSError
        if failure == "host_typed":
            reason: Literal["review_shape"] = "review_shape"
            raise InvalidCheckbackOutputError(reason)
        if failure == "length":
            value = json.loads(completion(verdict("accept")))
            value["choices"][0]["finish_reason"] = "length"
            return canonical_json(value)
        return completion(
            canonical_json(
                {
                    "verdict": "accept",
                    "issues": [],
                    "current_runtime_claims": "bad" if failure == "runtime_type" else ["Foreign assertion."],
                    **({"foreign": True} if failure == "runtime_mixed" else {}),
                }
            )
        )

    runtime = build_runtime(
        policy(), make_corpus(), profile=binding, model_relay=relay, started_at=STARTED, clock=lambda: NOW
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted relay
            if failure == "cancelled":
                with pytest.raises(asyncio.CancelledError):
                    await runtime.process(
                        make_request(action="converse").model_copy(update={"request_id": str(uuid4())})
                    )
            else:
                result = await runtime.process(
                    make_request(action="converse").model_copy(update={"request_id": str(uuid4())})
                )
                assert result.status == "error"
                assert result.text == ""
        assert calls == 2
        assert runtime.substrate.leases.active() == []
    finally:
        await runtime.aclose()


@pytest.mark.parametrize(
    ("unit", "axis", "limit"), [("漢", "payload_bytes", MAX_MODEL_PAYLOAD_BYTES), ("\\", "frame_bytes", MAX_WIRE_BYTES)]
)
def test_retry_actual_encoded_boundary_refuses_without_larger_payload_or_frame_cap(
    unit: str, axis: str, limit: int
) -> None:
    binding = retry_profile(max_input_chars=24_000)
    spec = checkback_spec(binding)
    request = make_request(action="converse")
    candidate = canonical_json({"kind": "answer", "text": "Exact answer."})

    def envelope(count: int) -> CheckbackEnvelope:
        return CheckbackEnvelope.prepare(request, canonical_json({"visible_text": unit * count}))

    first = model_input_cost(binding, spec.instructions, envelope(1).prompt(candidate), phase="checkback")
    second = model_input_cost(binding, spec.instructions, envelope(2).prompt(candidate), phase="checkback")
    count = 1 + (limit - getattr(first, axis)) // (getattr(second, axis) - getattr(first, axis))
    frozen = envelope(count)
    original = model_input_cost(binding, spec.instructions, frozen.prompt(candidate), phase="checkback")
    retried = frozen.prompt(candidate, retry_reason="coverage_binding")
    assert max(original.excess(binding, InputBudget())) <= 0
    assert getattr(model_input_cost(binding, spec.instructions, retried, phase="checkback"), axis) > limit
    validate_checkback_budget(binding, spec, frozen.prompt(candidate), phase="checkback")
    with pytest.raises(DocumentsRefused, match="conversation_budget"):
        validate_checkback_budget(binding, spec, retried, phase="checkback")


@pytest.mark.asyncio
async def test_native_retry_preserves_exact_apostrophes_and_frozen_goal_bindings() -> None:
    binding = retry_profile(request_goals=True, decision_schema_version=4)
    prompts: list[dict[str, Any]] = []
    events: list[ReachTraceEvent] = []
    candidate = "The author\N{RIGHT SINGLE QUOTATION MARK}s method has a defined purpose."

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        prompts.append(prompt)
        if prompt.get("phase") == "interpretation":
            return completion(
                canonical_json(
                    {
                        "version": 1,
                        "goals": ["Name the method"],
                        "constraints": [],
                        "quotation_presentation": "none",
                        "required_context": [],
                    }
                )
            )
        if prompt.get("phase") == "checkback":
            return completion(
                canonical_json(
                    {
                        "verdict": "accept",
                        "issues": [],
                        "coverage": [
                            {
                                "goal": 0,
                                "status": "complete",
                                "answer_quote": "The author\N{RIGHT SINGLE QUOTATION MARK}s method"
                                if "review_retry" in prompt
                                else "The author's method",
                            }
                        ],
                    }
                )
            )
        return completion(canonical_json({"kind": "answer", "text": candidate}))

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=events.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted relay
            result = await runtime.process(
                make_request(action="converse").model_copy(update={"request_id": str(uuid4())})
            )
        assert result.status == "conversation"
        assert result.text == candidate
        reviews = [prompt for prompt in prompts if prompt.get("phase") == "checkback"]
        assert len(reviews) == 2
        retried = dict(reviews[1])
        assert retried.pop("review_retry") == checkback_retry_control("coverage_binding")
        assert retried == reviews[0]
        settled = [event for event in events if event.name == "checkback" and event.status in {"ok", "failed"}]
        assert tuple(event.status for event in settled) == ("failed", "ok")
        assert tuple(event.review_attempt for event in settled) == (0, 1)
        assert len({event.candidate_digest for event in settled}) == 1
        assert settled[0].verdict is None
        assert settled[0].invalid_review_reason == "coverage_binding"
        assert settled[1].review_retry_digest == checkback_retry_digest("coverage_binding")
    finally:
        await runtime.aclose()


def test_opted_in_review_observation_has_bounded_metadata_without_hidden_capture_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from contextlib import nullcontext
    from types import SimpleNamespace

    from lychd.compositions.reach import conversation_workflow as workflow

    request = make_request(action="converse").model_copy(update={"request_id": str(uuid4())})
    events: list[ReachTraceEvent] = []
    context = SimpleNamespace(
        deps=SimpleNamespace(profile=retry_profile(), trace=events.append),
        state=SimpleNamespace(envelope=SimpleNamespace(request=request), run_id=str(uuid4())),
    )

    # Expose a malformed observation at its construction boundary, before best-effort suppression.
    def expose_capture(*_errors: type[BaseException]) -> nullcontext[None]:
        return nullcontext()

    monkeypatch.setattr(workflow, "suppress", expose_capture)
    observe = workflow._checkback_trace  # pyright: ignore[reportPrivateUsage] - focused trace construction boundary
    observe(
        cast("Any", context),
        CheckbackEnvelope.prepare(request, "{}"),
        canonical_json({"kind": "answer", "text": "Exact candidate."}),
        name="checkback",
        status="started",
        attempt=0,
        review_attempt=0,
    )
    assert len(events) == 1
    assert events[0].review_attempt == 0
    assert events[0].retry_ordinal == 0


@pytest.mark.parametrize(
    "general_failure",
    ["foreign_field", "invalid_coverage", "wrong_goal", "foreign_quote", "invalid_verdict", "inconsistent_verdict"],
)
@pytest.mark.parametrize(
    "runtime_failure", ["foreign", "duplicate", "missing", "null", "array_type", "item_type", "count", "chars", "utf8"]
)
def test_runtime_field_failures_precede_other_review_shape_failures(general_failure: str, runtime_failure: str) -> None:
    context = canonical_json(
        {"research_phase": "synthesis", "evidence_scope": PUBLIC_TEXT_SCOPE, "request_goals": ["Explain the method"]}
    )
    envelope = CheckbackEnvelope.prepare(make_request(action="converse"), context)
    clauses = ["Documented method.", "One.", "Two.", "Three.", "Four.", "x" * 241, "漢" * 180]
    candidate = canonical_json({"kind": "answer", "text": " ".join(clauses)})
    raw: dict[str, Any] = {
        "verdict": "accept",
        "issues": [],
        "coverage": [{"goal": 0, "status": "complete", "answer_quote": "Documented method."}],
        "current_runtime_claims": [],
    }
    if general_failure == "foreign_field":
        raw["foreign"] = True
    elif general_failure == "invalid_coverage":
        raw["coverage"] = "not an array"
    elif general_failure == "wrong_goal":
        raw["coverage"][0]["goal"] = 1
    elif general_failure == "foreign_quote":
        raw["coverage"][0]["answer_quote"] = "Foreign coverage excerpt."
    elif general_failure == "invalid_verdict":
        raw["verdict"] = "unlisted"
    else:
        raw["issues"] = ["unsupported_claim"]
    if runtime_failure == "missing":
        raw.pop("current_runtime_claims")
    else:
        raw["current_runtime_claims"] = {
            "foreign": ["Foreign assertion."],
            "duplicate": [clauses[0], clauses[0]],
            "null": None,
            "array_type": clauses[0],
            "item_type": [1],
            "count": clauses[:5],
            "chars": [clauses[5]],
            "utf8": [clauses[6]],
        }[runtime_failure]
    with pytest.raises(ValueError, match="conversation_checkback_runtime_claims") as caught:
        envelope.parse(canonical_json(raw), candidate, classify_invalid=True)
    assert not isinstance(caught.value, InvalidCheckbackOutputError)


@pytest.mark.parametrize("output", ["{", "not JSON"])
def test_malformed_json_still_has_only_the_closed_shape_recovery(output: str) -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"),
        canonical_json({"research_phase": "synthesis", "evidence_scope": PUBLIC_TEXT_SCOPE}),
    )
    with pytest.raises(InvalidCheckbackOutputError) as caught:
        envelope.parse(output, canonical_json({"kind": "answer", "text": "Documented method."}), classify_invalid=True)
    assert caught.value.reason == "review_shape"


def test_direct_parser_preserves_general_schema_failure_order_without_opt_in() -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"),
        canonical_json({"research_phase": "synthesis", "evidence_scope": PUBLIC_TEXT_SCOPE}),
    )
    output = canonical_json(
        {"verdict": "accept", "issues": [], "current_runtime_claims": ["Foreign assertion."], "foreign": True}
    )
    candidate = canonical_json({"kind": "answer", "text": "Documented method."})
    with pytest.raises(ValidationError, match="foreign"):
        envelope.parse(output, candidate)
    with pytest.raises(ValueError, match="conversation_checkback_runtime_claims") as caught:
        envelope.parse(output, candidate, classify_invalid=True)
    assert not isinstance(caught.value, InvalidCheckbackOutputError)


@pytest.mark.parametrize("output", ["[]", "null", '"review"', "12", "true"])
@pytest.mark.parametrize("public", [False, True])
def test_nonobject_json_roots_remain_review_shape_failures_in_each_scope(output: str, *, public: bool) -> None:
    context = {"research_phase": "synthesis", "evidence_scope": PUBLIC_TEXT_SCOPE} if public else {}
    envelope = CheckbackEnvelope.prepare(make_request(action="converse"), canonical_json(context))
    candidate = canonical_json({"kind": "answer", "text": "Documented method."})
    with pytest.raises(InvalidCheckbackOutputError) as caught:
        envelope.parse(output, candidate, classify_invalid=True)
    assert caught.value.reason == "review_shape"
    with pytest.raises(ValidationError):
        envelope.parse(output, candidate)


@pytest.mark.parametrize("output", ["{}", '{"current_runtime_claims":null}'])
def test_public_object_missing_or_null_runtime_observation_remains_terminal(output: str) -> None:
    envelope = CheckbackEnvelope.prepare(
        make_request(action="converse"),
        canonical_json({"research_phase": "synthesis", "evidence_scope": PUBLIC_TEXT_SCOPE}),
    )
    candidate = canonical_json({"kind": "answer", "text": "Documented method."})
    with pytest.raises(ValueError, match="conversation_checkback_runtime_claims") as caught:
        envelope.parse(output, candidate, classify_invalid=True)
    assert not isinstance(caught.value, InvalidCheckbackOutputError)
