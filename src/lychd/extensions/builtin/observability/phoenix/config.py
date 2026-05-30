from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Final

from pydantic import Field

from lychd.config.runes import RuneConfig

PORT_PHOENIX_UI: Final[int] = 6006
PORT_PHOENIX_OTLP: Final[int] = 4317


class ObservabilityConfig(RuneConfig):
    """Abstract branch Rune for observability-owned configuration."""

    path_fragment: ClassVar[Path] = Path("observability")


class PhoenixSettings(ObservabilityConfig):
    """Rune config for the built-in Arize Phoenix observability service."""

    path_fragment: ClassVar[Path] = Path("phoenix")
    sample_template: ClassVar[str | None] = """
name = "oculus"
image = "docker.io/arize-ai/phoenix:latest"
host = "localhost"
ui_port = 6006
otlp_port = 4317
"""

    name: str = Field(default="oculus", description="Stable local service identity for the Phoenix container.")
    image: str = Field(default="docker.io/arize-ai/phoenix:latest", description="OCI image for Arize Phoenix.")
    host: str = Field(default="localhost", description="Host used when presenting Phoenix URLs.")
    ui_port: int = Field(default=PORT_PHOENIX_UI, ge=1, le=65535, description="Host port for the Phoenix UI.")
    otlp_port: int = Field(default=PORT_PHOENIX_OTLP, ge=1, le=65535, description="Host port for OTLP ingestion.")

    @property
    def service_name(self) -> str:
        """Systemd service stem used for the Phoenix container."""
        return f"lychd-{self.name}"

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.otlp_port}"
