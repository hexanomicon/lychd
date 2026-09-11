from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, ClassVar, cast

import httpx
import pytest
import respx
from pydantic_ai.models.openai import OpenAIChatModel

from lychd.config.runes.loader import ConfigLoader
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.animators import RuntimeAnimator
from lychd.domain.animation.capabilities import (
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    SourceKind,
)
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import (
    CapabilityFamily,
    ConcurrencyIntent,
    ModelInfo,
    OpenAIPortalConfig,
    PortalConfig,
    SoulstoneConfig,
)
from lychd.domain.animation.services.adapters.contracts import PortalDefinition
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.adapters.runtimes.openai_compat import OpenAICompatibleRuntimeAdapter
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector, PortalAnimator
from lychd.domain.animation.services.declarations import (
    AnimatorDeclarations,
    compile_animator_declarations,
)
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.extensions.builtin.animator import LlamaCppSoulstoneConfig, VllmSoulstoneConfig
from lychd.extensions.builtin.animator.llamacpp import LlamaCppControlPlane
from lychd.extensions.builtin.animator.register import build_openai_portal, probe_openai_portal
from lychd.extensions.builtin.animator.runtimes import (
    LlamaCppRuntimeAdapter,
)

_SOULSTONE_SCHEMAS = (LlamaCppSoulstoneConfig, VllmSoulstoneConfig, OpenAIPortalConfig)
_OPENAI_PORTAL = PortalDefinition(
    rune_schema=OpenAIPortalConfig,
    factory=build_openai_portal,
    probe=probe_openai_portal,
)


@pytest.fixture(autouse=True)
def local_runtime_probes_are_offline(respx_mock: respx.MockRouter) -> None:
    """Keep registry unit tests deterministic while exercising real probe projection."""
    respx_mock.route(host="localhost").mock(
        side_effect=httpx.ConnectError("local runtime intentionally unavailable in unit tests")
    )


def _builtin_adapters() -> list[Any]:
    from lychd.extensions.builtin.animator import SglangSoulstoneConfig

    return [
        LlamaCppRuntimeAdapter(),
        OpenAICompatibleRuntimeAdapter(runtime="vllm", config_type=VllmSoulstoneConfig),
        OpenAICompatibleRuntimeAdapter(runtime="sglang", config_type=SglangSoulstoneConfig),
    ]


def _declarations(
    runes_dir: Path,
    schemas: list[type] | tuple[type, ...] = _SOULSTONE_SCHEMAS,
) -> AnimatorDeclarations:
    return compile_animator_declarations(
        settings=get_settings(),
        runes=RuneRegistry(ConfigLoader(runes_dir).load_all(list(schemas))),
        core_reserved_ports={},
    )


def _registry(runes_dir: Path, **kwargs: Any) -> AnimatorRegistry:
    kwargs.setdefault("portal_definitions", [_OPENAI_PORTAL])
    return AnimatorRegistry(
        declarations=_declarations(runes_dir),
        runtime_adapters=_builtin_adapters(),
        **kwargs,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{content.strip()}\n", encoding="utf-8")


class CustomPortalConfig(PortalConfig):
    path_fragment: ClassVar[Path] = Path("custom")


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
    assert spec.concurrency.persistent_resident is False
    assert registry.get_capability(spec.key) == spec
    state = registry.get_capability_state(spec.key)
    assert state is not None
    # A vLLM soulstone is FIXED and unreachable at rest ⇒ static, cold.
    assert state.is_active is False
    assert state.phase is CapabilityPhase.COLD


@pytest.mark.parametrize(
    ("update", "detail"),
    [
        ({"animator_name": "other-stone"}, "animator_name"),
        ({"runtime": "sglang"}, "runtime"),
        ({"source_kind": SourceKind.PORTAL}, "source_kind"),
        ({"key": "other-stone:chat:main-model"}, "key"),
        ({"concurrency": ConcurrencyIntent(dedicated=True)}, "concurrency"),
    ],
)
def test_registry_rejects_capability_outside_runtime_ownership(
    tmp_path: Path,
    update: dict[str, object],
    detail: str,
) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "main.toml",
        """
        name = "main-stone"
        model_path = "/models/main-model.gguf"
        [concurrency]
        dedicated = false
        """,
    )

    class ForeignCapabilityAdapter(OpenAICompatibleRuntimeAdapter):
        def build_capability_specs(self, animator: RuntimeAnimator) -> list[CapabilitySpec]:
            return [spec.model_copy(update=update) for spec in super().build_capability_specs(animator)]

    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [VllmSoulstoneConfig]),
        runtime_adapters=[ForeignCapabilityAdapter(runtime="vllm", config_type=VllmSoulstoneConfig)],
    )

    with pytest.raises(ValueError, match=f"Capability ownership mismatch.*{detail}"):
        registry.load()


