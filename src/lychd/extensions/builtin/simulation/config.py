from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field

from lychd.config.runes import RuneConfig


class ShadowSimulationConfig(RuneConfig):
    """Configuration for Shadow simulation behavior."""

    path_fragment: ClassVar[Path] = Path("simulation")

    mode: str = Field(default="tomb", description="Execution mode for speculative simulation.")
    max_timelines: int = Field(default=8, ge=1, description="Maximum concurrent speculative branches.")
