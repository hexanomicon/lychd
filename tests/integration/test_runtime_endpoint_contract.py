"""Runtime commands must agree with the endpoint admitted before host binding."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings import Settings
from lychd.domain.animation.capabilities import CapabilitySpec
from lychd.domain.animation.connectors import Connector
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator, SoulstoneDefinition
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.adapters.runtimes.openai_compat import OpenAICompatibleRuntimeAdapter
from lychd.domain.animation.services.adapters.surfaces import SoulstoneAnimator
from lychd.domain.animation.services.declarations import compile_animator_declarations
from lychd.extensions.builtin.animator.llamacpp.connector import LlamacppConnector
from lychd.extensions.builtin.animator.runtimes.llamacpp import LlamaCppRuntimeAdapter
from lychd.extensions.builtin.animator.soulstones import (
    ExLlamaV3SoulstoneConfig,
    LlamaCppSoulstoneConfig,
    VllmSoulstoneConfig,
)
from lychd.extensions.context import ExtensionContext
from lychd.extensions.host import AssembledExtensions, assemble_extensions
from lychd.system.services.bind_compilation import compile_bind_request


def _compile(fields: dict[str, object]) -> LlamaCppSoulstoneConfig:
    stone = LlamaCppSoulstoneConfig.model_validate({"name": "review", **fields})
    declarations = compile_animator_declarations(settings=Settings(), runes=RuneRegistry([stone]))
    hydrated = declarations.soulstones[0]
    assert isinstance(hydrated, LlamaCppSoulstoneConfig)
    return hydrated


@pytest.mark.parametrize(
    "fields",
    [
        {
            "port": 23333,
            "exec": ["llama-server", "--sleep-idle-seconds", "-1", "-m", "/models/review.gguf", "--port", "8080"],
        },
        {"port": 23333, "exec": ["llama-server", "--sleep-idle-seconds", "-1", "--port=8080"]},
        {"port": 23333, "exec": ["llama-server", "--sleep-idle-seconds", "-1"], "env_vars": {"LLAMA_ARG_PORT": "8080"}},
        {"port": 23333, "model_path": "/models/review.gguf", "extra_args": ["--port", "8080"]},
        {
            "base_url": "http://localhost:23333/v1",
            "exec": ["llama-server", "--sleep-idle-seconds", "-1", "--port", "8080"],
        },
        {"exec": ["llama-server", "--sleep-idle-seconds", "-1", "--port", "8080"]},
        {
            "port": 23333,
            "exec": ["llama-server", "--sleep-idle-seconds", "-1", "--port", "23333", "--port", "8080"],
            "env_vars": {"LLAMA_ARG_PORT": "23333"},
        },
    ],
    ids=["exec", "equals", "environment", "managed-overlay", "endpoint-only", "auto-port", "last-cli-wins"],
)
def test_compilation_rejects_known_runtime_port_conflict(fields: dict[str, object]) -> None:
    with pytest.raises(ValueError, match=r"endpoint port .* listening port 8080"):
        _compile(fields)


@pytest.mark.parametrize(
    ("fields", "expected_port"),
    [
        ({"port": 23333, "exec": ["llama-server", "--sleep-idle-seconds", "-1", "--port", "23333"]}, 23333),
        ({"port": 23333, "exec": ["llama-server", "--sleep-idle-seconds", "-1", "--port=23333"]}, 23333),
        (
            {
                "base_url": "http://localhost:23333/v1",
                "exec": ["llama-server", "--sleep-idle-seconds", "-1", "--port", "23333"],
            },
            23333,
        ),
        ({"exec": ["llama-server", "--sleep-idle-seconds", "-1", "--port", "20000"]}, 20000),
        (
            {
                "port": 23333,
                "exec": ["llama-server", "--sleep-idle-seconds", "-1"],
                "env_vars": {"LLAMA_ARG_PORT": "23333"},
            },
            23333,
        ),
        (
            {
                "port": 23333,
                "exec": ["llama-server", "--sleep-idle-seconds", "-1", "--port", "8080", "--port", "23333"],
                "env_vars": {"LLAMA_ARG_PORT": "8080"},
            },
            23333,
        ),
        ({"port": 23333, "model_path": "/models/review.gguf", "env_vars": {"LLAMA_ARG_PORT": "8080"}}, 23333),
        ({"port": 23333, "exec": ["custom-wrapper", "--sleep-idle-seconds", "-1", "--custom-listen", "8080"]}, 23333),
    ],
    ids=["exec", "equals", "endpoint-only", "auto-port", "environment", "cli-over-env", "managed-over-env", "unknown"],
)
def test_compilation_preserves_consistent_endpoint_and_command(fields: dict[str, object], expected_port: int) -> None:
    stone = _compile(fields)
    plan = LlamaCppRuntimeAdapter().plan(stone)

    assert stone.port == expected_port
    assert str(stone.base_url) == f"http://localhost:{expected_port}/v1"
    if "exec" in fields:
        assert plan.exec_args == fields["exec"]
    else:
        index = plan.exec_args.index("--port")
        assert plan.exec_args[index + 1] == str(expected_port)


def test_preset_replacement_cannot_split_a_runtime_catalogue_from_its_specs(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text("[*]\nctx-size=8192\nparallel=1\ntemp=0.3\n[first]\nmodel=/models/first.gguf\n")
    stone = _compile(
        {
            "port": 23333,
            "exec": ["llama-server", "--sleep-idle-seconds", "-1", "--models-preset", str(preset), "--port", "23333"],
        }
    )
    adapter = LlamaCppRuntimeAdapter()
    runtime = adapter.build_runtime(stone)
    assert runtime is not None
    assert isinstance(runtime.connector, LlamacppConnector)

    preset.write_text("[*]\nctx-size=16384\nparallel=1\ntemp=0.9\n[second]\nmodel=/models/second.gguf\n")
    specs = adapter.build_capability_specs(runtime)

    assert [info.id for info in runtime.connector.model_infos] == ["review", "first"]
    assert [spec.model_id for spec in specs] == ["review", "first"]
    assert specs[0].generation_profile.max_context == 8192
    assert specs[0].generation_profile.temperature == 0.3
    assert specs[0].is_dynamic is True

    replacement = adapter.build_runtime(stone)
    assert replacement is not None
    replacement_specs = adapter.build_capability_specs(replacement)
    assert [spec.model_id for spec in replacement_specs] == ["review", "second"]
    assert replacement_specs[0].generation_profile.max_context == 16384
    assert replacement_specs[0].generation_profile.temperature == 0.9


def test_bind_compilation_builds_runtime_metadata_without_http_or_secret_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings.model_validate(
        {"extensions": {"builtins": ("animator/llamacpp", "animator/vllm", "animator/exllamav3"), "crypt": ()}}
    )
    extensions = assemble_extensions(settings)
    runes = RuneRegistry(
        [
            LlamaCppSoulstoneConfig(name="llama", model_path="/models/llama.gguf"),
            VllmSoulstoneConfig(name="vllm", port=23333, exec=("serve", "qwen", "--port", "23333")),
            ExLlamaV3SoulstoneConfig.model_validate(
                {
                    "name": "tabby",
                    "auth_secret_name": "missing-tabby-auth",
                    "volumes": ["/data/models:/app/models:ro"],
                    "models": [{"id": "small", "path": "/app/models/small-exl3", "format": "EXL3"}],
                }
            ),
        ]
    )
    declarations = compile_animator_declarations(settings=settings, runes=runes)

    def unexpected_read(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("Bind compilation attempted a secret/file read or HTTP request")

    monkeypatch.setattr(Path, "read_text", unexpected_read)
    monkeypatch.setattr(httpx.AsyncClient, "request", unexpected_read)
    monkeypatch.setattr(httpx.Client, "request", unexpected_read)
    request = compile_bind_request(
        settings=settings,
        extensions=extensions,
        runes=runes,
        soulstones=declarations.soulstones,
        portals=declarations.portals,
        uncaged=False,
    )

    assert "missing-tabby-auth" in request.required_secret_names
    assert request.manifests


@pytest.mark.parametrize("entry", ["registry", "bind"])
@pytest.mark.parametrize("mismatch", ["rune", "name"])
def test_runtime_identity_is_rejected_before_capability_extraction(entry: str, mismatch: str) -> None:
    class ForeignNameAnimator(SoulstoneAnimator[Connector, SoulstoneConfig]):
        @property
        def name(self) -> str:
            return "foreign"

    class ForeignRuntimeAdapter(OpenAICompatibleRuntimeAdapter):
        def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
            if mismatch == "rune":
                return super().build_runtime(soulstone.model_copy(update={"name": "foreign"}))
            runtime = super().build_runtime(soulstone)
            assert runtime is not None
            return ForeignNameAnimator(rune=soulstone, connector=runtime.connector)

        def build_capability_specs(self, animator: RuntimeAnimator) -> list[CapabilitySpec]:
            del animator
            pytest.fail("Invalid runtime reached capability extraction")

    adapter = ForeignRuntimeAdapter(runtime="vllm", config_type=VllmSoulstoneConfig)
    stone = VllmSoulstoneConfig(name="admitted", port=23333, exec=("serve", "qwen", "--port", "23333"))
    context = ExtensionContext()
    with context.provenance("core"):
        context.soulstones.add(SoulstoneDefinition(rune_schema=VllmSoulstoneConfig, runtime_adapter=adapter))
    extensions = AssembledExtensions(context)

    def compile_invalid() -> None:
        if entry == "registry":
            RuntimeAdapterRegistry(adapters=[adapter]).build_runtime(stone)
        else:
            compile_bind_request(
                settings=Settings(),
                extensions=extensions,
                runes=RuneRegistry([stone]),
                soulstones=(stone,),
                portals=(),
                uncaged=False,
            )

    with pytest.raises(ValueError, match=r"does not retain the declared Rune|must use canonical name"):
        compile_invalid()
