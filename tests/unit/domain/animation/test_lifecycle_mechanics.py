"""A3-U4 mechanics: phase mapping, ActivationResult, await_warm, generation bridge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lychd.domain.animation.capabilities import ActivationResult, CapabilityPhase
from lychd.domain.animation.errors import ActivationFailed, ActivationTimeout, CapabilityUnavailable
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.schemas import GenerationProfile
from lychd.domain.animation.services.binder import generation_to_model_settings
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.extensions.builtin.animator import LlamaCppSoulstoneConfig
from lychd.extensions.builtin.animator.llamacpp import LlamaCppControlPlane
from lychd.extensions.builtin.animator.runtimes import LlamaCppRuntimeAdapter


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{content.strip()}\n", encoding="utf-8")


class _SingleControl(LlamaCppControlPlane):
    """Stub control plane returning a fixed single-mode health for every probe."""

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


def _single_registry(tmp_path: Path, control: LlamaCppControlPlane) -> tuple[AnimatorRegistry, str]:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "qwen.toml",
        """
        name = "qwen-local"
        model_path = "/models/qwen.gguf"
        """,
    )
    registry = AnimatorRegistry(
        rune_schemas=[LlamaCppSoulstoneConfig],
        runtime_adapters=[LlamaCppRuntimeAdapter(control_plane=control)],
        runes_dir=runes_dir,
        reserved_ports={},
    )
    registry.ensure_loaded()
    key = registry.list_capabilities()[0].key
    return registry, key


# --- phase mapping table (spec §2) -----------------------------------------


@pytest.mark.parametrize(
    ("health", "expected"),
    [
        ("ok", CapabilityPhase.WARM),
        ("loading", CapabilityPhase.WARMING),
        ("error", CapabilityPhase.ERROR),
        ("unknown", CapabilityPhase.COLD),
    ],
)
def test_single_mode_phase_mapping(tmp_path: Path, health: str, expected: CapabilityPhase) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl(health))
    state = registry.get_capability_state(key)
    assert state is not None
    assert state.phase is expected


def test_router_phase_mapping_activatable_vs_warm(tmp_path: Path) -> None:
    preset = tmp_path / "models.ini"
    preset.write_text(
        "version = 1\n\n[main]\nmodel = /models/main.gguf\n\n[aux]\nmodel = /models/aux.gguf\n",
        encoding="utf-8",
    )

    class RouterControl(LlamaCppControlPlane):
        async def inspect_animator(self, animator: Any) -> AnimatorLifecycle:
            return AnimatorLifecycle(
                runtime="llamacpp",
                base_url=animator.connector.base_url,
                mode="router",
                health="ok",
                supports_router=True,
                loaded_models=["main"],
                available_models=["main", "aux"],
            )

    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "router.toml",
        f"""
        name = "router"
        startup_mode = "router"
        models_preset = "{preset}"
        """,
    )
    registry = AnimatorRegistry(
        rune_schemas=[LlamaCppSoulstoneConfig],
        runtime_adapters=[LlamaCppRuntimeAdapter(control_plane=RouterControl())],
        runes_dir=runes_dir,
        reserved_ports={},
    )
    states = {s.capability_key: s for s in registry.list_capability_states()}
    main = registry.get_capability("router:chat:main")
    aux = registry.get_capability("router:chat:aux")
    assert main is not None
    assert aux is not None
    assert states[main.key].phase is CapabilityPhase.WARM
    assert states[aux.key].phase is CapabilityPhase.ACTIVATABLE


# --- ActivationResult -------------------------------------------------------


def test_activate_fixed_single_mode_returns_not_accepted(tmp_path: Path) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("ok"))
    result = registry.activate_capability(key)
    assert isinstance(result, ActivationResult)
    assert result.accepted is False
    assert result.reason == "fixed capability; lifecycle owned by unit"


def test_activate_unknown_capability(tmp_path: Path) -> None:
    registry, _ = _single_registry(tmp_path, _SingleControl("ok"))
    result = registry.activate_capability("does-not-exist")
    assert result.accepted is False
    assert result.phase is CapabilityPhase.UNKNOWN


# --- await_warm -------------------------------------------------------------


@pytest.mark.asyncio
async def test_await_warm_returns_when_warm(tmp_path: Path) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("ok"))
    state = await registry.await_warm(key, timeout_s=1.0, interval_s=0.01)
    assert state.phase is CapabilityPhase.WARM


@pytest.mark.asyncio
async def test_await_warm_times_out_on_persistent_warming(tmp_path: Path) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("loading"))
    with pytest.raises(ActivationTimeout) as exc:
        await registry.await_warm(key, timeout_s=0.05, interval_s=0.01)
    assert exc.value.last_state.phase is CapabilityPhase.WARMING


@pytest.mark.asyncio
async def test_await_warm_raises_on_error(tmp_path: Path) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("error"))
    with pytest.raises(ActivationFailed):
        await registry.await_warm(key, timeout_s=1.0, interval_s=0.01)


@pytest.mark.asyncio
async def test_await_warm_unknown_capability(tmp_path: Path) -> None:
    registry, _ = _single_registry(tmp_path, _SingleControl("ok"))
    with pytest.raises(CapabilityUnavailable):
        await registry.await_warm("nope", timeout_s=0.1)


# --- generation bridge + overlay -------------------------------------------


def test_generation_to_model_settings_maps_known_fields() -> None:
    profile = GenerationProfile(max_tokens=256, temperature=0.4, top_p=0.9, top_k=40)
    settings = generation_to_model_settings(profile)
    assert settings is not None
    assert settings["max_tokens"] == 256
    assert settings["temperature"] == 0.4
    assert settings["top_p"] == 0.9
    # top_k is not a pydantic-ai ModelSettings key and is omitted.
    assert "top_k" not in settings


def test_generation_to_model_settings_empty_returns_none() -> None:
    assert generation_to_model_settings(GenerationProfile()) is None


def test_generation_profile_overlay_prefers_non_none() -> None:
    base = GenerationProfile(temperature=0.7, max_tokens=1024)
    override = GenerationProfile(temperature=0.2)
    merged = base.overlay(override)
    assert merged.temperature == 0.2
    assert merged.max_tokens == 1024
    assert base.overlay(None) == base
