from __future__ import annotations

from pathlib import Path
from typing import cast

import httpx
import pytest
import respx
from pydantic import BaseModel, ValidationError

from lychd.domain.animation.capabilities import CapabilityFamily, CapabilityPhase, CapabilitySpec
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.schemas import GenericSoulstoneConfig, SoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import RuntimePlan
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.adapters.runtimes.openai_compat import OpenAICompatibleRuntimeAdapter
from lychd.domain.animation.services.adapters.surfaces import (
    OpenAICompatibleConnector,
)
from lychd.extensions.builtin.animator import (
    ExLlamaV3SoulstoneConfig,
    LlamaCppSoulstoneConfig,
    SglangSoulstoneConfig,
    VllmSoulstoneConfig,
)
from lychd.extensions.builtin.animator.llamacpp import LlamacppConnector, LlamaCppControlPlane
from lychd.extensions.builtin.animator.runtimes import (
    LlamaCppRuntimeAdapter,
)

pytestmark = pytest.mark.httpx2(assert_all_called=False)


def _vllm_adapter() -> OpenAICompatibleRuntimeAdapter:
    return OpenAICompatibleRuntimeAdapter(runtime="vllm", config_type=VllmSoulstoneConfig)


def _sglang_adapter() -> OpenAICompatibleRuntimeAdapter:
    return OpenAICompatibleRuntimeAdapter(runtime="sglang", config_type=SglangSoulstoneConfig)


def _runtime_registry() -> RuntimeAdapterRegistry:
    """Build a registry wired with the builtin runtime adapters under test."""
    return RuntimeAdapterRegistry(
        adapters=[LlamaCppRuntimeAdapter(), _vllm_adapter(), _sglang_adapter()],
    )


def _capability_specs(registry: RuntimeAdapterRegistry, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
    runtime = registry.build_runtime(soulstone)
    assert runtime is not None
    return registry.build_capability_specs(runtime)


@pytest.mark.parametrize(
    "schema",
    [
        LlamaCppSoulstoneConfig,
        VllmSoulstoneConfig,
        SglangSoulstoneConfig,
        ExLlamaV3SoulstoneConfig,
    ],
)
def test_concrete_soulstone_schema_rejects_foreign_runtime(schema: type[BaseModel]) -> None:
    with pytest.raises(ValidationError) as exc_info:
        schema.model_validate({"name": "wrong-runtime", "runtime": "foreign"})

    assert any(error["loc"] == ("runtime",) and error["type"] == "literal_error" for error in exc_info.value.errors())


def test_generic_soulstone_keeps_open_runtime_selector() -> None:
    stone = GenericSoulstoneConfig.model_validate(
        {
            "name": "custom-runtime",
            "runtime": "extension-owned",
            "quadlet": {"image": "example/runtime:latest"},
        }
    )

    assert stone.runtime == "extension-owned"


def _build_llamacpp_connector(soulstone: LlamaCppSoulstoneConfig) -> tuple[LlamacppConnector, RuntimePlan]:
    registry = _runtime_registry()
    runtime = registry.build_runtime(soulstone)
    assert runtime is not None
    connector = runtime.connector
    assert isinstance(connector, LlamacppConnector)
    return connector, registry.plan(soulstone)


def _build_vllm_connector(soulstone: VllmSoulstoneConfig) -> tuple[OpenAICompatibleConnector, RuntimePlan]:
    registry = _runtime_registry()
    runtime = registry.build_runtime(soulstone)
    assert runtime is not None
    connector = runtime.connector
    assert isinstance(connector, OpenAICompatibleConnector)
    return connector, registry.plan(soulstone)


def _build_sglang_connector(soulstone: SglangSoulstoneConfig) -> tuple[OpenAICompatibleConnector, RuntimePlan]:
    registry = _runtime_registry()
    runtime = registry.build_runtime(soulstone)
    assert runtime is not None
    connector = runtime.connector
    assert isinstance(connector, OpenAICompatibleConnector)
    return connector, registry.plan(soulstone)


def test_llamacpp_single_mode_plan() -> None:
    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "qwen-local",
            "model_path": "/models/qwen.gguf",
        }
    )

    connector, plan = _build_llamacpp_connector(soulstone)
    specs = _capability_specs(_runtime_registry(), soulstone)

    assert connector.mode == "single"
    assert plan.exec_args[:4] == ["--sleep-idle-seconds", "-1", "-m", "/models/qwen.gguf"]
    assert "--alias" in plan.exec_args
    assert "qwen" in plan.exec_args
    assert {spec.model_id for spec in specs} == {"qwen"}


