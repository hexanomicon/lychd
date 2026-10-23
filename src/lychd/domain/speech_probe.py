"""Pinned local engineering speech observations, without native Echo admission."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from lychd.domain.artifacts import ArtifactRef

MAX_INPUT_BYTES = 1_048_576
MAX_PROFILE_BYTES = 32_768
MAX_TEXT_CHARS = 8192
MAX_AUDIO_BYTES = 16_777_216
STOCK_VOICES = ("M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5")
type StockVoice = Literal["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]
_ENDPOINT = re.compile(r"http://(?:127\.0\.0\.1|\[::1\]):([1-9][0-9]{0,4})\Z")
_LANGUAGE = re.compile(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*\Z")
_MAX_LANGUAGE_LENGTH = 35
_MAX_PORT = 65535


def content_digest(content: bytes) -> str:
    """Name exact bytes, without treating their digest as permission or custody."""
    return "sha256:" + hashlib.sha256(content).hexdigest()


class SpeechProbeError(ValueError):
    """Content-free refusal; a submitted request may still execute on the server."""


class ProbeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SpeechModel(ProbeModel):
    """An operator-supplied model pin, not an attestation of server-loaded bytes."""

    model: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    family: Literal["parakeet-tdt-0.6b-v3", "supertonic-3"]
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    languages: tuple[str, ...] = Field(min_length=1, max_length=128)
    license: str = Field(min_length=1, max_length=256)

    @field_validator("languages")
    @classmethod
    def declared_languages(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value) or any(
            len(item) > _MAX_LANGUAGE_LENGTH or not _LANGUAGE.fullmatch(item) for item in value
        ):
            msg = "Model languages must be unique bounded language tags."
            raise ValueError(msg)
        return value


class SpeechProfile(ProbeModel):
    """An explicit finite audio.cpp batch dialect; declarations are not quality bakes."""

    schema_version: Literal[1] = 1
    runtime: Literal["audio.cpp"] = "audio.cpp"
    dialect: Literal["audio.cpp-batch-v1"] = "audio.cpp-batch-v1"
    endpoint: str = Field(max_length=64)
    runtime_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    backend: str = Field(min_length=1, max_length=64)
    device: str = Field(min_length=1, max_length=64)
    transcriber: SpeechModel
    synthesizer: SpeechModel
    transport_timeout_seconds: float = Field(gt=0, le=30, allow_inf_nan=False)
    total_timeout_seconds: float = Field(gt=0, le=300, allow_inf_nan=False)
    max_response_bytes: int = Field(ge=44, le=MAX_AUDIO_BYTES)
    max_text_chars: int = Field(ge=1, le=MAX_TEXT_CHARS)

    @field_validator("endpoint")
    @classmethod
    def literal_loopback(cls, value: str) -> str:
        match = _ENDPOINT.fullmatch(value)
        if match is None or int(match[1]) > _MAX_PORT:
            msg = "Endpoint must be exact HTTP literal loopback with an explicit port and no path."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def exact_bindings(self) -> Self:
        if self.transcriber.family != "parakeet-tdt-0.6b-v3" or self.synthesizer.family != "supertonic-3":
            msg = "The two operation bindings must use their separately declared candidate model families."
            raise ValueError(msg)
        return self

    @property
    def digest(self) -> str:
        sealed = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return content_digest(sealed.encode())

    def language_for_transcription(self, language: str | None) -> str | None:
        """Omission permits this model's detection; it grants no translation."""
        if language is not None and language not in self.transcriber.languages:
            msg = "Transcription language is not declared by the selected model."
            raise SpeechProbeError(msg)
        return language

    def language_for_synthesis(self, language: str) -> str:
        if language not in self.synthesizer.languages:
            msg = "Synthesis language is not declared by the selected model."
            raise SpeechProbeError(msg)
        return language

    @property
    def transcriber_binding(self) -> LocalSpeechBinding:
        return self._binding(self.transcriber)

    @property
    def synthesizer_binding(self) -> LocalSpeechBinding:
        return self._binding(self.synthesizer)

    def _binding(self, model: SpeechModel) -> LocalSpeechBinding:
        return LocalSpeechBinding(
            runtime=self.runtime,
            dialect=self.dialect,
            endpoint=self.endpoint,
            runtime_revision=self.runtime_revision,
            backend=self.backend,
            device=self.device,
            model=model,
        )


