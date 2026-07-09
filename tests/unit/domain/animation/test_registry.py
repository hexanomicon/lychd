from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pytest
from pydantic_ai.models.openai import OpenAIChatModel

from lychd.domain.animation.capabilities import CapabilityPhase
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import ModelInfo, OpenAIPortalConfig, PortalConfig
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector, OpenAIPortal
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.extensions.builtin.animator import LlamaCppSoulstoneConfig, VllmSoulstoneConfig
from lychd.extensions.builtin.animator.llamacpp import LlamaCppControlPlane
from lychd.extensions.builtin.animator.register import build_openai_portal
from lychd.extensions.builtin.animator.runtimes import (
    LlamaCppRuntimeAdapter,
    SglangRuntimeAdapter,
    VllmRuntimeAdapter,
)

_SOULSTONE_SCHEMAS = (LlamaCppSoulstoneConfig, VllmSoulstoneConfig, OpenAIPortalConfig)


def _builtin_adapters() -> list[Any]:
    return [LlamaCppRuntimeAdapter(), VllmRuntimeAdapter(), SglangRuntimeAdapter()]


def _registry(runes_dir: Path, **kwargs: Any) -> AnimatorRegistry:
    kwargs.setdefault("portal_factories", [build_openai_portal])
    return AnimatorRegistry(
        rune_schemas=list(_SOULSTONE_SCHEMAS),
        runtime_adapters=_builtin_adapters(),
        runes_dir=runes_dir,
        reserved_ports={},
        **kwargs,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{content.strip()}\n", encoding="utf-8")


class CustomPortalConfig(PortalConfig):
    path_fragment: ClassVar[Path] = Path("custom")


def test_registry_binds_model_for_portal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runes_dir = tmp_path / "runes"
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    (secrets_dir / "portal_openai_main").write_text("sk-proj-test\n", encoding="utf-8")
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(secrets_dir))
    _write(
        runes_dir / "animator" / "portals" / "openai" / "main.toml",
        """
        name = "openai-main"
        description = "OpenAI test portal"
        api_key_secret_name = "portal_openai_main"
        """,
    )

    registry = _registry(runes_dir)

    model = registry.bind_model("openai-main", model_id="gpt-5")
    toolsets = registry.bind_toolsets("openai-main")

    assert isinstance(model, OpenAIChatModel)
    assert model.model_name == "gpt-5"
    assert model.base_url.rstrip("/") == "https://api.openai.com/v1"
    assert registry.bind_toolset("openai-main") is None
    assert toolsets == ()
    assert registry.prepare("openai-main") is None


def test_registry_prepare_returns_runtime_plan_for_soulstone(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "qwen.toml",
        """
        name = "qwen-local"
        model_path = "/models/qwen.gguf"
        port = 18080
        """,
    )

    registry = _registry(runes_dir)
    plan = registry.prepare("qwen-local")

    assert plan is not None
    assert plan.exec_args[:2] == ["-m", "/models/qwen.gguf"]


def test_registry_indexes_capabilities(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "embedder.toml",
        """
        name = "embedder"
        model_path = "/models/embedder.gguf"
        """,
    )

    registry = _registry(runes_dir)
    capabilities = registry.list_capabilities()

    assert len(capabilities) == 1
    spec = capabilities[0]
    assert spec.animator_name == "embedder"
    # Concurrency is derived with defaults and no rune surface configures
    # residency, so nothing is indexed as a persistent resident.
    assert spec.concurrency.persistent_resident is False
    assert registry.list_persistent_residents() == []
    assert registry.get_capability(spec.key) == spec
    state = registry.get_capability_state(spec.key)
    assert state is not None
    # A vLLM soulstone is FIXED and unreachable at rest ⇒ static, cold.
    assert state.is_static is True
    assert state.is_active is False
    assert state.phase is CapabilityPhase.COLD