@pytest.mark.parametrize("source", ["extra_args", "env_vars"])
@pytest.mark.parametrize("router_option", ["models-dir", "models-preset"])
def test_llamacpp_explicit_single_overrides_router_hints(source: str, router_option: str, tmp_path: Path) -> None:
    preset = tmp_path / "router.ini"
    preset.write_text("[other]\nmodel=/models/other.gguf\n", encoding="utf-8")
    value = str(preset) if router_option == "models-preset" else "/models"
    fields: dict[str, object] = {
        "name": "forced-single",
        "startup_mode": "single",
        "model_path": "/models/chat.gguf",
        source: [f"--{router_option}", value]
        if source == "extra_args"
        else {f"LLAMA_ARG_{router_option.upper().replace('-', '_')}": value},
    }
    soulstone = LlamaCppSoulstoneConfig.model_validate(fields)

    connector, plan = _build_llamacpp_connector(soulstone)
    specs = _capability_specs(_runtime_registry(), soulstone)

    assert plan.exec_args[:4] == ["--sleep-idle-seconds", "-1", "-m", "/models/chat.gguf"]
    assert connector.mode == "single"
    assert connector.router_query_model_id is None
    assert {spec.model_id for spec in specs} == {"chat"}
    assert all(not spec.is_dynamic for spec in specs)
    if source == "extra_args":
        assert plan.exec_args[-2:] == [f"--{router_option}", value]


@pytest.mark.parametrize("mode", ["single", "router"])
@pytest.mark.parametrize(
    "control",
    [
        ("-m", "/models/chat.gguf"),
        ("--model", "/models/chat.gguf"),
        ("-m", ""),
        ("--model", ""),
        ("--hf-repo", "example/chat"),
        ("--model=/models/chat.gguf",),
        ("-mu", "https://example.invalid/chat.gguf"),
        ("--model-url", "https://example.invalid/chat.gguf"),
        ("--model_url=https://example.invalid/chat.gguf",),
        ("-dr", "ai/chat"),
        ("--docker_repo", "ai/chat"),
        ("-hf", "example/chat"),
        ("-hfr", "example/chat"),
        ("--hf_repo=example/chat",),
        ("-hff", "chat.gguf"),
        ("--hf-file", "chat.gguf"),
        ("--embd-gemma-default",),
        ("--fim-qwen-1.5b-default",),
        ("--fim-qwen-3b-default",),
        ("--fim-qwen-7b-default",),
        ("--fim-qwen-7b-spec",),
        ("--fim-qwen-14b-spec",),
        ("--fim-qwen-30b-default",),
        ("--gpt-oss-20b-default",),
        ("--gpt-oss-120b-default",),
        ("--vision-gemma-4b-default",),
        ("--vision_gemma_12b_default",),
        # A token consumed as an option value is deliberately also refused.
        ("--alias", "--model"),
    ],
)
def test_llamacpp_forced_modes_refuse_main_model_source_args(mode: str, control: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError, match=rf"forced {mode}.*model-source.*extra_args"):
        LlamaCppSoulstoneConfig.model_validate(
            {
                "name": "forced-mode",
                "startup_mode": mode,
                "model_path": "/models/chat.gguf",
                "models_dir": "/models",
                "extra_args": ["--models-dir", "/models", *control],
            }
        )


@pytest.mark.parametrize("source", ["env_vars", "secret_env_files"])
@pytest.mark.parametrize(
    "variable",
    ["LLAMA_ARG_MODEL", "LLAMA_ARG_MODEL_URL", "LLAMA_ARG_DOCKER_REPO", "LLAMA_ARG_HF_REPO", "LLAMA_ARG_HF_FILE"],
)
def test_llamacpp_forced_router_refuses_single_model_source_env(variable: str, source: str) -> None:
    with pytest.raises(ValidationError, match=rf"forced router.*model-source.*{source}"):
        LlamaCppSoulstoneConfig.model_validate(
            {
                "name": "forced-router",
                "startup_mode": "router",
                "models_dir": "/models",
                source: {variable: "model-source"},
            }
        )


@pytest.mark.parametrize("source", ["env_vars", "secret_env_files"])
def test_llamacpp_forced_single_refuses_hf_repo_environment(source: str) -> None:
    with pytest.raises(ValidationError, match=rf"forced single.*model-source.*{source}"):
        LlamaCppSoulstoneConfig.model_validate(
            {
                "name": "forced-single-hf",
                "startup_mode": "single",
                "model_path": "/models/chat.gguf",
                source: {"LLAMA_ARG_HF_REPO": "remote-preset"},
            }
        )


@pytest.mark.parametrize("extra_args", [("--alias", "chat-alias"), ("--spec-default",)])
def test_llamacpp_forced_single_retains_local_model_with_safe_overlays(extra_args: tuple[str, ...]) -> None:
    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "forced-single",
            "startup_mode": "single",
            "model_path": "/models/chat.gguf",
            "extra_args": extra_args,
            "env_vars": {"LLAMA_ARG_MODEL": "", "LLAMA_ARG_HF_FILE": "chat.gguf"},
            "secret_env_files": {"LLAMA_ARG_MODEL": "model-file"},
        }
    )

    connector, plan = _build_llamacpp_connector(soulstone)

    assert connector.mode == "single"
    assert plan.exec_args[:4] == ["--sleep-idle-seconds", "-1", "-m", "/models/chat.gguf"]
    assert plan.exec_args[-len(extra_args) :] == list(extra_args)


