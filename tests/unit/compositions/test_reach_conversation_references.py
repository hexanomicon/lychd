"""Expected observations come from literal spans, never chronology or label arithmetic."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import timedelta
from hashlib import sha256

import pytest

from lychd.compositions.reach.conversation_references import (
    REFERENCE_PARSER_VERSION,
    anchor_references,
    opening_successor,
    reference_digest,
    reference_payload,
    reference_selectors,
)
from lychd.compositions.reach.operator_model_wire import canonical_json
from lychd.compositions.reach.operator_wire import ReachHistoryEntry, ReachWorkerRequest
from tests.unit.compositions.test_reach_documents import NOW, make_request

ANCHOR = "1. **Week 00**: opening.\n2. **Week 01**: middle.\n3. **Week 02**: closing.\n"
QUESTION = "Compare the second and third weeks from your answer."
SUCCESSOR_QUESTION = "Use doc:docs/roadmap.md: what comes after that first week?"
SUCCESSOR_ANCHOR = (
    "Today is our opening project week, Stage 00 (__new__), 2\N{EN DASH}8 November. "
    "We meet, talk and explore without delivery assignments. "
    "Looking ahead, the next week is Stage 01 (__enter__), 9\N{EN DASH}15 November: "
    "curiosity becomes active participation and we choose a shared agent task."
)


def anchored_request(text: str = ANCHOR, question: str = QUESTION) -> ReachWorkerRequest:
    anchor = ReachHistoryEntry(
        subject_id="bot:one",
        event_id="anchor:one",
        conversation_id="channel:one",
        occurred_at=NOW - timedelta(seconds=2),
        text=text,
    )
    return make_request(action="converse", question=question).model_copy(
        update={"reply_to_event_id": anchor.event_id, "reply_anchor": anchor}
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (ANCHOR, ("Week 01", "Week 02")),
        (ANCHOR.replace("2.", "1.").replace("3.", "1."), ("Week 01", "Week 02")),
        ("### Week 04\nOpening.\n### Week 09\nMiddle.\n### Week 12\nClosing.\n", ("Week 09", "Week 12")),
        ("**Week04**\nOpening.\n**Week09**\nMiddle.\n**Week12**\nClosing.\n", ("Week09", "Week12")),
        ("1) Week-04\n2) Week-09\n3) Week-12\n", ("Week-09", "Week-12")),
    ],
)
def test_physical_anchor_order_binds_exact_literal_spans(text: str, expected: tuple[str, str]) -> None:
    request = anchored_request(text)
    hints = anchor_references(request)
    assert tuple(hint.label for hint in hints) == expected
    assert tuple(hint.position for hint in hints) == (2, 3)
    assert tuple(request.event.question[hint.question_start : hint.question_end] for hint in hints) == (
        "second",
        "third",
    )
    for hint in hints:
        assert text[hint.anchor_start : hint.anchor_end] == hint.label
        assert hint.scope_start <= hint.anchor_start < hint.anchor_end <= hint.scope_end <= len(text)
        assert hint.anchor_digest == sha256(text.encode()).hexdigest()
        assert hint.anchor_event_id == "anchor:one"
        assert hint.origin == "reply_anchor"
        assert hint.unit == "week"
        assert hint.label_unit == "week"
        assert hint.relation == "position"
        assert hint.parser_version == REFERENCE_PARSER_VERSION
    assert reference_selectors(request) == expected


def test_observed_aliases_are_exact_and_hints_are_immutable_json_values() -> None:
    request = anchored_request("### Week00 `__init__`\n### Week01 `__next__`\n### Week02 {#week-two}\n")
    hints = anchor_references(request)
    assert hints[0].aliases == ("__next__",)
    assert hints[1].aliases == ("week-two",)
    with pytest.raises(FrozenInstanceError):
        hints[0].__setattr__("label", "Week03")
    payload = reference_payload(request)
    assert payload[0]["aliases"] == ["__next__"]
    assert reference_digest(request) == sha256(canonical_json(payload).encode()).hexdigest()
    payload[0]["label"] = "untrusted mutation"
    assert reference_selectors(request) == ("Week01", "Week02")


@pytest.mark.parametrize(
    "question",
    [
        "Compare second or third weeks.",
        "Compare second weeks and third weeks.",
        "Compare second and second weeks.",
        "Compare second and third months.",
        "Compare second and fourth weeks.",
        "What comes after the first week?",
        'Explain the quoted instruction "compare second and third weeks".',
        "Compare `second and third weeks`.",
        "Compare second and third weeks, especially Week03.",
        "Compare second and third weeks, especially Week9999999.",
        "Compare second and third weeks, especially Week01 and 03.",
        "Compare second and third weeks, and Month02.",
        "Compare the second and third.",
        "Compare first, second, third and fourth weeks.",
        "Compare f\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}rst and third weeks from your answer.",
        "Compare f\N{LATIN SMALL LETTER DOTLESS I}rst and third weeks from your answer.",
        "Compare second and third wee\N{KELVIN SIGN}s from your answer.",
    ],
)
def test_ambiguous_relational_conflicting_and_out_of_range_questions_abstain(question: str) -> None:
    request = anchored_request(question=question)
    assert anchor_references(request) == ()
    assert reference_selectors(request) == ()
    assert reference_payload(request) == []


@pytest.mark.parametrize(
    "text",
    [
        "1. Week00\n2. Week01\n3. Week01\n",
        "1. Week00\n  1. Week01\n2. Week02\n",
        "1. Week00\n2. Month01\n3. Week02\n",
        "1. Wee\N{KELVIN SIGN}00\n2. Week01\n3. Week02\n",
        "2. Week00\n3. Week01\n4. Week02\n",
        "1. Week00\n2. Week01\n1. Week02\n",
        "### Week00\n#### Week01\n### Week02\n",
        "## First programme\n### Week00\n## Another programme\n### Week01\n### Week02\n",
        "1. Week00\n2. Week01\n### Week02\n",
        "```md\n1. Week00\n2. Week01\n3. Week02\n```\n",
        "<pre><code>\n1. Week00\n2. Week01\n3. Week02\n</code></pre>\n",
        "> 1. Week00\n> 2. Week01\n> 3. Week02\n",
        "Part 2 of 3\n" + ANCHOR,
        "[2/3]\n" + ANCHOR,
        "1. Week00\nA different sequence follows.\n1. Week01\n1. Week02\n",
        "...\n" + ANCHOR,
        ANCHOR + "[truncated]",
        ANCHOR + "x" * (2000 - len(ANCHOR)),
        "".join(f"{index + 1}. Week{index:02}\n" for index in range(13)),
    ],
)
def test_ambiguous_nested_competing_quoted_or_incomplete_sequences_abstain(text: str) -> None:
    assert anchor_references(anchored_request(text)) == ()


@pytest.mark.parametrize(
    "prefix",
    [
        "```md\n~~~\n~~~\n",
        "~~~md\n```\n```\n",
        "````md\n```\n```\n",
        "```md\n```not-a-closer\n",
        "~~~md\n~~~not-a-closer\n",
        "```md\n> ```\n",
        "```md\n    ```\n",
        "```md\n~~~\n~~~\n    ```\n",
        "```md\n```\N{NO-BREAK SPACE}\n",
    ],
)
def test_fence_markers_disable_observations_despite_mixed_short_or_ambiguous_closers(prefix: str) -> None:
    request = anchored_request(prefix + ANCHOR)
    assert anchor_references(request) == ()
    assert reference_selectors(request) == ()


def test_even_balanced_fences_before_a_visible_list_conservatively_suppress_hints() -> None:
    prefix = "```md\n~~~\n~~~\n```\n"
    request = anchored_request(prefix + ANCHOR)
    assert anchor_references(request) == ()
    assert reference_payload(request) == []


@pytest.mark.parametrize(
    "text",
    [
        "**Programme A**\n**Week00**\nOpening.\n**Programme B**\n**Week01**\nMiddle.\n**Week02**\nClosing.\n",
        "## Programme A\n### Week00\nOpening.\n## Programme B\n### Week01\nMiddle.\n### Week02\nClosing.\n",
        "## Programme A\n**Week00**\nOpening.\n## Programme B\n**Week01**\nMiddle.\n**Week02**\nClosing.\n",
    ],
)
def test_distinct_bold_or_atx_parent_branches_cannot_form_one_anchor_sequence(text: str) -> None:
    request = anchored_request(text)
    assert anchor_references(request) == ()
    assert reference_payload(request) == []
    assert reference_selectors(request) == ()


def test_bounded_coordination_supports_the_twelfth_position_without_label_arithmetic() -> None:
    text = "".join(f"1. Stage {index * 7:02}\n" for index in range(12))
    request = anchored_request(text, "Compare the first, sixth, and twelfth stages.")
    assert reference_selectors(request) == ("Stage 00", "Stage 35", "Stage 77")


def test_only_the_actual_anchor_applies_and_conflicting_anchors_abstain() -> None:
    request = anchored_request()
    assert request.reply_anchor is not None
    later = request.reply_anchor.model_copy(update={"event_id": "later:one", "text": ANCHOR.replace("Week", "Month")})
    assert reference_selectors(request.model_copy(update={"history": (later,)})) == ("Week 01", "Week 02")
    assert anchor_references(request.model_copy(update={"reply_to_event_id": "another:one"})) == ()
    assert anchor_references(request.model_copy(update={"continuation_anchor": later})) == ()
    assert (
        anchor_references(
            request.model_copy(
                update={"reply_to_event_id": None, "reply_anchor": None, "history": (request.reply_anchor,)}
            )
        )
        == ()
    )
    continuation = request.model_copy(
        update={"reply_to_event_id": None, "reply_anchor": None, "continuation_anchor": request.reply_anchor}
    )
    assert tuple(hint.origin for hint in anchor_references(continuation)) == ("continuation_anchor",) * 2
    assert reference_selectors(continuation) == ("Week 01", "Week 02")


@pytest.mark.parametrize(("opening", "target"), [("00", "01"), ("04", "99")])
def test_literal_opening_successor_preserves_target_spans_alias_and_printed_label(opening: str, target: str) -> None:
    text = SUCCESSOR_ANCHOR.replace("Stage 00", f"Stage {opening}").replace("Stage 01", f"Stage {target}")
    request = anchored_request(text, SUCCESSOR_QUESTION)
    hint = opening_successor(request)
    assert hint is not None
    assert hint.relation == "opening_successor"
    assert hint.unit == "week"
    assert hint.label_unit == "stage"
    assert hint.position == 2
    assert hint.label == f"Stage {target}"
    assert hint.aliases == ("__enter__",)
    assert text[hint.anchor_start : hint.anchor_end] == hint.label
    assert "__enter__" in text[hint.scope_start : hint.scope_end]
    assert request.event.question[hint.question_start : hint.question_end] == "what comes after that first week"
    assert hint.anchor_event_id == "anchor:one"
    assert hint.anchor_digest == sha256(text.encode()).hexdigest()
    assert hint.parser_version == "anchor-order-v2"
    assert anchor_references(request) == (hint,)
    assert reference_payload(request)[0]["relation"] == "opening_successor"
    assert reference_selectors(request) == ()


@pytest.mark.parametrize(
    "question",
    [
        "What comes after that first day?",
        "What comes after first week and after opening week?",
        "What comes after first week or second week?",
        "What comes after first week, Stage 02?",
        'Quote "what comes after that first week".',
        "What comes after that first week if the plan changes?",
        "What comes after that f\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}rst week?",
        "What comes after that first wee\N{KELVIN SIGN}?",
        "What happens in the next week?",
        "What comes before that first week?",
    ],
)
def test_opening_successor_abstains_on_conflicting_ambiguous_or_unsupported_questions(question: str) -> None:
    request = anchored_request(SUCCESSOR_ANCHOR, question)
    assert opening_successor(request) is None
    assert anchor_references(request) == ()


@pytest.mark.parametrize(
    "text",
    [
        SUCCESSOR_ANCHOR.replace("opening project week", "opening project day"),
        SUCCESSOR_ANCHOR.replace("next week", "next month"),
        SUCCESSOR_ANCHOR.replace("Stage 01", "Week 01"),
        SUCCESSOR_ANCHOR.replace("Stage 01", "Stage 00"),
        SUCCESSOR_ANCHOR.replace("__enter__", "__new__"),
        SUCCESSOR_ANCHOR.replace("opening project week", "early project week"),
        SUCCESSOR_ANCHOR.replace("the next week is", "a later week is"),
        SUCCESSOR_ANCHOR + " The next week is Stage 02 (__exit__).",
        SUCCESSOR_ANCHOR + " Stage 9999999 is another possibility.",
        SUCCESSOR_ANCHOR + " [truncated]",
        "```text\n" + SUCCESSOR_ANCHOR + "\n```",
        "> " + SUCCESSOR_ANCHOR,
        '"' + SUCCESSOR_ANCHOR + '"',
        "\N{LEFT SINGLE QUOTATION MARK}" + SUCCESSOR_ANCHOR + "\N{RIGHT SINGLE QUOTATION MARK}",
        "Our opening week, Stage00. It is not true that the next week is Stage01.",
        "Our opening week, Stage00. If the next week is Stage01, we will discuss it.",
        "Our opening week, Stage00. Perhaps the next week is Stage01.",
        SUCCESSOR_ANCHOR.replace("Stage 01", "Sta\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}ge 01"),
        "The next week is Stage 01 (__enter__). Our opening project week, Stage 00 (__new__).",
        "Our opening project week is Stage 00. Stage 01 is also visible.",
    ],
)
def test_opening_successor_requires_one_unquoted_complete_explicit_relation(text: str) -> None:
    request = anchored_request(text, SUCCESSOR_QUESTION)
    assert opening_successor(request) is None
    assert reference_payload(request) == []
    assert reference_selectors(request) == ()


def test_opening_successor_uses_only_the_actual_anchor_and_observes_optional_alias_literally() -> None:
    request = anchored_request(SUCCESSOR_ANCHOR.replace(" (__enter__)", ""), SUCCESSOR_QUESTION)
    assert request.reply_anchor is not None
    unrelated = request.reply_anchor.model_copy(update={"event_id": "other:one", "text": SUCCESSOR_ANCHOR})
    request = request.model_copy(update={"history": (unrelated,)})
    hint = opening_successor(request)
    assert hint is not None
    assert hint.label == "Stage 01"
    assert hint.aliases == ()
    assert reference_selectors(request) == ()
    assert opening_successor(request.model_copy(update={"reply_anchor": None})) is None
    assert opening_successor(request.model_copy(update={"continuation_anchor": unrelated})) is None
    continuation = request.model_copy(
        update={"reply_anchor": None, "reply_to_event_id": None, "continuation_anchor": request.reply_anchor}
    )
    continued = opening_successor(continuation)
    assert continued is not None
    assert continued.origin == "continuation_anchor"
    assert continued.label == hint.label
