from __future__ import annotations

from pathlib import Path
from typing import cast

import httpx
import pytest
import respx

from lychd.domain.animation.capabilities import CapabilityFamily, CapabilityPhase
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import GenericSoulstoneConfig, ModelInfo, ModelSurface
from lychd.domain.animation.services.adapters.contracts import RuntimePlan
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.adapters.surfaces import (
    GenericSoulstone,
    OpenAICompatibleConnector,
    OpenAICompatibleSoulstone,
)
from lychd.extensions.builtin.animator import LlamaCppSoulstoneConfig, SglangSoulstoneConfig, VllmSoulstoneConfig
from lychd.extensions.builtin.animator.llamacpp import LlamacppConnector, LlamaCppControlPlane, LlamaCppLifecycle
from lychd.extensions.builtin.animator.runtimes import (
    LlamaCppRuntimeAdapter,
    SglangRuntimeAdapter,
    VllmRuntimeAdapter,
)


def _runtime_registry() -> RuntimeAdapterRegistry:
    """Build a registry wired with the builtin runtime adapters under test."""
    return RuntimeAdapterRegistry(
        adapters=[LlamaCppRuntimeAdapter(), VllmRuntimeAdapter(), SglangRuntimeAdapter()],
    )


def test_runtime_adapter_selection_uses_exact_declared_owner() -> None:
    class BroadAdapter(VllmRuntimeAdapter):
        runtime = "broad"

    broad = BroadAdapter()
    exact = VllmRuntimeAdapter()
    registry = RuntimeAdapterRegistry(adapters=[broad, exact])
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "exact-vllm",
            "model_path": "/models/exact.gguf",
        }
    )

    assert registry.adapter_for(soulstone) is exact


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


def test_openai_compatible_model_inventory_is_detached_on_admission_and_read() -> None:
    supplied = ModelInfo(
        id="canonical",
        modalities_in=["text"],
        metadata={"provider": {"revision": "one"}},
    )
    connector = OpenAICompatibleConnector(
        kind="portal:test",
        link=Link(up=True),
        base_url="http://127.0.0.1:8000/v1",
        model_infos=(supplied,),
    )

    supplied.id = "forged-at-admission"
    supplied.modalities_in.append("image")
    first = connector.list_models()[0]
    first.id = "forged-at-read"
    first.modalities_in.append("audio")
    first.metadata["provider"]["revision"] = "forged"

    retained = connector.list_models()[0]
    assert retained.id == "canonical"
    assert retained.modalities_in == ["text"]
    assert retained.metadata == {"provider": {"revision": "one"}}


def test_llamacpp_single_mode_plan() -> None:
    soulstone = LlamaCppSoulstoneConfig.model_validate(
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

    soulstone = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "qwen-router",
            "startup_mode": "router",
            "models_preset": str(preset),
        }
    )

    connector, plan = _build_llamacpp_connector(soulstone)
    model_ids = [info.id for info in connector.list_models()]

    assert connector.mode == "router"
    # Without a models catalog the router query model falls back to the Soulstone name.
    assert connector.router_query_model_id == "qwen-router"
    assert "qwen3-64k" in model_ids
    assert "qwen3-150k" in model_ids
    assert "--models-preset" in plan.exec_args
    assert str(preset) in plan.exec_args


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

    connector, plan = _build_vllm_connector(soulstone)

    assert connector.kind == "vllm"
    assert [info.id for info in connector.list_models()] == ["glm-flash"]
    assert plan.exec_args == exec_args
    assert "--ipc=host" not in plan.podman_args
    assert connector.list_models()[0].supports_tools is True
    assert connector.metadata["runtime"] == "vllm"


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

    connector, _ = _build_vllm_connector(soulstone)
    model = connector.list_models()[0]

    assert model.id == "vision-awq"
    assert model.surface == ModelSurface.CHAT
    assert model.modalities_in == ["text"]
    assert model.modalities_out == ["text"]
    assert model.supports_tools is True
    assert model.supports_streaming is True


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

    connector, plan = _build_sglang_connector(soulstone)

    assert connector.kind == "sglang"
    assert [info.id for info in connector.list_models()] == ["public-qwen"]
    assert plan.exec_args == exec_args
    assert "--ipc=host" not in plan.podman_args
    assert connector.metadata["runtime"] == "sglang"


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
    specs = registry.build_capability_specs(soulstone)

    assert len(specs) == 1
    spec = specs[0]
    assert spec.family == CapabilityFamily.CHAT
    assert spec.model_id == "embedder-awq"
    assert spec.concurrency.dedicated is True
    assert spec.concurrency.persistent_resident is False
    assert spec.metadata["runtime"] == "vllm"


