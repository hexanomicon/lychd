from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field

from lychd.config import QuadletConfig
from lychd.domain.animation.schemas import ModelFormat, SoulstoneConfig


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
    runtime: str = "sglang"
    quadlet: QuadletConfig = Field(default_factory=lambda: QuadletConfig(image="lmsysorg/sglang:latest"))
    model_format: ModelFormat | None = ModelFormat.AWQ

    # Legacy runes may retain these fields. They are accepted as inert inputs;
    # pod members never receive host IPC or host networking flags.
    ipc_host: bool = False
    network_host: bool = False