def test_llamacpp_forced_router_ignores_unused_model_path_and_allows_non_source_defaults() -> None:
    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "forced-router",
            "startup_mode": "router",
            "model_path": "/models/unused.gguf",
            "models_dir": "/models",
            "extra_args": ["--spec-default"],
        }
    )

    connector, plan = _build_llamacpp_connector(soulstone)

    assert connector.mode == "router"
    assert "-m" not in plan.exec_args
    assert plan.exec_args[plan.exec_args.index("--models-dir") + 1] == "/models"
    assert plan.exec_args[-1] == "--spec-default"
    assert all(spec.is_dynamic for spec in _capability_specs(_runtime_registry(), soulstone))


def test_llamacpp_auto_keeps_router_environment_inference_above_typed_model_path() -> None:
    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "auto-router",
            "model_path": "/models/unused.gguf",
            "env_vars": {"LLAMA_ARG_MODELS_DIR": "/models"},
        }
    )

    connector, plan = _build_llamacpp_connector(soulstone)

    assert connector.mode == "router"
    assert "-m" not in plan.exec_args
    assert plan.exec_args[plan.exec_args.index("--models-dir") + 1] == "/models"


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

    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "qwen-router",
            "startup_mode": "router",
            "models_preset": str(preset),
        }
    )

    connector, plan = _build_llamacpp_connector(soulstone)
    model_ids = {spec.model_id for spec in _capability_specs(_runtime_registry(), soulstone)}

    assert connector.mode == "router"
    # Without a models catalog the router query model falls back to the Soulstone name.
    assert connector.router_query_model_id == "qwen-router"
    assert "qwen3-64k" in model_ids
    assert "qwen3-150k" in model_ids
    assert "--models-preset" in plan.exec_args
    assert str(preset) in plan.exec_args


def test_llamacpp_declared_models_filter_preset_inventory(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        "version = 1\n\n[*]\nc = 8192\n\n[discovered]\nmodel = /models/discovered.gguf\n",
        encoding="utf-8",
    )
    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "bounded-router",
            "startup_mode": "router",
            "models_preset": str(preset),
            "models": [{"id": "declared", "path": "/models/declared.gguf"}],
        }
    )
    specs = _capability_specs(_runtime_registry(), soulstone)

    assert {spec.model_id for spec in specs} == {"declared"}


def test_vllm_openai_compatible_plan() -> None:
    # vLLM is exec-passthrough: the operator's ``exec`` list is authoritative and
    # framework flags are never re-typed on the Soulstone.
    exec_args = [
        "serve",
        "/models/glm-flash",
        "--served-model-name",
        "glm-flash",
        "--tensor-parallel-size",
        "2",
    ]
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "glm47",
            "model_path": "/models/glm-flash",
            "port": 8000,
            "exec": exec_args,
        }
    )

    _connector, plan = _build_vllm_connector(soulstone)
    specs = _capability_specs(_runtime_registry(), soulstone)

    assert {spec.model_id for spec in specs} == {"glm-flash"}
    assert plan.exec_args == exec_args
    assert "--ipc=host" not in plan.podman_args
    assert specs[0].supports_tools is True


def test_vllm_model_uses_runtime_profile_capabilities() -> None:
    # The single model is derived from ``model_path`` and its capability surface
    # comes from the vLLM runtime profile (no per-model capability catalog).
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "vllm-defaults",
            "model_path": "/models/vision-awq",
            "port": 8000,
        }
    )

    model = _capability_specs(_runtime_registry(), soulstone)[0]

    assert model.model_id == "vision-awq"
    assert model.modalities_in == ("text",)
    assert model.supports_tools is True


def test_sglang_openai_compatible_plan() -> None:
    # SGLang is exec-passthrough as well; the container envelope only contributes
    # deterministic podman flags.
    exec_args = [
        "python3",
        "-m",
        "sglang.launch_server",
        "--model-path",
        "/models/qwen-awq",
        "--tp",
        "2",
    ]
    soulstone = SglangSoulstoneConfig.model_validate(
        {
            "name": "qwen-sglang",
            "model_path": "/models/qwen-awq",
            "served_model_id": "public-qwen",
            "port": 8011,
            "exec": exec_args,
        }
    )

    _connector, plan = _build_sglang_connector(soulstone)
    specs = _capability_specs(_runtime_registry(), soulstone)

    assert {spec.model_id for spec in specs} == {"public-qwen"}
    assert plan.exec_args == exec_args
    assert "--ipc=host" not in plan.podman_args


