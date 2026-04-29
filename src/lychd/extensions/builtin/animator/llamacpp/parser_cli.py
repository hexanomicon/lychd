from __future__ import annotations

from pathlib import Path
from typing import Final, Literal

from lychd.extensions.builtin.animator.llamacpp.parser_models import LlamaCppRuntimeInference


class LlamaCppCliInferenceParser:
    """Infer llama.cpp runtime metadata from CLI/env inputs."""

    _NO_VALUE_FLAGS: Final[set[str]] = {
        "--models-autoload",
        "--no-models-autoload",
        "--jinja",
        "--no-jinja",
    }
    _SHORT_TO_LONG: Final[dict[str, str]] = {
        "-m": "--model",
        "-mu": "--model-url",
        "-dr": "--docker-repo",
        "-hf": "--hf-repo",
        "-hfr": "--hf-repo",
        "-hff": "--hf-file",
        "-hfd": "--hf-repo-draft",
        "-a": "--alias",
        "-c": "--ctx-size",
        "-n": "--n-predict",
        "-np": "--parallel",
    }
    _LONG_TO_CANONICAL: Final[dict[str, str]] = {
        "--predict": "--n-predict",
    }
    _SINGLE_SOURCE_FLAGS: Final[set[str]] = {
        "--model",
        "--model-url",
        "--docker-repo",
        "--hf-repo",
        "--hf-file",
        "--hf-repo-draft",
    }
    _ROUTER_FLAGS: Final[set[str]] = {
        "--models-dir",
        "--models-preset",
    }

    def infer_args(self, args: list[str], *, source: str) -> LlamaCppRuntimeInference:
        """Infer runtime metadata from explicit CLI args."""
        if not args:
            return LlamaCppRuntimeInference()

        options = self._parse_cli_options(args)
        mode = self._infer_mode(options)
        model_provider = self._infer_model_provider(options)
        return LlamaCppRuntimeInference(
            mode=mode,
            model_provider=model_provider,
            model_path=self._as_str(options.get("--model")),
            models_dir=self._as_str(options.get("--models-dir")),
            models_preset=self._as_str(options.get("--models-preset")),
            n_ctx=self._as_int(options.get("--ctx-size")),
            n_parallel=self._as_int(options.get("--parallel")),
            n_predict=self._as_int(options.get("--n-predict")),
            temperature=self._as_float(options.get("--temp")),
            top_k=self._as_int(options.get("--top-k")),
            top_p=self._as_float(options.get("--top-p")),
            min_p=self._as_float(options.get("--min-p")),
            reasoning_format=self._as_str(options.get("--reasoning-format")),
            source=source,
        )

    def infer_env(self, env: dict[str, str]) -> LlamaCppRuntimeInference:
        """Infer runtime metadata from LLAMA_ARG_* environment variables."""
        if not env:
            return LlamaCppRuntimeInference()

        mode: Literal["single", "router"] | None = None
        if env.get("LLAMA_ARG_MODELS_DIR") or env.get("LLAMA_ARG_MODELS_PRESET"):
            mode = "router"
        elif any(
            env.get(k)
            for k in (
                "LLAMA_ARG_MODEL",
                "LLAMA_ARG_MODEL_URL",
                "LLAMA_ARG_DOCKER_REPO",
                "LLAMA_ARG_HF_REPO",
                "LLAMA_ARG_HF_FILE",
                "LLAMA_ARG_HFD_REPO",
            )
        ):
            mode = "single"

        return LlamaCppRuntimeInference(
            mode=mode,
            model_provider=env.get("LLAMA_ARG_ALIAS"),
            model_path=env.get("LLAMA_ARG_MODEL"),
            models_dir=env.get("LLAMA_ARG_MODELS_DIR"),
            models_preset=env.get("LLAMA_ARG_MODELS_PRESET"),
            n_ctx=self._as_int(env.get("LLAMA_ARG_CTX_SIZE")),
            n_parallel=self._as_int(env.get("LLAMA_ARG_N_PARALLEL")),
            n_predict=self._as_int(env.get("LLAMA_ARG_N_PREDICT")),
            temperature=self._as_float(env.get("LLAMA_ARG_TEMPERATURE")),
            top_k=self._as_int(env.get("LLAMA_ARG_TOP_K")),
            top_p=self._as_float(env.get("LLAMA_ARG_TOP_P")),
            min_p=self._as_float(env.get("LLAMA_ARG_MIN_P")),
            reasoning_format=env.get("LLAMA_ARG_THINK"),
            source="env_vars",
        )

    def merge(
        self,
        *,
        primary: LlamaCppRuntimeInference,
        secondary: LlamaCppRuntimeInference,
    ) -> LlamaCppRuntimeInference:
        """Merge inferences with primary taking precedence."""
        return LlamaCppRuntimeInference(
            mode=primary.mode or secondary.mode,
            model_provider=primary.model_provider or secondary.model_provider,
            model_path=primary.model_path or secondary.model_path,
            models_dir=primary.models_dir or secondary.models_dir,
            models_preset=primary.models_preset or secondary.models_preset,
            n_ctx=primary.n_ctx if primary.n_ctx is not None else secondary.n_ctx,
            n_parallel=primary.n_parallel if primary.n_parallel is not None else secondary.n_parallel,
            n_predict=primary.n_predict if primary.n_predict is not None else secondary.n_predict,
            temperature=primary.temperature if primary.temperature is not None else secondary.temperature,
            top_k=primary.top_k if primary.top_k is not None else secondary.top_k,
            top_p=primary.top_p if primary.top_p is not None else secondary.top_p,
            min_p=primary.min_p if primary.min_p is not None else secondary.min_p,
            reasoning_format=primary.reasoning_format or secondary.reasoning_format,
            source=primary.source or secondary.source,
        )

    def inspect_exec_args(self, args: list[str]) -> list[str]:
        """Return non-fatal diagnostics for explicit exec passthrough usage."""
        if not args:
            return []

        options = self._parse_cli_options(args)
        diagnostics: list[str] = []

        has_host = "--host" in options
        has_port = "--port" in options
        has_single_source = any(key in options for key in self._SINGLE_SOURCE_FLAGS)
        has_router_source = any(key in options for key in self._ROUTER_FLAGS)

        if not has_host:
            diagnostics.append("exec_missing_host_flag")
        if not has_port:
            diagnostics.append("exec_missing_port_flag")
        if not has_single_source and not has_router_source:
            diagnostics.append("exec_missing_model_or_router_source")
        if has_single_source and has_router_source:
            diagnostics.append("exec_mixes_single_and_router_flags")
        return diagnostics

    def _parse_cli_options(self, args: list[str]) -> dict[str, str | bool]:
        options: dict[str, str | bool] = {}
        index = 0
        while index < len(args):
            token = args[index]

            if token in self._SHORT_TO_LONG:
                key = self._SHORT_TO_LONG[token]
                if index + 1 < len(args) and not args[index + 1].startswith("-"):
                    options[key] = args[index + 1]
                    index += 2
                    continue
                options[key] = True
                index += 1
                continue

            if not token.startswith("--"):
                index += 1
                continue

            if "=" in token:
                raw_key, value = token.split("=", 1)
                key = self._LONG_TO_CANONICAL.get(raw_key, raw_key)
                options[key] = value
                index += 1
                continue

            key = self._LONG_TO_CANONICAL.get(token, token)

            if key in self._NO_VALUE_FLAGS:
                options[key] = True
                index += 1
                continue

            if index + 1 < len(args) and not args[index + 1].startswith("-"):
                options[key] = args[index + 1]
                index += 2
                continue

            options[key] = True
            index += 1

        return options

    def _infer_mode(self, options: dict[str, str | bool]) -> Literal["single", "router"] | None:
        keys = set(options.keys())
        if keys.intersection(self._ROUTER_FLAGS):
            return "router"

        if keys.intersection(self._SINGLE_SOURCE_FLAGS):
            return "single"

        if any(key.endswith("-default") for key in keys):
            return "single"

        return None

    def _infer_model_provider(self, options: dict[str, str | bool]) -> str | None:
        alias = self._as_str(options.get("--alias"))
        if alias:
            return alias

        for key in ("--hf-repo", "--docker-repo"):
            value = self._as_str(options.get(key))
            if value:
                return value

        model = self._as_str(options.get("--model"))
        if model:
            return Path(model).stem

        for key, value in options.items():
            if key.endswith("-default") and isinstance(value, bool) and value:
                return key.removeprefix("--").removesuffix("-default")

        return None

    def _as_str(self, value: object) -> str | None:
        if isinstance(value, str):
            return value
        return None

    def _as_int(self, value: object) -> int | None:
        if not isinstance(value, str):
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _as_float(self, value: object) -> float | None:
        if not isinstance(value, str):
            return None
        try:
            return float(value)
        except ValueError:
            return None


__all__ = ["LlamaCppCliInferenceParser"]