@pytest.mark.asyncio
async def test_vllm_probe_warms_only_the_exact_observed_model(respx_mock: respx.MockRouter) -> None:
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "declaration-name",
            "model_path": "/models/weights-directory",
            "served_model_id": "public-model-alias",
            "port": 8000,
        }
    )
    adapter = VllmRuntimeAdapter()
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    respx_mock.get("http://localhost:8000/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": [{"id": "public-model-alias"}]})
    )

    specs = adapter.build_capability_specs(soulstone)
    states = await adapter.probe_capability_states(runtime, specs)

    assert [spec.model_id for spec in specs] == ["public-model-alias"]
    assert {state.phase for state in states} == {CapabilityPhase.WARM}
    assert all(state.loaded_model_ids == ["public-model-alias"] for state in states)


@pytest.mark.asyncio
async def test_vllm_probe_rejects_a_declared_model_absent_from_inventory(respx_mock: respx.MockRouter) -> None:
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "missing-vllm",
            "model_path": "/models/declared-model",
            "port": 8000,
        }
    )
    adapter = VllmRuntimeAdapter()
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    respx_mock.get("http://localhost:8000/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": [{"id": "unrelated-model"}]})
    )

    states = await adapter.probe_capability_states(runtime, adapter.build_capability_specs(soulstone))

    assert {state.phase for state in states} == {CapabilityPhase.ERROR}
    assert all(state.health == "model_missing" for state in states)
    assert all(state.loaded_model_ids == [] for state in states)
    activation = await adapter.activate_capability(runtime, adapter.build_capability_specs(soulstone)[0])
    assert activation.phase is CapabilityPhase.ERROR
    assert "absent from /models" in (activation.reason or "")


