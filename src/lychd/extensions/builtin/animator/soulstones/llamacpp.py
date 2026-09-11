from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, model_validator

from lychd.config import QuadletConfig
from lychd.domain.animation.schemas import SoulstoneConfig

_MAX_PORT = 65535


class LlamaCppMode(StrEnum):
    """Operational mode for llama.cpp server."""

    AUTO = "auto"
    SINGLE = "single"
    ROUTER = "router"


class LlamaCppSoulstoneConfig(SoulstoneConfig):
    """llama.cpp single-model or router runtime declarations.

    Contract:
    - ``exec`` present => passthrough mode (command is authoritative)
    - ``exec`` absent  => managed mode (typed fields synthesize command args)
    - managed single mode requires ``model_path``
    - managed router mode requires ``models_dir``/``models_preset`` or equivalent router flags
    - engine idle sleep is disabled; passthrough must explicitly carry the disabling flag
    """

    path_fragment: ClassVar[Path] = Path("llamacpp")
    runtime: Literal["llamacpp"] = "llamacpp"  # pyright: ignore[reportIncompatibleVariableOverride]
    quadlet: QuadletConfig = Field(
        default_factory=lambda: QuadletConfig(image="ghcr.io/ggml-org/llama.cpp:server-cuda")
    )

    startup_mode: LlamaCppMode = LlamaCppMode.AUTO
    models_dir: str | None = None
    models_preset: str | None = None
    models_max: int | None = Field(default=None, ge=0)
    models_autoload: bool = True
    sleep_idle_seconds: Literal[-1] | None = Field(
        default=None,
        description="Engine idle sleep is unsupported; omitted or -1 emits --sleep-idle-seconds -1.",
    )

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

    lora_adapters: tuple[str, ...] = Field(default_factory=tuple)
    extra_args: tuple[str, ...] = Field(default_factory=tuple)
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
    def _validate_runtime_contract(self) -> LlamaCppSoulstoneConfig:
        """Reject mixed command authority and enforce mode prerequisites."""
        self._validate_endpoint_port()
        if self.exec:
            conflicting = sorted(field for field in self._PASSTHROUGH_CONFLICT_FIELDS if field in self.model_fields_set)
            if conflicting:
                joined = ", ".join(conflicting)
                msg = (
                    "LlamaCppSoulstoneConfig uses exec passthrough, but managed fields were also set: "
                    f"{joined}. Remove managed fields or remove 'exec'."
                )
                raise ValueError(msg)
            self._validate_sleep_contract()
            return self

        self._validate_sleep_contract()
        if self.resolved_mode() == "single":
            if not self.model_path:
                msg = "LlamaCppSoulstoneConfig in single mode requires 'model_path'."
                raise ValueError(msg)
            return self

        if self.models_dir or self.models_preset:
            return self
        if self._router_source_in_extra_args() or self._router_source_in_env():
            return self

        msg = (
            "LlamaCppSoulstoneConfig in router mode requires 'models_dir' or 'models_preset' "
            "(or router flags in extra_args/env_vars)."
        )
        raise ValueError(msg)

    def _validate_sleep_contract(self) -> None:
        """Admit only commands that keep readiness transitions under Orchestrator."""
        remaining = self.extra_args
        if self.exec:
            offset = int(bool(self.exec[0]) and not self.exec[0].startswith("-"))
            if tuple(self.exec[offset : offset + 2]) != ("--sleep-idle-seconds", "-1"):
                msg = (
                    "The llama.cpp profile requires --sleep-idle-seconds -1 at the start of exec "
                    "arguments or immediately after a non-option executable token."
                )
                raise ValueError(msg)
            remaining = self.exec[offset + 2 :]
        # Reject even a disabling lookalike consumed as another option's value.
        # We do not clone upstream's full option-arity grammar to prove its role.
        if any(arg.partition("=")[0].replace("_", "-") == "--sleep-idle-seconds" for arg in remaining):
            msg = (
                "The llama.cpp profile forbids later --sleep-idle-seconds controls in exec or extra_args, "
                "including duplicates, underscore aliases, and equals spellings."
            )
            raise ValueError(msg)

    def _validate_endpoint_port(self) -> None:
        """Reject a known command port that disagrees with the admitted endpoint."""
        if self.port is None:
            # Declaration compilation allocates the endpoint and revalidates.
            return

        from lychd.extensions.builtin.animator.llamacpp.parser_cli import LlamaCppCliInferenceParser

        parser = LlamaCppCliInferenceParser()
        inferred = parser.infer_args(list(self.exec or self.extra_args))
        if self.exec:
            inferred = parser.merge(primary=inferred, secondary=parser.infer_env(self.env_vars))
        # Managed commands emit their typed port before extra_args, overriding
        # the environment. Unknown or invalid passthrough syntax proves no port.
        if inferred.port is not None and 1 <= inferred.port <= _MAX_PORT and inferred.port != self.port:
            msg = (
                f"LlamaCppSoulstoneConfig declares endpoint port {self.port}, but its runtime inputs "
                f"declare listening port {inferred.port}. Set 'port' to match the command or correct the command."
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