def test_vllm_builds_capability_specs_with_concurrency_metadata() -> None:
    # Capability specs are synthesized from runtime-derived model info with the
    # default concurrency intent; there is no per-Soulstone capability/concurrency
    # declaration anymore.
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "support-vllm",
            "model_path": "/models/embedder-awq",
            "port": 8000,
        }
    )

    registry = _runtime_registry()
    specs = _capability_specs(registry, soulstone)

    assert len(specs) == 1
    spec = specs[0]
    assert spec.family == CapabilityFamily.CHAT
    assert spec.model_id == "embedder-awq"
    assert spec.concurrency.dedicated is True
    assert spec.concurrency.persistent_resident is False


@pytest.mark.asyncio
async def test_vllm_probe_warms_only_the_exact_observed_model(httpx2_mock: respx.MockRouter) -> None:
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "declaration-name",
            "model_path": "/models/weights-directory",
            "served_model_id": "public-model-alias",
            "port": 8000,
        }
    )
    adapter = _vllm_adapter()
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    httpx2_mock.get("http://localhost:8000/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": [{"id": "public-model-alias"}]})
    )

    specs = adapter.build_capability_specs(runtime)
    states = await adapter.probe_capability_states(runtime, specs)

    assert [spec.model_id for spec in specs] == ["public-model-alias"]
    assert {state.phase for state in states} == {CapabilityPhase.WARM}


@pytest.mark.asyncio
async def test_vllm_probe_rejects_a_declared_model_absent_from_inventory(httpx2_mock: respx.MockRouter) -> None:
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "missing-vllm",
            "model_path": "/models/declared-model",
            "port": 8000,
        }
    )
    adapter = _vllm_adapter()
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    httpx2_mock.get("http://localhost:8000/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": [{"id": "unrelated-model"}]})
    )

    states = await adapter.probe_capability_states(runtime, adapter.build_capability_specs(runtime))

    assert {state.phase for state in states} == {CapabilityPhase.ERROR}
    assert all(state.health == "model_missing" for state in states)


@pytest.mark.asyncio
async def test_vllm_probe_fails_closed_on_malformed_inventory(httpx2_mock: respx.MockRouter) -> None:
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "malformed-vllm",
            "model_path": "/models/declared-model",
            "port": 8000,
        }
    )
    adapter = _vllm_adapter()
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    httpx2_mock.get("http://localhost:8000/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": [{"object": "model"}]})
    )

    states = await adapter.probe_capability_states(runtime, adapter.build_capability_specs(runtime))

    assert runtime.connector.link.up is True
    assert {state.phase for state in states} == {CapabilityPhase.ERROR}
    assert all(state.health == "inventory_invalid" for state in states)
    assert all("non-empty string id" in (state.reason or "") for state in states)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("inventory", "reason"),
    [
        ([{"id": f"model-{index}"} for index in range(1025)], "exceeds 1024 entries"),
        ([{"id": "m" * 513}], "exceeds 512 characters"),
    ],
)
async def test_vllm_probe_bounds_live_model_inventory(
    httpx2_mock: respx.MockRouter,
    inventory: list[dict[str, str]],
    reason: str,
) -> None:
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "bounded-vllm",
            "model_path": "/models/declared-model",
            "port": 8000,
        }
    )
    adapter = _vllm_adapter()
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    connector = cast("OpenAICompatibleConnector", runtime.connector)
    httpx2_mock.get("http://localhost:8000/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": inventory})
    )

    states = await adapter.probe_capability_states(runtime, adapter.build_capability_specs(runtime))

    assert {state.phase for state in states} == {CapabilityPhase.ERROR}
    assert all(state.health == "inventory_invalid" for state in states)
    assert all(reason in (state.reason or "") for state in states)
    assert connector.observed_model_ids is None


def test_llamacpp_router_builds_specs_for_preset_catalog(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        (
            "version = 1\n\n"
            "[router-main]\n"
            "model = /models/router-main.gguf\n\n"
            "[router-vision]\n"
            "model = /models/router-vision.gguf\n"
        ),
        encoding="utf-8",
    )

    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "router",
            "startup_mode": "router",
            "models_preset": str(preset),
        }
    )

    registry = _runtime_registry()
    specs = _capability_specs(registry, soulstone)

    # Preset sections plus the Soulstone-name fallback each yield a dynamic spec.
    assert {spec.model_id for spec in specs} == {"router", "router-main", "router-vision"}
    assert all(spec.is_dynamic for spec in specs)


