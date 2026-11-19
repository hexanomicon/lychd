"""Explicit local exchange folders for privately paired Nexus colleagues."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from lychd.config.settings.section import SettingsSection


class PresencePair(SettingsSection):
    """One local label, private key reference and two-slot replicated directory."""

    name: Annotated[str, Field(min_length=1, max_length=64)]
    slot: Literal["a", "b"]
    directory: Path
    key_file: Path

    @field_validator("name")
    @classmethod
    def visible_name(cls, value: str) -> str:
        if value != value.strip() or not value.isprintable():
            msg = "Peer names must be printable and trimmed."
            raise ValueError(msg)
        return value

    @field_validator("directory", "key_file")
    @classmethod
    def local_path(cls, value: Path) -> Path:
        if not value.is_absolute() or ".." in value.parts or not value.name:
            msg = "Presence paths must be explicit absolute local paths."
            raise ValueError(msg)
        return value


class PresenceSettings(SettingsSection):
    """A finite audience. Omission disables all file access and publication."""

    pairs: tuple[PresencePair, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def distinct_pairs(self) -> Self:
        names = {pair.name.casefold() for pair in self.pairs}
        dirs = {pair.directory for pair in self.pairs}
        if len(names) != len(self.pairs) or len(dirs) != len(self.pairs):
            msg = "Each presence pair needs a distinct label and directory."
            raise ValueError(msg)
        if any(
            pair.key_file.is_relative_to(root) or root in pair.directory.parents for root in dirs for pair in self.pairs
        ):
            msg = "Pair folders must be disjoint and keys must stay outside every exchange folder."
            raise ValueError(msg)
        return self
