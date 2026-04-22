from __future__ import annotations

import textwrap
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, SecretStr

from lychd.config.settings import get_settings
from lychd.system.constants import (
    PATH_LYCHD_TOML,
    PATH_PORTALS_DIR,
    PATH_POSTGRES_DIR,
    PATH_RUNE_TEMPLATES_DIR,
    PATH_SOULSTONES_DIR,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = structlog.get_logger()


class CodexService:
    """The Scribe of Laws.

    Responsible for the Initialization Ritual.
    - Inscribes the Prime Directive (lychd.toml) via introspection.
    - Inscribes example Soulstones and Portals via Jinja templates.
    """

    def __init__(
        self,
        toml_path: Path | None = None,
        soulstones_path: Path | None = None,
        portals_path: Path | None = None,
        templates_dir: Path | None = None,
    ) -> None:
        """Initialize the Codex Service with target paths."""
        self.toml_path = toml_path or PATH_LYCHD_TOML
        self.souls_path = soulstones_path or PATH_SOULSTONES_DIR
        self.portals_path = portals_path or PATH_PORTALS_DIR
        self.templates_dir = templates_dir or PATH_RUNE_TEMPLATES_DIR

        self._env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=False,  # noqa: S701 TOML generation
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def inscribe(self) -> None:
        """Perform the Initialization Ritual.

        Assumes the directory structure has been established by the LayoutService.
        """
        self._inscribe_lychd_toml()
        self._inscribe_init_db()
        self._inscribe_defaults()

        logger.info(
            "codex_inscribed",
            location=str(self.toml_path.parent),
        )

    def _inscribe_lychd_toml(self) -> None:
        """Generate lychd.toml from Pydantic Settings."""
        if self.toml_path.exists():
            logger.debug("prime_directive_exists", path=str(self.toml_path))
            return

        settings = get_settings()
        lines = self._introspect_model(settings)
        content = "\n".join(lines)

        self.toml_path.write_text(content, encoding="utf-8")
        logger.info("inscribed_prime_directive", path=str(self.toml_path))

    def _inscribe_init_db(self) -> None:
        """Inscribe the dynamic DB initialization script."""
        init_sh_path = PATH_POSTGRES_DIR / "init_db.sh"
        if init_sh_path.exists():
            return

        # Ensure the directory exists
        init_sh_path.parent.mkdir(parents=True, exist_ok=True)

        tmpl = self._env.get_template("init_db.sh.jinja")
        content = tmpl.render(databases=["lychd", "phoenix"])

        init_sh_path.write_text(content, encoding="utf-8")
        # Ensure it's executable
        init_sh_path.chmod(0o755)
        logger.info("inscribed_init_db", path=str(init_sh_path))

    def _inscribe_defaults(self) -> None:
        """Generate example soulstones and portals if directories are empty."""
        # 1. Hermes (Soulstone)
        hermes_path = self.souls_path / "hermes.toml"
        if not hermes_path.exists():
            tmpl = self._env.get_template("soulstone.toml.jinja")
            content = tmpl.render(
                name="hermes",
                group="hermes-accompanied",
                image="ghcr.io/ggerganov/llama.cpp:server",
                port=30000,
                model_path="hermes-v2.gguf",
                model_name="hermes-v2",
                description="A locally hosted Hermes model.",
                max_context=4096,
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                repetition_penalty=1.1,
                exec=[],
                volumes=[],
                env_vars={},
            )
            hermes_path.write_text(content, encoding="utf-8")
            logger.info("inscribed_soulstone_example", name="hermes")

        # 2. OpenAI (Portal)
        openai_path = self.portals_path / "openai.toml"
        if not openai_path.exists():
            tmpl = self._env.get_template("portal.toml.jinja")
            content = tmpl.render(
                name="openai",
                provider="openai",
                uri="https://api.openai.com/v1",
                model_name="gpt-4o",
                api_key_env="OPENAI_API_KEY",
                description="The official OpenAI endpoint.",
            )
            openai_path.write_text(content, encoding="utf-8")
            logger.info("inscribed_portal_example", name="openai")

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

            formatted_value = self._format_toml_value(value)
            lines.append(f"{field_name} = {formatted_value}")

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

        if isinstance(value, SecretStr):
            return f'"{value.get_secret_value()}"'

        return f'"{value!s}"'
