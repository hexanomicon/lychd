from __future__ import annotations

import textwrap
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from lychd.config.runes import ConfigWriter, RuneSchemaDiscovery
from lychd.config.settings import get_settings
from lychd.system.constants import PATH_LYCHD_TOML, PATH_POSTGRES_DIR, PATH_RUNE_TEMPLATES_DIR, PATH_RUNES_DIR

if TYPE_CHECKING:
    from pathlib import Path

logger = structlog.get_logger()


class CodexService:
    """The Scribe of Laws.

    Responsible for initialization:
    - inscribe global settings (`lychd.toml`)
    - inscribe dynamic db init script
    - initialize configurable rune anchors and sample TOMLs
    """

    def __init__(
        self,
        toml_path: Path | None = None,
        runes_path: Path | None = None,
        templates_dir: Path | None = None,
    ) -> None:
        """Create a codex service bound to concrete codex/runes paths."""
        self.toml_path = toml_path or PATH_LYCHD_TOML
        self.runes_path = runes_path or PATH_RUNES_DIR
        self.templates_dir = templates_dir or PATH_RUNE_TEMPLATES_DIR

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
        lines = self._introspect_model(settings)
        self.toml_path.parent.mkdir(parents=True, exist_ok=True)
        self.toml_path.write_text("\n".join(lines), encoding="utf-8")
        try:
            self.toml_path.chmod(0o600)
        except OSError:
            logger.warning("prime_directive_permission_set_failed", path=str(self.toml_path), expected_mode="0o600")
        logger.info("inscribed_prime_directive", path=str(self.toml_path))

    def _inscribe_init_db(self) -> None:
        """Inscribe the dynamic DB initialization script."""
        init_sh_path = PATH_POSTGRES_DIR / "init_db.sh"
        if init_sh_path.exists():
            return

        init_sh_path.parent.mkdir(parents=True, exist_ok=True)

        tmpl = self._env.get_template("init_db.sh.jinja")
        content = tmpl.render(databases=["lychd", "phoenix"])

        init_sh_path.write_text(content, encoding="utf-8")
        init_sh_path.chmod(0o755)
        logger.info("inscribed_init_db", path=str(init_sh_path))

    def _inscribe_configurables(self) -> None:
        """Initialize rune anchor directories and sample TOMLs."""
        schemas = RuneSchemaDiscovery(include_builtin_extensions=True).discover_classes()

        writer = ConfigWriter(runes_dir=self.runes_path)
        writer.initialize_anchors(schemas)
        writer.inscribe_samples(schemas)

        logger.info("configurable_anchors_inscribed", count=len(schemas), runes_root=str(self.runes_path))

    def _introspect_model(self, model: BaseModel) -> list[str]:
        """Recursively walk the Pydantic model to generate TOML lines."""
        lines: list[str] = []
        model_cls = type(model)

        for field_name, field_info in model_cls.model_fields.items():
            value = getattr(model, field_name)

            if field_name.startswith("_"):
                continue

            if isinstance(value, BaseModel):
                lines.append("")
                lines.append(f"[{field_name}]")
                lines.extend(self._introspect_model(value))
                continue

            if field_info.description:
                comments = textwrap.wrap(field_info.description, width=80)
                lines.extend(f"# {comment}" for comment in comments)

            lines.append(f"{field_name} = {self._format_toml_value(value)}")

        return lines

    def _format_toml_value(self, value: Any) -> str:
        """Convert Python objects to strict TOML string representation."""
        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, int | float):
            return str(value)

        if isinstance(value, list):
            from typing import cast

            items = [self._format_toml_value(v) for v in cast("list[Any]", value)]
            return f"[{', '.join(items)}]"

        if isinstance(value, Enum):
            return f'"{value.value}"'

        return f'"{value!s}"'
