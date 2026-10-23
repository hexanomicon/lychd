import json

import pytest
from pydantic import ValidationError

from lychd.domain.speech_probe import (
    LocalSpeechBinding,
    SpeechModel,
    SpeechProbeError,
    SpeechProfile,
    SpeechProfileV2,
    WhisperModel,
    content_digest,
    load_speech_profile,
    speech_profile_schema,
)


def profile() -> SpeechProfile:
    return SpeechProfile(
        endpoint="http://127.0.0.1:8080",
        runtime_revision="a" * 40,
        backend="cpu",
        device="cpu",
        transcriber=SpeechModel(
            model="parakeet-test",
            family="parakeet-tdt-0.6b-v3",
            digest="sha256:" + "b" * 64,
            languages=("sk", "cs", "en"),
            license="operator-reviewed-test-only",
        ),
        synthesizer=SpeechModel(
            model="supertonic-test",
            family="supertonic-3",
            digest="sha256:" + "c" * 64,
            languages=("sk", "cs", "en"),
            license="operator-reviewed-test-only",
        ),
        transport_timeout_seconds=2.0,
        total_timeout_seconds=4.0,
        max_response_bytes=1_048_576,
        max_text_chars=256,
    )


def profile_v2() -> SpeechProfileV2:
    return SpeechProfileV2(
        schema_version=2,
        transcriber_binding=LocalSpeechBinding(
            runtime="whisper.cpp",
            dialect="whisper.cpp-batch-v1",
            endpoint="http://127.0.0.1:8081",
            runtime_revision="d" * 40,
            backend="cpu",
            device="host",
            model=WhisperModel(
                model="whisper-small-test",
                family="whisper-small",
                digest="sha256:" + "d" * 64,
                languages=("sk", "cs", "en"),
                license="operator-reviewed-test-only",
            ),
        ),
        synthesizer_binding=LocalSpeechBinding(
            runtime="audio.cpp",
            dialect="audio.cpp-batch-v1",
            endpoint="http://127.0.0.1:8082",
            runtime_revision="e" * 40,
            backend="cpu",
            device="host",
            model=profile().synthesizer,
        ),
        transport_timeout_seconds=2.0,
        total_timeout_seconds=4.0,
        max_response_bytes=1_048_576,
        max_text_chars=256,
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://localhost:8080",
        "https://127.0.0.1:8080",
        "http://127.1:8080",
        "http://127.0.0.2:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:0",
        "http://127.0.0.1:65536",
        "http://127.0.0.1:08080",
        "http://127.0.0.1:8080/",
        "http://127.0.0.1:8080?",
        "http://127.0.0.1:8080#",
        "http://user@127.0.0.1:8080",
        "http://127.0.0.1:8080@evil.example",
        "http://[::ffff:127.0.0.1]:8080",
        " http://127.0.0.1:8080",
        "http://127.0.0.1:8080\n",
    ],
)
def test_exact_endpoint_refuses_ambiguous_or_remote_spellings(endpoint: str) -> None:
    data = profile().model_dump(mode="json")
    data["endpoint"] = endpoint
    with pytest.raises(ValidationError):
        SpeechProfile.model_validate_json(json.dumps(data))


def test_ipv6_literal_and_json_roundtrip_are_supported() -> None:
    data = profile().model_dump(mode="json")
    data["endpoint"] = "http://[::1]:8081"
    loaded = SpeechProfile.model_validate_json(json.dumps(data))
    assert loaded.endpoint == "http://[::1]:8081"
    assert SpeechProfile.model_validate_json(loaded.model_dump_json()).digest == loaded.digest


def test_pins_are_frozen_and_profile_digest_changes_with_each_binding() -> None:
    pinned = profile()
    with pytest.raises(ValidationError, match="frozen"):
        pinned.endpoint = "http://127.0.0.1:8001"
    with pytest.raises(ValidationError, match="frozen"):
        pinned.transcriber.model = "changed"
    for key, value in (("runtime_revision", "d" * 40), ("backend", "cuda"), ("device", "cuda:0")):
        assert pinned.model_copy(update={key: value}).digest != pinned.digest
    assert (
        pinned.model_copy(
            update={"synthesizer": pinned.synthesizer.model_copy(update={"digest": "sha256:" + "d" * 64})}
        ).digest
        != pinned.digest
    )


def test_languages_are_per_binding_and_have_no_global_default() -> None:
    pinned = profile()
    data = pinned.model_dump(mode="json")
    data["transcriber"]["languages"] = ["ja"]
    data["synthesizer"]["languages"] = ["de"]
    other = SpeechProfile.model_validate_json(json.dumps(data))
    assert other.language_for_transcription(None) is None
    assert other.language_for_transcription("ja") == "ja"
    assert other.language_for_synthesis("de") == "de"
    for operation in (other.language_for_transcription, other.language_for_synthesis):
        with pytest.raises(SpeechProbeError, match="not declared"):
            operation("sk")


@pytest.mark.parametrize("languages", [[], ["sk", "sk"], ["SK"], ["sk\n"], ["../../sk"]])
def test_refuses_invalid_language_declarations(languages: list[str]) -> None:
    data = profile().model_dump(mode="json")
    data["transcriber"]["languages"] = languages
    with pytest.raises(ValidationError):
        SpeechProfile.model_validate_json(json.dumps(data))


