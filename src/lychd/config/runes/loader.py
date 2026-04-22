from __future__ import annotations

import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import structlog

from lychd.config.runes.base import RuneConfig

logger = structlog.get_logger()


class RuneConfigError(ValueError):
    """Raised when rune configuration violates structural contracts."""


class ConfigLoader:
    """Validation loader for explicit RuneConfig schemas."""

    def __init__(self, runes_dir: Path | None = None) -> None:
        """Create a loader for runes under a specific root."""
        self._runes_dir = runes_dir or RuneConfig.config_root

    def load_all(self, schemas: Sequence[type[RuneConfig]]) -> list[RuneConfig]:
        """Load and validate all rune instances for explicit schema classes."""
        loaded: list[RuneConfig] = []

        for cls in schemas:
            loaded.extend(self._load_class_instances(cls))

        logger.debug("runes_loaded", count=len(loaded), classes=[c.__name__ for c in schemas])
        return loaded

    def _load_class_instances(self, cls: type[RuneConfig]) -> list[RuneConfig]:
        files = self._candidate_files(cls)
        instances: list[RuneConfig] = []

        for file_path in files:
            payload = self._read_payload(file_path, cls)
            instance = cls.model_validate(payload).with_file_name(file_path)
            instances.append(instance)

        if cls.effective_singleton() and len(instances) > 1:
            msg = f"Schema '{cls.__name__}' is singleton but found {len(instances)} files in '{cls.anchor_dir()}'."
            raise RuneConfigError(msg)

        self._assert_unique_identity(cls, files)
        return instances

    def _candidate_files(self, cls: type[RuneConfig]) -> list[Path]:
        if cls.relative_path is None:
            singleton_path = self._runes_dir / cls.default_file_name()
            return [singleton_path] if singleton_path.exists() else []

        anchor = self._runes_dir / cls.relative_path
        if not anchor.exists():
            return []

        files = sorted(anchor.rglob("*.toml"))
        if not files:
            return []

        # Parent schemas do not sweep child anchors.
        child_anchors = [self._runes_dir / rel for rel in self._descendant_relative_paths(cls)]
        if not child_anchors:
            return files

        return [path for path in files if not any(path.is_relative_to(child) for child in child_anchors)]

    def _descendant_relative_paths(self, cls: type[RuneConfig]) -> set[Path]:
        paths: set[Path] = set()
        for sub in cls.__subclasses__():
            if sub.relative_path is not None:
                paths.add(sub.relative_path)
            paths.update(self._descendant_relative_paths(sub))
        return paths

    def _read_payload(self, file_path: Path, cls: type[RuneConfig]) -> dict[str, Any]:
        try:
            parsed = tomllib.loads(file_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            msg = f"Malformed TOML in '{file_path}'."
            raise RuneConfigError(msg) from exc
        except OSError as exc:
            msg = f"Could not read '{file_path}'."
            raise RuneConfigError(msg) from exc

        content: dict[str, Any] = {str(k): v for k, v in parsed.items()}
        if "model" in content and isinstance(content["model"], dict) and "model" not in cls.model_fields:
            msg = (
                f"File '{file_path}' uses legacy '[model]' envelope syntax. "
                "Rune payload must be written at TOML top level."
            )
            raise RuneConfigError(msg)

        return content

    def _assert_unique_identity(self, cls: type[RuneConfig], files: list[Path]) -> None:
        seen: set[str] = set()

        for file_path in files:
            identity = cls.instance_id_from_path(file_path, root=self._runes_dir)
            if identity in seen:
                msg = f"Duplicate identity detected: '{identity}'."
                raise RuneConfigError(msg)
            seen.add(identity)
