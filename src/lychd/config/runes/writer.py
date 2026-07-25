from __future__ import annotations

import inspect
import os
from collections.abc import Callable
from pathlib import Path
from types import UnionType
from typing import Any, Union, get_args, get_origin

import structlog
from pydantic_core import PydanticUndefined

from lychd.config.runes.base import RuneConfig
from lychd.system.constants import PATH_RUNES_DIR

logger = structlog.get_logger()

SAMPLE_MARKER = "# lychd: sample-rune"
"""Comment marker used to identify generated non-authoritative sample TOMLs."""


class ConfigWriter:
    """Materialize rune anchors and first-run sample TOMLs.

    The writer operates from schema classes, not instances. It creates anchor
    directories for every active rune class, but only leaf classes receive
    sample TOML files because branch anchors are namespaces. Samples are
    operator-facing scaffolds: they show the top-level TOML shape and provide
    syntactically valid placeholder values, but they are not loaded defaults and
    they do not replace schema validation.
    """

    def __init__(self, runes_dir: Path | None = None) -> None:
        """Create a writer for runes under a specific root.

        Args:
            runes_dir: Optional root directory to write. Defaults to
                ``PATH_RUNES_DIR``.

        """
        self._runes_dir = runes_dir or PATH_RUNES_DIR

    def initialize_anchors(
        self,
        schemas: list[type[RuneConfig]],
        *,
        on_created: Callable[[tuple[Path, ...]], None] | None = None,
    ) -> list[Path]:
        """Ensure every provided rune class has an anchor directory.

        Branch anchors are still materialized so the filesystem mirrors the
        schema tree, even though branch classes never own TOML instances.

        Args:
            schemas: Rune classes whose anchors should exist.
            on_created: Optional durable journal called after each new anchor batch.

        """
        created: list[Path] = []
        for schema in schemas:
            anchor = schema.anchor_dir(self._runes_dir)
            missing: list[Path] = []
            current = anchor
            while current != current.parent and not current.exists():
                missing.append(current)
                current = current.parent
            created_now = tuple(reversed(missing))
            anchor.mkdir(parents=True, exist_ok=True)
            try:
                if on_created is not None and created_now:
                    on_created(created_now)
            except BaseException:
                for path in reversed(created_now):
                    try:
                        path.rmdir()
                    except OSError:
                        continue
                raise
            created.extend(created_now)
            logger.debug("anchor_initialized", schema=schema.__name__, anchor=str(anchor))
        return sorted(set(created))

    def planned_sample_paths(self, schemas: list[type[RuneConfig]]) -> list[Path]:
        """Return sample paths a mutation-free inscription would create."""
        return [target for schema in schemas if (target := self._target_sample_file(schema)) is not None]

    def planned_path_descriptions(self, schemas: list[type[RuneConfig]]) -> dict[Path, str]:
        """Project Rune class docstrings onto their planned anchors and samples."""
        descriptions: dict[Path, str] = {}
        for schema in schemas:
            lineage = tuple(
                ancestor
                for ancestor in reversed(schema.mro())
                if issubclass(ancestor, RuneConfig) and ancestor is not RuneConfig
            )
            for ancestor in lineage:
                summary = self._schema_summary(ancestor)
                if summary is not None:
                    descriptions[ancestor.anchor_dir(self._runes_dir)] = summary
            target = self._target_sample_file(schema)
            if target is not None:
                descriptions[target] = "Generated inactive example; remove its marker before use."
        return descriptions

    @staticmethod
    def _schema_summary(schema: type[RuneConfig]) -> str | None:
        """Return exactly the first line of a Rune class docstring."""
        if schema.__doc__ is None:
            return None
        description = inspect.cleandoc(schema.__doc__)
        return description.partition("\n")[0] or None

    def inscribe_samples(
        self,
        schemas: list[type[RuneConfig]],
        *,
        on_created: Callable[[Path], None] | None = None,
    ) -> list[Path]:
        """Write first-run sample TOMLs for empty leaf anchors.

        Existing TOML files are treated as operator-owned configuration, so the
        writer does not overwrite them or add another sample beside them.

        Args:
            schemas: Rune classes considered for sample generation.
            on_created: Optional durable journal called after each new sample.

        Returns:
            Paths of sample TOMLs created during this call.

        """
        created: list[Path] = []

        for schema in schemas:
            target = self._target_sample_file(schema)
            if target is None:
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            if not self._write_sample_exclusive(target, self._render_sample(schema)):
                continue
            try:
                if on_created is not None:
                    on_created(target)
            except BaseException:
                target.unlink(missing_ok=True)
                raise
            created.append(target)
            logger.info("rune_sample_inscribed", schema=schema.__name__, path=str(target))

        return created

    @staticmethod
    def _write_sample_exclusive(path: Path, content: str) -> bool:
        """Create one owner-only sample durably without a permissive-mode window."""
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError:
            return False
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = -1
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        return True

    def _target_sample_file(self, schema: type[RuneConfig]) -> Path | None:
        """Return the sample path for an empty leaf anchor.

        Branch schemas return ``None`` because their anchors are namespaces.
        Leaf schemas also return ``None`` once any direct TOML file exists in
        the anchor; existing files mean the operator has already configured the
        rune family.

        Args:
            schema: Rune class considered for sample generation.

        Returns:
            Target sample path, or ``None`` when no sample should be written.

        """
        if schema.__subclasses__():
            return None

        file_name = self._default_file_name(schema)

        anchor = schema.anchor_dir(self._runes_dir)
        existing = list(anchor.glob("*.toml")) if anchor.exists() else []
        if existing:
            return None

        return anchor / file_name

    def _default_file_name(self, schema: type[RuneConfig]) -> str:
        """Derive the generated TOML sample filename for a rune class.

        Args:
            schema: Rune class needing a generated sample filename.

        Returns:
            The lowercase rune class name with a ``.toml`` suffix.

        """
        return f"{schema.__name__.lower()}.toml"

    def _render_sample(self, schema: type[RuneConfig]) -> str:
        """Render a top-level TOML sample from Pydantic model fields.

        A schema may define ``sample_template`` for a hand-authored complete
        sample. When absent, the writer falls back to a generic scaffold derived
        from model fields.

        Required fields are emitted as active placeholder assignments. Fields
        with defaults are documented but commented out, preserving the default
        unless the operator chooses to enable them.

        The rendered file is meant to be edited by an operator before use;
        placeholder values only make the initial sample readable and TOML-shaped.

        Args:
            schema: Rune class whose model fields define the TOML shape.

        Returns:
            Complete sample TOML content ending with a newline.

        """
        if "sample_template" in schema.__dict__ and schema.sample_template is not None:
            return self._with_sample_marker(self._normalize_sample_template(schema.sample_template))

        lines: list[str] = []

        for field_name, field_info in schema.model_fields.items():
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

        return self._with_sample_marker("\n".join(lines).rstrip() + "\n")

    def _with_sample_marker(self, content: str) -> str:
        """Mark generated samples so loaders can skip placeholders safely."""
        normalized = content.rstrip() + "\n"
        if normalized.startswith(SAMPLE_MARKER):
            return normalized
        return f"{SAMPLE_MARKER}\n# Edit this file, then remove this marker to activate it.\n\n{normalized}"

    def _normalize_sample_template(self, template: str) -> str:
        """Normalize a custom sample template for file writing.

        Args:
            template: Complete TOML sample content supplied by the schema.

        Returns:
            Template content with exactly one trailing newline.

        """
        return template.rstrip() + "\n"

    def _sample_value(self, annotation: Any, *, required: bool) -> str:
        """Build a deterministic TOML literal for a sample assignment.

        The writer does not know the operator's real value, so it derives the
        smallest useful TOML literal from the field annotation: empty containers
        for collection fields, scalar examples for primitive fields, and a
        generic string for anything more complex.

        Args:
            annotation: Field annotation used to infer the placeholder shape.
            required: Whether the field is required in the schema.

        Returns:
            TOML literal string suitable for a sample assignment.

        """
        # TOML has no null literal. For Optional[T], show an example for T; the
        # caller decides whether the assignment is active or commented out.
        sample_annotation = self._sample_annotation(annotation)
        origin = get_origin(sample_annotation)

        # Containers get empty TOML literals. A sample should show shape without
        # inventing list items or key/value pairs for the operator.
        collection_sample = self._collection_placeholder(origin)
        if collection_sample is not None:
            return collection_sample

        # Primitive scalars get concrete TOML literals. Unknown complex types
        # fall through to a generic string placeholder below.
        scalar_sample = self._scalar_placeholder(annotation=sample_annotation, required=required)
        if scalar_sample is not None:
            return scalar_sample

        return '"<value>"'

    def _sample_annotation(self, annotation: Any) -> Any:
        """Return the annotation that should drive sample literal selection.

        Optional fields still need a non-null example because TOML has no null
        value. ``Optional[T]``/``T | None`` therefore samples as ``T``. Other
        annotations pass through unchanged.

        Args:
            annotation: Original field annotation from the Pydantic model.

        Returns:
            Annotation used to choose a TOML placeholder literal.

        """
        origin = get_origin(annotation)
        if origin not in (Union, UnionType):
            return annotation

        args = get_args(annotation)
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
        return annotation

    def _collection_placeholder(self, origin: Any) -> str | None:
        """Return TOML literals for container annotations.

        ``typing.get_origin()`` turns annotations such as ``list[str]`` or
        ``dict[str, str]`` into their runtime container type. Samples use empty
        containers because they are valid TOML and do not invent operator data.

        Args:
            origin: Runtime container type from ``typing.get_origin``.

        Returns:
            TOML literal for a known container type, otherwise ``None``.

        """
        if origin in (list, set, tuple):
            return "[]"
        if origin is dict:
            return "{}"
        return None

    def _scalar_placeholder(self, *, annotation: Any, required: bool) -> str | None:
        """Return TOML literals for primitive scalar annotations.

        Args:
            annotation: Field annotation to map to a TOML scalar.
            required: Whether a string placeholder should be marked required.

        Returns:
            TOML literal for a known scalar type, otherwise ``None``.

        """
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
