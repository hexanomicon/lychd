from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from jinja2 import Environment, FileSystemLoader
from tomlkit import dumps as _tomlkit_dumps  # pyright: ignore[reportUnknownVariableType]

from lychd.config.runes import ConfigWriter, RuneConfig
from lychd.config.settings import get_settings
from lychd.system.constants import PATH_LYCHD_TOML, PATH_POSTGRES_ROOT_DIR, PATH_RUNE_TEMPLATES_DIR, PATH_RUNES_DIR

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = structlog.get_logger()


def _toml_dumps(data: dict[str, Any]) -> str:
    """Narrow tomlkit's untyped Mapping signature at the dependency boundary."""
    return _tomlkit_dumps(data)


def _write_new_atomic(path: Path, content: str, *, mode: int) -> bool:
    """Durably create ``path`` without overwriting a concurrent/existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw_temporary)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return False
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return True
    finally:
        temporary.unlink(missing_ok=True)


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

    def inscribe(self) -> None:
        """Perform codex initialization."""
        self._inscribe_lychd_toml()
        self._inscribe_init_db()
        self._inscribe_configurables()

        logger.info("codex_inscribed", location=str(self.toml_path.parent))

    def _inscribe_lychd_toml(self) -> None:
        """Generate `lychd.toml` from Pydantic Settings defaults."""
        if self.toml_path.exists():
            logger.debug("prime_directive_exists", path=str(self.toml_path))
            return

        settings = get_settings()
        content = _toml_dumps(settings.model_dump(mode="json", exclude_none=True))
        if not _write_new_atomic(self.toml_path, content, mode=0o600):
            logger.debug("prime_directive_exists", path=str(self.toml_path))
            return
        logger.info("inscribed_prime_directive", path=str(self.toml_path))

    def _inscribe_init_db(self) -> None:
        """Inscribe the dynamic DB initialization script."""
        init_sh_path = self.postgres_root_path / "init_db.sh"
        if init_sh_path.exists():
            return

        tmpl = self._env.get_template("init_db.sh.jinja")
        content = tmpl.render()
        if not _write_new_atomic(init_sh_path, content, mode=0o755):
            return
        logger.info("inscribed_init_db", path=str(init_sh_path))

    def _inscribe_configurables(self) -> None:
        """Initialize rune anchor directories and sample TOMLs."""
        writer = ConfigWriter(runes_dir=self.runes_path)
        writer.initialize_anchors(self.rune_schemas)
        writer.inscribe_samples(self.rune_schemas)

        logger.info("configurable_anchors_inscribed", count=len(self.rune_schemas), runes_root=str(self.runes_path))
