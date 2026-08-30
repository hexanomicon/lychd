from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field

from lychd.config import QuadletConfig
from lychd.domain.animation.schemas import SoulstoneConfig


class SglangSoulstoneConfig(SoulstoneConfig):
    """SGLang runtime declarations and launch recipes.

    Exec-passthrough-by-default: the operator supplies the full SGLang serve
    command as the ``exec`` list (authoritative). Container-level concerns
    remain typed fields; framework flags live in ``exec``.
    """

    path_fragment: ClassVar[Path] = Path("sglang")
    sample_template: ClassVar[str | None] = """
# ~/.config/lychd/runes/animator/soulstones/sglang/main.toml

name = "sglang-main"
description = "SGLang Soulstone."
port = 8011
served_model_id = "/models/your-model"

exec = ["-m", "sglang.launch_server", "--port", "8011", "--model-path", "/models/your-model"]

[quadlet]
image = "lmsysorg/sglang:latest"
"""
    runtime: Literal["sglang"] = "sglang"  # pyright: ignore[reportIncompatibleVariableOverride]
    quadlet: QuadletConfig = Field(default_factory=lambda: QuadletConfig(image="lmsysorg/sglang:latest"))
