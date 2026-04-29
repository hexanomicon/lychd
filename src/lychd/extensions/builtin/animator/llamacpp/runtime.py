from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import structlog

from lychd.domain.animation.schemas import ModelInfo
from lychd.extensions.builtin.animator.llamacpp.parser import (
    LlamaCppCommandParser,
    LlamaCppPresetDefaults,
    LlamaCppPresetDocument,
    LlamaCppRuntimeInference,
)
from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstone

logger = structlog.get_logger()


@dataclass(slots=True)
class LlamaCppDescriptor:
    mode: Literal["single", "router"]
    model_infos: tuple[ModelInfo, ...]
    default_model_id: str | None
    router_query_model_id: str | None
    metadata: dict[str, object]


class LlamaCppRuntimePlanner:
    """Build llama.cpp command plans and connector metadata."""

    def plan_exec_args(
        self,
        *,
        soulstone: LlamaCppSoulstone,
        inferred: LlamaCppRuntimeInference,
        mode: Literal["single", "router"],
        listen_host: str,
    ) -> list[str]:
        args = self._common_args(soulstone=soulstone, listen_host=listen_host)
        if mode == "single":
            args = self._single_mode_args(soulstone=soulstone, args=args, inferred=inferred)
        else:
            args = self._router_mode_args(soulstone=soulstone, args=args, inferred=inferred)
        return self._append_optional_args(soulstone=soulstone, args=args)

    def describe_runtime(
        self,
        *,
        soulstone: LlamaCppSoulstone,
        inferred: LlamaCppRuntimeInference,
        mode: Literal["single", "router"],
        parser: LlamaCppCommandParser,
    ) -> LlamaCppDescriptor:
        model_provider = inferred.model_provider or self.preferred_model_id(soulstone) or soulstone.name
        models_preset = inferred.models_preset or soulstone.models_preset
        model_path = inferred.model_path or soulstone.model_path
        preset_doc = parser.load_preset(models_preset) if models_preset else None
        preset_defaults = (
            parser.parse_preset_defaults(
                path=models_preset,
                model_provider=model_provider,
                model_path=model_path,
                preset=preset_doc,
            )
            if models_preset
            else LlamaCppPresetDefaults(values={})
        )
        effective_defaults = {**preset_defaults.values, **self.inferred_defaults(inferred)}

        catalog = self._discover_model_catalog(
            soulstone_name=soulstone.name,
            mode=mode,
            model_provider=model_provider,
            models_preset=models_preset,
            preset_doc=preset_doc,
        )
        model_infos = tuple(ModelInfo(id=item) for item in catalog)
        exec_diagnostics = self.exec_diagnostics(soulstone=soulstone, parser=parser)

        metadata: dict[str, object] = {
            "models_dir": inferred.models_dir or soulstone.models_dir,
            "models_preset": models_preset,
            "mode": mode,
            "inferred_from": inferred.source,
            "inferred_model_path": inferred.model_path,
            "inferred_n_ctx": inferred.n_ctx,
            "inferred_n_parallel": inferred.n_parallel,
            "preset_defaults": preset_defaults.values,
            "preset_model_section": preset_defaults.model_section,
            "effective_defaults": effective_defaults,
            "exec_passthrough": bool(soulstone.exec),
            "exec_diagnostics": exec_diagnostics,
        }
        if model_path:
            metadata["model_path"] = model_path

        router_query_model_id = model_provider if mode == "router" else None
        return LlamaCppDescriptor(
            mode=mode,
            model_infos=model_infos,
            default_model_id=model_provider,
            router_query_model_id=router_query_model_id,
            metadata=metadata,
        )

    def inferred_defaults(self, inferred: LlamaCppRuntimeInference) -> dict[str, object]:
        defaults: dict[str, object] = {}
        if inferred.n_ctx is not None:
            defaults["n_ctx"] = inferred.n_ctx
        if inferred.n_parallel is not None:
            defaults["n_parallel"] = inferred.n_parallel
        if inferred.n_predict is not None:
            defaults["n_predict"] = inferred.n_predict
        if inferred.temperature is not None:
            defaults["temperature"] = inferred.temperature
        if inferred.top_k is not None:
            defaults["top_k"] = inferred.top_k
        if inferred.top_p is not None:
            defaults["top_p"] = inferred.top_p
        if inferred.min_p is not None:
            defaults["min_p"] = inferred.min_p
        if inferred.reasoning_format is not None:
            defaults["reasoning_format"] = inferred.reasoning_format
        return defaults

    def exec_diagnostics(self, *, soulstone: LlamaCppSoulstone, parser: LlamaCppCommandParser) -> list[str]:
        if not soulstone.exec:
            return []
        return parser.inspect_exec_args(list(soulstone.exec))

    def preferred_model_id(self, soulstone: LlamaCppSoulstone) -> str:
        if soulstone.models:
            return next(iter(soulstone.models.values())).id
        if soulstone.model_path:
            return Path(soulstone.model_path).stem
        return soulstone.name

    def _single_mode_args(
        self,
        *,
        soulstone: LlamaCppSoulstone,
        args: list[str],
        inferred: LlamaCppRuntimeInference,
    ) -> list[str]:
        result = list(args)
        model_ref = inferred.model_path or soulstone.model_path
        if model_ref:
            result = ["-m", model_ref, *result]
        result.extend(["--alias", inferred.model_provider or self.preferred_model_id(soulstone)])
        return result

    def _router_mode_args(
        self,
        *,
        soulstone: LlamaCppSoulstone,
        args: list[str],
        inferred: LlamaCppRuntimeInference,
    ) -> list[str]:
        models_dir = inferred.models_dir or soulstone.models_dir
        models_preset = inferred.models_preset or soulstone.models_preset
        if models_dir:
            args.extend(["--models-dir", models_dir])
        if models_preset:
            args.extend(["--models-preset", models_preset])
        if soulstone.models_max is not None:
            args.extend(["--models-max", str(soulstone.models_max)])
        if soulstone.models_autoload:
            args.append("--models-autoload")
        else:
            args.append("--no-models-autoload")
        return args

    def _append_optional_args(self, *, soulstone: LlamaCppSoulstone, args: list[str]) -> list[str]:
        if soulstone.sleep_idle_seconds is not None:
            args.extend(["--sleep-idle-seconds", str(soulstone.sleep_idle_seconds)])
        if soulstone.chat_template:
            args.extend(["--chat-template", soulstone.chat_template])
        for adapter in soulstone.lora_adapters:
            args.extend(["--lora", adapter])
        args.extend(soulstone.extra_args)
        return args

    def _common_args(self, *, soulstone: LlamaCppSoulstone, listen_host: str) -> list[str]:
        args = [
            "--host",
            listen_host,
            "--port",
            str(soulstone.port),
            "-ngl",
            str(soulstone.n_gpu_layers),
            "-c",
            str(soulstone.n_ctx),
            "-np",
            str(soulstone.n_parallel),
            "-ctk",
            soulstone.cache_type_k,
            "-ctv",
            soulstone.cache_type_v,
            "-sm",
            soulstone.split_mode,
        ]
        args.extend(["-fa", "on" if soulstone.flash_attn else "off"])
        args.extend(["--jinja" if soulstone.jinja else "--no-jinja"])

        if soulstone.n_cpu_moe is not None:
            args.extend(["--n-cpu-moe", str(soulstone.n_cpu_moe)])
        if soulstone.threads is not None:
            args.extend(["-t", str(soulstone.threads)])
        if soulstone.threads_batch is not None:
            args.extend(["-tb", str(soulstone.threads_batch)])
        return args

    def _discover_model_catalog(
        self,
        *,
        soulstone_name: str,
        mode: Literal["single", "router"],
        model_provider: str,
        models_preset: str | None,
        preset_doc: LlamaCppPresetDocument | None,
    ) -> list[str]:
        if mode == "single":
            return [model_provider]

        if not models_preset:
            return [model_provider]

        if preset_doc is None:
            return [model_provider]

        if preset_doc.error == "missing":
            logger.warning("llamacpp_models_preset_missing", path=str(preset_doc.path), soulstone=soulstone_name)
            return [model_provider]

        if preset_doc.error == "read_error":
            logger.warning(
                "llamacpp_models_preset_parse_failed",
                path=str(preset_doc.path),
                soulstone=soulstone_name,
                error="read_error",
            )
            return [model_provider]

        catalog = [section for section in preset_doc.sections if section and section != "*"]

        if model_provider and model_provider not in catalog:
            catalog.insert(0, model_provider)

        return list(dict.fromkeys(catalog))


__all__ = ["LlamaCppDescriptor", "LlamaCppRuntimePlanner"]
