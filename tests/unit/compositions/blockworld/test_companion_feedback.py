from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import uuid4

import pytest

from lychd.compositions.blockworld.companion import (
    BridgeState,
    CompanionReason,
    CompanionRequest,
    CompanionResult,
    parse_text,
)
from lychd.compositions.blockworld.companion_feedback import MAX_FEEDBACK_CHARS, feedback_text, reply_text
from lychd.compositions.blockworld.companion_intent import CompanionInstruction


def request(text: str = "state") -> CompanionRequest:
    return CompanionRequest(request_id=str(uuid4()), action=parse_text(text))


def observation() -> BridgeState:
    return BridgeState.model_validate(
        {
            "protocol": 1,
            "boot_id": str(uuid4()),
            "generation": 0,
            "actor_id": str(uuid4()),
            "mode": "idle",
            "position": [1.25, 64.0, -2.5],
            "yaw": 0.0,
            "pitch": 0.0,
            "queue_depth": 0,
            "active_action_id": None,
            "players": [{"id": str(uuid4()), "name": "PrivatePlayer", "position": [2.0, 64.0, 0.0]}],
            "timestamp_ms": int(time.time() * 1000),
        }
    )


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_state_reply_uses_observed_pose_without_identifiers_or_diagnostic_prose(language: str) -> None:
    command = request()
    state = observation()
    result = CompanionResult(
        request_id=command.request_id,
        kind="applied",
        detail="private diagnostic must never be spoken",
        observation=state,
    )
    text = feedback_text(command, result, kind="applied", language=language)
    assert "X 1.2" in text
    assert "Y 64.0" in text
    assert "Z -2.5" in text
    assert text != reply_text("applied", language)
    assert all(value not in text for value in (state.boot_id, state.actor_id, "PrivatePlayer", "private diagnostic"))
    assert len(text) <= MAX_FEEDBACK_CHARS


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("kind", ["cancelled", "unknown", "new-unrecognized-kind"])
def test_uncertain_outcomes_cannot_become_a_successful_observation(kind: str, language: str) -> None:
    command = request()
    result = CompanionResult(request_id=command.request_id, kind="applied", detail="ignored", observation=observation())
    assert feedback_text(command, result, kind=kind, language=language) == reply_text("unknown", language)


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_missing_or_unrelated_receipt_cannot_supply_a_spoken_state(language: str) -> None:
    command = request()
    unrelated = CompanionResult(request_id=str(uuid4()), kind="applied", detail="ignored", observation=observation())
    for result in (None, unrelated):
        assert feedback_text(command, result, kind="applied", language=language) == reply_text("unknown", language)


@pytest.mark.parametrize("mode", ["idle", "look", "goto", "follow", "stopped", "unavailable"])
@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_every_reported_mode_has_bounded_localized_feedback(mode: str, language: str) -> None:
    command = request()
    state = observation().model_copy(update={"mode": mode})
    result = CompanionResult(request_id=command.request_id, kind="applied", detail="ignored", observation=state)
    text = feedback_text(command, result, kind="applied", language=language)
    assert text
    assert len(text) <= MAX_FEEDBACK_CHARS
    assert text != reply_text("applied", language)


@pytest.mark.parametrize("instruction", ["goto 1 64 0", f"follow {uuid4()}"])
def test_navigation_receipt_does_not_claim_observed_movement_or_arrival(instruction: str) -> None:
    command = request(instruction)
    result = CompanionResult(request_id=command.request_id, kind="applied", detail="navigation inactive")
    text = feedback_text(command, result, kind="applied", language="en")
    assert "instruction was applied" in text
    assert "unconfirmed" in text or "not yet verified" in text


def test_chat_reply_never_echoes_private_message() -> None:
    command = request("say private-message")
    result = CompanionResult(request_id=command.request_id, kind="applied", detail="ignored")
    text = feedback_text(command, result, kind="applied", language="en")
    assert "game chat" in text
    assert "private-message" not in text


def test_unrenderable_coordinates_and_unknown_language_refuse_presentation() -> None:
    command = request()
    state = observation().model_copy(update={"position": (1e300, 64.0, 0.0)})
    result = CompanionResult(request_id=command.request_id, kind="applied", detail="ignored", observation=state)
    assert feedback_text(command, result, kind="applied", language="en") == reply_text("unknown", "en")
    with pytest.raises(ValueError, match="support"):
        feedback_text(command, result, kind="applied", language="xx")


