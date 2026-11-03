import base64
import json
import struct
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from lychd.domain.dictation import (
    MAX_AUDIO_BASE64_CHARS,
    DictationAttemptIdentity,
    DictationCorrection,
    DictationCorrectionRequest,
    DictationDiscovery,
    DictationError,
    DictationLexiconRuleRequest,
    DictationProfile,
    DictationRequest,
    DictationResult,
    decide_attempt,
    decode_audio,
)
from lychd.domain.speech_probe import LocalSpeechBinding, WhisperModel, content_digest


def profile() -> DictationProfile:
    return DictationProfile(
        transcriber_binding=LocalSpeechBinding(
            runtime="whisper.cpp",
            dialect="whisper.cpp-batch-v1",
            endpoint="http://127.0.0.1:8081",
            runtime_revision="a" * 40,
            backend="cpu",
            device="host",
            model=WhisperModel(
                model="small-test",
                family="whisper-small",
                digest="sha256:" + "b" * 64,
                languages=("en", "sk"),
                license="synthetic-test-only",
            ),
        ),
    )


def wav(frames: int = 1) -> bytes:
    size = frames * 2
    return (
        struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            size + 36,
            b"WAVE",
            b"fmt ",
            16,
            1,
            1,
            16000,
            32000,
            2,
            16,
            b"data",
            size,
        )
        + b"\x00" * size
    )


def request(content: bytes) -> DictationRequest:
    return DictationRequest(attempt_id=uuid4(), audio_base64=base64.b64encode(content).decode(), language="en")


def identity() -> DictationAttemptIdentity:
    return DictationAttemptIdentity(
        owner="alice",
        attempt_id=uuid4(),
        source_digest=content_digest(wav()),
        profile_digest=profile().digest,
        language="en",
    )


def test_profile_is_exact_cpu_and_has_no_tts_binding() -> None:
    original = profile()
    assert DictationProfile.model_validate_json(original.model_dump_json()) == original
    assert "synthesizer" not in original.model_dump_json()
    for field, value in (("backend", "cuda"), ("device", "cuda:0"), ("runtime", "audio.cpp")):
        data = original.model_dump(mode="json")
        data["transcriber_binding"][field] = value
        with pytest.raises(ValidationError):
            DictationProfile.model_validate_json(json.dumps(data))
    changed = original.model_dump(mode="json")
    changed["transcriber_binding"]["runtime_revision"] = "c" * 40
    assert DictationProfile.model_validate_json(json.dumps(changed)).digest != original.digest


def test_discovery_defaults_unavailable_and_needs_identified_available_profile() -> None:
    assert DictationDiscovery().status == "unavailable"
    with pytest.raises(ValidationError):
        DictationDiscovery(status="available", reason=None)
    assert (
        DictationDiscovery(
            status="available",
            reason=None,
            profile_digest=profile().digest,
            languages=("en",),
        ).status
        == "available"
    )


@pytest.mark.parametrize("frames", [1, 16000, 480000])
def test_canonical_pcm_including_silence_and_maximum_duration(frames: int) -> None:
    content = wav(frames)
    assert decode_audio(request(content)) == content


@pytest.mark.parametrize("content", [wav(0), wav(480001), wav() + b"\x00", wav()[:-1]])
def test_refuses_empty_overlong_truncated_or_trailing_audio(content: bytes) -> None:
    with pytest.raises(DictationError, match="invalid_audio"):
        decode_audio(request(content))


@pytest.mark.parametrize("offset", [0, 4, 8, 12, 16, 20, 22, 24, 28, 32, 34, 36, 40])
def test_every_canonical_header_field_is_checked(offset: int) -> None:
    content = bytearray(wav())
    content[offset] ^= 1
    with pytest.raises(DictationError, match="invalid_audio"):
        decode_audio(request(bytes(content)))


@pytest.mark.parametrize("encoded", [" ", "%%%%", "AAAA\n", "AA=A", "é"])
def test_refuses_noncanonical_base64(encoded: str) -> None:
    data = DictationRequest(attempt_id=uuid4(), audio_base64=encoded, language="en")
    with pytest.raises(DictationError, match="invalid_audio"):
        decode_audio(data)


