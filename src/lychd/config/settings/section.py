"""Strict Pydantic section base shared by settings ownership modules."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SettingsSection(BaseModel):
    """A strict configuration section; misspellings are startup errors."""

    # A misspelled operator setting must fail at startup, never be silently ignored.
    # Bare string literals immediately after fields become Pydantic schema descriptions.
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)