@pytest.mark.asyncio
async def test_llamacpp_router_probe_maps_dynamic_capability_state(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        (
            "version = 1\n\n"
            "[router-main]\n"
            "model = /models/router-main.gguf\n\n"
            "[router-vision]\n"
            "model = /models/router-vision.gguf\n"
        ),
        encoding="utf-8",
    )

    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "router",
            "startup_mode": "router",
            "models_preset": str(preset),
        }
    )

    class StubControlPlane:
        async def inspect_animator(self, _animator: object) -> AnimatorLifecycle:
            return AnimatorLifecycle(
                health="ok",
                supports_router=True,
                active_model="/models/router-main.gguf",
                loaded_models=["router-main"],
                unloaded_models=["router-vision"],
                available_models=["router-main", "router-vision"],
            )

    adapter = LlamaCppRuntimeAdapter(control_plane=cast("LlamaCppControlPlane", StubControlPlane()))
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    runtime.connector.link.up = True

    specs = adapter.build_capability_specs(runtime)
    states = {state.capability_key: state for state in await adapter.probe_capability_states(runtime, specs)}

    main = next(spec for spec in specs if spec.model_id == "router-main")
    vision = next(spec for spec in specs if spec.model_id == "router-vision")

    # router-main is loaded + health ok ⇒ WARM; router-vision unloaded ⇒ ACTIVATABLE.
    assert states[main.key].phase is CapabilityPhase.WARM
    assert states[main.key].is_active is True
    assert states[vision.key].phase is CapabilityPhase.ACTIVATABLE
    assert states[vision.key].is_active is False
    assert states[vision.key].runtime_started is True


@pytest.mark.asyncio
async def test_llamacpp_router_activation_reports_clean_load_rejection(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        "version = 1\n\n[target]\nmodel = /models/target.gguf\n",
        encoding="utf-8",
    )
    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "router",
            "startup_mode": "router",
            "models_preset": str(preset),
        }
    )

    class RejectingControlPlane:
        async def inspect_animator(self, _animator: object) -> AnimatorLifecycle:
            return AnimatorLifecycle(
                health="ok",
                supports_router=True,
                available_models=["target"],
                unloaded_models=["target"],
            )

        async def load_model(self, _base_url: str, _model: str) -> bool:
            return False

    adapter = LlamaCppRuntimeAdapter(
        control_plane=cast("LlamaCppControlPlane", RejectingControlPlane()),
    )
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    target = next(spec for spec in adapter.build_capability_specs(runtime) if spec.model_id == "target")

    result = await adapter.activate_capability(runtime, target)

    assert result.accepted is False
    assert result.reason == "router rejected model load"


@pytest.mark.parametrize("runtime_name", ["crawler", "openai_compatible", "openai-compatible", "openai"])
def test_unregistered_runtime_keeps_command_plan_without_fabricating_a_surface(runtime_name: str) -> None:
    exec_args = ["custom-server", "--model", "/models/qwen.gguf"]
    soulstone = GenericSoulstoneConfig.model_validate(
        {
            "name": "unregistered",
            "quadlet": {"image": "invalid.example/inert"},
            "runtime": runtime_name,
            "model_path": "/models/qwen.gguf",
            "port": 18080,
            "exec": exec_args,
        }
    )

    registry = _runtime_registry()
    assert registry.plan(soulstone).exec_args == exec_args
    assert registry.build_runtime(soulstone) is None


def test_llamacpp_resolve_infers_single_mode_and_alias_from_exec() -> None:
    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "qwen-cmd",
            "exec": [
                "llama-server",
                "--sleep-idle-seconds",
                "-1",
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
    specs = _capability_specs(_runtime_registry(), soulstone)
    assert connector.mode == "single"
    assert {spec.model_id for spec in specs} == {"qwen-next-80b"}
    assert {spec.generation_profile.max_context for spec in specs} == {16384}


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

    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "router-cmd",
            "exec": [
                "llama-server",
                "--sleep-idle-seconds",
                "-1",
                "--models-preset",
                str(preset),
                "--alias",
                "qwen-next-80b",
            ],
        }
    )

    connector, _ = _build_llamacpp_connector(soulstone)
    model_ids = {spec.model_id for spec in _capability_specs(_runtime_registry(), soulstone)}
    assert connector.mode == "router"
    assert connector.router_query_model_id == "qwen-next-80b"
    assert "qwen-next-80b" in model_ids
    assert "qwen-next-7b" in model_ids


def test_llamacpp_managed_command_shadows_environment_context_default() -> None:
    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "env-driven",
            "env_vars": {
                "LLAMA_ARG_MODELS_PRESET": "/models/models.ini",
                "LLAMA_ARG_ALIAS": "qwen-from-env",
                "LLAMA_ARG_CTX_SIZE": "32768",
            },
        }
    )

    connector, plan = _build_llamacpp_connector(soulstone)
    specs = _capability_specs(_runtime_registry(), soulstone)
    assert connector.mode == "router"
    assert connector.router_query_model_id == "qwen-from-env"
    assert plan.exec_args[plan.exec_args.index("-c") + 1] == "8192"
    assert {spec.generation_profile.max_context for spec in specs} == {8192}


def test_llamacpp_plan_follows_inferred_router_mode_from_extra_args(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        "version = 1\n[*]\nc = 4096\n[qwen-next]\nmodel = /models/qwen-next.gguf\n",
        encoding="utf-8",
    )

    soulstone = LlamaCppSoulstoneConfig.model_validate(
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
    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "predict-alias",
            "exec": [
                "llama-server",
                "--sleep-idle-seconds",
                "-1",
                "-m",
                "/models/qwen-next.gguf",
                "--predict",
                "768",
            ],
        }
    )

    specs = _capability_specs(_runtime_registry(), soulstone)
    assert {spec.generation_profile.max_tokens for spec in specs} == {768}


