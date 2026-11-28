"""Resolve a fixed native llama.cpp command from trusted installation settings and a Soulstone."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.orchestration.actuator import RuntimePreconditionError
from lychd.extensions.builtin.animator.llamacpp.parser_models import LlamaCppRuntimeInference
from lychd.extensions.builtin.animator.llamacpp.runtime import LlamaCppRuntimePlanner
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppSoulstoneConfig
from lychd.system.desktop.private import check_native_inputs

if TYPE_CHECKING:
    from lychd.config.settings.orchestration import SwitchingSettings
    from lychd.domain.animation.schemas import SoulstoneConfig


def native_llama_command(
    rune: SoulstoneConfig | None, settings: SwitchingSettings, *, name: str
) -> tuple[list[str], int]:
    """Validate the approved executable and GGUF before deriving fixed loopback argv."""
    engine = settings.native_llama_server
    root = settings.native_model_root
    if (
        not isinstance(rune, LlamaCppSoulstoneConfig)
        or not rune.concurrency.dedicated
        or engine is None
        or root is None
    ):
        msg = f"No managed native llama.cpp binding for {name!r}."
        raise RuntimePreconditionError(msg)
    try:
        placement = rune.resolved_placement("native")
    except ValueError as exc:
        msg = f"Native llama.cpp cannot use the supplied launch overrides: {exc}"
        raise RuntimePreconditionError(msg) from exc
    if placement != "native" or rune.port is None or not rune.model_path:
        msg = "A native engine requires a native fixed GGUF binding and allocated port."
        raise RuntimePreconditionError(msg)
    if rune.base_url is not None and str(rune.base_url).rstrip("/") != f"http://127.0.0.1:{rune.port}/v1":
        msg = "Native llama.cpp requires an explicit http://127.0.0.1:<port>/v1 endpoint."
        raise RuntimePreconditionError(msg)
    if (
        engine.name != ("llama-server.exe" if os.name == "nt" else "llama-server")
        or not engine.is_file()
        or not os.access(engine, os.X_OK)
    ):
        msg = "The approved llama-server executable is missing or unusable."
        raise RuntimePreconditionError(msg)
    model = Path(rune.model_path)
    if (
        not model.is_absolute()
        or not root.is_dir()
        or not model.is_relative_to(root)
        or model.suffix.lower() != ".gguf"
        or not model.is_file()
    ):
        msg = "Native model must be an existing absolute GGUF file inside native_model_root."
        raise RuntimePreconditionError(msg)
    try:
        check_native_inputs(engine, model)
    except (OSError, ValueError) as exc:
        raise RuntimePreconditionError(str(exc)) from exc
    planner = LlamaCppRuntimePlanner()
    args = planner.plan_exec_args(
        soulstone=rune, inferred=LlamaCppRuntimeInference(), mode="single", listen_host="127.0.0.1"
    )
    return [str(engine.resolve(strict=True)), *args], rune.port