@pytest.mark.asyncio
async def test_vllm_probe_fails_closed_on_malformed_inventory(respx_mock: respx.MockRouter) -> None:
    soulstone = VllmSoulstoneConfig.model_validate(
        {
            "name": "malformed-vllm",
            "model_path": "/models/declared-model",
            "port": 8000,
        }
    )
    adapter = VllmRuntimeAdapter()
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    respx_mock.get("http://localhost:8000/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": [{"object": "model"}]})
    )

    states = await adapter.probe_capability_states(runtime, adapter.build_capability_specs(soulstone))

    assert runtime.connector.link.up is True
    assert {state.phase for state in states} == {CapabilityPhase.ERROR}
    assert all(state.health == "inventory_invalid" for state in states)
    assert all(state.loaded_model_ids == [] for state in states)
    assert all("non-empty string id" in (state.reason or "") for state in states)
    activation = await adapter.activate_capability(runtime, adapter.build_capability_specs(soulstone)[0])
    assert activation.phase is CapabilityPhase.ERROR
    assert "non-empty string id" in (activation.reason or "")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("inventory", "reason"),
    [
        ([{"id": f"model-{index}"} for index in range(1025)], "exceeds 1024 entries"),
        ([{"id": "m" * 513}], "exceeds 512 characters"),
    ],
)
async def test_vllm_probe_bounds_live_model_inventory(
    respx_mock: respx.MockRouter,
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
    adapter = VllmRuntimeAdapter()
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    connector = cast("OpenAICompatibleConnector", runtime.connector)
    respx_mock.get("http://localhost:8000/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": inventory})
    )

    states = await adapter.probe_capability_states(runtime, adapter.build_capability_specs(soulstone))

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
    specs = registry.build_capability_specs(soulstone)

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
        async def inspect_animator(self, _animator: object) -> LlamaCppLifecycle:
            return LlamaCppLifecycle(
                runtime="llamacpp",
                base_url="http://localhost:8080/v1",
                mode="router",
                health="ok",
                supports_router=True,
                active_model="/models/router-main.gguf",
                loaded_models=["router-main"],
                available_models=["router-main", "router-vision"],
            )

    adapter = LlamaCppRuntimeAdapter(control_plane=cast("LlamaCppControlPlane", StubControlPlane()))
    runtime = adapter.build_runtime(soulstone)
    assert runtime is not None
    runtime.connector.link.up = True

    specs = adapter.build_capability_specs(soulstone)
    states = {state.capability_key: state for state in await adapter.probe_capability_states(runtime, specs)}

    main = next(spec for spec in specs if spec.model_id == "router-main")
    vision = next(spec for spec in specs if spec.model_id == "router-vision")

    # router-main is loaded + health ok ⇒ WARM; router-vision unloaded ⇒ ACTIVATABLE.
    assert states[main.key].is_static is False
    assert states[main.key].phase is CapabilityPhase.WARM
    assert states[main.key].is_active is True
    assert states[vision.key].phase is CapabilityPhase.ACTIVATABLE
    assert states[vision.key].is_active is False
    assert states[vision.key].runtime_started is True
    assert states[main.key].active_model_id == "router-main"


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
        async def inspect_animator(self, _animator: object) -> LlamaCppLifecycle:
            return LlamaCppLifecycle(
                runtime="llamacpp",
                base_url="http://localhost:8080/v1",
                mode="router",
                health="ok",
                supports_router=True,
                available_models=["target"],
            )

        async def load_model(self, _base_url: str, _model: str) -> bool:
            return False

    adapter = LlamaCppRuntimeAdapter(
        control_plane=cast("LlamaCppControlPlane", RejectingControlPlane()),
    )
    runtime = adapter.build_runtime(soulstone)
    target = next(spec for spec in adapter.build_capability_specs(soulstone) if spec.model_id == "target")
    assert runtime is not None

    result = await adapter.activate_capability(runtime, target)

    assert result.accepted is False
    assert result.phase is CapabilityPhase.ACTIVATABLE
    assert result.reason == "router rejected model load"


def test_generic_runtime_does_not_assume_openai_compatible_surface() -> None:
    soulstone = GenericSoulstoneConfig.model_validate(
        {
            "name": "crawler",
            "quadlet": {"image": "crawler:latest"},
            "runtime": "crawler",
            "port": 18080,
        }
    )

    registry = _runtime_registry()
    runtime = registry.build_runtime(soulstone)
    assert isinstance(runtime, GenericSoulstone)
    assert runtime.connector.kind == "generic:crawler"
    # An unknown runtime is not assumed to be OpenAI-compatible and invents no specs.
    assert registry.build_capability_specs(soulstone) == []


def test_generic_runtime_supports_explicit_openai_compatible_surface() -> None:
    soulstone = GenericSoulstoneConfig.model_validate(
        {
            "name": "local-openai",
            "quadlet": {"image": "local-openai:latest"},
            "runtime": "openai_compatible",
            "model_path": "/models/qwen.gguf",
            "port": 18080,
        }
    )

    registry = _runtime_registry()
    runtime = registry.build_runtime(soulstone)
    assert isinstance(runtime, OpenAICompatibleSoulstone)
    assert runtime.connector.kind == "generic-openai-compatible"


def test_generic_runtime_without_capability_hints_does_not_invent_chat() -> None:
    soulstone = GenericSoulstoneConfig.model_validate(
        {
            "name": "sidecar",
            "quadlet": {"image": "sidecar:latest"},
            "runtime": "crawler",
        }
    )

    registry = _runtime_registry()

    assert registry.build_capability_specs(soulstone) == []


def test_llamacpp_resolve_infers_single_mode_and_alias_from_exec() -> None:
    soulstone = LlamaCppSoulstoneConfig.model_validate(
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

    soulstone = LlamaCppSoulstoneConfig.model_validate(
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
    soulstone = LlamaCppSoulstoneConfig.model_validate(
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

    soulstone = LlamaCppSoulstoneConfig.model_validate(
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

    soulstone = LlamaCppSoulstoneConfig.model_validate(
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
    soulstone = LlamaCppSoulstoneConfig.model_validate(
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
