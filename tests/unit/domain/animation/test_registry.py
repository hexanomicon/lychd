from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, ClassVar

import httpx
import pytest
import respx
from pydantic_ai.models.openai import OpenAIChatModel

from lychd.config.runes import ConfigLoader
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.capabilities import (
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    SourceKind,
)
from lychd.domain.animation.conflicts import ConflictTopologyError
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import ModelInfo, OpenAIPortalConfig, PortalConfig, SoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import PortalDefinition
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector, OpenAIPortal
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
    SglangRuntimeAdapter,
    VllmRuntimeAdapter,
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
    return [LlamaCppRuntimeAdapter(), VllmRuntimeAdapter(), SglangRuntimeAdapter()]


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


def test_soulstone_runtime_does_not_retain_deployment_manifest(tmp_path: Path) -> None:
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
    runtime = registry.get_runtime("qwen-local")

    assert runtime is not None
    assert not hasattr(runtime, "quadlet")


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


def test_registry_rune_projections_are_detached_and_groups_are_immutable_sequences(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "main.toml",
        """
        name = "main-stone"
        model_path = "/models/main.gguf"
        groups = ["primary"]
        """,
    )
    _write(
        runes_dir / "animator" / "portals" / "openai" / "cloud.toml",
        """
        name = "cloud"
        [[models]]
        id = "gpt-x"
        """,
    )
    registry = _registry(runes_dir)

    soulstone = registry.get_soulstone_rune("main-stone")
    portal = registry.get_portal_rune("cloud")
    assert soulstone is not None
    assert portal is not None
    soulstone.groups.append("forged")
    portal.models.clear()
    registry.list_soulstone_runes()[0].groups.clear()
    grouped = registry.get_group("primary")
    assert isinstance(grouped, tuple)
    grouped[0].groups.append("forged-group")
    listed_portal = next(rune for rune in registry.list_runes() if rune.name == "cloud")
    assert isinstance(listed_portal, PortalConfig)
    listed_portal.models.clear()

    canonical_soulstone = registry.get_soulstone_rune("main-stone")
    canonical_portal = registry.get_portal_rune("cloud")
    assert canonical_soulstone is not None
    assert canonical_portal is not None
    assert canonical_soulstone.groups == ["primary"]
    assert canonical_portal.name == "cloud"
    assert [model.id for model in canonical_portal.models] == ["gpt-x"]
    assert len(registry.get_group("primary")) == 1


def test_registry_read_models_cannot_mutate_canonical_capability_state(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "embedder.toml",
        """
        name = "embedder"
        model_path = "/models/embedder.gguf"
        """,
    )
    registry = _registry(runes_dir)
    exposed_spec = registry.list_capabilities()[0]
    exposed_state = registry.get_capability_state(exposed_spec.key)
    assert exposed_state is not None

    exposed_spec.modalities_in.append("poison")
    exposed_spec.metadata["poison"] = True
    exposed_state.loaded_model_ids.append("poison")
    exposed_state.metadata["poison"] = True

    canonical_spec = registry.get_capability(exposed_spec.key)
    canonical_state = registry.get_capability_state(exposed_spec.key)
    assert canonical_spec is not None
    assert canonical_state is not None
    assert "poison" not in canonical_spec.modalities_in
    assert "poison" not in canonical_spec.metadata
    assert "poison" not in canonical_state.loaded_model_ids
    assert "poison" not in canonical_state.metadata


def test_persistent_resident_projection_cannot_mutate_canonical_spec(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "embedder.toml",
        """
        name = "embedder"
        model_path = "/models/embedder.gguf"
        """,
    )
    registry = _registry(runes_dir)
    key = registry.list_capabilities()[0].key
    canonical = registry._capabilities[key]  # pyright: ignore[reportPrivateUsage]
    canonical.concurrency.persistent_resident = True

    exposed = registry.list_persistent_residents()[0]
    exposed.key = "forged:key"
    exposed.metadata["forged"] = True

    reread = registry.get_capability(key)
    assert reread is not None
    assert reread.key == key
    assert "forged" not in reread.metadata


def test_registry_rejects_noncanonical_runtime_identity(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    portal_path = runes_dir / "animator" / "portals" / "openai" / "main.toml"
    _write(portal_path, 'name = "main-portal"')

    class CollidingPortal(OpenAIPortal):
        @property
        def id(self) -> str:
            return "shared-runtime"

    def colliding_factory(rune: SoulstoneConfig | PortalConfig) -> CollidingPortal | None:
        if not isinstance(rune, PortalConfig):
            return None
        return CollidingPortal(
            rune=rune,
            connector=OpenAICompatibleConnector(
                kind="adversarial-portal",
                link=Link(up=True, activatable=False),
                base_url=str(rune.base_url or ""),
            ),
        )

    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [OpenAIPortalConfig]),
        runtime_adapters=[],
        runtime_factories=[colliding_factory],
    )

    with pytest.raises(ValueError, match="must use canonical name/id") as exc_info:
        registry.load()

    message = str(exc_info.value)
    assert "main-portal" in message
    assert "shared-runtime" in message
    assert str(portal_path) in message
    assert registry.is_loaded is False