def test_registry_unknown_animator_returns_empty_bindings(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    (runes_dir / "animator" / "soulstones").mkdir(parents=True, exist_ok=True)
    (runes_dir / "animator" / "portals").mkdir(parents=True, exist_ok=True)
    registry = _registry(runes_dir)

    assert registry.get_runtime("missing") is None
    assert registry.bind_model("missing") is None
    assert registry.bind_toolset("missing") is None
    assert registry.bind_toolsets("missing") == ()
    assert registry.prepare("missing") is None
    assert registry.is_ready("missing") is False
    assert registry.list_models("missing") == ()


@pytest.mark.asyncio
async def test_registry_activate_capability_returns_result_for_static_runtime(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "embedder.toml",
        """
        name = "embedder"
        model_path = "/models/embedder.gguf"
        """,
    )

    registry = _registry(runes_dir)
    spec = registry.list_capabilities()[0]

    result = await registry.activate_capability(spec.key)
    assert result.accepted is False
    assert result.reason == "fixed capability; lifecycle owned by unit"


@pytest.mark.asyncio
async def test_registry_inspect_lifecycle_delegates_to_control_plane(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "qwen.toml",
        """
        name = "qwen-local"
        model_path = "/models/qwen.gguf"
        """,
    )

    class StubControl(LlamaCppControlPlane):
        def __init__(self) -> None:
            super().__init__()
            self.seen_animator_id: str | None = None

        async def inspect_animator(self, animator: Any) -> AnimatorLifecycle:
            self.seen_animator_id = animator.id
            return AnimatorLifecycle(
                runtime="llamacpp",
                base_url=animator.connector.base_url,
                mode="single",
                health="ok",
            )

    control = StubControl()
    registry = AnimatorRegistry(
        rune_schemas=[LlamaCppSoulstoneConfig],
        runtime_adapters=[LlamaCppRuntimeAdapter(control_plane=control)],
        runes_dir=runes_dir,
        reserved_ports={},
    )

    lifecycle = await registry.inspect_lifecycle("qwen-local")

    assert lifecycle is not None
    assert lifecycle.health == "ok"
    assert control.seen_animator_id == "qwen-local"


def test_runtime_adapter_registry_supports_custom_portal_factories() -> None:
    portal = CustomPortalConfig.model_validate(
        {
            "name": "custom-portal",
            "description": "Custom OpenAI-compatible portal",
            "base_url": "https://custom.portal/v1",
            "provider_name": "my-openai-gateway",
        }
    )

    def custom_factory(portal: PortalConfig) -> OpenAIPortal | None:
        if portal.provider_name != "my-openai-gateway":
            return None
        connector = OpenAICompatibleConnector(
            kind="portal:my-openai-gateway",
            link=Link(up=True, activatable=False),
            base_url=str(portal.base_url or ""),
            model_infos=(ModelInfo(id="custom-gpt"),),
            default_model_id="custom-gpt",
        )
        return OpenAIPortal(rune=portal, connector=connector)

    adapters = RuntimeAdapterRegistry(portal_factories=[custom_factory])
    runtime = adapters.build_runtime(portal)

    assert runtime is not None
    assert isinstance(runtime, OpenAIPortal)
    assert runtime.connector.kind == "portal:my-openai-gateway"


def test_passive_portal_without_declared_capabilities_does_not_invent_chat_capability() -> None:
    portal = CustomPortalConfig.model_validate(
        {
            "name": "crawler-tools",
            "description": "Custom crawler portal",
            "base_url": "https://crawler.internal",
            "provider_name": "crawler",
        }
    )

    adapters = RuntimeAdapterRegistry()
    runtime = adapters.build_runtime(portal)
    assert runtime is not None
    specs = adapters.build_capability_specs(portal, runtime)

    assert specs == []


class _HealthControl(LlamaCppControlPlane):
    """Stub control plane reporting a fixed single-mode health for issue_grant tests."""

    def __init__(self, health: str) -> None:
        super().__init__()
        self._health = health

    async def inspect_animator(self, animator: Any) -> AnimatorLifecycle:
        return AnimatorLifecycle(
            runtime="llamacpp",
            base_url=animator.connector.base_url,
            mode="single",
            health=self._health,
        )


def _warm_registry(runes_dir: Path, *, health: str) -> tuple[AnimatorRegistry, str]:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "qwen.toml",
        """
        name = "qwen-local"
        model_path = "/models/qwen.gguf"
        """,
    )
    registry = AnimatorRegistry(
        rune_schemas=[LlamaCppSoulstoneConfig],
        runtime_adapters=[LlamaCppRuntimeAdapter(control_plane=_HealthControl(health))],
        runes_dir=runes_dir,
        reserved_ports={},
    )
    registry.ensure_loaded()
    return registry, registry.list_capabilities()[0].key


@pytest.mark.asyncio
async def test_issue_grant_returns_grant_for_warm_capability(tmp_path: Path) -> None:
    registry, key = _warm_registry(tmp_path / "runes", health="ok")

    grant = await registry.issue_grant(key, holder="run:r1")

    assert grant.spec.key == key
    assert grant.state.phase is CapabilityPhase.WARM
    assert grant.lease.holder == "run:r1"
    assert grant.generation == grant.spec.generation_profile
    assert isinstance(grant.model, OpenAIChatModel)

    again = await registry.issue_grant(key, holder="run:r1")
    assert again.lease.grant_id != grant.lease.grant_id  # unique per issue


@pytest.mark.asyncio
async def test_issue_grant_raises_for_non_warm_capability(tmp_path: Path) -> None:
    registry, key = _warm_registry(tmp_path / "runes", health="loading")

    with pytest.raises(CapabilityUnavailable):
        await registry.issue_grant(key, holder="run:r1")


@pytest.mark.asyncio
async def test_issue_grant_raises_for_unknown_capability(tmp_path: Path) -> None:
    registry, _ = _warm_registry(tmp_path / "runes", health="ok")

    with pytest.raises(CapabilityUnavailable):
        await registry.issue_grant("nope:chat:nope", holder="run:r1")


def test_registry_logs_unresolved_runtime_factory(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "qwen.toml",
        """
        name = "qwen-local"
        model_path = "/models/qwen.gguf"
        """,
    )

    def unresolved(_rune: object, _quadlet: object = None) -> None:
        return None

    caplog.set_level("WARNING")

    registry = AnimatorRegistry(
        rune_schemas=[LlamaCppSoulstoneConfig],
        runtime_adapters=_builtin_adapters(),
        runes_dir=runes_dir,
        reserved_ports={},
        runtime_factories=[unresolved],
    )
    registry.load()

    assert registry.get_runtime("qwen-local") is None