def test_registry_rejects_duplicate_capability_keys_with_declaration_provenance(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    stone_path = runes_dir / "animator" / "soulstones" / "vllm" / "main.toml"
    _write(
        stone_path,
        """
        name = "main-stone"
        model_path = "/models/main-model.gguf"
        """,
    )

    class DuplicatingCapabilityAdapter(OpenAICompatibleRuntimeAdapter):
        def build_capability_specs(self, animator: RuntimeAnimator) -> list[CapabilitySpec]:
            specs = super().build_capability_specs(animator)
            return [*specs, *specs]

    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [VllmSoulstoneConfig]),
        runtime_adapters=[DuplicatingCapabilityAdapter(runtime="vllm", config_type=VllmSoulstoneConfig)],
    )

    with pytest.raises(
        ValueError,
        match=r"Duplicate capability key 'main-stone:chat:main-model'",
    ) as exc_info:
        registry.load()

    message = str(exc_info.value)
    assert "animator_name='main-stone'" in message
    assert "model_id='main-model'" in message
    assert str(stone_path) in message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("malformed", "detail"),
    [
        ("duplicate", "duplicate"),
        ("missing", "missing"),
        ("foreign", "foreign"),
    ],
)
async def test_registry_rejects_malformed_probe_sets_without_partial_cache_update(
    tmp_path: Path,
    malformed: str,
    detail: str,
) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "main.toml",
        """
        name = "main-stone"
        model_path = "/models/main-model.gguf"
        """,
    )

    class MutableProbeAdapter(OpenAICompatibleRuntimeAdapter):
        probe_shape = "valid"

        async def probe_capability_states(
            self,
            animator: Any,
            specs: list[CapabilitySpec],
        ) -> list[CapabilityState]:
            _ = animator
            state = CapabilityState(
                capability_key=specs[0].key,
                phase=CapabilityPhase.WARM,
                health="ok",
            )
            if self.probe_shape == "duplicate":
                return [state, state]
            if self.probe_shape == "missing":
                return []
            if self.probe_shape == "foreign":
                return [state.model_copy(update={"capability_key": "foreign:key"})]
            return [state]

    adapter = MutableProbeAdapter(runtime="vllm", config_type=VllmSoulstoneConfig)
    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [VllmSoulstoneConfig]),
        runtime_adapters=[adapter],
    )
    registry.ensure_loaded()
    key = registry.list_capabilities()[0].key
    assert registry.get_capability_state(key) is not None
    adapter.probe_shape = malformed

    with pytest.raises(ValueError, match=f"Probe contract violation.*{detail}"):
        await registry.refresh_capability_states_for_animator("main-stone")

    assert registry.get_capability_state(key) is None
    assert registry.get_capability_state("foreign:key") is None


