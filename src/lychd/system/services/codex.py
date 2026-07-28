from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from jinja2 import Environment, FileSystemLoader
from tomlkit import dumps as _tomlkit_dumps  # pyright: ignore[reportUnknownVariableType]

from lychd.config.runes import RuneConfig
from lychd.config.runes.writer import ConfigWriter
from lychd.config.settings import Settings, get_settings
from lychd.system.constants import PATH_LYCHD_TOML, PATH_POSTGRES_ROOT_DIR, PATH_RUNE_TEMPLATES_DIR, PATH_RUNES_DIR
from lychd.system.services.lifecycle.models import CreatedResources
from lychd.system.services.publication import JournaledCreation

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
        creation = JournaledCreation(on_created=on_created)
        self._inscribe_lychd_toml(creation)
        self._inscribe_init_db(creation)
        self._inscribe_configurables(creation)

        logger.info("codex_inscribed", location=str(self.toml_path.parent))
        return creation.resources

    def _inscribe_lychd_toml(self, creation: JournaledCreation) -> None:
        """Generate `lychd.toml` from Pydantic Settings defaults."""
        settings = get_settings()
        content = _render_default_settings_toml(settings)
        resources = creation.create_text_file(
            self.toml_path,
            content,
            mode=0o600,
        )
        if not resources.files:
            logger.debug("prime_directive_exists", path=str(self.toml_path))
            return
        logger.info("inscribed_prime_directive", path=str(self.toml_path))

    def _inscribe_init_db(self, creation: JournaledCreation) -> None:
        """Inscribe the dynamic DB initialization script."""
        init_sh_path = self.postgres_root_path / "init_db.sh"
        tmpl = self._env.get_template("init_db.sh.jinja")
        content = tmpl.render()
        resources = creation.create_text_file(
            init_sh_path,
            content,
            mode=0o755,
        )
        if not resources.files:
            return
        logger.info("inscribed_init_db", path=str(init_sh_path))

    def _inscribe_configurables(
        self,
        creation: JournaledCreation,
    ) -> None:
        """Initialize rune anchor directories and sample TOMLs."""
        writer = ConfigWriter(
            runes_dir=self.runes_path,
            creation=creation,
        )
        writer.initialize_anchors(self.rune_schemas)
        writer.inscribe_samples(self.rune_schemas)

        logger.info("configurable_anchors_inscribed", count=len(self.rune_schemas), runes_root=str(self.runes_path))