def test_llamacpp_resolve_uses_single_model_section_when_provider_does_not_match(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        ("version = 1\n\n[*]\nc = 4096\n\n[qwen-next-80b]\nc = 65536\ntemp = 0.6\n"),
        encoding="utf-8",
    )

    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "router-unmatched-provider",
            "startup_mode": "router",
            "models_preset": str(preset),
        }
    )

    profiles = [spec.generation_profile for spec in _capability_specs(_runtime_registry(), soulstone)]
    assert profiles
    assert all(profile == profiles[0] for profile in profiles)
    profile = profiles[0]
    command = _runtime_registry().plan(soulstone).exec_args
    assert command[command.index("-c") + 1] == "8192"
    assert profile.max_context == 8192
    assert profile.temperature == 0.6


def test_llamacpp_resolve_effective_defaults_follow_cli_over_preset_precedence(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        ("version = 1\n\n[*]\nc = 4096\ntemp = 0.55\n\n[qwen-next-80b]\nc = 32768\ntemp = 0.7\n"),
        encoding="utf-8",
    )

    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "router-precedence",
            "exec": [
                "llama-server",
                "--sleep-idle-seconds",
                "-1",
                "--models-preset",
                str(preset),
                "--alias",
                "qwen-next-80b",
                "-c",
                "131072",
                "-np",
                "1",
            ],
        }
    )

    profiles = [spec.generation_profile for spec in _capability_specs(_runtime_registry(), soulstone)]
    assert profiles
    assert all(profile == profiles[0] for profile in profiles)
    profile = profiles[0]
    assert profile.max_context == 131072
    assert profile.temperature == 0.7


@pytest.mark.parametrize(
    ("arguments", "environment", "expected_mode", "expected_id"),
    [
        (("-m", "/models/chat.gguf", "--models-dir", "/models"), {}, "single", "/models/chat.gguf"),
        (("--models-dir", "/models", "-m", "/models/chat.gguf"), {}, "single", "/models/chat.gguf"),
        (("--models-dir", "/models"), {"LLAMA_ARG_MODEL": "/models/env.gguf"}, "single", "/models/env.gguf"),
        (("-m", "/models/chat.gguf"), {"LLAMA_ARG_MODELS_DIR": "/models"}, "single", "/models/chat.gguf"),
        (("--model", ""), {"LLAMA_ARG_MODEL": "/models/env.gguf"}, "router", "actual-mode"),
        (("-m", "/models/chat.gguf", "--model", ""), {}, "router", "actual-mode"),
        (("--model", "", "-m", "/models/chat.gguf"), {}, "single", "/models/chat.gguf"),
        (("--docker_repo", "ai/chat", "--models-dir", "/models"), {}, "single", "ai/chat"),
        (("--docker-repo", ""), {"LLAMA_ARG_DOCKER_REPO": "ai/chat"}, "router", "actual-mode"),
        (("--spec-default",), {"LLAMA_ARG_MODELS_DIR": "/models"}, "router", "actual-mode"),
        (("-hfd", "example/draft"), {}, "router", "actual-mode"),
        (("-hff", "chat.gguf"), {}, "router", "actual-mode"),
        (("-mu", "https://example.invalid/chat.gguf"), {}, "router", "actual-mode"),
        (("-m", "/models/chat.gguf"), {"LLAMA_ARG_ALIAS": "env-alias"}, "single", "env-alias"),
        (("-m", "/models/chat.gguf", "--alias", ""), {"LLAMA_ARG_ALIAS": "env-alias"}, "single", "env-alias"),
    ],
)
def test_llamacpp_actual_mode_overlays_options_before_classification(
    arguments: tuple[str, ...], environment: dict[str, str], expected_mode: str, expected_id: str
) -> None:
    command = ["llama-server", "--sleep-idle-seconds", "-1", *arguments]
    stone = LlamaCppSoulstoneConfig.model_validate({"name": "actual-mode", "exec": command, "env_vars": environment})
    connector, plan = _build_llamacpp_connector(stone)
    specs = _capability_specs(_runtime_registry(), stone)

    assert plan.exec_args == command
    assert connector.mode == expected_mode
    assert {spec.model_id for spec in specs} == {expected_id}
    assert {spec.is_dynamic for spec in specs} == {expected_mode == "router"}
    assert connector.router_query_model_id == (expected_id if expected_mode == "router" else None)