@pytest.mark.asyncio
async def test_registry_invalidates_prior_observation_when_probe_raises(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "main.toml",
        """
        name = "main-stone"
        model_path = "/models/main-model.gguf"
        """,
    )

    class FailingProbeAdapter(OpenAICompatibleRuntimeAdapter):
        fail = False

        async def probe_capability_states(
            self,
            animator: Any,
            specs: list[CapabilitySpec],
        ) -> list[CapabilityState]:
            _ = animator
            if self.fail:
                message = "probe transport failed"
                raise RuntimeError(message)
            return [
                CapabilityState(
                    capability_key=spec.key,
                    phase=CapabilityPhase.WARM,
                    health="ok",
                )
                for spec in specs
            ]

    adapter = FailingProbeAdapter(runtime="vllm", config_type=VllmSoulstoneConfig)
    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [VllmSoulstoneConfig]),
        runtime_adapters=[adapter],
    )
    registry.ensure_loaded()
    key = registry.list_capabilities()[0].key
    assert registry.get_capability_state(key) is not None

    adapter.fail = True
    with pytest.raises(RuntimeError, match="probe transport failed"):
        await registry.refresh_capability_states_for_animator("main-stone")

    assert registry.get_capability_state(key) is None


@pytest.mark.asyncio
async def test_registry_invalidates_prior_observation_when_probe_is_cancelled(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "main.toml",
        """
        name = "main-stone"
        model_path = "/models/main-model.gguf"
        """,
    )

    class BlockingProbeAdapter(OpenAICompatibleRuntimeAdapter):
        block = False
        entered = asyncio.Event()

        async def probe_capability_states(
            self,
            animator: Any,
            specs: list[CapabilitySpec],
        ) -> list[CapabilityState]:
            _ = animator
            if self.block:
                self.entered.set()
                await asyncio.Event().wait()
            return [
                CapabilityState(
                    capability_key=spec.key,
                    phase=CapabilityPhase.WARM,
                    health="ok",
                )
                for spec in specs
            ]

    adapter = BlockingProbeAdapter(runtime="vllm", config_type=VllmSoulstoneConfig)
    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [VllmSoulstoneConfig]),
        runtime_adapters=[adapter],
    )
    registry.ensure_loaded()
    key = registry.list_capabilities()[0].key
    assert registry.get_capability_state(key) is not None

    adapter.block = True
    task = asyncio.create_task(registry.refresh_capability_states_for_animator("main-stone"))
    await adapter.entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert registry.get_capability_state(key) is None


@pytest.mark.asyncio
async def test_concurrent_probes_cannot_publish_an_older_observation_last(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "main.toml",
        """
        name = "main-stone"
        model_path = "/models/main-model.gguf"
        """,
    )

    class SequencedProbeAdapter(OpenAICompatibleRuntimeAdapter):
        calls = 0
        started: asyncio.Event | None = None
        release: asyncio.Event | None = None

        async def probe_capability_states(
            self,
            animator: Any,
            specs: list[CapabilitySpec],
        ) -> list[CapabilityState]:
            _ = animator
            self.calls += 1
            call = self.calls
            if call == 2:
                assert self.started is not None
                assert self.release is not None
                self.started.set()
                await self.release.wait()
            return [
                CapabilityState(
                    capability_key=specs[0].key,
                    phase=CapabilityPhase.COLD if call == 2 else CapabilityPhase.WARM,
                )
            ]

    adapter = SequencedProbeAdapter(runtime="vllm", config_type=VllmSoulstoneConfig)
    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [VllmSoulstoneConfig]),
        runtime_adapters=[adapter],
    )
    registry.ensure_loaded()
    adapter.started = asyncio.Event()
    adapter.release = asyncio.Event()

    older = asyncio.create_task(registry.refresh_capability_states_for_animator("main-stone"))
    await adapter.started.wait()
    newer = asyncio.create_task(registry.refresh_capability_states_for_animator("main-stone"))
    await asyncio.sleep(0)
    assert adapter.calls == 2

    adapter.release.set()
    await asyncio.gather(older, newer)

    key = registry.list_capabilities()[0].key
    state = registry.get_capability_state(key)
    assert state is not None
    assert state.phase is CapabilityPhase.WARM


