from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from jinja2 import Environment, FileSystemLoader
from tomlkit import dumps as _tomlkit_dumps  # pyright: ignore[reportUnknownVariableType]

from lychd.config.runes import ConfigWriter, RuneConfig
from lychd.config.settings.root import Settings, get_settings
from lychd.system.constants import PATH_LYCHD_TOML, PATH_POSTGRES_ROOT_DIR, PATH_RUNE_TEMPLATES_DIR, PATH_RUNES_DIR
from lychd.system.services.lifecycle import CreatedResources, created_resources

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = structlog.get_logger()


def _toml_dumps(data: dict[str, Any]) -> str:
    """Narrow tomlkit's untyped Mapping signature at the dependency boundary."""
    return _tomlkit_dumps(data)


def _render_default_settings_toml(settings: Settings) -> str:
    """Render defaults with an operator-facing, inert extension selection hint."""
    content = _toml_dumps(settings.model_dump(mode="json", exclude_none=True))
    extension_table = "[extensions]\n"
    extension_hint = (
        "# Optional built-ins: choose only what this machine needs.\n"
        '# Local llama.cpp: builtins = ["animator/llamacpp"]\n'
        '# Other choices: "animator/exllamav3", "animator/vllm", "animator/sglang",\n'
        '#                "observability/phoenix", "simulation"\n'
    )
    if extension_table not in content:
        msg = "Settings TOML did not contain the required [extensions] table."
        raise RuntimeError(msg)
    return content.replace(extension_table, f"{extension_table}{extension_hint}", count=1)


def _write_new_atomic(path: Path, content: str, *, mode: int) -> bool:
    """Durably create ``path`` without overwriting a concurrent/existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw_temporary)
    linked = False
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            created = False
        else:
            linked = True
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            created = True
    except BaseException:
        if linked:
            path.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)
    return created


class CodexService:
    """The Scribe of Laws.

    Responsible for initialization:
    - inscribe global settings (`lychd.toml`)
    - inscribe dynamic db init script
    - initialize configurable rune anchors and sample TOMLs
    """

    def __init__(
        self,
        *,
        rune_schemas: Sequence[type[RuneConfig]],
        toml_path: Path | None = None,
        runes_path: Path | None = None,
        templates_dir: Path | None = None,
        postgres_root_path: Path | None = None,
    ) -> None:
        """Create a codex service bound to concrete codex/runes paths."""
        self.toml_path = toml_path or PATH_LYCHD_TOML
        self.runes_path = runes_path or PATH_RUNES_DIR
        self.templates_dir = templates_dir or PATH_RUNE_TEMPLATES_DIR
        self.postgres_root_path = postgres_root_path or PATH_POSTGRES_ROOT_DIR
        self.rune_schemas = list(rune_schemas)

        self._env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=False,  # noqa: S701 TOML generation
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def inscribe(
        self,
        *,
        on_created: Callable[[CreatedResources], None] | None = None,
    ) -> CreatedResources:
        """Perform codex initialization."""
        created: list[CreatedResources] = []
        for action in (self._inscribe_lychd_toml, self._inscribe_init_db):
            path = action()
            if path is None:
                continue
            resources = created_resources(files=(path,))
            self._journal_or_rollback(resources, on_created=on_created)
            created.append(resources)
        configurables = self._inscribe_configurables(on_created=on_created)

        logger.info("codex_inscribed", location=str(self.toml_path.parent))
        return CreatedResources.combine(*created, configurables)

    def _inscribe_lychd_toml(self) -> Path | None:
        """Generate `lychd.toml` from Pydantic Settings defaults."""
        if self.toml_path.exists():
            logger.debug("prime_directive_exists", path=str(self.toml_path))
            return None

        settings = get_settings()
        content = _render_default_settings_toml(settings)
        if not _write_new_atomic(self.toml_path, content, mode=0o600):
            logger.debug("prime_directive_exists", path=str(self.toml_path))
            return None
        logger.info("inscribed_prime_directive", path=str(self.toml_path))
        return self.toml_path

    def _inscribe_init_db(self) -> Path | None:
        """Inscribe the dynamic DB initialization script."""
        init_sh_path = self.postgres_root_path / "init_db.sh"
        if init_sh_path.exists():
            return None

        tmpl = self._env.get_template("init_db.sh.jinja")
        content = tmpl.render()
        if not _write_new_atomic(init_sh_path, content, mode=0o755):
            return None
        logger.info("inscribed_init_db", path=str(init_sh_path))
        return init_sh_path

    def _inscribe_configurables(
        self,
        *,
        on_created: Callable[[CreatedResources], None] | None,
    ) -> CreatedResources:
        """Initialize rune anchor directories and sample TOMLs."""
        writer = ConfigWriter(runes_dir=self.runes_path)
        directories = writer.initialize_anchors(
            self.rune_schemas,
            on_created=(
                None
                if on_created is None
                else lambda paths: on_created(created_resources(directories=paths))
            ),
        )
        files = writer.inscribe_samples(
            self.rune_schemas,
            on_created=(
                None
                if on_created is None
                else lambda path: on_created(created_resources(files=(path,)))
            ),
        )

        logger.info("configurable_anchors_inscribed", count=len(self.rune_schemas), runes_root=str(self.runes_path))
        return created_resources(directories=directories, files=files)

    @staticmethod
    def _journal_or_rollback(
        resources: CreatedResources,
        *,
        on_created: Callable[[CreatedResources], None] | None,
    ) -> None:
        """Persist creation authority or remove the just-created exact resources."""
        if on_created is None:
            return
        try:
            on_created(resources)
        except BaseException:
            for path in resources.files:
                path.unlink(missing_ok=True)
            for path in reversed(resources.directories):
                try:
                    path.rmdir()
                except OSError:
                    continue
            raise
