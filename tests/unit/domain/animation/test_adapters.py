from __future__ import annotations

from pathlib import Path
from typing import cast

from lychd.domain.animation.schemas import ModelSurface
from lychd.domain.animation.services.adapters.contracts import RuntimePlan
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.adapters.surfaces import LlamacppConnector, OpenAICompatibleConnector
from lychd.extensions.builtin.animator import LlamaCppSoulstone, SglangSoulstone, VllmSoulstone


def _build_llamacpp_connector(soulstone: LlamaCppSoulstone) -> tuple[LlamacppConnector, RuntimePlan]:
    registry = RuntimeAdapterRegistry()
    runtime = registry.build_runtime(soulstone)
    assert runtime is not None
    connector = runtime.connector
    assert isinstance(connector, LlamacppConnector)
    return connector, registry.plan(soulstone)


def _build_vllm_connector(soulstone: VllmSoulstone) -> tuple[OpenAICompatibleConnector, RuntimePlan]:
    registry = RuntimeAdapterRegistry()
    runtime = registry.build_runtime(soulstone)
    assert runtime is not None
    connector = runtime.connector
    assert isinstance(connector, OpenAICompatibleConnector)
    return connector, registry.plan(soulstone)


def _build_sglang_connector(soulstone: SglangSoulstone) -> tuple[OpenAICompatibleConnector, RuntimePlan]:
    registry = RuntimeAdapterRegistry()
    runtime = registry.build_runtime(soulstone)
    assert runtime is not None
    connector = runtime.connector
    assert isinstance(connector, OpenAICompatibleConnector)
    return connector, registry.plan(soulstone)


def test_llamacpp_single_mode_plan() -> None:
    soulstone = LlamaCppSoulstone.model_validate(
        {
            "name": "qwen-local",
            "model_path": "/models/qwen.gguf",
        }
    )

    connector, plan = _build_llamacpp_connector(soulstone)

    assert connector.mode == "single"
    assert plan.exec_args[:2] == ["-m", "/models/qwen.gguf"]
    assert "--alias" in plan.exec_args
    assert "qwen" in plan.exec_args
    assert [info.id for info in connector.list_models()] == ["qwen"]


def test_llamacpp_router_mode_detects_preset_models(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        (
            "version = 1\n\n"
            "[*]\n"
            "c = 8192\n\n"
            "[qwen3-64k]\n"
            "model = /models/qwen3-64k.gguf\n\n"
            "[qwen3-150k]\n"
            "model = /models/qwen3-150k.gguf\n"
        ),
        encoding="utf-8",
    )

    soulstone = LlamaCppSoulstone.model_validate(
        {
            "name": "qwen-router",
            "startup_mode": "router",
            "models_preset": str(preset),
            "models": {
                "default": {
                    "id": "qwen3-64k",
                    "path": "/models/qwen3-64k.gguf",
                }
            },
        }
    )

    connector, plan = _build_llamacpp_connector(soulstone)
    model_ids = [info.id for info in connector.list_models()]

    assert connector.mode == "router"
    assert connector.router_query_model_id == "qwen3-64k"
    assert "qwen3-64k" in model_ids
    assert "qwen3-150k" in model_ids
    assert "--models-preset" in plan.exec_args
    assert str(preset) in plan.exec_args


def test_vllm_openai_compatible_plan() -> None:
    soulstone = VllmSoulstone.model_validate(
        {
            "name": "glm47",
            "model_path": "/models/GLM-4.7-Flash-AWQ-4bit",
            "models": {
                "default": {
                    "id": "glm-4.7-flash",
                    "path": "/models/GLM-4.7-Flash-AWQ-4bit",
                }
            },
            "tensor_parallel_size": 2,
            "language_model_only": True,
            "tool_call_parser": "glm47",
            "reasoning_parser": "glm45",
            "enable_auto_tool_choice": True,
            "trust_remote_code": True,
            "ipc_host": True,
        }
    )

    connector, plan = _build_vllm_connector(soulstone)

    assert connector.kind == "vllm"
    assert [info.id for info in connector.list_models()] == ["glm-4.7-flash"]
    assert plan.exec_args[0] == "serve"
    assert "--served-model-name" in plan.exec_args
    assert "glm-4.7-flash" in plan.exec_args
    assert "--language-model-only" in plan.exec_args
    assert "--tool-call-parser" in plan.exec_args
    assert "glm47" in plan.exec_args
    assert "--reasoning-parser" in plan.exec_args
    assert "glm45" in plan.exec_args
    assert "--enable-auto-tool-choice" in plan.exec_args
    assert "--trust-remote-code" in plan.exec_args
    assert "--ipc=host" in plan.podman_args
    assert connector.list_models()[0].supports_tools is True


