from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import structlog

from lychd.config.runes.base import RuneConfig, admitted_branch_schemas
from lychd.config.runes.markers import SAMPLE_MARKER
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
            ValueError: If TOML parsing, branch-file enforcement, or Pydantic
                model validation fails.

        """
        loaded: list[RuneConfig] = []
        branch_schemas = admitted_branch_schemas(schemas)

        for cls in schemas:
            loaded.extend(self._load_class_instances(cls, is_branch=cls in branch_schemas))

        logger.debug("runes_loaded", count=len(loaded), classes=[c.__name__ for c in schemas])
        return loaded

    def _load_class_instances(self, cls: type[RuneConfig], *, is_branch: bool) -> list[RuneConfig]:
        """Load every TOML instance owned by one rune class.

        Args:
            cls: Rune class whose anchor should be scanned.
            is_branch: Whether another schema in this admitted generation derives
                from ``cls``.

        Returns:
            Validated instances for ``cls``.

        Raises:
            ValueError: If a branch rune owns TOML files or payload validation fails.

        """
        files = self._candidate_files(cls)
        if is_branch:
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
            payload = self._read_payload(file_path)
            instance = cls.model_validate(payload).bind_source_file(file_path)
            instances.append(instance)

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

    def _read_payload(self, file_path: Path) -> dict[str, Any]:
        """Read one TOML payload.

        Args:
            file_path: TOML file to read.

        Returns:
            Parsed TOML payload with string keys.

        Raises:
            ValueError: If the file is unreadable or malformed.

        """
        try:
            parsed = tomllib.loads(file_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            msg = f"Malformed TOML in '{file_path}'."
            raise ValueError(msg) from exc
        except OSError as exc:
            msg = f"Could not read '{file_path}'."
            raise ValueError(msg) from exc

        return {str(k): v for k, v in parsed.items()}