def test_runtime_adapter_registry_supports_custom_portal_definition() -> None:
    portal = CustomPortalConfig.model_validate(
        {
            "name": "custom-portal",
            "base_url": "https://custom.portal/v1",
            "provider_name": "my-openai-gateway",
        }
    )

    def custom_factory(portal: PortalConfig) -> PortalAnimator[OpenAICompatibleConnector, PortalConfig]:
        if portal.provider_name != "my-openai-gateway":
            msg = "CustomPortalConfig requires the admitted gateway provider."
            raise ValueError(msg)
        connector = OpenAICompatibleConnector(
            link=Link(up=True),
            base_url=str(portal.base_url or ""),
            model_infos=(ModelInfo(id="custom-gpt"),),
            default_model_id="custom-gpt",
        )
        return PortalAnimator(rune=portal, connector=connector)

    adapters = RuntimeAdapterRegistry(
        portal_definitions=[PortalDefinition(rune_schema=CustomPortalConfig, factory=custom_factory)]
    )
    runtime = adapters.build_runtime(portal)

    assert runtime is not None
    assert runtime.connector.base_url == "https://custom.portal/v1"


def test_portal_definition_cannot_claim_another_schema() -> None:
    portal = CustomPortalConfig.model_validate(
        {
            "name": "custom-portal",
            "base_url": "https://custom.portal/v1",
            "provider_name": "custom",
        }
    )
    claimed = False

    def broad_factory(portal: PortalConfig) -> PortalAnimator[OpenAICompatibleConnector, PortalConfig]:
        nonlocal claimed
        claimed = True
        connector = OpenAICompatibleConnector(
            link=Link(up=True),
            base_url=str(portal.base_url or ""),
            model_infos=(ModelInfo(id="broad-model"),),
            default_model_id="broad-model",
        )
        return PortalAnimator(rune=portal, connector=connector)

    adapters = RuntimeAdapterRegistry(
        portal_definitions=[PortalDefinition(rune_schema=PortalConfig, factory=broad_factory)]
    )

    runtime = adapters.build_runtime(portal)

    assert runtime is None
    assert claimed is False


def test_portal_schema_without_exact_definition_builds_no_runtime_or_capabilities() -> None:
    portal = CustomPortalConfig.model_validate(
        {
            "name": "crawler-tools",
            "base_url": "https://crawler.internal",
            "provider_name": "crawler",
            "models": [{"id": "declared"}],
        }
    )

    adapters = RuntimeAdapterRegistry()
    runtime = adapters.build_runtime(portal)

    assert runtime is None


class _HealthControl(LlamaCppControlPlane):
    """Stub control plane reporting a fixed single-mode health for issue_grant tests."""

    def __init__(self, health: str, *, model_id: str = "qwen") -> None:
        super().__init__()
        self._health = health
        self._model_id = model_id

    async def inspect_animator(self, animator: Any) -> AnimatorLifecycle:
        del animator
        return AnimatorLifecycle(
            health=self._health,
            loaded_models=[self._model_id] if self._health == "ok" else [],
        )

    def set_health(self, health: str) -> None:
        """Change the next observed health without replacing the control plane."""
        self._health = health


def _family_registry(
    runes_dir: Path,
    *,
    family: CapabilityFamily,
    supports_tools: bool | None = None,
    toolsets: tuple[Any, ...] = (),
) -> tuple[AnimatorRegistry, str]:
    """Build one warm fixed runtime whose v1 family is controlled by the test."""
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "family.toml",
        """
        name = "family-local"
        model_path = "/models/family.gguf"
        """,
    )

    class FamilyAdapter(LlamaCppRuntimeAdapter):
        def build_runtime(self, soulstone: SoulstoneConfig) -> Any:
            runtime = super().build_runtime(soulstone)
            if runtime is not None:
                cast("Any", runtime.connector)._toolsets = toolsets
            return runtime

        def build_capability_specs(self, animator: RuntimeAnimator) -> list[CapabilitySpec]:
            base = super().build_capability_specs(animator)[0]
            return [
                base.model_copy(
                    update={
                        "family": family,
                        "key": f"{base.animator_name}:{family.value}:{base.model_id}",
                        "supports_tools": supports_tools,
                    }
                )
            ]

    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [LlamaCppSoulstoneConfig]),
        runtime_adapters=[FamilyAdapter(control_plane=_HealthControl("ok", model_id="family"))],
    )
    registry.ensure_loaded()
    return registry, registry.list_capabilities()[0].key


