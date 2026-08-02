from __future__ import annotations

import re
from abc import ABC
from pathlib import Path
from re import Pattern
from typing import Any, ClassVar, Final, Self

from pydantic import BaseModel, ConfigDict, PrivateAttr

# Shared grammar for one rune path segment. Keep this module-level so every
# runtime schema uses the same non-overridable path rule.
RUNE_PATH_PART_PATTERN: Final[Pattern[str]] = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,48}[a-z0-9])?$")


class RuneConfig(BaseModel, ABC):
    """Base for TOML-backed Codex runes. Frozen.

    A rune is one validated TOML config document under
    ``lychd.system.constants.PATH_RUNES_DIR``. Subclasses define TOML fields;
    this base validates class-level placement metadata. Leaf ownership is
    resolved when binding a source file, after import has revealed the subclass
    topology.

    ``RuneConfig`` does not import or discover extensions. Enabled extensions
    expose their rune subclasses through extension registration stores, usually from a
    ``register(context)`` shim that calls ``context.runes.add_schema(...)``.
    The Codex loader then receives the assembled schema list explicitly and
    remains only responsible for filesystem-backed TOML validation.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

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

        # The fragment is a single relative ``Path`` segment. Python inheritance
        # owns ancestry; one class must not smuggle multiple directories.
        # Loader/writer code owns the absolute root via ``PATH_RUNES_DIR``.
        if not isinstance(path_fragment, Path):
            msg = f"Rune '{cls.__name__}' declares non-Path path_fragment {path_fragment!r}."
            raise TypeError(msg)
        if path_fragment.is_absolute() or path_fragment == Path():
            msg = f"Rune '{cls.__name__}' declares invalid path_fragment '{path_fragment}'. Expected relative path fragment."
            raise ValueError(msg)
        if len(path_fragment.parts) != 1:
            msg = (
                f"Rune '{cls.__name__}' declares multi-part path_fragment '{path_fragment}'. Expected one path segment."
            )
            raise ValueError(msg)

        # The pattern rejects traversal, uppercase drift, spaces, and
        # filesystem-looking surprises.
        part = path_fragment.parts[0]
        if not RUNE_PATH_PART_PATTERN.fullmatch(part):
            pattern = RUNE_PATH_PART_PATTERN.pattern
            msg = f"Rune '{cls.__name__}' declares invalid path_fragment part '{part}'. Expected pattern: {pattern}"
            raise ValueError(msg)

        # The final path is a single parent chain plus this suffix. Multiple
        # RuneConfig parents would make that path ambiguous. Mixins that only
        # share fields should inherit BaseModel or object, not RuneConfig.
        rune_parents = [base for base in cls.__bases__ if issubclass(base, RuneConfig) and base is not RuneConfig]
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

    sample_template: ClassVar[str | None] = None
    """Optional complete sample TOML template used by ``ConfigWriter``."""

    _source_file: Path | None = PrivateAttr(default=None)

    @classmethod
    def anchor_dir(cls, runes_dir: Path) -> Path:
        """Resolve this rune class's anchor under an active rune root.

        Args:
            runes_dir: Active root directory for rune TOML files.

        Returns:
            Absolute or caller-root-relative anchor directory for this class.

        """
        return runes_dir / cls.relative_path

    @property
    def source_file(self) -> Path | None:
        """Absolute source TOML file that produced this validated instance."""
        return self._source_file

    def bind_source_file(self, source_file: Path) -> Self:
        """Bind filesystem provenance after TOML validation.

        Source binding turns a validated schema instance into a concrete
        file-backed rune. Branch ownership belongs to the loader's exact admitted
        schema generation; unrelated imported subclasses cannot alter this record.

        Args:
            source_file: Absolute TOML file path that produced this instance.

        Returns:
            This rune instance, with source provenance bound.

        Raises:
            ValueError: If this instance is already bound to another source.

        """
        if self._source_file is not None and self._source_file != source_file:
            msg = f"Rune source_file already bound to '{self._source_file}'."
            raise ValueError(msg)
        self._source_file = source_file
        return self
