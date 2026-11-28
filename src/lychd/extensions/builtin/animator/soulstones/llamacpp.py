from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal

from pydantic import Field, model_validator

from lychd.config import QuadletConfig
from lychd.domain.animation.schemas import SoulstoneConfig

if TYPE_CHECKING:
    from lychd.extensions.builtin.animator.llamacpp.parser_models import LlamaCppRuntimeInference

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
    - explicit managed startup mode wins over inference; AUTO uses inferred mode first
    - managed single mode requires ``model_path``
    - forced modes refuse known main-model source arguments
    - forced single refuses HF repository environment controls; router refuses model-source environment controls
    - AUTO/exec refuse effective main HF repositories, main-model presets, and ambiguous source syntax
    - managed router mode requires ``models_dir``/``models_preset`` or equivalent router flags
    - engine idle sleep is disabled; passthrough must explicitly carry the disabling flag
    """

    path_fragment: ClassVar[Path] = Path("llamacpp")
    runtime: Literal["llamacpp"] = "llamacpp"  # pyright: ignore[reportIncompatibleVariableOverride]
    quadlet: QuadletConfig = Field(
        default_factory=lambda: QuadletConfig(image="ghcr.io/ggml-org/llama.cpp:server-cuda")
    )

    embedding_profile: Literal["qwen3-06b-q8-b9445@1"] | None = None

    structured_output: Literal["json-schema"] | None = None
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

    # Main-model controls and presets from upstream arg.cpp at
    # 434ddbbc0e30522e897670681e503b797c12b7c1. Draft-only controls and
    # --spec-default do not select a main model and are not refused here.
    _MODEL_PRESET_FLAGS: ClassVar[frozenset[str]] = frozenset(
        {
            "--embd-gemma-default",
            "--fim-qwen-1.5b-default",
            "--fim-qwen-3b-default",
            "--fim-qwen-7b-default",
            "--fim-qwen-7b-spec",
            "--fim-qwen-14b-spec",
            "--fim-qwen-30b-default",
            "--gpt-oss-20b-default",
            "--gpt-oss-120b-default",
            "--vision-gemma-4b-default",
            "--vision-gemma-12b-default",
        }
    )
    _SINGLE_MODEL_SOURCE_FLAGS: ClassVar[frozenset[str]] = (
        frozenset(
            {
                "-m",
                "--model",
                "-mu",
                "--model-url",
                "-dr",
                "--docker-repo",
                "-hf",
                "-hfr",
                "--hf-repo",
                "-hff",
                "--hf-file",
            }
        )
        | _MODEL_PRESET_FLAGS
    )
    _SINGLE_MODEL_SOURCE_ENV: ClassVar[frozenset[str]] = frozenset(
        {"LLAMA_ARG_MODEL", "LLAMA_ARG_MODEL_URL", "LLAMA_ARG_DOCKER_REPO", "LLAMA_ARG_HF_REPO", "LLAMA_ARG_HF_FILE"}
    )

    def _validate_native_placement(self) -> None:
        """Admit the trusted fixed-model plan without command or container overrides."""
        if (
            not self.concurrency.dedicated
            or self.startup_mode != LlamaCppMode.SINGLE
            or not self.model_path
            or self.extra_args
            or self.lora_adapters
            or self.embedding_profile
            or self.models_dir
            or self.models_preset
            or self.chat_template
            or self.model_fields_set.intersection({"models_max", "models_autoload"})
        ):
            msg = f"Native llama.cpp Soulstone {self.name!r} requires a dedicated fixed single model without router, adapter, embedding or command overrides."
            raise ValueError(msg)

    def resolved_mode(self, inferred_mode: Literal["single", "router"] | None = None) -> Literal["single", "router"]:
        """Honor explicit startup intent; infer AUTO before the typed-model fallback."""
        if self.startup_mode == LlamaCppMode.SINGLE:
            return "single"
        if self.startup_mode == LlamaCppMode.ROUTER:
            return "router"
        if inferred_mode is not None:
            return inferred_mode
        if self.model_path:
            return "single"
        return "router"

    @model_validator(mode="after")
    def _validate_runtime_contract(self) -> LlamaCppSoulstoneConfig:
        """Reject mixed command authority and enforce mode prerequisites."""
        if self.embedding_profile is not None:
            from lychd.extensions.builtin.animator.llamacpp.embedding_profile import require_profile_config

            require_profile_config(self)
            return self
        if self.structured_output is not None and self.startup_mode != LlamaCppMode.SINGLE:
            msg = "JSON Schema output requires a fixed single-model llama.cpp Rune."
            raise ValueError(msg)
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
            self._validate_inferred_sources()
            return self

        self._validate_sleep_contract()
        self._validate_forced_mode_sources()
        inferred = self._validate_inferred_sources()
        if self.resolved_mode() == "single":
            if not self.model_path:
                msg = "LlamaCppSoulstoneConfig in single mode requires 'model_path'."
                raise ValueError(msg)
            return self

        if self.models_dir or self.models_preset:
            return self
        if inferred.models_dir or inferred.models_preset:
            return self

        msg = (
            "LlamaCppSoulstoneConfig in router mode requires 'models_dir' or 'models_preset' "
            "(or router flags in extra_args/env_vars)."
        )
        raise ValueError(msg)

    def inference_env(self) -> dict[str, str]:
        """Project the environment used by Transmutation without reading secrets."""
        return {
            **self.env_vars,
            **{key: f"/run/secrets/{name}" for key, name in self.secret_env_files.items()},
        }

    def _validate_inferred_sources(self) -> LlamaCppRuntimeInference:
        """Refuse sources whose mutable remote presets can change startup mode."""
        from lychd.extensions.builtin.animator.llamacpp.parser_cli import LlamaCppCliInferenceParser

        arguments = list(self.exec or self.extra_args)
        if any(arg.partition("=")[0].replace("_", "-") in self._MODEL_PRESET_FLAGS for arg in arguments):
            msg = "The llama.cpp profile cannot classify remote-resolved main-model presets. Use a local model path."
            raise ValueError(msg)
        parser = LlamaCppCliInferenceParser()
        inferred = parser.merge(primary=parser.infer_args(arguments), secondary=parser.infer_env(self.inference_env()))
        if inferred.hf_repo:
            msg = "The llama.cpp profile cannot classify a remote-resolved main-model HF repository. Use a local model path."
            raise ValueError(msg)
        return inferred

    def _validate_forced_mode_sources(self) -> None:
        """Refuse known controls that can defeat a forced startup mode."""
        if self.startup_mode == LlamaCppMode.AUTO:
            return
        # Token lookalikes are refused even in value positions, without guessing
        # upstream option arity. A final empty -m can clear the generated model;
        # an HF remote preset can clear it before upstream selects server mode.
        conflicting_sources: list[str] = []
        if any(arg.partition("=")[0].replace("_", "-") in self._SINGLE_MODEL_SOURCE_FLAGS for arg in self.extra_args):
            conflicting_sources.append("extra_args")
        env_keys = self._SINGLE_MODEL_SOURCE_ENV if self.startup_mode == LlamaCppMode.ROUTER else {"LLAMA_ARG_HF_REPO"}
        if any(self.env_vars.get(key) for key in env_keys):
            conflicting_sources.append("env_vars")
        # Transmutation projects each secret mapping as a nonempty /run/secrets
        # path, overriding env_vars. Admission needs keys, never secret contents.
        if any(key in self.secret_env_files for key in env_keys):
            conflicting_sources.append("secret_env_files")
        if conflicting_sources:
            msg = (
                f"LlamaCppSoulstoneConfig in forced {self.startup_mode} mode forbids model-source controls "
                f"in {', '.join(conflicting_sources)}. Use model_path for single mode or router model directories/presets."
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