@pytest.mark.parametrize("source", ["env_vars", "secret_env_files"])
def test_llamacpp_actual_mode_uses_environment_after_auto_router_plan(source: str) -> None:
    stone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "auto-mixed",
            "model_path": "/models/unused.gguf",
            "extra_args": ["--models-dir", "/models"],
            "env_vars": {"LLAMA_ARG_MODEL": ""},
            source: {"LLAMA_ARG_MODEL": "main-model"},
        }
    )
    connector, plan = _build_llamacpp_connector(stone)

    assert "-m" not in plan.exec_args
    assert connector.mode == "single"
    assert connector.router_query_model_id is None
    assert all(not spec.is_dynamic for spec in _capability_specs(_runtime_registry(), stone))


@pytest.mark.parametrize("source", ["env_vars", "secret_env_files"])
def test_llamacpp_actual_mode_cli_empty_clears_projected_model(source: str) -> None:
    command = ["--sleep-idle-seconds", "-1", "--model", ""]
    stone = LlamaCppSoulstoneConfig.model_validate(
        {"name": "empty-model", "exec": command, source: {"LLAMA_ARG_MODEL": "main-model"}}
    )
    connector, plan = _build_llamacpp_connector(stone)

    assert plan.exec_args == command
    assert connector.mode == "router"
    assert all(spec.is_dynamic for spec in _capability_specs(_runtime_registry(), stone))


@pytest.mark.parametrize("command_field", ["exec", "extra_args"])
@pytest.mark.parametrize(
    "source",
    [
        {"arguments": ["-hf", "example/chat"]},
        {"arguments": ["--hf-repo", "example/chat", "-m", "/models/chat.gguf"]},
        {"arguments": ["--hf-file", "chat.gguf"], "env_vars": {"LLAMA_ARG_HF_REPO": "example/chat"}},
        {"env_vars": {"LLAMA_ARG_HF_REPO": "example/chat"}},
        {"secret_env_files": {"LLAMA_ARG_HF_REPO": "remote-preset"}},
        {"arguments": ["--gpt-oss-20b-default"]},
        {"arguments": ["--fim-qwen-7b-spec"]},
        {"arguments": ["--vision_gemma_12b_default"]},
    ],
)
def test_llamacpp_actual_mode_refuses_remote_resolved_main_sources(
    command_field: str, source: dict[str, object]
) -> None:
    fields = {key: value for key, value in source.items() if key != "arguments"}
    arguments = cast("list[str]", source.get("arguments", []))
    fields[command_field] = ["--sleep-idle-seconds", "-1", *arguments] if command_field == "exec" else arguments
    if command_field == "extra_args":
        fields["model_path"] = "/models/chat.gguf"
    with pytest.raises(ValidationError, match="remote-resolved main-model"):
        LlamaCppSoulstoneConfig.model_validate({"name": "remote-source", **fields})


@pytest.mark.parametrize("source", ["env_vars", "secret_env_files"])
def test_llamacpp_actual_mode_allows_cli_to_clear_remote_repository(source: str) -> None:
    stone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "cleared-hf",
            "exec": ["--sleep-idle-seconds", "-1", "--hf-repo", "", "-m", "/models/chat.gguf"],
            source: {"LLAMA_ARG_HF_REPO": "remote-preset"},
        }
    )
    connector, _ = _build_llamacpp_connector(stone)

    assert connector.mode == "single"


@pytest.mark.parametrize(
    "arguments",
    [
        ("--model",),
        ("--model", "--models-dir", "/models"),
        ("--model=/models/chat.gguf",),
        ("-m=/models/chat.gguf",),
        ("--models_dir=/models",),
        ("--alias", "--model", "/models/chat.gguf"),
        ("--unknown", "--model", "/models/chat.gguf"),
        ("-unknown", "ordinary-value", "--model", "/models/chat.gguf"),
        ("--unknown", "ordinary-value", "--models-dir", "/models"),
        ("--unknown", "--alias", "advertised"),
        ("--unknown", "ordinary-value", "--alias", "advertised"),
        ("--alias=advertised",),
        ("--alias",),
    ],
)
def test_llamacpp_actual_mode_refuses_ambiguous_source_tokens(arguments: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError, match="source option"):
        LlamaCppSoulstoneConfig.model_validate(
            {"name": "ambiguous-source", "exec": ["--sleep-idle-seconds", "-1", *arguments]}
        )


def test_llamacpp_actual_mode_preserves_unknown_trailing_options() -> None:
    command = ["--sleep-idle-seconds", "-1", "--model", "/models/chat.gguf", "--unknown", "value"]
    stone = LlamaCppSoulstoneConfig.model_validate({"name": "trailing-options", "exec": command})
    connector, plan = _build_llamacpp_connector(stone)

    assert plan.exec_args == command
    assert connector.mode == "single"


