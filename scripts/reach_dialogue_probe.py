"""Run at most six private headless turns, carrying actual outputs between fresh Core workers.

This tests explicit transcript continuity, not persistent worker state or Discord delivery.
Literal acceptance criteria do not replace independent semantic assessment.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from lychd.compositions.reach.operator_wire import MAX_WIRE_BYTES, ReachWorkerResult, ReachWorkerStatus, strict_json
from lychd.compositions.reach.research_wire import SourceId
from lychd.compositions.reach.schemas import Record
from lychd.interface.discord.messages import split_message

if __package__:
    from scripts import reach_probe as probe
else:
    import reach_probe as probe

MAX_TURNS = 6
MAX_SESSION_SECONDS = MAX_TURNS * probe.MAX_TIMEOUT_SECONDS


class ReplyTarget(Record):
    turn: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    part: int = Field(default=0, ge=0, le=5)


class DialogueTurn(Record):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    question: str = Field(min_length=1, max_length=2000, repr=False)
    reply_to: ReplyTarget | None = None
    followup_to: ReplyTarget | None = None
    expected_status: ReachWorkerStatus | None = None
    required_source_ids: tuple[SourceId, ...] = Field(default=(), max_length=4)
    required_text: tuple[str, ...] = Field(default=(), max_length=32)
    prohibited_text: tuple[str, ...] = Field(default=(), max_length=32)
    text_case: Literal["sensitive", "casefold"] = "sensitive"
    plan_delivery: Literal["succeeded", "rejected", "unknown"] = "succeeded"

    @model_validator(mode="after")
    def one_target(self) -> DialogueTurn:
        if self.reply_to is not None and self.followup_to is not None:
            msg = "dialogue_ambiguous_target"
            raise ValueError(msg)
        # Reuse the exact single-turn literal bounds.
        probe.Scenario(
            question=self.question,
            required_text=self.required_text,
            prohibited_text=self.prohibited_text,
            text_case=self.text_case,
        )
        return self


class Dialogue(Record):
    schema_version: Literal[1] = 1
    direct: bool = False
    history: tuple[probe.HistoryItem, ...] = Field(default=(), max_length=20, repr=False)
    turns: tuple[DialogueTurn, ...] = Field(min_length=1, max_length=MAX_TURNS)

    @model_validator(mode="after")
    def prior_targets(self) -> Dialogue:
        seen: set[str] = set()
        for turn in self.turns:
            if turn.id in seen:
                msg = "dialogue_duplicate_turn"
                raise ValueError(msg)
            for target in (turn.reply_to, turn.followup_to):
                if target is not None and target.turn not in seen:
                    msg = "dialogue_future_target"
                    raise ValueError(msg)
            if self.direct and turn.followup_to is not None:
                msg = "dialogue_direct_followup"
                raise ValueError(msg)
            seen.add(turn.id)
        return self


def make_scenario(
    dialogue: Dialogue,
    turn: DialogueTurn,
    index: int,
    history: list[probe.HistoryItem],
    outputs: dict[str, tuple[probe.HistoryItem, ...]],
) -> probe.Scenario:
    """Select bounded actual history and retain the exact selected bot message part."""
    selected = history[-20:]
    target = turn.reply_to or turn.followup_to
    anchor_index: int | None = None
    if target is not None:
        parts = outputs.get(target.turn, ())
        if target.part >= len(parts):
            probe.refuse("dialogue_missing_target")
        anchor = parts[target.part]
        if anchor not in selected:
            selected = [anchor, *selected[-19:]]
        anchor_index = selected.index(anchor)
    refreshed = tuple(
        item.model_copy(update={"age_seconds": len(selected) - offset}) for offset, item in enumerate(selected)
    )
    return probe.Scenario(
        question=turn.question,
        direct=dialogue.direct,
        history=refreshed,
        trigger=(
            "followup"
            if turn.followup_to is not None
            else "reply"
            if target is not None and not dialogue.direct
            else None
        ),
        reply_to_history_index=anchor_index if turn.reply_to is not None else None,
        continuation_to_history_index=anchor_index if turn.followup_to is not None else None,
        expected_status=turn.expected_status,
        required_source_ids=turn.required_source_ids,
        required_text=turn.required_text,
        prohibited_text=turn.prohibited_text,
        text_case=turn.text_case,
        plan_delivery=turn.plan_delivery,
        event_sequence=index,
    )


def append_result(
    history: list[probe.HistoryItem],
    outputs: dict[str, tuple[probe.HistoryItem, ...]],
    turn: DialogueTurn,
    index: int,
    result: ReachWorkerResult,
) -> None:
    """Carry only observed terminal answer bytes, using production message partitioning."""
    history.append(probe.HistoryItem(text=turn.question, event_id=str(int(probe.SYNTHETIC["event_id"]) + index * 1000)))
    parts = (
        tuple(
            probe.HistoryItem(text=text, speaker="agent", event_id=str(900000000000500000 + index * 10 + part))
            for part, text in enumerate(split_message(result.text))
        )
        if result.text.strip() and result.status in {"conversation", "clarify"}
        else ()
    )
    outputs[turn.id] = parts
    history.extend(parts)


def child_arguments(args: argparse.Namespace, scenario: Path, output: Path, profile: Path, corpus: Path) -> list[str]:
    arguments = [
        sys.executable,
        str(Path(__file__).with_name("reach_probe.py").resolve()),
        "--engine",
        args.engine,
        "--core-image",
        args.core_image,
        "--conversation-profile",
        str(profile),
        "--corpus-dir",
        str(corpus),
        "--scenario",
        str(scenario),
        "--output",
        str(output),
        "--model-transport",
        args.model_transport,
        "--timeout-seconds",
        str(args.timeout_seconds),
    ]
    if args.capture_model_output:
        arguments.append("--capture-model-output")
    return arguments


def child_environment(engine: str) -> dict[str, str]:
    """Pin child imports to this selected helper's source, excluding inherited import paths."""
    environment = probe.operator.safe_environment(engine)
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    return environment


