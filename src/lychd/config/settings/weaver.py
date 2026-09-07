"""Bounded selection of the source-registered Core Bridge casting."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from lychd.config.settings.section import SettingsSection


class BridgeCastingSettings(SettingsSection):
    """Select the configured Bridge revision and one exact capability identity."""

    revision: Literal["2"]
    """The exact registered Bridge revision supporting a persisted capability binding."""
    capability_key: str = Field(min_length=1)
    """The exact animator:family:model capability key, never a model alias or pool."""

    @field_validator("capability_key")
    @classmethod
    def _require_exact_capability_key(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            msg = "Bridge capability_key must be nonblank and have no surrounding whitespace."
            raise ValueError(msg)
        return value


class WeaverSettings(SettingsSection):
    """Opt-in casting configuration; omission preserves the legacy Bridge route."""

    bridge: BridgeCastingSettings | None = None
    """Select bridge_chat@2; omitted configuration keeps bridge_chat@1 active."""
