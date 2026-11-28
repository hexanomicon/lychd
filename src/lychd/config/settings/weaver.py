"""Bounded selection of source-registered Bridge and delegated castings."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, ConfigDict, Field, field_validator, model_validator

from lychd.config.settings.section import SettingsSection
from lychd.domain.archive import ArchiveProfile
from lychd.domain.cortex.bridge_preference import BridgePreference
from lychd.domain.cortex.semantic_answer import SemanticAnswerSelection
from lychd.domain.delegation.routing import DelegatedRuntimeBinding
from lychd.domain.webcrawler.feed import WebcrawlerFeedProfile
from lychd.domain.webcrawler.profile import WebcrawlerProfile


class BridgeCastingSettings(SettingsSection):
    """Select exact Bridge execution, optionally ranked once at revision-2 admission."""

    revision: Literal["2", "3", "4", "5"]
    """The exact registered Bridge revision supporting a persisted capability binding."""
    capability_key: str | None = Field(default=None, min_length=1)
    """The exact animator:family:model capability key, never a model alias or pool."""
    preference: BridgePreference | None = None
    """Revision-2-only bounded local Chat preference; execution retains one exact key."""
    archive: ArchiveProfile | None = None
    """Mandatory exact public-note binding for the read-only revision 3."""
    webcrawler: WebcrawlerProfile | None = Field(default=None, validation_alias=AliasChoices("webcrawler", "scout"))
    """Mandatory explicit public-page profile for revision 4 only."""

    semantic: SemanticAnswerSelection | None = None
    """Mandatory explicit threshold and bounds for revision 5 only."""

    @model_validator(mode="after")
    def _require_archive_binding(self) -> BridgeCastingSettings:
        if self.revision == "2":
            if (self.capability_key is None) == (self.preference is None):
                msg = "Bridge revision 2 requires capability_key XOR preference."
                raise ValueError(msg)
        elif self.capability_key is None or self.preference is not None:
            msg = "Bridge revisions 3, 4 and 5 require capability_key and reject preference."
            raise ValueError(msg)
        if (self.revision == "3") != (self.archive is not None):
            msg = "Bridge revision 3 requires archive; revision 2 does not accept it."
            raise ValueError(msg)
        if (self.revision == "4") != (self.webcrawler is not None):
            msg = "Bridge revision 4 requires webcrawler; other revisions do not accept it."
            raise ValueError(msg)
        if (self.revision == "5") != (self.semantic is not None):
            msg = "Bridge revision 5 requires semantic; other revisions do not accept it."
            raise ValueError(msg)
        return self

    @field_validator("capability_key")
    @classmethod
    def _require_exact_capability_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
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


class ScavengerCastingSettings(SettingsSection):
    """Opt into one exact model-free finite observation and native feed binding."""

    revision: Literal["3"]
    webcrawler: WebcrawlerFeedProfile = Field(validation_alias=AliasChoices("webcrawler", "scout"))


class WeaverSettings(SettingsSection):
    """Opt-in casting configuration; omission preserves each legacy route."""

    scavenger: ScavengerCastingSettings | None = None
    """Select scavenger.observe_market@2; omission disables new observation admission."""

    creation: CreationCastingSettings | None = None
    """Select creation.investigate@2; omission disables investigation admission."""

    delegation: DelegationCastingSettings | None = None
    """Select one exact runtime for delegated_rite@2; omission preserves reference-only @1."""

    bridge: BridgeCastingSettings | None = None
    """Select an exact Bridge revision; omission keeps bridge_chat@1 active."""

    @model_validator(mode="after")
    def _one_webcrawler_binding(self) -> WeaverSettings:
        if self.scavenger is not None and self.bridge is not None and self.bridge.webcrawler is not None:
            message = "The first native profile permits one active Webcrawler binding, not page/feed coexistence."
            raise ValueError(message)
        return self