def read_child_artifact(path: Path) -> dict[str, Any]:
    """Read bounded local artifacts, whose corpus metadata can exceed a protocol frame."""
    return probe.operator.strict_object(probe.operator.read_regular(path, probe.MAX_TOTAL_BYTES))


def execute(args: argparse.Namespace) -> int:
    if (
        not 1 <= args.timeout_seconds <= probe.MAX_TIMEOUT_SECONDS
        or probe.operator.IMAGE_ID.fullmatch(args.core_image) is None
    ):
        probe.refuse("dialogue_arguments")
    probe.operator.external_path(args.output)
    if args.output.exists():
        probe.refuse("dialogue_output_exists")
    raw = probe.operator.read_regular(args.scenario, MAX_WIRE_BYTES, private=True)
    strict_json(raw)
    dialogue = Dialogue.model_validate_json(raw)
    profile_raw = probe.operator.read_regular(args.conversation_profile, MAX_WIRE_BYTES, private=True)
    strict_json(profile_raw)
    probe.OperatorConversationProfile.model_validate_json(profile_raw)
    probe.operator.private_directory(args.output)
    profile = args.output / "conversation.json"
    probe.operator.write_private(profile, profile_raw)
    corpus = args.output / "corpus"
    frozen_corpus = probe.freeze_corpus(args.corpus_dir, corpus)
    history = list(dialogue.history)
    outputs: dict[str, tuple[probe.HistoryItem, ...]] = {}
    receipts: list[dict[str, Any]] = []
    failures: list[str] = []
    for index, turn in enumerate(dialogue.turns):
        try:
            scenario = make_scenario(dialogue, turn, index, history, outputs)
            scenario_file = args.output / f"scenario-{turn.id}.json"
            probe.operator.write_private(scenario_file, scenario.model_dump_json().encode())
            output = args.output / f"turn-{turn.id}"
            child = subprocess.run(  # noqa: S603 - fixed executable/argv; no shell or credential discovery
                child_arguments(args, scenario_file, output, profile, corpus),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                # The child's native deadline owns process/container retirement. An outer
                # subprocess timeout would kill that supervisor before cleanup settled.
                env=child_environment(args.engine),
                check=False,
            )
            report = read_child_artifact(output / "report.json")
            value = read_child_artifact(output / "turn.json")
            result = ReachWorkerResult.model_validate_json(probe.canonical_json(value.get("result")))
            turn_failures = list(report["failures"])
            if child.returncode not in {0, 1} or (child.returncode == 0) != (not turn_failures):
                turn_failures.append("dialogue_child_status")
            # Recompute criteria over the actual bytes used for continuation.
            turn_failures.extend(
                code for code in probe.content_assertions(scenario, result.text) if code not in turn_failures
            )
            receipts.append(
                {
                    "id": turn.id,
                    "failures": turn_failures,
                    "structural_outcome": report["structural_outcome"],
                    "checkbacks": report["checkbacks"],
                    "checkback_controls": report.get("checkback_controls", []),
                    "reference_observation": report.get("reference_observation"),
                    "result_digest": probe.sha256(result.text.encode()).hexdigest(),
                }
            )
            failures.extend(f"{turn.id}:{code}" for code in turn_failures)
            append_result(history, outputs, turn, index, result)
        except (OSError, ValueError, KeyError, TypeError):
            failures.append(f"{turn.id}:dialogue_child_failed")
            break
    report = {
        "schema_version": 1,
        "outcome": "failed" if failures else "passed",
        "failures": failures,
        "scenario_file_sha256": probe.sha256(raw).hexdigest(),
        "profile_file_sha256": probe.sha256(profile_raw).hexdigest(),
        "corpus_digest": frozen_corpus.digest,
        "semantic_review": "needs_review",
        "turns": receipts,
        "fresh_core_per_turn": True,
        "claims": {"persistent_worker_state": False, "live_discord": False, "web_acquisition": False},
        "limits": {
            "turns": MAX_TURNS,
            "history_entries": 20,
            "model_calls_per_turn": probe.MAX_MODEL_CALLS,
            "session_execution_seconds_excluding_cleanup": MAX_SESSION_SECONDS,
        },
    }
    probe.operator.write_private(args.output / "report.json", probe.operator.json_bytes(report))
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    args = probe.parser().parse_args(argv)
    try:
        return execute(args)
    except KeyboardInterrupt:
        sys.stderr.write("reach_dialogue_probe_cancelled\n")
        return 130
    except Exception:  # noqa: BLE001 - never render private questions, provider responses or paths
        sys.stderr.write("reach_dialogue_probe_refused\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