def test_vllm_model_capability_hints_override_runtime_defaults() -> None:
    soulstone = VllmSoulstone.model_validate(
        {
            "name": "vllm-capability-overrides",
            "model_path": "/models/fallback-awq",
            "capabilities": {
                "modalities_in": ["text", "image"],
                "modalities_out": ["text"],
                "supports_tools": False,
            },
            "models": {
                "default": {
                    "id": "vision-model",
                    "path": "/models/vision-awq",
                    "capabilities": {
                        "surface": "responses",
                        "modalities_in": ["image", "text"],
                        "modalities_out": ["text"],
                        "supports_streaming": False,
                    },
                }
            },
        }
    )

    connector, _ = _build_vllm_connector(soulstone)
    model = connector.list_models()[0]

    assert model.id == "vision-model"
    assert model.surface == ModelSurface.RESPONSES
    assert model.modalities_in == ["image", "text"]
    assert model.modalities_out == ["text"]
    assert model.supports_tools is False
    assert model.supports_streaming is False


def test_sglang_openai_compatible_plan() -> None:
    soulstone = SglangSoulstone.model_validate(
        {
            "name": "qwen-sglang",
            "model_path": "/models/qwen-awq",
            "tensor_parallel_size": 2,
            "chat_template": "chatml",
            "attention_backend": "flashinfer",
            "quantization": "awq",
            "trust_remote_code": True,
            "enable_marlin": True,
        }
    )

    connector, plan = _build_sglang_connector(soulstone)

    assert connector.kind == "sglang"
    assert [info.id for info in connector.list_models()] == ["qwen-awq"]
    assert plan.exec_args[:4] == ["python3", "-m", "sglang.launch_server", "--model-path"]
    assert "/models/qwen-awq" in plan.exec_args
    assert "--tp" in plan.exec_args
    assert "2" in plan.exec_args
    assert "--chat-template" in plan.exec_args
    assert "chatml" in plan.exec_args
    assert "--attention-backend" in plan.exec_args
    assert "flashinfer" in plan.exec_args
    assert "--quantization" in plan.exec_args
    assert "awq" in plan.exec_args
    assert "--trust-remote-code" in plan.exec_args
    assert "--enable-marlin" in plan.exec_args


def test_llamacpp_resolve_infers_single_mode_and_alias_from_exec() -> None:
    soulstone = LlamaCppSoulstone.model_validate(
        {
            "name": "qwen-cmd",
            "exec": [
                "llama-server",
                "--host",
                "127.0.0.1",
                "--port",
                "18080",
                "-m",
                "/models/qwen-next-80b.gguf",
                "--alias",
                "qwen-next-80b",
                "-c",
                "65536",
                "-np",
                "4",
            ],
        }
    )

    connector, _ = _build_llamacpp_connector(soulstone)
    assert connector.mode == "single"
    assert [info.id for info in connector.list_models()] == ["qwen-next-80b"]
    assert connector.metadata["inferred_from"] == "exec"
    assert connector.metadata["inferred_model_path"] == "/models/qwen-next-80b.gguf"
    assert connector.metadata["inferred_n_ctx"] == 65536
    assert connector.metadata["inferred_n_parallel"] == 4


def test_llamacpp_resolve_infers_router_and_catalog_from_exec_models_preset(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        (
            "version = 1\n\n"
            "[*]\n"
            "c = 8192\n\n"
            "[qwen-next-80b]\n"
            "model = /models/qwen-next-80b.gguf\n\n"
            "[qwen-next-7b]\n"
            "model = /models/qwen-next-7b.gguf\n"
        ),
        encoding="utf-8",
    )

    soulstone = LlamaCppSoulstone.model_validate(
        {
            "name": "router-cmd",
            "exec": [
                "llama-server",
                "--models-preset",
                str(preset),
                "--alias",
                "qwen-next-80b",
            ],
        }
    )

    connector, _ = _build_llamacpp_connector(soulstone)
    model_ids = [info.id for info in connector.list_models()]
    assert connector.mode == "router"
    assert connector.router_query_model_id == "qwen-next-80b"
    assert "qwen-next-80b" in model_ids
    assert "qwen-next-7b" in model_ids
    assert connector.metadata["models_preset"] == str(preset)


