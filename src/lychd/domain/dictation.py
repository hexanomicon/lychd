"""Bounded Bridge dictation contracts; no Dispatcher grant or physical effects.

Profile pins are operator declarations, not proof of the running server. The
service must persist an unknown claim before its one external submission and
must never redispatch a retained attempt, including after restart or deletion.
"""

from __future__ import annotations

import base64
import binascii
import json
import struct
from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

from lychd.domain.speech_probe import LocalSpeechBinding, ProbeModel, content_digest

MAX_AUDIO_BYTES = 1_048_576
MAX_AUDIO_SECONDS = 30
MAX_AUDIO_FRAMES = 480_000
MAX_AUDIO_BASE64_CHARS = 4 * ((MAX_AUDIO_BYTES + 2) // 3)
MAX_TEXT_CHARS = 8192
MAX_RETENTION_SECONDS = 2_592_000
_CONTROL_CHAR_LIMIT = 32
_HEADER_BYTES = 44
_SAMPLE_RATE = 16_000
_SAMPLE_WIDTH = 2

type Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
type Language = Annotated[StrictStr, Field(min_length=2, max_length=35, pattern=r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")]
type DictationStatus = Literal["transcribed", "unavailable", "refused", "unknown"]
type DictationReason = Literal[
    "unconfigured",
    "not_qualified",
    "invalid_audio",
    "language_unavailable",
    "replay_conflict",
    "outcome_unknown",
    "capacity",
    "expired",
    "transport_unavailable",
]


class DictationError(ValueError):
    """Fixed content-free refusal safe for a public error projection."""

    def __init__(self, reason: DictationReason) -> None:
        """Retain only the fixed public refusal reason."""
        self.reason: DictationReason = reason
        super().__init__(reason)


class DictationTranscriberError(ValueError):
    """Content-free port failure; local waiting never proves remote settlement."""

    def __init__(self, outcome: Literal["refused", "unknown"], reason: DictationReason) -> None:
        """Retain a fixed outcome and content-free reason."""
        self.outcome: Literal["refused", "unknown"] = outcome
        self.reason: DictationReason = reason
        super().__init__(reason)


class DictationModel(BaseModel):
    """JSON-facing records reject ambient fields and preserve submitted text."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class DictationProfile(ProbeModel):
    """Explicit Bridge-only CPU binding; absence means unavailable.

    A configured profile alone does not establish readiness or measured language
    quality. The service's qualification decision is separate from this shape.
    """

    schema_version: Literal[1] = 1
    transcriber_binding: LocalSpeechBinding
    transport_timeout_seconds: float = Field(default=10.0, gt=0, le=30, allow_inf_nan=False)
    total_timeout_seconds: float = Field(default=30.0, gt=0, le=60, allow_inf_nan=False)
    max_response_bytes: int = Field(default=65_536, ge=1, le=65_536)
    max_text_chars: int = Field(default=MAX_TEXT_CHARS, ge=1, le=MAX_TEXT_CHARS)
    retention_seconds: int = Field(default=604_800, ge=1, le=MAX_RETENTION_SECONDS)
    max_records_per_owner: int = Field(default=100, ge=1, le=1000)
    raw_audio_retention_seconds: int = Field(default=300, ge=0, le=3600)

    @model_validator(mode="after")
    def bounded_binding(self) -> Self:
        binding = self.transcriber_binding
        if (
            binding.runtime != "whisper.cpp"
            or binding.dialect != "whisper.cpp-batch-v1"
            or binding.model.family != "whisper-small"
            or binding.backend != "cpu"
            or binding.device not in {"cpu", "host"}
        ):
            msg = "Bridge dictation requires the exact whisper.cpp CPU binding."
            raise ValueError(msg)
        if self.transport_timeout_seconds > self.total_timeout_seconds:
            msg = "Transport timeout cannot exceed the total timeout."
            raise ValueError(msg)
        return self

    @property
    def digest(self) -> str:
        sealed = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return content_digest(sealed.encode())


class DictationRequest(DictationModel):
    """Owner is resolved from authentication, never from this payload."""

    attempt_id: UUID
    audio_base64: StrictStr = Field(min_length=1, max_length=MAX_AUDIO_BASE64_CHARS, repr=False)
    language: Language


class DictationDiscovery(DictationModel):
    status: Literal["available", "unavailable"] = "unavailable"
    reason: DictationReason | None = "unconfigured"
    profile_digest: Digest | None = None
    languages: tuple[Language, ...] = ()
    max_audio_bytes: Literal[1_048_576] = MAX_AUDIO_BYTES
    max_audio_seconds: Literal[30] = MAX_AUDIO_SECONDS
    sample_rate_hz: Literal[16000] = _SAMPLE_RATE
    channels: Literal[1] = 1
    sample_width_bytes: Literal[2] = _SAMPLE_WIDTH
    raw_audio_retention_seconds: int = Field(default=300, ge=0, le=3600)
    retention_seconds: int | None = Field(default=None, ge=1, le=MAX_RETENTION_SECONDS)
    max_records_per_owner: int | None = Field(default=None, ge=1, le=1000)

    @model_validator(mode="after")
    def coherent_availability(self) -> Self:
        if self.status == "available" and (
            self.profile_digest is None or not self.languages or self.reason is not None
        ):
            msg = "Available dictation needs an identified profile, languages and no refusal."
            raise ValueError(msg)
        if self.status == "unavailable" and self.reason is None:
            msg = "Unavailable dictation needs a reason."
            raise ValueError(msg)
        return self


class DictationResult(DictationModel):
    attempt_id: UUID
    status: DictationStatus
    source_digest: Digest | None = None
    profile_digest: Digest | None = None
    language: Language
    original_text: StrictStr | None = Field(default=None, max_length=MAX_TEXT_CHARS, repr=False)
    reason: DictationReason | None = None

    @field_validator("original_text")
    @classmethod
    def bounded_original(cls, value: str | None) -> str | None:
        if value is not None:
            validate_text(value)
        return value

    @model_validator(mode="after")
    def coherent_outcome(self) -> Self:
        if self.status == "transcribed":
            if (
                self.original_text is None
                or self.source_digest is None
                or self.profile_digest is None
                or self.reason is not None
            ):
                msg = "Transcribed result needs original text and exact source/profile identities."
                raise ValueError(msg)
        elif self.original_text is not None or self.reason is None:
            msg = "Non-success results contain a reason and no transcript."
            raise ValueError(msg)
        if self.status == "unknown" and (self.source_digest is None or self.profile_digest is None):
            msg = "Unknown outcome must retain exact attempt provenance."
            raise ValueError(msg)
        return self


class DictationAttemptSummary(DictationModel):
    """Owned recovery catalogue metadata, with no transcript or source disclosure."""

    attempt_id: UUID
    status: DictationStatus
    language: Language
    created_at: datetime
    expires_at: datetime
    audio_expires_at: datetime
    audio_available: bool
    has_correction: bool


class DictationAttemptIdentity(DictationModel):
    """Private server record; never accepted as a browser-supplied request."""

    owner: StrictStr = Field(min_length=1, max_length=256, repr=False)
    attempt_id: UUID
    source_digest: Digest
    profile_digest: Digest
    language: Language


def decide_attempt(
    existing: DictationAttemptIdentity | None,
    incoming: DictationAttemptIdentity,
) -> Literal["dispatch", "replay", "refuse"]:
    """Compare within an atomic store claim, never authorize an effect by itself.

    Every retained state, even unknown, may only replay. A missing record is
    eligible only if the service also establishes that the identifier is fresh
    (not expired/deleted). Tombstone/epoch admission belongs to the store.
    """
    if existing is None:
        return "dispatch"
    return "replay" if existing == incoming else "refuse"


def decode_audio(request: DictationRequest) -> bytes:
    """Decode exact base64 and validate ADR 37's canonical PCM subset, purely.

    HTTP acquisition must be bounded before JSON decoding. This computes no
    custody claim and retains no bytes. The transport reruns Echo inspection.
    """
    try:
        content = base64.b64decode(request.audio_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        msg = "invalid_audio"
        raise DictationError(msg) from exc
    if len(content) > MAX_AUDIO_BYTES or len(content) < _HEADER_BYTES:
        msg = "invalid_audio"
        raise DictationError(msg)
    if base64.b64encode(content).decode("ascii") != request.audio_base64:
        msg = "invalid_audio"
        raise DictationError(msg)
    size = len(content) - _HEADER_BYTES
    if size % _SAMPLE_WIDTH or not 1 <= size // _SAMPLE_WIDTH <= MAX_AUDIO_FRAMES:
        msg = "invalid_audio"
        raise DictationError(msg)
    expected = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        len(content) - 8,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        _SAMPLE_RATE,
        _SAMPLE_RATE * _SAMPLE_WIDTH,
        _SAMPLE_WIDTH,
        16,
        b"data",
        size,
    )
    if content[:_HEADER_BYTES] != expected:
        msg = "invalid_audio"
        raise DictationError(msg)
    return content


def validate_text(text: str) -> None:
    """Preserve text verbatim while refusing invalid Unicode and control bytes."""
    try:
        text.encode("utf-8")
    except UnicodeError as exc:
        msg = "Invalid transcript text."
        raise ValueError(msg) from exc
    if len(text) > MAX_TEXT_CHARS or any(ord(char) < _CONTROL_CHAR_LIMIT and char not in "\n\r\t" for char in text):
        msg = "Invalid transcript text."
        raise ValueError(msg)


class DictationCorrectionRequest(DictationModel):
    """Explicit private text edit; source/original/owner are loaded by the server."""

    attempt_id: UUID
    final_text: StrictStr = Field(max_length=MAX_TEXT_CHARS, repr=False)

    @field_validator("final_text")
    @classmethod
    def bounded_final(cls, value: str) -> str:
        validate_text(value)
        return value


class DictationCorrection(DictationModel):
    """One latest private correction per attempt; never a training example grant."""

    attempt_id: UUID
    source_digest: Digest
    profile_digest: Digest
    language: Language
    original_text: StrictStr = Field(max_length=MAX_TEXT_CHARS, repr=False)
    final_text: StrictStr = Field(max_length=MAX_TEXT_CHARS, repr=False)
    created_at: datetime
    expires_at: datetime

    @field_validator("original_text", "final_text")
    @classmethod
    def bounded_text(cls, value: str) -> str:
        validate_text(value)
        return value

    @model_validator(mode="after")
    def bounded_retention(self) -> Self:
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            msg = "Correction retention requires timezone-aware timestamps."
            raise ValueError(msg)
        if not 0 < (self.expires_at - self.created_at).total_seconds() <= MAX_RETENTION_SECONDS:
            msg = "Correction retention must be positive and at most thirty days."
            raise ValueError(msg)
        return self


class DictationLexiconRuleRequest(DictationModel):
    """Explicit language-scoped suggestion, separate from corrections and training."""

    language: Language
    heard: StrictStr = Field(min_length=1, max_length=128)
    replacement: StrictStr = Field(min_length=1, max_length=128)
    approved: Literal[True]

    @field_validator("heard", "replacement")
    @classmethod
    def bounded_phrase(cls, value: str) -> str:
        validate_text(value)
        if not value.strip():
            msg = "Vocabulary phrases must not be blank."
            raise ValueError(msg)
        return value


def validate_new_attempt_time(attempt_id: UUID, now: datetime) -> None:
    """Refuse absent IDs unless UUIDv7 time is within five minutes, +30s skew.

    Call only for an absent ID, after owned retained-result/tombstone lookup.
    Retained exact attempts replay regardless of age. Deletion must preserve a
    refusal tombstone until this admission window has closed. Caller supplies
    current server time; the UUID timestamp never authenticates a principal.
    """
    if now.tzinfo is None:
        msg = "Attempt admission requires timezone-aware server time."
        raise ValueError(msg)
    if attempt_id.version != 7:  # noqa: PLR2004 - exact UUID version contract
        msg_0 = "expired"
        raise DictationError(msg_0)
    timestamp_ms = attempt_id.int >> 80
    age_ms = now.timestamp() * 1000 - timestamp_ms
    if not -30_000 <= age_ms <= 300_000:  # noqa: PLR2004 - admission window and clock skew
        msg_0 = "expired"
        raise DictationError(msg_0)