def test_wrong_families_hashes_bounds_and_extra_fields_are_refused() -> None:
    original = profile().model_dump(mode="json")
    for key, value in (
        ("runtime_revision", "latest"),
        ("max_response_bytes", True),
        ("max_text_chars", 0),
        ("total_timeout_seconds", float("inf")),
        ("proxy", "http://example.com"),
    ):
        data = {**original, key: value}
        with pytest.raises(ValidationError):
            SpeechProfile.model_validate_json(json.dumps(data))
    data = profile().model_dump(mode="json")
    data["transcriber"] = data["synthesizer"]
    with pytest.raises(ValidationError, match="families"):
        SpeechProfile.model_validate_json(json.dumps(data))
    data = profile().model_dump(mode="json")
    data["transcriber"]["digest"] = "not-pinned"
    with pytest.raises(ValidationError):
        SpeechProfile.model_validate_json(json.dumps(data))


def test_version_one_schema_and_digest_are_unchanged_by_operation_views() -> None:
    pinned = profile()
    assert pinned.digest == "sha256:9529bb6653d2d16c0267b0acc20222ab83212360525f51ee67d9466dd79f4d9b"
    schema_bytes = json.dumps(SpeechProfile.model_json_schema(), sort_keys=True, separators=(",", ":")).encode()
    assert content_digest(schema_bytes) == "sha256:e93ec443ee776458d273a2e0ee91a9ad6fac20fa2adbd6fadccbcf7c1e014155"
    original = pinned.model_dump(mode="json")
    assert pinned.transcriber_binding.model == pinned.transcriber
    assert pinned.synthesizer_binding.model == pinned.synthesizer
    assert pinned.model_dump(mode="json") == original
    assert "transcriber_binding" not in original
    assert load_speech_profile(pinned.model_dump_json()).digest == pinned.digest
    original.pop("schema_version")
    assert load_speech_profile(json.dumps(original)).digest == pinned.digest


def test_version_two_roundtrip_keeps_distinct_operation_pins_and_full_identity() -> None:
    pinned = profile_v2()
    loaded = load_speech_profile(pinned.model_dump_json())
    assert isinstance(loaded, SpeechProfileV2)
    assert loaded.digest == pinned.digest
    assert loaded.transcriber_binding.runtime == "whisper.cpp"
    assert loaded.synthesizer_binding.runtime == "audio.cpp"
    assert loaded.transcriber_binding.endpoint != loaded.synthesizer_binding.endpoint
    assert loaded.transcriber_binding.runtime_revision != loaded.synthesizer_binding.runtime_revision
    assert {"SpeechProfile", "SpeechProfileV2"} <= set(speech_profile_schema()["$defs"])
    assert "schema_version" in speech_profile_schema()["$defs"]["SpeechProfileV2"]["required"]
    for role in ("transcriber_binding", "synthesizer_binding"):
        for field, value in (
            ("endpoint", "http://[::1]:8083"),
            ("runtime_revision", "f" * 40),
            ("backend", "cuda"),
            ("device", "cuda:0"),
        ):
            document = pinned.model_dump(mode="json")
            document[role][field] = value
            assert load_speech_profile(json.dumps(document)).digest != pinned.digest
        document = pinned.model_dump(mode="json")
        document[role]["model"]["digest"] = "sha256:" + "f" * 64
        assert load_speech_profile(json.dumps(document)).digest != pinned.digest


@pytest.mark.parametrize(
    ("role", "field", "value"),
    [
        ("transcriber_binding", "runtime", "audio.cpp"),
        ("transcriber_binding", "dialect", "audio.cpp-batch-v1"),
        ("synthesizer_binding", "runtime", "whisper.cpp"),
        ("synthesizer_binding", "dialect", "whisper.cpp-batch-v1"),
        ("transcriber_binding", "endpoint", "http://localhost:8081"),
        ("synthesizer_binding", "endpoint", "http://user:secret@127.0.0.1:8082"),
        ("transcriber_binding", "endpoint", "http://127.0.0.1:8081/"),
        ("synthesizer_binding", "endpoint", True),
        ("transcriber_binding", "runtime_revision", "latest"),
        ("transcriber_binding", "model", {"model": "small"}),
    ],
)
def test_version_two_refuses_invalid_endpoint_type_and_runtime_dialect_pairs(
    role: str, field: str, value: object
) -> None:
    document = profile_v2().model_dump(mode="json")
    document[role][field] = value
    with pytest.raises(ValidationError):
        load_speech_profile(json.dumps(document))


def test_version_two_refuses_swapped_roles_and_undeclared_whisper_variants() -> None:
    document = profile_v2().model_dump(mode="json")
    document["transcriber_binding"], document["synthesizer_binding"] = (
        document["synthesizer_binding"],
        document["transcriber_binding"],
    )
    with pytest.raises(ValidationError, match="families"):
        load_speech_profile(json.dumps(document))
    document = profile_v2().model_dump(mode="json")
    document["transcriber_binding"]["model"]["family"] = "whisper-small.en"
    with pytest.raises(ValidationError):
        load_speech_profile(json.dumps(document))


@pytest.mark.parametrize("version", [True, "2", 2.0, 3, None])
def test_loader_refuses_nonoriginal_or_unsupported_versions(version: object) -> None:
    document = profile_v2().model_dump(mode="json")
    document["schema_version"] = version
    with pytest.raises(SpeechProbeError, match="original integer"):
        load_speech_profile(json.dumps(document))


def test_whisper_requires_declared_explicit_language_without_affecting_audio_detection() -> None:
    pinned = profile_v2()
    with pytest.raises(SpeechProbeError, match="explicit"):
        pinned.language_for_transcription(None)
    with pytest.raises(SpeechProbeError, match="not declared"):
        pinned.language_for_transcription("ja")
    assert pinned.language_for_transcription("sk") == "sk"
    audio = pinned.model_copy(update={"transcriber_binding": profile().transcriber_binding})
    assert audio.language_for_transcription(None) is None
