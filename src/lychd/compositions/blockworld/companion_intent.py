"""Closed local interpretation profile and immutable, original instruction custody."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Literal, cast
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lychd.domain.artifacts import ArtifactRef


def validate_raw_instruction(text: str) -> str:
    """Refuse unsafe framing and malformed strict commands before interpretation.

    The narrow interpreter cannot select identities, coordinates, weather or clocks.
    Weather/clock wording anywhere, and exact movement, gaze and chat heads, stay with
    deterministic admission even when malformed.
    """
    value = text.strip()
    reserved = {
        "weather",
        "počasie",
        "pocasie",
        "počasí",
        "pocasi",
        "daj",
        "nastav",
        "spusti",
        "spusť",
        "spust",
        "clear",
        "make",
        "prepni",
        "přepni",
        "toggle",
        "set",
        "look",
        "pozri",
        "podívej",
        "goto",
        "choď",
        "chod",
        "jdi",
        "say",
        "povedz",
        "řekni",
        "state",
        "stav",
        "idle",
        "čakaj",
        "cakaj",
        "čekej",
        "cekej",
        "oddychuj",
        "odpočívej",
    }
    parts = value.casefold().split(maxsplit=1)
    original_head = parts[0] if parts else ""
    head = "".join(char for char in original_head if unicodedata.category(char)[0] in {"L", "M"})
    if (
        not value
        or len(text) > 1000  # noqa: PLR2004 - original companion instruction bound
        or len(text.encode("utf-8")) > 4096  # noqa: PLR2004 - bounded instruction payload
        or any(unicodedata.category(char) == "Cc" or char.isdigit() for char in text)
        or re.search(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", text) is not None
        or "/" in text
        or ":" in text
        or re.search(
            r"\b(?:weather|počasie|pocasie|počasí|pocasi|time|čas|cas|day|night|deň|den|noc)\b",
            value,
            flags=re.IGNORECASE,
        )
        is not None
        or head in reserved
        or (
            head in {"follow", "nasleduj", "následuj"}
            and value.casefold() not in {"follow me", "nasleduj ma", "následuj mě", "nasleduj me"}
        )
    ):
        msg = "Instruction is outside the bounded interpretation input."
        raise ValueError(msg)
    return text


class CompanionIntentProfile(BaseModel):
    """One explicit local model, with no discovery, fallback or runtime authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)
    version: Literal[1] = 1
    base_url: str
    model_id: str = Field(min_length=1, max_length=256)
    context_tokens: int = Field(default=4096, ge=1024, le=8192)
    max_tokens: int = Field(default=512, ge=1, le=512)
    inference_timeout_s: float = Field(default=15.0, ge=0.1, le=15)
    max_requests: int = Field(default=16, ge=1, le=32)

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int or value != 1:
            msg = "Intent profile version requires original integer 1."
            raise ValueError(msg)
        return value

    @field_validator("base_url")
    @classmethod
    def literal_endpoint(cls, value: str) -> str:
        target = urlsplit(value)
        if (
            target.scheme != "http"
            or target.hostname not in {"127.0.0.1", "::1"}
            or target.port is None
            or not 1 <= target.port <= 65535  # noqa: PLR2004 - TCP port range
            or target.username is not None
            or target.password is not None
            or target.query
            or target.fragment
            or target.path != "/v1"
            or value != value.strip()
            or not value.isprintable()
            or target.netloc != (f"[::1]:{target.port}" if target.hostname == "::1" else f"127.0.0.1:{target.port}")
            or value != f"http://{target.netloc}/v1"
        ):
            msg = "Intent endpoint requires literal loopback HTTP, explicit port and exact /v1."
            raise ValueError(msg)
        return value

    @field_validator("model_id")
    @classmethod
    def exact_model(cls, value: str) -> str:
        if value != value.strip() or not value.isprintable():
            msg = "Intent model id must be an exact printable identity."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def input_capacity(self) -> CompanionIntentProfile:
        if self.max_tokens >= self.context_tokens:
            msg = "Intent profile must reserve finite input capacity."
            raise ValueError(msg)
        return self

    @property
    def digest(self) -> str:
        document = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return "sha256:" + hashlib.sha256(document.encode()).hexdigest()

    @property
    def capability_key(self) -> str:
        return f"companion-intent:chat:{self.model_id}"


class CompanionInstruction(BaseModel):
    """Capture once before asynchronous work; a proposal cannot renew this envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)
    kind: Literal["raw_instruction"] = "raw_instruction"
    request_id: str
    original_text: str = Field(min_length=1, max_length=1000)
    source: Literal["text", "transcript"] = "text"
    language: Literal["sk", "cs", "en"] = "en"
    generation: int = Field(ge=0)
    target_id: str | None
    source_artifacts: tuple[ArtifactRef, ...] = Field(default=(), max_length=4)
    profile_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expires_at_ms: int = Field(gt=0)

    @field_validator("source_artifacts", mode="before")
    @classmethod
    def artifact_sequence(cls, value: object) -> object:
        return tuple(cast("list[object]", value)) if isinstance(value, list) else value

    @field_validator("request_id", "target_id")
    @classmethod
    def canonical_identity(cls, value: str | None) -> str | None:
        if value is not None and str(UUID(value)) != value:
            msg = "Instruction identity must be a canonical UUID."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def eligible(self) -> CompanionInstruction:
        validate_raw_instruction(self.instruction)
        return self

    @property
    def instruction(self) -> str:
        return self.original_text.strip(" \t\r\n") if self.source == "transcript" else self.original_text


def load_intent_profile(document: str | bytes) -> CompanionIntentProfile:
    """Decode the closed profile with the companion's duplicate/nonfinite refusal."""
    from lychd.compositions.blockworld.companion import strict_json

    return CompanionIntentProfile.model_validate(strict_json(document))


def revalidate_intent_profile(profile: CompanionIntentProfile) -> CompanionIntentProfile:
    """Detach and validate supplied instances; model_copy is not trusted validation."""
    return CompanionIntentProfile.model_validate(profile.model_dump(mode="python", warnings=False))
