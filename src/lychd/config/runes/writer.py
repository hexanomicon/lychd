from __future__ import annotations

from pathlib import Path
from typing import Any, get_args, get_origin

import structlog
from pydantic_core import PydanticUndefined

from lychd.config.runes.base import RuneConfig

logger = structlog.get_logger()


class ConfigWriter:
    """Writes rune sample TOMLs and initializes schema anchor directories."""

    def __init__(self, runes_dir: Path | None = None) -> None:
        """Create a writer for runes under a specific root."""
        self._runes_dir = runes_dir or RuneConfig.config_root

    def initialize_anchors(self, schemas: list[type[RuneConfig]]) -> None:
        """Ensure all schema anchor directories exist."""
        for schema in schemas:
            anchor = self._runes_dir if schema.relative_path is None else self._runes_dir / schema.relative_path
            anchor.mkdir(parents=True, exist_ok=True)
            logger.debug("anchor_initialized", schema=schema.__name__, anchor=str(anchor))

    def inscribe_samples(self, schemas: list[type[RuneConfig]]) -> list[Path]:
        """Write one sample TOML per schema when no files exist yet."""
        created: list[Path] = []

        for schema in schemas:
            target = self._target_sample_file(schema)
            if target is None:
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(self._render_sample(schema), encoding="utf-8")
            created.append(target)
            logger.info("rune_sample_inscribed", schema=schema.__name__, path=str(target))

        return created

    def _target_sample_file(self, schema: type[RuneConfig]) -> Path | None:
        """Return sample target path if schema has no existing TOML instances."""
        if schema.relative_path is None:
            target = self._runes_dir / schema.default_file_name()
            return None if target.exists() else target

        anchor = self._runes_dir / schema.relative_path
        existing = list(anchor.rglob("*.toml")) if anchor.exists() else []
        child_anchors = [self._runes_dir / rel for rel in self._descendant_relative_paths(schema)]
        if child_anchors:
            existing = [path for path in existing if not any(path.is_relative_to(child) for child in child_anchors)]
        if existing:
            return None

        return anchor / schema.default_file_name()

    def _descendant_relative_paths(self, schema: type[RuneConfig]) -> set[Path]:
        paths: set[Path] = set()
        for sub in schema.__subclasses__():
            if sub.relative_path is not None:
                paths.add(sub.relative_path)
            paths.update(self._descendant_relative_paths(sub))
        return paths

    def _render_sample(self, schema: type[RuneConfig]) -> str:
        lines: list[str] = []

        for field_name, field_info in schema.model_fields.items():
            if field_name == "file_name":
                continue

            if field_info.description:
                lines.append(f"# {field_info.description}")

            if field_info.default is not PydanticUndefined:
                lines.append(f"# default: {field_info.default!r}")
            elif field_info.default_factory is not None:
                lines.append("# default: <factory>")

            value = self._sample_value(field_info.annotation, required=field_info.is_required())
            assignment = f"{field_name} = {value}"

            if field_info.is_required():
                lines.append(assignment)
            else:
                # Optional/defaulted fields are documented but commented out.
                lines.append(f"# {assignment}")

            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _sample_value(self, annotation: Any, *, required: bool) -> str:
        """Build a deterministic placeholder value for a field annotation."""
        origin = get_origin(annotation)
        args = get_args(annotation)

        if args:
            resolved = self._resolve_optional_union(args)
            if resolved is not None:
                return self._sample_value(resolved, required=required)

        collection_sample = self._collection_placeholder(origin)
        if collection_sample is not None:
            return collection_sample

        scalar_sample = self._scalar_placeholder(annotation=annotation, required=required)
        if scalar_sample is not None:
            return scalar_sample

        return '"<value>"'

    def _resolve_optional_union(self, args: tuple[Any, ...]) -> Any | None:
        """Return inner type for Optional[T] style unions, else None."""
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
        return None

    def _collection_placeholder(self, origin: Any) -> str | None:
        """Return placeholder for known collection/container origins."""
        if origin in (list, set, tuple):
            return "[]"
        if origin is dict:
            return "{}"
        return None

    def _scalar_placeholder(self, *, annotation: Any, required: bool) -> str | None:
        """Return placeholder for known scalar python types."""
        if annotation is Any:
            return '"<value>"'

        if get_origin(annotation) is not None:
            # Non-container generic we do not model explicitly.
            return None

        if isinstance(annotation, type):
            scalar_map = {
                int: "0",
                float: "0.0",
                bool: "false",
            }
            if annotation is str:
                return '"<required:str>"' if required else '"<optional:str>"'
            return scalar_map.get(annotation)

        return None
