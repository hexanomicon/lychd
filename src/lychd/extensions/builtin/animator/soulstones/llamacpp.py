from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, model_validator

from lychd.domain.animation.schemas import ModelFormat, SoulstoneConfig


class LlamaCppMode(StrEnum):
    """Operational mode for llama.cpp server."""

    AUTO = "auto"
    SINGLE = "single"
    ROUTER = "router"


class LlamaCppSoulstone(SoulstoneConfig):
    """Builtin Soulstone profile for llama.cpp.

    Contract:
    - ``exec`` present => passthrough mode (command is authoritative)
    - ``exec`` absent  => managed mode (typed fields synthesize command args)
    - managed single mode requires ``model_path``
    - managed router mode requires ``models_dir``/``models_preset`` or equivalent router flags
    """

    relative_path: ClassVar[Path | None] = Path("animator/soulstones/llamacpp")
    runtime: str = "llamacpp"
    image: str = "ghcr.io/ggml-org/llama.cpp:server-cuda"
    model_format: ModelFormat | None = ModelFormat.GGUF

    startup_mode: LlamaCppMode = LlamaCppMode.AUTO
    models_dir: str | None = None
    models_preset: str | None = None
    models_max: int | None = Field(default=None, ge=0)
    models_autoload: bool = True
    sleep_idle_seconds: int | None = Field(default=None, ge=-1)

    n_gpu_layers: int = Field(default=99, ge=0)
    n_ctx: int = Field(default=8192, ge=1)
    n_parallel: int = Field(default=1, ge=1)
    flash_attn: bool = True
    cache_type_k: str = "q4_0"
    cache_type_v: str = "q4_0"
    n_cpu_moe: int | None = Field(default=None, ge=0)
    split_mode: Literal["none", "layer", "row"] = "layer"
    threads: int | None = Field(default=None, ge=1)
    threads_batch: int | None = Field(default=None, ge=1)
    jinja: bool = True
    chat_template: str | None = None

    lora_adapters: list[str] = Field(default_factory=list)
    extra_args: list[str] = Field(default_factory=list)
    _PASSTHROUGH_CONFLICT_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "startup_mode",
            "model_path",
            "models_dir",
            "models_preset",
            "models_max",
            "models_autoload",
            "sleep_idle_seconds",
            "n_gpu_layers",
            "n_ctx",
            "n_parallel",
            "flash_attn",
            "cache_type_k",
            "cache_type_v",
            "n_cpu_moe",
            "split_mode",
            "threads",
            "threads_batch",
            "jinja",
            "chat_template",
            "lora_adapters",
            "extra_args",
            "llm_defaults",
        }
    )

    def resolved_mode(self) -> Literal["single", "router"]:
        """Resolve runtime mode from startup preference and model inputs."""
        if self.startup_mode == LlamaCppMode.SINGLE:
            return "single"
        if self.startup_mode == LlamaCppMode.ROUTER:
            return "router"
        if self.model_path:
            return "single"
        return "router"

    @model_validator(mode="after")
    def _validate_runtime_contract(self) -> LlamaCppSoulstone:
        """Reject mixed command authority and enforce mode prerequisites."""
        if self.exec:
            conflicting = sorted(field for field in self._PASSTHROUGH_CONFLICT_FIELDS if field in self.model_fields_set)
            if conflicting:
                joined = ", ".join(conflicting)
                msg = (
                    "LlamaCppSoulstone uses exec passthrough, but managed fields were also set: "
                    f"{joined}. Remove managed fields or remove 'exec'."
                )
                raise ValueError(msg)
            return self

        if self.resolved_mode() == "single":
            if not self.model_path:
                msg = "LlamaCppSoulstone in single mode requires 'model_path'."
                raise ValueError(msg)
            return self

        if self.models_dir or self.models_preset:
            return self
        if self._router_source_in_extra_args() or self._router_source_in_env():
            return self

        msg = (
            "LlamaCppSoulstone in router mode requires 'models_dir' or 'models_preset' "
            "(or router flags in extra_args/env_vars)."
        )
        raise ValueError(msg)

    def _router_source_in_extra_args(self) -> bool:
        """Return True when extra args provide router model source flags."""
        for arg in self.extra_args:
            if arg in {"--models-dir", "--models-preset"}:
                return True
            if arg.startswith(("--models-dir=", "--models-preset=")):
                return True
        return False

    def _router_source_in_env(self) -> bool:
        """Return True when env vars provide router model source."""
        return bool(self.env_vars.get("LLAMA_ARG_MODELS_DIR") or self.env_vars.get("LLAMA_ARG_MODELS_PRESET"))