def _warm_registry(runes_dir: Path, *, health: str) -> tuple[AnimatorRegistry, str]:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "qwen.toml",
        """
        name = "qwen-local"
        model_path = "/models/qwen.gguf"
        """,
    )
    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [LlamaCppSoulstoneConfig]),
        runtime_adapters=[LlamaCppRuntimeAdapter(control_plane=_HealthControl(health))],
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
    assert isinstance(grant.model, OpenAIChatModel)
    assert not hasattr(grant, "animator")

    again = await registry.issue_grant(key, holder="run:r1")
    assert again.lease.grant_id != grant.lease.grant_id  # unique per issue


@pytest.mark.asyncio
async def test_issue_grant_reprobes_cached_warm_state_before_issue(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "qwen.toml",
        """
        name = "qwen-local"
        model_path = "/models/qwen.gguf"
        """,
    )
    control = _HealthControl("ok")
    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [LlamaCppSoulstoneConfig]),
        runtime_adapters=[LlamaCppRuntimeAdapter(control_plane=control)],
    )
    registry.ensure_loaded()
    key = registry.list_capabilities()[0].key
    assert registry.get_capability_state(key).phase is CapabilityPhase.WARM  # type: ignore[union-attr]

    control.set_health("loading")

    with pytest.raises(CapabilityUnavailable, match="phase=warming"):
        await registry.issue_grant(key, holder="run:r1")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "family",
    [
        CapabilityFamily.VISION,
        CapabilityFamily.EMBEDDING,
        CapabilityFamily.STT,
        CapabilityFamily.TTS,
        CapabilityFamily.RERANK,
    ],
)
async def test_issue_grant_refuses_metadata_only_v1_families(tmp_path: Path, family: CapabilityFamily) -> None:
    registry, key = _family_registry(tmp_path / family.value, family=family)

    with pytest.raises(CapabilityUnavailable, match="routing metadata without an executable grant surface"):
        await registry.issue_grant(key, holder="run:r1")


@pytest.mark.asyncio
async def test_chat_grant_attaches_toolsets_only_when_explicitly_admitted(tmp_path: Path) -> None:
    marker = object()
    for label, supports_tools in (("unknown", None), ("denied", False)):
        denied_registry, denied_key = _family_registry(
            tmp_path / label,
            family=CapabilityFamily.CHAT,
            supports_tools=supports_tools,
            toolsets=(marker,),
        )

        denied_grant = await denied_registry.issue_grant(denied_key, holder="run:r1")

        assert denied_grant.toolsets == ()

    admitted_registry, admitted_key = _family_registry(
        tmp_path / "admitted",
        family=CapabilityFamily.CHAT,
        supports_tools=True,
        toolsets=(marker,),
    )

    admitted_grant = await admitted_registry.issue_grant(admitted_key, holder="run:r1")

    assert admitted_grant.toolsets == (marker,)


@pytest.mark.asyncio
async def test_tool_execution_grant_refuses_an_empty_surface(tmp_path: Path) -> None:
    registry, key = _family_registry(
        tmp_path / "tool-only",
        family=CapabilityFamily.TOOL_EXECUTION,
    )

    with pytest.raises(CapabilityUnavailable, match="has no admitted toolset surface"):
        await registry.issue_grant(key, holder="run:r1")


@pytest.mark.asyncio
async def test_tool_execution_grant_exposes_only_a_non_empty_toolset_surface(tmp_path: Path) -> None:
    marker = object()
    registry, key = _family_registry(
        tmp_path / "tool-only",
        family=CapabilityFamily.TOOL_EXECUTION,
        toolsets=(marker,),
    )

    grant = await registry.issue_grant(key, holder="run:r1")

    assert grant.model is None
    assert grant.toolsets == (marker,)
    assert not hasattr(grant, "animator")


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
