"""Explicit same-host structural snapshot selection; no directory discovery."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict, Field, field_validator, model_validator

from lychd.config.settings.section import SettingsSection
from lychd.domain.oculus.models import MAX_SOURCES, ObservationSourceSelection


class SnapshotSourceSettings(ObservationSourceSelection):
    """Select one private directory containing the replaceable snapshot.json file."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=False, hide_input_in_errors=True)
    path: Path

    @field_validator("path")
    @classmethod
    def absolute_path(cls, value: Path) -> Path:
        if not value.is_absolute() or ".." in value.parts:
            msg = "Observation source paths must be explicit absolute directories."
            raise ValueError(msg)
        return value


class ObservabilitySettings(SettingsSection):
    """Only selected metadata sources enter Orb and Loom; none start services."""

    sources: tuple[SnapshotSourceSettings, ...] = Field(default=(), max_length=MAX_SOURCES)

    @model_validator(mode="after")
    def distinct_sources(self) -> ObservabilitySettings:
        if len({source.source_id for source in self.sources}) != len(self.sources) or len(
            {source.path for source in self.sources}
        ) != len(self.sources):
            msg = "Observation sources require distinct identities and custody paths."
            raise ValueError(msg)
        return self
