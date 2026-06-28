from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from lychd.domain.animation.schemas import ModelFormat, SoulstoneConfig


class SglangSoulstoneConfig(SoulstoneConfig):
    """Builtin Soulstone profile for SGLang.

    Exec-passthrough-by-default: the operator supplies the full SGLang serve
    command as the ``exec`` list (authoritative). Container-level concerns
    remain typed fields; framework flags live in ``exec``.
    """

    path_fragment: ClassVar[Path] = Path("sglang")
    sample_template: ClassVar[str | None] = """
# ~/.config/lychd/runes/animator/soulstones/sglang/main.toml

name = "sglang-main"
description = "SGLang Soulstone."
image = "lmsysorg/sglang:latest"
port = 8011
ipc_host = true

exec = ["-m", "sglang.launch_server", "--port", "8011", "--model-path", "/models/your-model"]
"""
    runtime: str = "sglang"
    image: str = "lmsysorg/sglang:latest"
    model_format: ModelFormat | None = ModelFormat.AWQ

    ipc_host: bool = True
    network_host: bool = False