def test_request_limits_base64_and_forbids_owner_and_language_omission() -> None:
    data = request(wav()).model_dump(mode="json")
    for extra in (
        {"owner": "alice"},
        {"audio_base64": ""},
        {"audio_base64": "A" * (MAX_AUDIO_BASE64_CHARS + 1)},
        {"language": ""},
    ):
        with pytest.raises(ValidationError):
            DictationRequest.model_validate({**data, **extra})
    del data["language"]
    with pytest.raises(ValidationError):
        DictationRequest.model_validate(data)


def test_attempt_replay_requires_every_identity_axis() -> None:
    original = identity()
    assert decide_attempt(None, original) == "dispatch"
    assert decide_attempt(original, original) == "replay"
    for field, value in (
        ("owner", "bob"),
        ("attempt_id", uuid4()),
        ("language", "sk"),
        ("source_digest", content_digest(wav(2))),
        ("profile_digest", "sha256:" + "d" * 64),
    ):
        changed = DictationAttemptIdentity.model_validate({**original.model_dump(), field: value})
        assert decide_attempt(original, changed) == "refuse"


def test_results_never_fabricate_transcript_or_drop_success_provenance() -> None:
    original = identity()
    metadata = original.model_dump(exclude={"owner"})
    assert DictationResult(**metadata, status="transcribed", original_text="").original_text == ""
    unknown = DictationResult(**metadata, status="unknown", reason="outcome_unknown")
    assert unknown.original_text is None
    with pytest.raises(ValidationError):
        DictationResult(**metadata, status="unknown", reason="outcome_unknown", original_text="leaked")
    with pytest.raises(ValidationError):
        DictationResult(attempt_id=original.attempt_id, language="en", status="transcribed", original_text="text")
    with pytest.raises(ValidationError):
        DictationResult(**metadata, status="transcribed", original_text="bad\x00text")


def test_corrections_preserve_original_and_have_no_owner_or_training_fields() -> None:
    now = datetime.now(UTC)
    record = DictationCorrection(
        **identity().model_dump(exclude={"owner"}),
        original_text="wright",
        final_text="right",
        created_at=now,
        expires_at=now + timedelta(days=7),
    )
    assert record.original_text == "wright"
    assert record.final_text == "right"
    with pytest.raises(ValidationError):
        DictationCorrection.model_validate({**record.model_dump(), "expires_at": now + timedelta(days=31)})
    with pytest.raises(ValidationError):
        DictationCorrectionRequest.model_validate(
            {"attempt_id": record.attempt_id, "final_text": "fixed", "owner": "bob"}
        )
    assert "original_text" not in DictationCorrectionRequest.model_fields
    assert "training" not in DictationCorrection.model_fields


def test_glossary_is_separate_explicit_language_scoped_approval() -> None:
    data = {"language": "en", "heard": "licked", "replacement": "LychD"}
    with pytest.raises(ValidationError):
        DictationLexiconRuleRequest.model_validate(data)
    with pytest.raises(ValidationError):
        DictationLexiconRuleRequest.model_validate({**data, "approved": False})
    assert DictationLexiconRuleRequest.model_validate({**data, "approved": True}).language == "en"


def test_only_absent_uuid7_within_bounded_time_may_claim() -> None:
    from uuid import UUID

    from lychd.domain.dictation import validate_new_attempt_time

    now = datetime(2026, 11, 3, tzinfo=UTC)
    timestamp_ms = int(now.timestamp() * 1000)
    for delta in (-300_000, 0, 30_000):
        attempt = UUID(int=((timestamp_ms + delta) << 80) | (7 << 76) | (2 << 62) | 1)
        validate_new_attempt_time(attempt, now)
    for delta in (-300_001, 30_001):
        attempt = UUID(int=((timestamp_ms + delta) << 80) | (7 << 76) | (2 << 62) | 1)
        with pytest.raises(DictationError, match="expired"):
            validate_new_attempt_time(attempt, now)
    with pytest.raises(DictationError, match="expired"):
        validate_new_attempt_time(uuid4(), now)
    with pytest.raises(ValueError, match="timezone-aware"):
        validate_new_attempt_time(attempt, now.replace(tzinfo=None))
