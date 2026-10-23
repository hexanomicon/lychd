"""Pure human-view oracles; no session, device, process or service is constructed."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, cast

import pytest

from lychd.cli.companion_view import Language, format_companion_event


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("sk", '[r1] Rozpoznané (dodaný WAV): "stav"'),
        ("cs", '[r1] Rozpoznáno (dodaný WAV): "stav"'),
        ("en", '[r1] Recognized (supplied WAV): "stav"'),
    ],
)
def test_recognized_words_have_exact_localized_whole_lines(language: Language, expected: str) -> None:
    event: Mapping[str, Any] = {"kind": "heard", "request_id": "r1", "source": "supplied", "text": "stav"}
    assert format_companion_event(event, language=language) == expected


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("sk", "[r1] Výsledok (odmietnuté): Príkaz sa nevykonal."),
        ("cs", "[r1] Výsledek (odmítnuto): Príkaz sa nevykonal."),
        ("en", "[r1] Result (refused): Príkaz sa nevykonal."),
    ],
)
def test_fixed_host_feedback_is_reused_without_translation(language: Language, expected: str) -> None:
    event: Mapping[str, Any] = {
        "kind": "refused",
        "request_id": "r1",
        "feedback": {"language": "sk", "text": "Príkaz sa nevykonal."},
        "detail": "PRIVATE diagnostic says applied",
        "profile": "PRIVATE profile",
    }
    assert format_companion_event(event, language=language) == expected


def test_feedback_does_not_reclassify_supplied_unknown_kind() -> None:
    event: Mapping[str, Any] = {"kind": "unknown", "request_id": "r", "feedback": {"text": "The command was applied."}}
    assert format_companion_event(event, language="en") == "[r] Result (unknown): The command was applied."


def test_heard_text_quotes_controls_format_controls_and_literal_markup() -> None:
    event: Mapping[str, Any] = {
        "kind": "heard",
        "request_id": "r\x1b",
        "source": "microphone",
        "text": '[bold]hi[/]\n\r\t\x1b[2J\u202e\u2066\u200d"\\',
    }
    assert format_companion_event(event, language="en") == (
        "[r\\u001b] Recognized (requested microphone): "
        '"[bold]hi[/]\\u000a\\u000d\\u0009\\u001b[2J\\u202e\\u2066\\u200d\\"\\\\"'
    )


@pytest.mark.parametrize(("language", "marker"), [("sk", "[skrátené]"), ("cs", "[zkráceno]"), ("en", "[truncated]")])
def test_recognized_text_is_bounded_without_mutating_original(language: Language, marker: str) -> None:
    event: Mapping[str, Any] = {"kind": "heard", "request_id": "r", "source": "supplied", "text": "a" * 10000}
    original = deepcopy(event)
    line = format_companion_event(event, language=language)
    assert line is not None
    assert "a" * 240 + marker in line
    assert "a" * 241 not in line
    assert len(line) < 400
    assert event == original


def test_escaping_budget_never_cuts_a_terminal_control_escape() -> None:
    line = format_companion_event({"kind": "heard", "text": "\x1b" * 1000}, language="en")
    assert line is not None
    assert '"' + "\\u001b" * 40 + '[truncated]"' in line
    assert "\x1b" not in line


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        ({"kind": "stop_requested"}, "Stop requested; acknowledgement pending."),
        ({"control": "stop", "kind": "applied", "request_id": "s"}, "[s] Server acknowledged stop."),
        ({"control": "stop", "kind": "refused", "request_id": "s"}, "[s] Stop refused."),
        ({"control": "stop", "kind": "cancelled", "request_id": "s"}, "[s] Stop cancelled; stop unconfirmed."),
        ({"kind": "stop_unknown"}, "Stop outcome unconfirmed; no automatic replay."),
    ],
)
def test_stop_request_is_distinct_from_server_acknowledgement(event: Mapping[str, Any], expected: str) -> None:
    assert format_companion_event(event, language="en") == expected


def test_stop_result_keeps_passed_host_feedback_without_changing_stop_disposition() -> None:
    event: Mapping[str, Any] = {
        "control": "stop",
        "kind": "unknown",
        "request_id": "s",
        "feedback": {"text": "Host wording."},
    }
    assert (
        format_companion_event(event, language="en")
        == "[s] Stop outcome unconfirmed; no automatic replay. Host wording."
    )


def test_queued_input_counts_local_retention_without_game_execution_claim() -> None:
    assert format_companion_event(
        {"kind": "queued", "request_id": "q", "local_pending": 2, "local_capacity": 4}, language="en"
    ) == ("[q] Queued; Pending inputs=2/4.")
    assert format_companion_event({"kind": "queued", "request_id": "q"}, language="en") == ("[q] Queued.")


@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        ("waiting_audio", "waiting for audio"),
        ("recording_pending", "recording requested"),
        ("reading_audio", "reading supplied audio"),
        ("transcribing", "recognizing"),
    ],
)
def test_voice_stages_describe_operations_without_device_attestation(phase: str, expected: str) -> None:
    assert format_companion_event(
        {"kind": "voice_stage", "request_id": "v", "phase": phase, "source": "microphone"}, language="en"
    ) == (f"[v] Audio input: {expected} (requested microphone).")
    assert format_companion_event({"capture": "active"}, language="en") is None


@pytest.mark.parametrize(
    ("playback", "label"),
    [
        ("not_attempted", "not attempted"),
        ("player_exited", "player finished"),
        ("interrupted", "interrupted"),
        ("failed", "failed"),
        ("settlement_unknown", "settlement unknown"),
    ],
)
def test_reply_generation_player_settlement_and_retention_are_independent(playback: str, label: str) -> None:
    event: Mapping[str, Any] = {
        "kind": "reply_evidence",
        "request_id": "r",
        "reply_status": "generated",
        "playback": playback,
        "evidence_status": "recorded",
        "path": "PRIVATE",
        "body": "PRIVATE",
    }
    assert format_companion_event(event, language="en") == (
        f"[r] Voice reply: voice prepared; playback: {label}; evidence: retained."
    )


def test_failed_speech_evidence_preserves_unknown_server_work_and_no_hearing_claim() -> None:
    event: Mapping[str, Any] = {
        "kind": "reply_evidence_failed",
        "request_id": "r",
        "reply_status": "cancelled_server_work_unknown",
        "playback": "settlement_unknown",
        "evidence_status": "failed",
        "game_kind": "applied",
    }
    assert format_companion_event(event, language="en") == (
        "[r] Voice reply: cancelled; server work unknown; playback: settlement unknown; evidence: failed."
    )


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        ({"capture": "off"}, "Recording finished."),
        ({"capture": "unknown", "detail": "PRIVATE"}, "Recording stop unconfirmed; audio disabled, text available."),
        ({"kind": "voice_refused", "request_id": "v"}, "[v] Audio input refused."),
        ({"kind": "voice_evidence_failed", "request_id": "v"}, "[v] Audio input evidence retention failed."),
    ],
)
def test_audio_closure_and_retention_failures_are_explicit(event: Mapping[str, Any], expected: str) -> None:
    assert format_companion_event(event, language="en") == expected


def test_status_uses_supplied_independent_state_without_expiry_or_retirement_inference() -> None:
    event: Mapping[str, Any] = {
        "kind": "status",
        "session": {
            "observed_at_ms": 1000,
            "opened": True,
            "closed": True,
            "stopping": True,
            "fenced": False,
            "generation": 7,
            "capacity": 4,
            "actor_id": "actor",
            "current": {
                "request_id": "now",
                "run_id": "run-1",
                "phase": "response_pending",
                "remaining_ms": 0,
                "original_deadline_ms": 999,
            },
            "pending": (
                {
                    "request_id": "next",
                    "run_id": None,
                    "phase": "admission_pending",
                    "remaining_ms": 20,
                    "original_deadline_ms": 1020,
                },
            ),
            "pending_evidence": 2,
        },
        "voice": {"request_id": "voice", "phase": "waiting_audio", "source": "supplied"},
        "replies": [{"request_id": "reply", "phase": "player_pending", "source": "reply"}],
        "audio_blocked": True,
        "stopping": True,
        "target_id": "target",
        "presentation_failed": False,
        "detail": "PRIVATE",
        "profile": "PRIVATE",
        "server_mailbox": ["PRIVATE"],
    }
    original = deepcopy(event)
    assert format_companion_event(event, language="en") == (
        "Local status: open=yes; admission closed=yes; stopping=yes; fenced=no.\n"
        "Current input [now]: waiting for result; Run run-1; deadline passed; finish unconfirmed.\n"
        "Pending inputs: 1/4.\n"
        "Pending input [next]: waiting for admission; Run ID not yet known; time left: 20 ms.\n"
        "[voice] Audio input: waiting for audio (supplied WAV).\n"
        "[reply] Voice reply: playback requested.\n"
        "audio blocked.\n"
        "pending evidence: 2.\n"
        "Selected target: target."
    )
    assert event == original
    line = format_companion_event(event, language="en")
    assert line is not None
    assert "generation" not in line
    assert "observed ms" not in line
    assert "999" not in line
    assert "1020" not in line
    assert "expired" not in line


def test_status_bounds_membership_but_keeps_actual_supplied_count() -> None:
    command = {"request_id": "r" * 10000, "phase": "settling", "remaining_ms": 0}
    line = format_companion_event(
        {"kind": "status", "session": {"pending": [command] * 10000}, "replies": []}, language="en"
    )
    assert line is not None
    assert "Pending inputs: 10000/unknown." in line
    assert line.count("Pending input [") == 16
    assert "[truncated]" in line
    assert len(line) < 6000
    assert "expired" not in line


def test_actor_binding_and_ids_are_safe_and_other_private_fields_are_ignored() -> None:
    assert (
        format_companion_event({"server": {"actor_id": "a\n\u202e", "players": ["PRIVATE"]}}, language="en")
        == "Server reports actor: a\\u000a\\u202e."
    )
    assert format_companion_event({"target_id": "t\x1b"}, language="en") == "Selected target: t\\u001b."


@pytest.mark.parametrize(
    "event",
    [
        {"kind": "unrecognized", "detail": "PRIVATE", "token": "PRIVATE"},
        {"evidence": {"transcript": "PRIVATE"}},
        {"capture": "active", "profile": "PRIVATE"},
    ],
)
def test_diagnostic_and_evidence_only_events_never_dump_private_material(event: Mapping[str, Any]) -> None:
    assert format_companion_event(event, language="en") is None


def test_generic_refusal_uses_fixed_words_only() -> None:
    assert (
        format_companion_event({"kind": "refused", "detail": "PRIVATE\x1b", "exception": "PRIVATE"}, language="en")
        == "[none] Input or control refused."
    )


def test_ready_setup_lists_supported_controls_without_claiming_device_or_model_readiness() -> None:
    event: Mapping[str, Any] = {
        "ready": True,
        "language": "sk",
        "reply_language": None,
        "target_id": None,
        "recognizer": "whisper",
        "interpretation_selected": False,
        "profile": "PRIVATE",
    }
    assert format_companion_event(event, language="en") == (
        "Selected setup: input language=sk, speech language=none, recognizer=whisper, interpretation selected=no.\n"
        "Selected target: none.\n"
        "Selected models do not confirm that the microphone or listening works.\n"
        "Commands: state | idle | follow me | goto X Y Z | look X Y Z | inspect X Y Z | say TEXT | stop\n"
        ":record [1-15] | :wav ABS_PATH | :target UUID | :language [INPUT [REPLY]] | :status | :quit"
    )


def test_unsupported_interface_language_is_rejected() -> None:
    with pytest.raises(ValueError, match="support sk, cs and en"):
        format_companion_event({}, language=cast("Language", "de"))


@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        ("waiting_audio", "waiting for audio"),
        ("synthesizing", "preparing voice"),
        ("generated", "voice prepared"),
        ("player_pending", "playback requested"),
    ],
)
def test_reply_stages_describe_preparation_and_playback_request(phase: str, expected: str) -> None:
    event: Mapping[str, Any] = {"kind": "reply_stage", "request_id": "r", "phase": phase}
    assert format_companion_event(event, language="en") == f"[r] Voice reply: {expected}."


def test_stop_feedback_is_safe_literal_text_with_original_unknown_disposition() -> None:
    event: Mapping[str, Any] = {
        "control": "stop",
        "kind": "unknown",
        "request_id": "s",
        "feedback": {"text": "[bold]Host[/]\n\u202e"},
        "detail": "PRIVATE",
    }
    assert format_companion_event(event, language="en") == (
        "[s] Stop outcome unconfirmed; no automatic replay. [bold]Host[/]\\u000a\\u202e"
    )


def test_failed_reply_retention_with_original_feedback_stays_an_audio_failure() -> None:
    event: Mapping[str, Any] = {
        "kind": "reply_evidence_failed",
        "request_id": "r",
        "game_kind": "applied",
        "feedback": {"text": "The controller started."},
        "reply_status": "generated",
        "playback": "player_exited",
        "evidence_status": "failed",
    }
    assert format_companion_event(event, language="en") == (
        "[r] Voice reply: voice prepared; playback: player finished; evidence: failed."
    )
