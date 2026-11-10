"""Closed public host-operation intent; secret values never enter these DTOs."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lychd.domain.tether.models import AttachmentAdmission, OfferedPeer, TetherRune

MAX_DOCUMENT_BYTES = 1024 * 1024
DEFAULT_OWNER_WEB_PORT = 7134


class TetherError(RuntimeError):
    """A bounded host refusal that never renders input or secret material."""


class TetherIntent(BaseModel):
    """One original public topology and initial admission request."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, populate_by_name=False)

    schema_name: Literal["lychd.tether.intent"] = Field(default="lychd.tether.intent", alias="schema")
    version: Literal[1] = 1
    rune: TetherRune
    offered_peers: tuple[OfferedPeer, ...] = Field(default=(), max_length=128)
    attachments: tuple[AttachmentAdmission, ...] = Field(default=(), max_length=32)
    web_port: int = Field(default=DEFAULT_OWNER_WEB_PORT, strict=True, ge=1, le=65535)

    @field_validator("rune")
    @classmethod
    def immutable_image(cls, value: TetherRune) -> TetherRune:
        """Refuse a moving image before original initialization creates any files."""
        if re.fullmatch(r"[a-z0-9._:/-]+@sha256:[0-9a-f]{64}", value.quadlet.image) is None:
            message = "Native Tether intent requires an immutable OCI image digest"
            raise ValueError(message)
        return value

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        """Reject a boolean masquerading as protocol version one."""
        if type(value) is not int:
            message = "Tether intent version must be an integer"
            raise ValueError(message)
        return value


def canonical_bytes(value: object) -> bytes:
    """Encode bounded canonical JSON without non-finite numbers or implicit objects."""
    try:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json", by_alias=True)
        result = (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n"
        ).encode("ascii")
        if len(result) > MAX_DOCUMENT_BYTES:
            msg = "Tether document exceeds its bound"
            raise TetherError(msg)
    except (ValueError, TypeError, OverflowError, RecursionError):
        msg = "Tether document cannot be encoded"
        raise TetherError(msg) from None
    return result


def digest(value: object) -> str:
    """Identify canonical public intent independently of live filesystem identity."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_intent(path: Path) -> TetherIntent:
    """Load private public-intent input through the descriptor-safe custody boundary."""
    from lychd.system.services.tether.custody import load_intent as read_intent

    return read_intent(path)
