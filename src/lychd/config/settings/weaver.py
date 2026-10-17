"""Bounded selection of source-registered Bridge and delegated castings."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from lychd.config.settings.section import SettingsSection
from lychd.domain.archive import ArchiveProfile
from lychd.domain.delegation.routing import DelegatedRuntimeBinding
from lychd.domain.scout.profile import ScoutProfile


class BridgeCastingSettings(SettingsSection):
    """Select the configured Bridge revision and one exact capability identity."""

    revision: Literal["2", "3", "4"]
    """The exact registered Bridge revision supporting a persisted capability binding."""
    capability_key: str = Field(min_length=1)
    """The exact animator:family:model capability key, never a model alias or pool."""
    archive: ArchiveProfile | None = None
    """Mandatory exact public-note binding for the read-only revision 3."""
    scout: ScoutProfile | None = None
    """Mandatory explicit public-page profile for revision 4 only."""

    @model_validator(mode="after")
    def _require_archive_binding(self) -> BridgeCastingSettings:
        if (self.revision == "3") != (self.archive is not None):
            msg = "Bridge revision 3 requires archive; revision 2 does not accept it."
            raise ValueError(msg)
        if (self.revision == "4") != (self.scout is not None):
            msg = "Bridge revision 4 requires scout; other revisions do not accept it."
            raise ValueError(msg)
        return self

    @field_validator("capability_key")
    @classmethod
    def _require_exact_capability_key(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            msg = "Bridge capability_key must be nonblank and have no surrounding whitespace."
            raise ValueError(msg)
        return value


class DelegationCastingSettings(DelegatedRuntimeBinding):
    """Opt into delegated_rite@2; registration never grants host execution authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    revision: Literal["2"]

    def binding(self) -> DelegatedRuntimeBinding:
        """Retain only the exact execution identity in the admitted Run."""
        return DelegatedRuntimeBinding(runtime=self.runtime, profile=self.profile)


class CreationCastingSettings(SettingsSection):
    """Opt into the exact bounded investigation revision and local capability."""

    revision: Literal["2"]
    capability_key: str = Field(min_length=1)


class WeaverSettings(SettingsSection):
    """Opt-in casting configuration; omission preserves each legacy route."""

    creation: CreationCastingSettings | None = None
    """Select creation.investigate@2; omission disables investigation admission."""

    delegation: DelegationCastingSettings | None = None
    """Select one exact runtime for delegated_rite@2; omission preserves reference-only @1."""

    bridge: BridgeCastingSettings | None = None
    """Select an exact Bridge revision; omission keeps bridge_chat@1 active."""
