from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Final

from pydantic import Field

from lychd.config import QuadletConfig
from lychd.config.runes import RuneConfig

PORT_PHOENIX_UI: Final[int] = 6006
PORT_PHOENIX_OTLP: Final[int] = 4317

# Internal container ports the Phoenix image binds to (extension-private now:
# moved out of system/constants.py, which is core-only).
CONTAINER_PHOENIX_UI_PORT: Final[int] = 6006
CONTAINER_PHOENIX_OTLP_PORT: Final[int] = 4317


class ObservabilityConfig(RuneConfig):
    """Observability service declarations."""

    path_fragment: ClassVar[Path] = Path("observability")


class PhoenixSettings(ObservabilityConfig):
    """Optional external Arize Phoenix Eye."""

    path_fragment: ClassVar[Path] = Path("phoenix")
    sample_template: ClassVar[str | None] = """
name = "phoenix"
host = "localhost"
ui_port = 6006
otlp_port = 4317

[quadlet]
image = "docker.io/arize-ai/phoenix:latest"
"""

    name: str = Field(
        default="phoenix",
        description=(
            "Stable local service identity for the external Phoenix Eye. Existing configurations "
            "may retain the legacy value 'oculus' until deliberately migrated."
        ),
    )
    quadlet: QuadletConfig = Field(
        default_factory=lambda: QuadletConfig(image="docker.io/arize-ai/phoenix:latest"),
        description="Typed deployment body compiled into the Phoenix Quadlet container.",
    )
    host: str = Field(default="localhost", description="Host used when presenting Phoenix URLs.")
    ui_port: int = Field(default=PORT_PHOENIX_UI, ge=1, le=65535, description="Host port for the Phoenix UI.")
    otlp_port: int = Field(default=PORT_PHOENIX_OTLP, ge=1, le=65535, description="Host port for OTLP ingestion.")

    def reserved_ports(self) -> dict[str, int]:
        """Host port claims (satisfies ``config.runes.protocols.PortReserver``)."""
        return {"Phoenix Eye UI": self.ui_port, "Phoenix Eye OTLP": self.otlp_port}

    @property
    def service_name(self) -> str:
        """Systemd service stem used for the Phoenix container."""
        return f"lychd-{self.name}"

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.otlp_port}"