@pytest.mark.parametrize(
    ("language", "no_action", "clarification"),
    [
        ("sk", "Žiadnu hernú akciu nevykonám.", "Prosím, upresni jeden pokyn."),
        ("cs", "Žádnou herní akci neprovedu.", "Prosím, upřesni jeden pokyn."),
        ("en", "I will take no game action.", "Please clarify one instruction."),
    ],
)
def test_terminal_nonactions_have_distinct_bounded_localized_feedback(
    language: str, no_action: str, clarification: str
) -> None:
    command = request()
    diagnostic = "private player or instruction must never be spoken"
    misleading = CompanionResult(
        request_id=command.request_id, kind="applied", detail=diagnostic, observation=observation()
    )
    for kind, expected in (("no_action", no_action), ("clarification", clarification)):
        text = feedback_text(command, misleading, kind=kind, language=language)
        assert text == expected
        assert text == reply_text(kind, language)
        assert diagnostic not in text
        assert "PrivatePlayer" not in text
        assert "X 1.2" not in text
        assert len(text) <= MAX_FEEDBACK_CHARS
        assert text != reply_text("applied", language)


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("kind", ["no_action", "clarification", "refused", "expired", "unknown"])
def test_raw_instruction_terminal_feedback_never_echoes_custody_or_foreign_text(kind: str, language: str) -> None:
    from lychd.compositions.blockworld.companion_intent import CompanionInstruction

    raw = CompanionInstruction(
        request_id=str(uuid4()),
        original_text="please wait with PrivatePlayer",
        generation=2,
        target_id=str(uuid4()),
        profile_digest="sha256:" + "c" * 64,
        expires_at_ms=123456789,
    )
    text = feedback_text(raw, None, kind=kind, language=language)
    assert text == reply_text(kind, language)
    assert len(text) <= MAX_FEEDBACK_CHARS
    assert all(value not in text for value in (raw.request_id, raw.original_text, "PrivatePlayer", raw.profile_digest))
    assert text != reply_text("applied", language)


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_raw_instruction_applied_receipt_requires_matching_correlation(language: str) -> None:
    from lychd.compositions.blockworld.companion_intent import CompanionInstruction

    raw = CompanionInstruction(
        request_id=str(uuid4()),
        original_text="please stay with me",
        generation=1,
        target_id=None,
        profile_digest="sha256:" + "c" * 64,
        expires_at_ms=123456789,
    )
    foreign = CompanionResult(request_id=str(uuid4()), kind="applied", detail="success is not evidence")
    assert feedback_text(raw, foreign, kind="applied", language=language) == reply_text("unknown", language)
    matched = CompanionResult(request_id=raw.request_id, kind="applied", detail="private diagnostic")
    assert feedback_text(raw, matched, kind="applied", language=language) == reply_text("applied", language)


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_interpreted_state_uses_only_matched_observed_snapshot(language: str) -> None:
    from lychd.compositions.blockworld.companion_intent import CompanionInstruction

    command = CompanionInstruction(
        request_id=str(uuid4()),
        original_text="Please tell me how you are",
        generation=0,
        target_id=None,
        profile_digest="sha256:" + "a" * 64,
        expires_at_ms=123456789,
    )
    state = observation()
    result = CompanionResult(
        request_id=command.request_id, kind="applied", detail="private foreign diagnostic", observation=state
    )
    text = feedback_text(command, result, kind="applied", language=language)
    assert "X 1.2" in text
    assert "Y 64.0" in text
    assert "Z -2.5" in text
    assert "private" not in text
    assert state.actor_id not in text
    unrelated = result.model_copy(update={"request_id": str(uuid4())})
    assert feedback_text(command, unrelated, kind="applied", language=language) == reply_text("unknown", language)


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize(
    ("reason", "kind"),
    [
        ("bounds", "refused"),
        ("actor_unavailable", "refused"),
        ("target_unavailable", "refused"),
        ("target_distant", "refused"),
        ("target_unbound", "clarification"),
        ("interpretation_budget_exhausted", "refused"),
        ("interpretation_unavailable", "refused"),
        ("interpretation_response_refused", "refused"),
        ("cancelled_before_execution", "cancelled"),
        ("expired_before_execution", "expired"),
    ],
)
def test_closed_host_reason_is_localized_bounded_and_private(reason: str, kind: str, language: str) -> None:
    command = request("say private-transcript")
    state = observation()
    result = CompanionResult.model_validate(
        {
            "request_id": command.request_id,
            "kind": kind,
            "detail": "private foreign detail: offline PlayerName",
            "observation": state,
            "reason": reason,
        }
    )
    text = feedback_text(command, result, kind=kind, language=language)
    assert 0 < len(text) <= MAX_FEEDBACK_CHARS
    assert text != reply_text(kind, language)
    assert all(
        value not in text
        for value in ("private", "PlayerName", "PrivatePlayer", "offline", command.request_id, state.actor_id)
    )
    if language == "en" and reason == "target_unavailable":
        assert "unavailable in the observation" in text
    if language == "en" and reason == "interpretation_budget_exhausted":
        assert "budget is exhausted" in text
        assert "exact command" in text


