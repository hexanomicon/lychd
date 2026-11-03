"""Headless transcript continuity and acceptance negative controls, without Core or inference."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts import reach_dialogue_probe as dialogue
from scripts import reach_probe as probe

from lychd.compositions.reach.operator_wire import ReachWorkerResult
from lychd.interface.discord.messages import split_message


def result(text: str) -> ReachWorkerResult:
    return ReachWorkerResult(
        request_id="r", status="conversation", text=text, policy_digest="a" * 64, corpus_digest="b" * 64
    )


def test_actual_multipart_output_and_exact_older_anchor_survive_distractors() -> None:
    first = dialogue.DialogueTurn(id="first", question="Explain all points")
    second = dialogue.DialogueTurn(
        id="second", question="Explain this one", reply_to=dialogue.ReplyTarget(turn="first", part=1)
    )
    session = dialogue.Dialogue(turns=(first, second))
    history: list[probe.HistoryItem] = []
    outputs: dict[str, tuple[probe.HistoryItem, ...]] = {}
    text = "Actual answer. " * 190
    dialogue.append_result(history, outputs, first, 0, result(text))
    expected = split_message(text)
    assert tuple(item.text for item in outputs["first"]) == expected
    history.extend(probe.HistoryItem(text=f"Unrelated distractor {index}") for index in range(25))
    scenario = dialogue.make_scenario(session, second, 1, history, outputs)
    assert len(scenario.history) == 20
    assert scenario.reply_to_history_index is not None
    anchor = scenario.history[scenario.reply_to_history_index]
    assert anchor.text == expected[1]
    assert anchor.event_id == outputs["first"][1].event_id
    assert anchor.speaker == "agent"


def test_followup_uses_actual_final_part_without_explicit_reply() -> None:
    first = dialogue.DialogueTurn(id="first", question="A question")
    second = dialogue.DialogueTurn(id="second", question="And why?", followup_to=dialogue.ReplyTarget(turn="first"))
    session = dialogue.Dialogue(turns=(first, second))
    history: list[probe.HistoryItem] = []
    outputs: dict[str, tuple[probe.HistoryItem, ...]] = {}
    dialogue.append_result(history, outputs, first, 0, result("Actual final answer"))
    scenario = dialogue.make_scenario(session, second, 1, history, outputs)
    assert scenario.trigger == "followup"
    assert scenario.reply_to_history_index is None
    assert scenario.continuation_to_history_index == 1
    assert scenario.history[1].text == "Actual final answer"


@pytest.mark.parametrize("status", ["ignore", "error", "refused", "need_context"])
def test_nonanswers_never_become_dialogue_reply_targets(status: str) -> None:
    first = dialogue.DialogueTurn(id="first", question="A question")
    history: list[probe.HistoryItem] = []
    outputs: dict[str, tuple[probe.HistoryItem, ...]] = {}
    observed = result("Private diagnostic or intermediate text").model_copy(update={"status": status})
    dialogue.append_result(history, outputs, first, 0, observed)
    assert outputs["first"] == ()
    assert len(history) == 1


@pytest.mark.parametrize("target", ["missing", "second"])
def test_unknown_and_future_reply_targets_are_rejected(target: str) -> None:
    first = dialogue.DialogueTurn(id="first", question="First", reply_to=dialogue.ReplyTarget(turn=target))
    second = dialogue.DialogueTurn(id="second", question="Second")
    with pytest.raises(ValidationError, match="future_target"):
        dialogue.Dialogue(turns=(first, second))


def test_nonexistent_part_cannot_be_replaced_by_authored_history() -> None:
    first = dialogue.DialogueTurn(id="first", question="First")
    second = dialogue.DialogueTurn(id="second", question="Second", reply_to=dialogue.ReplyTarget(turn="first", part=1))
    session = dialogue.Dialogue(turns=(first, second))
    history = [probe.HistoryItem(text="Authored substitute", speaker="agent")]
    with pytest.raises(probe.ProbeError, match="missing_target"):
        dialogue.make_scenario(session, second, 1, history, {"first": (history[0],)})


def test_session_and_literal_term_budgets_are_closed() -> None:
    with pytest.raises(ValidationError):
        dialogue.Dialogue(turns=tuple(dialogue.DialogueTurn(id=f"turn{i}", question="x") for i in range(7)))
    with pytest.raises(ValidationError):
        dialogue.DialogueTurn(id="first", question="Quote", required_text=("",))


def test_literal_negative_control_rejects_source_only_success() -> None:
    first = dialogue.DialogueTurn(id="first", question="Give exact quote", required_text=("Exact authored quotation",))
    session = dialogue.Dialogue(turns=(first,))
    scenario = dialogue.make_scenario(session, first, 0, [], {})
    failures = probe.content_assertions(scenario, "A paraphrase. Sources: [Author](https://example.com)")
    assert failures == ["required_text_0"]


def test_child_imports_selected_source_without_inheriting_host_paths_or_provider_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/unselected/source")
    monkeypatch.setenv("OPENAI_API_KEY", "private canary")
    environment = dialogue.child_environment("docker")
    assert environment["PYTHONPATH"].endswith("/src")
    assert environment["PYTHONPATH"] != "/unselected/source"
    assert "OPENAI_API_KEY" not in environment


def test_child_artifacts_can_include_large_corpus_metadata_but_reject_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    padding = "x" * probe.MAX_WIRE_BYTES
    path.write_text(json.dumps({"padding": padding, "outcome": "passed"}))
    assert dialogue.read_child_artifact(path)["outcome"] == "passed"
    path.write_text('{"padding":' + json.dumps(padding) + ',"outcome":"passed","outcome":"failed"}')
    with pytest.raises(ValueError, match="duplicate_key"):
        dialogue.read_child_artifact(path)