@pytest.mark.parametrize(
    ("arguments", "environment", "expected_id"),
    [
        (("--alias", "z-last"), {"LLAMA_ARG_ALIAS": "a-first"}, "a-first"),
        (("--alias", "z-last", "--alias", "a-first", "--alias", ""), {}, "a-first"),
        (("--alias", "  z-last, a-first , ,middle  "), {}, "a-first"),
        (("--alias", "\t\r\na-first\v\f"), {}, "a-first"),
        (("--alias", ""), {"LLAMA_ARG_ALIAS": "env-alias"}, "env-alias"),
    ],
)
def test_llamacpp_actual_inventory_identity_accumulates_aliases(
    arguments: tuple[str, ...], environment: dict[str, str], expected_id: str
) -> None:
    command = ["--sleep-idle-seconds", "-1", "-m", "/models/base.gguf", *arguments]
    stone = LlamaCppSoulstoneConfig.model_validate(
        {"name": "aliases", "port": 23333, "exec": command, "env_vars": environment}
    )
    connector, plan = _build_llamacpp_connector(stone)
    specs = _capability_specs(_runtime_registry(), stone)

    assert plan.exec_args == command
    assert {info.id for info in connector.model_infos} == {expected_id}
    assert {spec.model_id for spec in specs} == {expected_id}
    assert connector.get_model().model_name == expected_id


def test_llamacpp_actual_inventory_identity_keeps_managed_stem_alias() -> None:
    stone = LlamaCppSoulstoneConfig.model_validate({"name": "managed", "model_path": "/models/chat.gguf"})
    connector, plan = _build_llamacpp_connector(stone)

    assert plan.exec_args[plan.exec_args.index("--alias") + 1] == "chat"
    assert {info.id for info in connector.model_infos} == {"chat"}


@pytest.mark.parametrize(
    ("overrides", "expected_id"),
    [
        ({"env_vars": {"LLAMA_ARG_ALIAS": "env-alias"}}, "env-alias"),
        ({"extra_args": ["--model", "/models/override.gguf"]}, "override"),
        (
            {"extra_args": ["--models-dir", "/models"], "env_vars": {"LLAMA_ARG_MODEL": "/models/env.gguf"}},
            "/models/env.gguf",
        ),
        ({"served_model_id": "public-model", "env_vars": {"LLAMA_ARG_MODEL": "/models/env.gguf"}}, "public-model"),
        (
            {
                "served_model_id": "public-model",
                "extra_args": ["--alias", "z-last"],
                "env_vars": {"LLAMA_ARG_ALIAS": "a-first"},
            },
            "a-first",
        ),
    ],
)
def test_llamacpp_actual_inventory_default_follows_captured_catalogue(
    overrides: dict[str, object], expected_id: str
) -> None:
    stone = LlamaCppSoulstoneConfig.model_validate(
        {"name": "default-model", "port": 23333, "model_path": "/models/typed.gguf", **overrides}
    )
    connector, _ = _build_llamacpp_connector(stone)

    assert {info.id for info in connector.model_infos} == {expected_id}
    assert connector.get_model().model_name == expected_id


@pytest.mark.parametrize("mode", ["auto", "router"])
@pytest.mark.parametrize("source", ["underscore", "secret"])
@pytest.mark.parametrize("option", ["models-dir", "models-preset"])
def test_llamacpp_actual_router_admission_reuses_projected_options(mode: str, source: str, option: str) -> None:
    fields: dict[str, object] = {"name": "router-inputs", "startup_mode": mode}
    if source == "underscore":
        fields["extra_args"] = [f"--{option.replace('-', '_')}", "/models/router-source"]
    else:
        fields["secret_env_files"] = {f"LLAMA_ARG_{option.replace('-', '_').upper()}": "router-source"}
    stone = LlamaCppSoulstoneConfig.model_validate(fields)
    connector, _ = _build_llamacpp_connector(stone)

    assert connector.mode == "router"
    assert all(spec.is_dynamic for spec in _capability_specs(_runtime_registry(), stone))


def test_llamacpp_actual_router_admission_does_not_restore_cleared_environment() -> None:
    with pytest.raises(ValidationError, match="requires 'models_dir' or 'models_preset'"):
        LlamaCppSoulstoneConfig.model_validate(
            {
                "name": "cleared-router",
                "extra_args": ["--models-dir", ""],
                "env_vars": {"LLAMA_ARG_MODELS_DIR": "/models"},
            }
        )


def test_llamacpp_actual_router_secret_preset_is_not_read(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_load(_parser: object, _path: str) -> None:
        pytest.fail("Runtime construction attempted to read a projected secret preset")

    monkeypatch.setattr(
        "lychd.extensions.builtin.animator.llamacpp.parser_preset.LlamaCppPresetParser.load_preset", unexpected_load
    )
    stone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "private-preset",
            "secret_env_files": {"LLAMA_ARG_MODELS_PRESET": "private-models"},
            "models": [{"id": "declared", "path": "/models/declared.gguf"}],
        }
    )
    connector, plan = _build_llamacpp_connector(stone)

    assert connector.mode == "router"
    assert "/run/secrets/private-models" in plan.exec_args
    assert {info.id for info in connector.model_infos} == {"declared"}
    assert all(spec.is_dynamic for spec in _capability_specs(_runtime_registry(), stone))
