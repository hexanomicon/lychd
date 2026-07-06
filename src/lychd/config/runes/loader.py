from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import structlog

from lychd.config.runes.base import RuneConfig
from lychd.config.runes.writer import SAMPLE_MARKER
from lychd.system.constants import PATH_RUNES_DIR

logger = structlog.get_logger()


class ConfigLoader:
    """Validation loader for explicit RuneConfig rune classes."""

    def __init__(self, runes_dir: Path | None = None) -> None:
        """Create a loader for a concrete rune root.

        Args:
            runes_dir: Optional root directory to scan. Defaults to
                ``PATH_RUNES_DIR``.

        """
        self._runes_dir = runes_dir or PATH_RUNES_DIR

    def load_all(self, schemas: list[type[RuneConfig]]) -> list[RuneConfig]:
        """Load and validate all instances for the provided rune classes.

        Args:
            schemas: Rune classes whose anchors should be scanned.

        Returns:
            Validated rune instances bound to their source filenames.

        Raises:
            ValueError: If TOML parsing, branch-file enforcement, identity
                validation, or Pydantic model validation fails.

        """
        loaded: list[RuneConfig] = []

        for cls in schemas:
            loaded.extend(self._load_class_instances(cls))

        logger.debug("runes_loaded", count=len(loaded), classes=[c.__name__ for c in schemas])
        return loaded

    def _load_class_instances(self, cls: type[RuneConfig]) -> list[RuneConfig]:
        """Load every TOML instance owned by one rune class.

        Args:
            cls: Rune class whose anchor should be scanned.

        Returns:
            Validated instances for ``cls``.

        Raises:
            ValueError: If a branch rune owns TOML files, or if payload/identity
                validation fails.

        """
        files = self._candidate_files(cls)
        if cls.__subclasses__():
            if files:
                msg = (
                    f"Branch rune class '{cls.__name__}' cannot own TOML files in '{cls.anchor_dir(self._runes_dir)}'."
                )
                raise ValueError(msg)
            return []

        instances: list[RuneConfig] = []

        for file_path in files:
            if self._is_generated_sample(file_path):
                logger.debug("skipping_sample_rune", schema=cls.__name__, path=str(file_path))
                continue
            payload = self._read_payload(file_path, cls)
            instance = cls.model_validate(payload).bind_source_file(file_path)
            instances.append(instance)

        self._assert_unique_identity(files)
        return instances

    def _candidate_files(self, cls: type[RuneConfig]) -> list[Path]:
        """Find candidate TOML files for a rune anchor.

        Args:
            cls: Rune class whose anchor should be scanned.

        Returns:
            Sorted TOML files directly in the rune class's anchor.

        """
        anchor = cls.anchor_dir(self._runes_dir)
        if not anchor.exists():
            return []

        return sorted(anchor.glob("*.toml"))

    def _is_generated_sample(self, file_path: Path) -> bool:
        """Return whether a TOML file is a generated inactive sample."""
        try:
            with file_path.open(encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    return stripped == SAMPLE_MARKER
        except OSError as exc:
            msg = f"Could not read '{file_path}'."
            raise ValueError(msg) from exc
        return False

    def _read_payload(self, file_path: Path, cls: type[RuneConfig]) -> dict[str, Any]:
        """Read one TOML payload and enforce rune envelope rules.

        Args:
            file_path: TOML file to read.
            cls: Rune class used to decide whether legacy envelope keys are
                allowed.

        Returns:
            Parsed TOML payload with string keys.

        Raises:
            ValueError: If the file is unreadable, malformed, or uses a legacy
                ``[model]`` envelope for a rune class that does not declare a
                ``model`` field.

        """
        try:
            parsed = tomllib.loads(file_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            msg = f"Malformed TOML in '{file_path}'."
            raise ValueError(msg) from exc
        except OSError as exc:
            msg = f"Could not read '{file_path}'."
            raise ValueError(msg) from exc

        content: dict[str, Any] = {str(k): v for k, v in parsed.items()}
        if "model" in content and isinstance(content["model"], dict) and "model" not in cls.model_fields:
            msg = (
                f"File '{file_path}' uses legacy '[model]' envelope syntax. "
                "Rune payload must be written at TOML top level."
            )
            raise ValueError(msg)

        return content

    def _assert_unique_identity(self, files: list[Path]) -> None:
        """Reject duplicate identities after path normalization.

        Args:
            files: Candidate TOML files for that rune class.

        Raises:
            ValueError: If two files derive the same rune-local identity.

        """
        seen: set[str] = set()

        for file_path in files:
            identity = self._instance_id_from_path(file_path)
            if identity in seen:
                msg = f"Duplicate identity detected: '{identity}'."
                raise ValueError(msg)
            seen.add(identity)

    def _instance_id_from_path(self, file_path: Path) -> str:
        """Derive a stable instance identity from a TOML path.

        Args:
            file_path: TOML file path under this loader's rune root.

        Returns:
            Rune-root-relative path without the TOML suffix.

        Raises:
            ValueError: If ``file_path`` is outside this loader's rune root.

        """
        rel = file_path.relative_to(self._runes_dir)
        return str(rel.with_suffix(""))
