"""Closed recovery wording and literal foreground projection, without effects."""

from typing import Literal

import pytest

from lychd.cli.companion_view import format_companion_event
from lychd.compositions.blockworld.companion_feedback import voice_failure_text


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize(
    "failure",
    [
        "input_unavailable",
        "capture_failed",
        "audio_unsettled",
        "audio_read_failed",
        "source_retention_failed",
        "transcription_failed",
        "transcript_retention_failed",
        "instruction_refused",
        "admission_unknown",
        "stop_unconfirmed",
    ],
)
def test_host_voice_feedback_stays_bounded_and_literal(failure: str, language: str) -> None:
    text = voice_failure_text(failure, language)
    assert 0 < len(text) <= 200
    assert text.isprintable()
    assert "PRIVATE" not in text
    assert "/" not in text
    assert "http" not in text


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_unknown_failure_cannot_inject_diagnostics_or_offer_replay(language: str) -> None:
    assert voice_failure_text("PRIVATE /source.wav applied\nrecord again", language) == voice_failure_text(
        "admission_unknown", language
    )


@pytest.mark.parametrize("kind", ["voice_refused", "voice_unknown", "refused", "unknown"])
def test_voice_feedback_is_rendered_as_audio_and_bounded_literal_text(kind: str) -> None:
    event = {
        "kind": kind,
        "request_id": "original",
        "voice_failure": "transcription_failed",
        "feedback": {"language": "en", "text": "[bold]host[/]\n" + "x" * 1000},
        "detail": "PRIVATE provider diagnostics",
    }
    line = format_companion_event(event, language="en")
    assert line is not None
    assert line.startswith("[original] Audio input")
    assert "[bold]host[/]\\u000a" in line
    assert "[truncated]" in line
    assert "PRIVATE" not in line
    assert "Result (" not in line
    assert len(line) < 340


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_correlated_spoken_stop_keeps_unknown_wording(language: Literal["sk", "cs", "en"]) -> None:
    feedback = voice_failure_text("stop_unconfirmed", language)
    line = format_companion_event(
        {"kind": "voice_stop_result", "request_id": "original", "game_kind": "unknown", "feedback": {"text": feedback}},
        language=language,
    )
    assert line is not None
    assert line.startswith("[original]")
    assert feedback in line


def test_failure_feedback_requires_a_supported_reply_language() -> None:
    with pytest.raises(ValueError, match="sk, cs and en"):
        voice_failure_text("transcription_failed", "xx")