def test_registry_rejects_runtime_that_wraps_another_rune_instance(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "portals" / "openai" / "main.toml",
        'name = "main-portal"',
    )

    def foreign_rune_factory(rune: SoulstoneConfig | PortalConfig) -> OpenAIPortal | None:
        if not isinstance(rune, PortalConfig):
            return None
        return OpenAIPortal(
            rune=rune.model_copy(),
            connector=OpenAICompatibleConnector(
                kind="foreign-rune",
                link=Link(up=True, activatable=False),
                base_url=str(rune.base_url or ""),
            ),
        )

    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [OpenAIPortalConfig]),
        runtime_adapters=[],
        runtime_factories=[foreign_rune_factory],
    )

    with pytest.raises(ValueError, match="does not retain the exact input Rune"):
        registry.load()

    assert registry.is_loaded is False


@pytest.mark.parametrize(
    ("update", "detail"),
    [
        ({"animator_name": "other-stone"}, "animator_name"),
        ({"runtime": "sglang"}, "runtime"),
        ({"source_kind": SourceKind.PORTAL}, "source_kind"),
        ({"key": "other-stone:chat:main-model"}, "key"),
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
        """,
    )

    class ForeignCapabilityAdapter(VllmRuntimeAdapter):
        def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
            return [spec.model_copy(update=update) for spec in super().build_capability_specs(soulstone)]

    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [VllmSoulstoneConfig]),
        runtime_adapters=[ForeignCapabilityAdapter()],
    )

    with pytest.raises(ValueError, match=f"Capability ownership mismatch.*{detail}"):
        registry.load()

    assert registry.is_loaded is False


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

    class DuplicatingCapabilityAdapter(VllmRuntimeAdapter):
        def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
            specs = super().build_capability_specs(soulstone)
            return [*specs, *specs]

    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [VllmSoulstoneConfig]),
        runtime_adapters=[DuplicatingCapabilityAdapter()],
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
    assert registry.is_loaded is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("malformed", "detail"),
    [
        ("duplicate", "duplicate"),
        ("missing", "missing"),
        ("foreign", "foreign"),
        ("dynamic", "inconsistent"),
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

    class MutableProbeAdapter(VllmRuntimeAdapter):
        probe_shape = "valid"

        async def probe_capability_states(
            self,
            animator: Any,
            specs: list[CapabilitySpec],
        ) -> list[CapabilityState]:
            _ = animator
            state = CapabilityState(
                capability_key=specs[0].key,
                is_dynamic=specs[0].is_dynamic,
                phase=CapabilityPhase.WARM,
                health="ok",
            )
            if self.probe_shape == "duplicate":
                return [state, state]
            if self.probe_shape == "missing":
                return []
            if self.probe_shape == "foreign":
                return [state.model_copy(update={"capability_key": "foreign:key"})]
            if self.probe_shape == "dynamic":
                return [state.model_copy(update={"is_dynamic": not specs[0].is_dynamic})]
            return [state]

    adapter = MutableProbeAdapter()
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

    class FailingProbeAdapter(VllmRuntimeAdapter):
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
                    is_dynamic=spec.is_dynamic,
                    phase=CapabilityPhase.WARM,
                    health="ok",
                )
                for spec in specs
            ]

    adapter = FailingProbeAdapter()
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

    class BlockingProbeAdapter(VllmRuntimeAdapter):
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
                    is_dynamic=spec.is_dynamic,
                    phase=CapabilityPhase.WARM,
                    health="ok",
                )
                for spec in specs
            ]

    adapter = BlockingProbeAdapter()
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

    class SequencedProbeAdapter(VllmRuntimeAdapter):
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
                    is_dynamic=specs[0].is_dynamic,
                    phase=CapabilityPhase.COLD if call == 2 else CapabilityPhase.WARM,
                )
            ]

    adapter = SequencedProbeAdapter()
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


def test_registry_unknown_animator_returns_empty_bindings(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    (runes_dir / "animator" / "soulstones").mkdir(parents=True, exist_ok=True)
    (runes_dir / "animator" / "portals").mkdir(parents=True, exist_ok=True)
    registry = _registry(runes_dir)

    assert registry.get_runtime("missing") is None
    assert registry.bind_model("missing") is None
    assert registry.bind_toolset("missing") is None
    assert registry.bind_toolsets("missing") == ()
    assert registry.is_ready("missing") is False
    assert registry.list_models("missing") == ()


def test_registry_model_inventory_projection_is_detached(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "embedder.toml",
        """
        name = "embedder"
        model_path = "/models/embedder.gguf"
        """,
    )
    registry = _registry(runes_dir)
    runtime = registry.get_runtime("embedder")
    assert runtime is not None
    canonical = ModelInfo(id="extension-owned", metadata={"owner": {"id": "extension"}})
    monkeypatch.setattr(runtime.connector, "list_models", lambda: (canonical,))

    projected = registry.list_models("embedder")[0]
    projected.id = "forged"
    projected.metadata["owner"]["id"] = "forged"

    retained = registry.list_models("embedder")[0]
    assert retained.id == "extension-owned"
    assert retained.metadata == {"owner": {"id": "extension"}}
    assert canonical.id == "extension-owned"


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
        declarations=_declarations(runes_dir, [LlamaCppSoulstoneConfig]),
        runtime_adapters=[LlamaCppRuntimeAdapter(control_plane=control)],
    )

    lifecycle = await registry.inspect_lifecycle("qwen-local")

    assert lifecycle is not None
    assert lifecycle.health == "ok"
    assert control.seen_animator_id == "qwen-local"


def test_runtime_adapter_registry_supports_custom_portal_definition() -> None:
    portal = CustomPortalConfig.model_validate(
        {
            "name": "custom-portal",
            "description": "Custom OpenAI-compatible portal",
            "base_url": "https://custom.portal/v1",
            "provider_name": "my-openai-gateway",
        }
    )

    def custom_factory(portal: PortalConfig) -> OpenAIPortal:
        if portal.provider_name != "my-openai-gateway":
            msg = "CustomPortalConfig requires the admitted gateway provider."
            raise ValueError(msg)
        connector = OpenAICompatibleConnector(
            kind="portal:my-openai-gateway",
            link=Link(up=True, activatable=False),
            base_url=str(portal.base_url or ""),
            model_infos=(ModelInfo(id="custom-gpt"),),
            default_model_id="custom-gpt",
        )
        return OpenAIPortal(rune=portal, connector=connector)

    adapters = RuntimeAdapterRegistry(
        portal_definitions=[PortalDefinition(rune_schema=CustomPortalConfig, factory=custom_factory)]
    )
    runtime = adapters.build_runtime(portal)

    assert runtime is not None
    assert isinstance(runtime, OpenAIPortal)
    assert runtime.connector.kind == "portal:my-openai-gateway"


def test_portal_definition_cannot_claim_another_schema() -> None:
    portal = CustomPortalConfig.model_validate(
        {
            "name": "custom-portal",
            "base_url": "https://custom.portal/v1",
            "provider_name": "custom",
        }
    )
    claimed = False

    def broad_factory(portal: PortalConfig) -> OpenAIPortal:
        nonlocal claimed
        claimed = True
        connector = OpenAICompatibleConnector(
            kind="portal:broad",
            link=Link(up=True, activatable=False),
            base_url=str(portal.base_url or ""),
            model_infos=(ModelInfo(id="broad-model"),),
            default_model_id="broad-model",
        )
        return OpenAIPortal(rune=portal, connector=connector)

    adapters = RuntimeAdapterRegistry(
        portal_definitions=[PortalDefinition(rune_schema=PortalConfig, factory=broad_factory)]
    )

    runtime = adapters.build_runtime(portal)

    assert runtime is not None
    assert claimed is False
    assert runtime.connector.kind == "portal:custom"


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
    assert grant.generation == grant.spec.generation_profile
    assert isinstance(grant.model, OpenAIChatModel)

    spec_snapshot = grant.spec
    state_snapshot = grant.state
    spec_snapshot.modalities_in.append("forged")
    spec_snapshot.metadata["forged"] = True
    state_snapshot.loaded_model_ids.append("forged")
    state_snapshot.metadata["forged"] = True
    assert "forged" not in grant.spec.modalities_in
    assert "forged" not in grant.spec.metadata
    assert "forged" not in grant.state.loaded_model_ids
    assert "forged" not in grant.state.metadata

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

    def unresolved(_rune: object) -> None:
        return None

    caplog.set_level("WARNING")

    registry = AnimatorRegistry(
        declarations=_declarations(runes_dir, [LlamaCppSoulstoneConfig]),
        runtime_adapters=_builtin_adapters(),
        runtime_factories=[unresolved],
    )
    with pytest.raises(
        ConflictTopologyError,
        match=r"at least one capability.*qwen-local",
    ):
        registry.load()
