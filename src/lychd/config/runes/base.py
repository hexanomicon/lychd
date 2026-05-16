from __future__ import annotations

import re
from abc import ABC
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

RUNE_PATH_PART_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,48}[a-z0-9])?$")


class RuneConfig(BaseModel, ABC):
    """Base for TOML-backed Codex runes.

    A rune is one validated TOML config document under
    ``lychd.system.constants.PATH_RUNES_DIR``. Subclasses define TOML fields;
    this base validates class-level placement metadata.
    """

    model_config = ConfigDict(extra="forbid")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Validate rune class metadata when a rune subclass is declared.

        Args:
            **kwargs: Extra subclass initialization keywords forwarded to
                ``BaseModel``.

        Raises:
            ValueError: If the subclass declares an invalid ``path_fragment``.
            TypeError: If ``path_fragment`` is not a ``Path`` or rune ancestry
                is ambiguous.

        """
        super().__init_subclass__(**kwargs)

        # ``ClassVar`` values are inherited. ``getattr(cls, "path_fragment")``
        # would therefore let a child silently reuse its parent suffix, producing
        # the wrong anchor. Require a class-local declaration instead.
        if "path_fragment" not in cls.__dict__:
            msg = f"Rune '{cls.__name__}' declares no path_fragment."
            raise ValueError(msg)
        path_fragment: Any = cls.__dict__["path_fragment"]

        # The fragment is a relative ``Path`` suffix, not a filesystem root.
        # Loader/writer code owns the absolute root via ``PATH_RUNES_DIR``.
        if not isinstance(path_fragment, Path):
            msg = f"Rune '{cls.__name__}' declares non-Path path_fragment {path_fragment!r}."
            raise TypeError(msg)
        if path_fragment.is_absolute() or path_fragment == Path():
            msg = f"Rune '{cls.__name__}' declares invalid path_fragment '{path_fragment}'. Expected relative path fragment."
            raise ValueError(msg)

        # Validate every fragment part because a fragment may contain more than
        # one suffix component. The pattern rejects traversal, uppercase drift,
        # spaces, and filesystem-looking surprises.
        for part in path_fragment.parts:
            if not RUNE_PATH_PART_PATTERN.fullmatch(part):
                pattern = RUNE_PATH_PART_PATTERN.pattern
                msg = f"Rune '{cls.__name__}' declares invalid path_fragment part '{part}'. Expected pattern: {pattern}"
                raise ValueError(msg)

        # The final path is a single parent chain plus this suffix. Multiple
        # RuneConfig parents would make that path ambiguous. Mixins that only
        # share fields should inherit BaseModel or object, not RuneConfig.
        rune_parents = [
            base for base in cls.__bases__ if issubclass(base, RuneConfig) and base is not RuneConfig
        ]
        if len(rune_parents) > 1:
            names = ", ".join(parent.__name__ for parent in rune_parents)
            msg = f"Rune '{cls.__name__}' declares multiple rune parents: {names}."
            raise TypeError(msg)
        parent = rune_parents[0] if rune_parents else None

        # Store the final path under PATH_RUNES_DIR, still relative. RuneConfig
        # computes schema-local placement; loaders/writers choose the root.
        cls.relative_path = path_fragment if parent is None else parent.relative_path / path_fragment

    path_fragment: ClassVar[Path]
    """Relative suffix appended after the parent rune class's ``relative_path``."""

    relative_path: ClassVar[Path]
    """Computed path under ``PATH_RUNES_DIR`` where this class's TOMLs live."""

    source_file: Path | None = Field(default=None, exclude=True, repr=False)
    """Absolute source TOML file that produced this validated instance."""