@dataclass(frozen=True)
class HostDisposition:
    request_id: str
    kind: str
    reason: CompanionReason | None = None


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_pre_run_reason_needs_matched_session_identity_and_no_conflicting_native_receipt(language: str) -> None:
    command = request()
    outcome = HostDisposition(command.request_id, "cancelled", "cancelled_before_execution")
    before = feedback_text(command, None, kind="cancelled", language=language, outcome=outcome)
    assert before != reply_text("unknown", language)
    unrelated = HostDisposition(str(uuid4()), "cancelled", "cancelled_before_execution")
    assert feedback_text(command, None, kind="cancelled", language=language, outcome=unrelated) == reply_text(
        "unknown", language
    )
    foreign = CompanionResult(request_id=str(uuid4()), kind="cancelled", detail="foreign")
    assert feedback_text(command, foreign, kind="cancelled", language=language, outcome=outcome) == reply_text(
        "unknown", language
    )
    matched = foreign.model_copy(update={"request_id": command.request_id, "reason": "cancelled_before_execution"})
    assert feedback_text(command, matched, kind="cancelled", language=language, outcome=unrelated) == reply_text(
        "unknown", language
    )
    mismatched = HostDisposition(command.request_id, "refused", "cancelled_before_execution")
    assert feedback_text(command, None, kind="cancelled", language=language, outcome=mismatched) == reply_text(
        "unknown", language
    )


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("forged", ["future_host_reason", {"bounds": True}, ["bounds"]])
def test_unknown_or_forged_reason_uses_conservative_feedback(forged: object, language: str) -> None:
    command = request()
    result = CompanionResult(request_id=command.request_id, kind="refused", detail="foreign").model_copy(
        update={"reason": forged}
    )
    assert feedback_text(command, result, kind="refused", language=language) == reply_text("refused", language)


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_reason_cannot_change_uncertain_kind_or_uncorrelated_refusal(language: str) -> None:
    command = request()
    uncertain = CompanionResult(
        request_id=command.request_id, kind="unknown", detail="private", reason="cancelled_before_execution"
    )
    assert feedback_text(command, uncertain, kind="unknown", language=language) == reply_text("unknown", language)
    active = uncertain.model_copy(update={"kind": "cancelled", "reason": "bounds"})
    assert feedback_text(command, active, kind="cancelled", language=language) == reply_text("unknown", language)
    foreign = uncertain.model_copy(update={"request_id": str(uuid4()), "kind": "refused", "reason": "bounds"})
    assert feedback_text(command, foreign, kind="refused", language=language) == reply_text("refused", language)


