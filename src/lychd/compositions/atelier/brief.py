"""The public, text-only commission a colleague may submit for review."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_UTC_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)")
_MAX_WIRE_BYTES = 8192


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    values: dict[str, object] = {}
    for name, value in pairs:
        if name in values:
            msg = "Duplicate brief field."
            raise ValueError(msg)
        values[name] = value
    return values


class ShortVideoBrief(BaseModel):
    """A requested finish. Admission creates no model or rendering effect."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    recipe: Literal["illustrated-story", "animated-lesson", "captioned-excerpt"]
    script: str = Field(min_length=1, max_length=8000)
    duration_seconds: int = Field(ge=1, le=180)
    not_before: datetime | None = Field(default=None, exclude_if=lambda value: value is None)
    latest_start_at: datetime | None = Field(default=None, exclude_if=lambda value: value is None)

    @classmethod
    def from_wire(cls, text: object) -> Self:
        """Decode the bounded foreign JSON text before interpreting its fields."""
        if not isinstance(text, str) or len(text) > _MAX_WIRE_BYTES or len(text.encode("utf-8")) > _MAX_WIRE_BYTES:
            msg = "Brief exceeds its wire limit."
            raise ValueError(msg)
        try:
            value: object = json.loads(text, object_pairs_hook=_unique_fields)
        except RecursionError:
            msg = "Invalid brief JSON depth."
            raise ValueError(msg) from None
        return cls.model_validate(value)

    @field_validator("not_before", "latest_start_at", mode="before")
    @classmethod
    def utc_timestamp(cls, value: object) -> datetime:
        if not isinstance(value, str) or not _UTC_TIMESTAMP.fullmatch(value):
            msg = "A UTC timestamp with seconds is required."
            raise ValueError(msg)
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            msg = "Invalid UTC timestamp."
            raise ValueError(msg) from None

    @model_validator(mode="after")
    def paired_window(self) -> Self:
        if self.not_before is None and self.latest_start_at is None:
            return self
        if self.not_before is None or self.latest_start_at is None or self.latest_start_at <= self.not_before:
            msg = "A start window needs both UTC bounds in ascending order."
            raise ValueError(msg)
        return self

    def can_start(self, now: datetime) -> bool:
        """Allow a first start at the opening instant and strictly before the closing instant."""
        if now.utcoffset() is None:
            msg = "A timezone-aware clock is required."
            raise ValueError(msg)
        if self.not_before is None or self.latest_start_at is None:
            return True
        return self.not_before <= now < self.latest_start_at

    @field_validator("script")
    @classmethod
    def substantive_script(cls, text: str) -> str:
        if not text.strip():
            msg = "The commission needs a script."
            raise ValueError(msg)
        return text