def test_llamacpp_resolve_uses_env_when_no_exec_args() -> None:
    soulstone = LlamaCppSoulstone.model_validate(
        {
            "name": "env-driven",
            "env_vars": {
                "LLAMA_ARG_MODELS_PRESET": "/models/models.ini",
                "LLAMA_ARG_ALIAS": "qwen-from-env",
                "LLAMA_ARG_CTX_SIZE": "32768",
                "LLAMA_ARG_N_PARALLEL": "2",
            },
        }
    )

    connector, _ = _build_llamacpp_connector(soulstone)
    assert connector.mode == "router"
    assert connector.router_query_model_id == "qwen-from-env"
    assert connector.metadata["inferred_from"] == "env_vars"
    assert connector.metadata["models_preset"] == "/models/models.ini"
    assert connector.metadata["inferred_n_ctx"] == 32768
    assert connector.metadata["inferred_n_parallel"] == 2


def test_llamacpp_plan_follows_inferred_router_mode_from_extra_args(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        "version = 1\n[*]\nc = 4096\n[qwen-next]\nmodel = /models/qwen-next.gguf\n",
        encoding="utf-8",
    )

    soulstone = LlamaCppSoulstone.model_validate(
        {
            "name": "router-from-extra",
            "model_path": "/models/should-not-force-single.gguf",
            "extra_args": ["--models-preset", str(preset)],
        }
    )

    connector, plan = _build_llamacpp_connector(soulstone)

    assert connector.mode == "router"
    assert "--models-preset" in plan.exec_args
    assert str(preset) in plan.exec_args
    assert "-m" not in plan.exec_args


def test_llamacpp_resolve_infers_n_predict_from_predict_alias() -> None:
    soulstone = LlamaCppSoulstone.model_validate(
        {
            "name": "predict-alias",
            "exec": [
                "llama-server",
                "-m",
                "/models/qwen-next.gguf",
                "--predict",
                "768",
            ],
        }
    )

    connector, _ = _build_llamacpp_connector(soulstone)
    effective_defaults = cast("dict[str, object]", connector.metadata["effective_defaults"])
    assert effective_defaults["n_predict"] == 768


def test_llamacpp_resolve_uses_single_model_section_when_provider_does_not_match(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        ("version = 1\n\n[*]\nc = 4096\n\n[qwen-next-80b]\nc = 65536\ntemp = 0.6\ntop-k = 64\n"),
        encoding="utf-8",
    )

    soulstone = LlamaCppSoulstone.model_validate(
        {
            "name": "router-unmatched-provider",
            "startup_mode": "router",
            "models_preset": str(preset),
        }
    )

    connector, _ = _build_llamacpp_connector(soulstone)
    effective_defaults = cast("dict[str, object]", connector.metadata["effective_defaults"])
    assert connector.metadata["preset_model_section"] == "qwen-next-80b"
    assert effective_defaults["n_ctx"] == 65536
    assert effective_defaults["temperature"] == 0.6
    assert effective_defaults["top_k"] == 64


def test_llamacpp_resolve_effective_defaults_follow_cli_over_preset_precedence(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        (
            "version = 1\n\n"
            "[*]\n"
            "c = 4096\n"
            "temp = 0.55\n"
            "top-k = 32\n\n"
            "[qwen-next-80b]\n"
            "c = 32768\n"
            "temp = 0.7\n"
            "top-k = 48\n"
        ),
        encoding="utf-8",
    )

    soulstone = LlamaCppSoulstone.model_validate(
        {
            "name": "router-precedence",
            "exec": [
                "llama-server",
                "--models-preset",
                str(preset),
                "--alias",
                "qwen-next-80b",
                "-c",
                "131072",
            ],
        }
    )

    connector, _ = _build_llamacpp_connector(soulstone)
    effective = cast("dict[str, object]", connector.metadata["effective_defaults"])
    assert effective["n_ctx"] == 131072
    assert effective["temperature"] == 0.7
    assert effective["top_k"] == 48


def test_llamacpp_resolve_reports_exec_passthrough_diagnostics() -> None:
    soulstone = LlamaCppSoulstone.model_validate(
        {
            "name": "diagnostics",
            "exec": ["llama-server", "-m", "/models/qwen.gguf"],
        }
    )

    connector, _ = _build_llamacpp_connector(soulstone)
    diagnostics = cast("list[str]", connector.metadata["exec_diagnostics"])

    assert connector.metadata["exec_passthrough"] is True
    assert "exec_missing_host_flag" in diagnostics
    assert "exec_missing_port_flag" in diagnostics