def test_future_reason_refuses_schema_and_legacy_result_defaults_to_no_reason() -> None:
    command = request()
    result = CompanionResult(request_id=command.request_id, kind="refused", detail="legacy")
    assert result.reason is None
    with pytest.raises(ValueError, match="reason"):
        CompanionResult.model_validate({**result.model_dump(), "reason": "future_host_reason"})


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("kind", ["applied", "refused", "expired", "cancelled"])
@pytest.mark.parametrize("conflict", ["outcome_identity", "outcome_kind", "result_identity", "result_kind", "reason"])
def test_every_supplied_disposition_must_agree_before_any_feedback(language: str, kind: str, conflict: str) -> None:
    command = request()
    result = CompanionResult.model_validate(
        {
            "request_id": command.request_id,
            "kind": kind,
            "detail": "private diagnostic",
            "observation": observation(),
            "reason": "bounds" if kind == "refused" else None,
        }
    )
    outcome = HostDisposition(command.request_id, kind, result.reason)
    if conflict == "outcome_identity":
        outcome = HostDisposition(str(uuid4()), kind, result.reason)
    elif conflict == "outcome_kind":
        outcome = HostDisposition(command.request_id, "unknown", result.reason)
    elif conflict == "result_identity":
        result = result.model_copy(update={"request_id": str(uuid4())})
    elif conflict == "result_kind":
        result = result.model_copy(update={"kind": "unknown"})
    else:
        outcome = HostDisposition(command.request_id, kind, "target_unavailable")
    text = feedback_text(command, result, kind=kind, language=language, outcome=outcome)
    assert text == reply_text("unknown", language)
    assert "private" not in text


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("kind", ["refused", "expired", "cancelled"])
def test_unmatched_pre_run_outcome_is_unknown_even_without_native_result(kind: str, language: str) -> None:
    command = request()
    outcome = HostDisposition(str(uuid4()), kind)
    assert feedback_text(command, None, kind=kind, language=language, outcome=outcome) == reply_text(
        "unknown", language
    )


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_matching_native_and_session_dispositions_keep_localized_feedback(language: str) -> None:
    command = request()
    for kind, reason in (("applied", None), ("refused", "bounds")):
        result = CompanionResult.model_validate(
            {
                "request_id": command.request_id,
                "kind": kind,
                "detail": "private diagnostic",
                "observation": observation(),
                "reason": reason,
            }
        )
        outcome = HostDisposition(command.request_id, kind, result.reason)
        assert feedback_text(command, result, kind=kind, language=language, outcome=outcome) == feedback_text(
            command, result, kind=kind, language=language
        )


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("instruction", ["idle", "look 1 64 0", "goto 1 64 0", f"follow {uuid4()}"])
def test_applied_controller_explains_finite_upper_bound_without_progress_claim(language: str, instruction: str) -> None:
    command = request(instruction)
    result = CompanionResult(
        request_id=command.request_id, kind="applied", detail="private", controller_expires_at_ms=16_001
    )
    text = feedback_text(command, result, kind="applied", language=language, at_ms=1001)
    assert "15 s" in text
    assert "stav" in text if language != "en" else "state" in text
    assert len(text) <= MAX_FEEDBACK_CHARS
    assert "private" not in text
    assert command.request_id not in text
    if language == "en" and command.action.kind == "follow":
        assert "Movement is not yet verified." in text
    if language == "en" and command.action.kind == "goto":
        assert "Arrival is unconfirmed." in text


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_elapsed_host_deadline_does_not_announce_observed_stop_or_reason(language: str) -> None:
    command = request("idle")
    result = CompanionResult(
        request_id=command.request_id, kind="applied", detail="target lost", controller_expires_at_ms=1000
    )
    text = feedback_text(command, result, kind="applied", language=language, at_ms=1001)
    assert len(text) <= MAX_FEEDBACK_CHARS
    assert "stav" in text if language != "en" else "state" in text
    assert "target lost" not in text
    assert "stopped" not in text
    if language == "en":
        assert "authorized window elapsed" in text


@pytest.mark.parametrize("instruction", ["state", "say hello"])
def test_unrelated_action_cannot_gain_controller_feedback(instruction: str) -> None:
    command = request(instruction)
    result = CompanionResult(
        request_id=command.request_id,
        kind="applied",
        detail="ignored",
        observation=observation(),
        controller_expires_at_ms=16_000,
    )
    text = feedback_text(command, result, kind="applied", language="en", at_ms=1000)
    assert "Control for at most" not in text
    assert "authorized window" not in text


@pytest.mark.parametrize("kind", ["refused", "unknown", "cancelled"])
def test_uncertain_result_ignores_controller_metadata(kind: str) -> None:
    command = request("idle")
    result = CompanionResult(
        request_id=command.request_id, kind="applied", detail="ignored", controller_expires_at_ms=16_000
    )
    assert feedback_text(command, result, kind=kind, language="en", at_ms=1000) == reply_text(kind, "en")


def test_raw_interpreted_controller_keeps_snapshot_and_limit() -> None:
    command = CompanionInstruction(
        request_id=str(uuid4()),
        original_text="Please wait quietly",
        generation=0,
        target_id=None,
        profile_digest="sha256:" + "a" * 64,
        expires_at_ms=30_000,
    )
    result = CompanionResult(
        request_id=command.request_id,
        kind="applied",
        detail="ignored",
        observation=observation(),
        controller_expires_at_ms=16_000,
    )
    text = feedback_text(command, result, kind="applied", language="en", at_ms=1000)
    assert "Reported state:" in text
    assert "at most 15 s" in text
    assert len(text) <= MAX_FEEDBACK_CHARS


def test_missing_formatting_time_never_guesses_remaining_seconds() -> None:
    command = request("idle")
    result = CompanionResult(
        request_id=command.request_id, kind="applied", detail="ignored", controller_expires_at_ms=16_000
    )
    text = feedback_text(command, result, kind="applied", language="en")
    assert "time limited" in text
    assert "15" not in text
