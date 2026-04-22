from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field

from lychd.system.constants import PATH_RUNES_DIR


class RuneConfig(BaseModel, ABC):
    """Base class for TOML-backed rune schemas.

    Contract:
    - Subclassing is the registration mechanism (no procedural registration API).
    - One TOML file equals one instance.
    - Instance payload lives at the TOML top level (path selects schema ownership).
    - ``relative_path`` is rooted at ``~/.config/lychd/runes``.
    """

    model_config = ConfigDict(extra="forbid")

    config_root: ClassVar[Path] = PATH_RUNES_DIR
    """Absolute root for all rune schema directories."""

    relative_path: ClassVar[Path | None] = None
    """Path relative to ``config_root``. ``None`` means top-level root file."""

    singleton: ClassVar[bool | None] = None
    """Optional singleton override.

    ``None`` means auto inference via :meth:`effective_singleton`.
    ``True``/``False`` force behavior when a schema must deviate from topology defaults
    (for example, a leaf schema that should still be singleton).
    """

    file_name: Path | None = Field(default=None, exclude=True, repr=False)
    """Absolute source TOML file for this instance."""

    @classmethod
    def anchor_dir(cls) -> Path:
        """Return the absolute anchor directory for this schema."""
        if cls.relative_path is None:
            return cls.config_root
        return cls.config_root / cls.relative_path

    @classmethod
    def effective_singleton(cls) -> bool:
        """Resolve the runtime singleton policy for loader behavior.

        Auto inference:
        - Explicit ``singleton`` always wins.
        - Top-level schemas (``relative_path is None``) are singleton.
        - Non-leaf schemas are singleton.
        - Leaf schemas are multi-instance by default.

        Callers should use this method instead of reading ``singleton`` directly.
        """
        if cls.singleton is not None:
            return cls.singleton

        if cls.relative_path is None:
            return True

        return bool(cls.__subclasses__())

    @classmethod
    def default_file_name(cls) -> str:
        """Return a default filename for sample generation."""
        return f"{cls.__name__.lower()}.toml"

    @classmethod
    def instance_id_from_path(cls, file_path: Path, *, root: Path | None = None) -> str:
        """Return stable identity from full path relative to runes root."""
        rel = file_path.relative_to(root or cls.config_root)
        return str(rel.with_suffix(""))

    def with_file_name(self, file_name: Path) -> Self:
        """Return a copy of the instance bound to a source filename."""
        return self.model_copy(update={"file_name": file_name})
