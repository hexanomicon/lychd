"""Settings that explicitly select optional runtime extensions."""

from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import Field, ValidationInfo, field_validator

from lychd.config.settings.section import SettingsSection
from lychd.extensions.builtin.catalog import BUILTIN_EXTENSIONS


class ExtensionSettings(SettingsSection):
    """Explicit optional extensions; each extension owns its own Rune schemas."""

    builtins: tuple[str, ...] = Field(default=())
    """Built-in extension IDs explicitly activated for this Vessel."""
    crypt: tuple[str, ...] = Field(default=())
    """Local Crypt extension IDs explicitly activated for this Vessel."""

    @field_validator("builtins", "crypt")
    @staticmethod
    def validate_ids(value: tuple[str, ...], info: ValidationInfo) -> tuple[str, ...]:
        """Validate safe, unique activation IDs without loading extension code.

        This checks only the settings-level grammar: an ID is a relative POSIX path
        with no traversal component, and it may appear once in its activation list.
        Built-in catalog membership is checked here because it is static and imports
        no extension code. Crypt ``register.py`` existence is checked later by
        ``ExtensionManager`` because that requires inspecting the local filesystem.
        """
        seen: set[str] = set()
        duplicates: set[str] = set()
        for extension_id in value:
            if extension_id in seen:
                duplicates.add(extension_id)
            seen.add(extension_id)
        if duplicates:
            msg = f"Extension activation list contains duplicate id(s): {', '.join(sorted(duplicates))}."
            raise ValueError(msg)
        for extension_id in value:
            path = PurePosixPath(extension_id)
            if path.is_absolute() or not path.parts or any(part in {".", ".."} for part in path.parts):
                msg = f"Invalid extension id {extension_id!r}."
                raise ValueError(msg)
        if info.field_name == "builtins":
            unknown = sorted(set(value).difference(BUILTIN_EXTENSIONS))
            if unknown:
                known = ", ".join(sorted(BUILTIN_EXTENSIONS))
                msg = f"Unknown built-in extension id(s): {', '.join(unknown)}. Known built-ins: {known}."
                raise ValueError(msg)
        return value