class WhisperModel(ProbeModel):
    """The multilingual small checkpoint; a pin does not attest loaded server weights."""

    model: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    family: Literal["whisper-small"]
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    languages: tuple[str, ...] = Field(min_length=1, max_length=128)
    license: str = Field(min_length=1, max_length=256)

    @field_validator("languages")
    @classmethod
    def declared_languages(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return SpeechModel.declared_languages(value)


class LocalSpeechBinding(ProbeModel):
    """One explicit local operation binding, with no runtime or model fallback."""

    runtime: Literal["audio.cpp", "whisper.cpp"]
    dialect: Literal["audio.cpp-batch-v1", "whisper.cpp-batch-v1"]
    endpoint: str = Field(max_length=64)
    runtime_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    backend: str = Field(min_length=1, max_length=64)
    device: str = Field(min_length=1, max_length=64)
    model: SpeechModel | WhisperModel

    @field_validator("endpoint")
    @classmethod
    def literal_loopback(cls, value: str) -> str:
        return SpeechProfile.literal_loopback(value)

    @model_validator(mode="after")
    def exact_dialect(self) -> Self:
        pair = self.runtime, self.dialect
        families = {
            ("audio.cpp", "audio.cpp-batch-v1"): {"parakeet-tdt-0.6b-v3", "supertonic-3"},
            ("whisper.cpp", "whisper.cpp-batch-v1"): {"whisper-small"},
        }
        if self.model.family not in families.get(pair, set()):
            msg = "Runtime, dialect and model family must be an exact supported binding."
            raise ValueError(msg)
        return self


class SpeechProfileV2(ProbeModel):
    """Independent local Ear/Voice probe bindings; neither is a native Echo grant."""

    schema_version: Literal[2]
    transcriber_binding: LocalSpeechBinding
    synthesizer_binding: LocalSpeechBinding
    transport_timeout_seconds: float = Field(gt=0, le=30, allow_inf_nan=False)
    total_timeout_seconds: float = Field(gt=0, le=300, allow_inf_nan=False)
    max_response_bytes: int = Field(ge=44, le=MAX_AUDIO_BYTES)
    max_text_chars: int = Field(ge=1, le=MAX_TEXT_CHARS)

    @field_validator("schema_version", mode="before")
    @classmethod
    def original_version(cls, value: Any) -> Any:
        if type(value) is not int or value != 2:  # noqa: PLR2004 - exact versioned profile
            msg = "Version 2 requires original integer 2."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def exact_operations(self) -> Self:
        if (
            self.transcriber_binding.model.family not in {"parakeet-tdt-0.6b-v3", "whisper-small"}
            or self.synthesizer_binding.model.family != "supertonic-3"
        ):
            msg = "The two operation bindings must use their separately declared candidate model families."
            raise ValueError(msg)
        return self

    @property
    def digest(self) -> str:
        sealed = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return content_digest(sealed.encode())

    def language_for_transcription(self, language: str | None) -> str | None:
        if self.transcriber_binding.runtime == "whisper.cpp" and language is None:
            msg = "The whisper.cpp dialect requires an explicit declared transcription language."
            raise SpeechProbeError(msg)
        if language is not None and language not in self.transcriber_binding.model.languages:
            msg = "Transcription language is not declared by the selected model."
            raise SpeechProbeError(msg)
        return language

    def language_for_synthesis(self, language: str) -> str:
        if language not in self.synthesizer_binding.model.languages:
            msg = "Synthesis language is not declared by the selected model."
            raise SpeechProbeError(msg)
        return language


type LocalSpeechProfile = SpeechProfile | SpeechProfileV2


def load_speech_profile(document: str | bytes) -> LocalSpeechProfile:
    """Select the explicit version without changing the version 1 schema or identity."""

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                msg = "Duplicate speech profile fields are refused."
                raise SpeechProbeError(msg)
            result[key] = value
        return result

    raw: Any = json.loads(document, object_pairs_hook=unique)
    if not isinstance(raw, dict):
        msg = "Speech profile must be an explicit versioned object."
        raise SpeechProbeError(msg)
    version = cast("dict[str, Any]", raw).get("schema_version", 1)
    if type(version) is not int or version not in (1, 2):
        msg = "Speech profile version must be original integer 1 or 2."
        raise SpeechProbeError(msg)
    if version == 1:
        return SpeechProfile.model_validate_json(document)
    return SpeechProfileV2.model_validate_json(document)


def speech_profile_schema() -> dict[str, Any]:
    """Describe both explicit engineering profiles, with their original model schemas."""
    return TypeAdapter(LocalSpeechProfile).json_schema()


class TranscriptObservation(ProbeModel):
    """An attributed interpretation; no confidence or detected language is fabricated."""

    source: ArtifactRef
    profile_digest: str
    runtime_revision: str
    model: SpeechModel | WhisperModel
    requested_language: str | None
    text: str = Field(max_length=MAX_TEXT_CHARS)
    native_echo_admission: Literal[False] = False


class WavFacts(ProbeModel):
    sample_rate_hz: int
    channels: int
    sample_width_bytes: int
    frame_count: int


class SynthesisObservation(ProbeModel):
    """Generated private bytes are neither delivered speech nor observed playback."""

    profile_digest: str
    runtime_revision: str
    model: SpeechModel
    requested_language: str
    voice: StockVoice
    text_digest: str
    audio_digest: str
    size: int
    wav: WavFacts
    generated: Literal[True] = True
    playback: Literal["not_attempted"] = "not_attempted"
    native_echo_admission: Literal[False] = False
