"""A3-U4 mechanics: phase mapping, ActivationResult, await_warm, generation bridge."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import anyio
import pytest
from pydantic import ValidationError

from lychd.config.runes.loader import ConfigLoader
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.capabilities import ActivationResult, CapabilityPhase, CapabilityState
from lychd.domain.animation.errors import ActivationFailed, ActivationTimeout, CapabilityUnavailable
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.schemas import GenerationProfile
from lychd.domain.animation.services.declarations import (
    AnimatorDeclarations,
    compile_animator_declarations,
)
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.extensions.builtin.animator import LlamaCppSoulstoneConfig
from lychd.extensions.builtin.animator.llamacpp import LlamaCppControlPlane
from lychd.extensions.builtin.animator.runtimes import LlamaCppRuntimeAdapter


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{content.strip()}\n", encoding="utf-8")


def _declarations(runes_dir: Path) -> AnimatorDeclarations:
    return compile_animator_declarations(
        settings=get_settings(),
        runes=RuneRegistry(
            ConfigLoader(runes_dir).load_all([LlamaCppSoulstoneConfig]),
        ),
        core_reserved_ports={},
    )


class _SingleControl(LlamaCppControlPlane):
    """Stub control plane returning a fixed single-mode health for every probe."""

    def __init__(self, health: str) -> None:
        super().__init__()
        self._health = health

    async def inspect_animator(self, animator: Any) -> AnimatorLifecycle:
        del animator
        return AnimatorLifecycle(
            health=self._health,
            loaded_models=["qwen"] if self._health == "ok" else [],
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
        declarations=_declarations(runes_dir),
        runtime_adapters=[LlamaCppRuntimeAdapter(control_plane=control)],
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
            del animator
            return AnimatorLifecycle(
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
        declarations=_declarations(runes_dir),
        runtime_adapters=[LlamaCppRuntimeAdapter(control_plane=RouterControl())],
    )
    states = {s.capability_key: s for s in registry.list_capability_states()}
    main = registry.get_capability("router:chat:main")
    aux = registry.get_capability("router:chat:aux")
    assert main is not None
    assert aux is not None
    assert states[main.key].phase is CapabilityPhase.WARM
    assert states[aux.key].phase is CapabilityPhase.ACTIVATABLE


# --- ActivationResult -------------------------------------------------------


@pytest.mark.asyncio
async def test_activate_unknown_capability(tmp_path: Path) -> None:
    registry, _ = _single_registry(tmp_path, _SingleControl("ok"))
    result = await registry.activate_capability("does-not-exist")
    assert result.accepted is False
    assert result.reason == "unknown capability"


@pytest.mark.asyncio
async def test_activation_cancellation_abandons_adapter_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("ok"))
    activation_started = asyncio.Event()
    release = asyncio.Event()
    cleanup_started = asyncio.Event()
    cleanup_release = asyncio.Event()
    abandoned: list[str] = []

    async def activate(_animator: Any, _spec: Any) -> ActivationResult:
        activation_started.set()
        await release.wait()
        return ActivationResult(accepted=True)

    async def abandon(_animator: Any, spec: Any) -> None:
        cleanup_started.set()
        await cleanup_release.wait()
        abandoned.append(spec.key)

    monkeypatch.setattr(registry._runtime_adapters, "activate_capability", activate)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(registry._runtime_adapters, "abandon_activation", abandon)  # pyright: ignore[reportPrivateUsage]
    task = asyncio.create_task(registry.activate_capability(key))
    await activation_started.wait()

    task.cancel()
    await cleanup_started.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()

    cleanup_release.set()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert abandoned == [key]


@pytest.mark.asyncio
async def test_accepted_activation_refresh_cancellation_abandons_adapter_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("ok"))
    refresh_started = asyncio.Event()
    release = asyncio.Event()
    abandoned: list[str] = []

    async def activate(_animator: Any, _spec: Any) -> ActivationResult:
        return ActivationResult(accepted=True)

    async def refresh(_animator_name: str) -> None:
        refresh_started.set()
        await release.wait()

    async def abandon(_animator: Any, spec: Any) -> None:
        abandoned.append(spec.key)

    monkeypatch.setattr(registry._runtime_adapters, "activate_capability", activate)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(registry, "refresh_capability_states_for_animator", refresh)
    monkeypatch.setattr(registry._runtime_adapters, "abandon_activation", abandon)  # pyright: ignore[reportPrivateUsage]
    task = asyncio.create_task(registry.activate_capability(key))
    await refresh_started.wait()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert abandoned == [key]


# --- await_warm -------------------------------------------------------------


@pytest.mark.asyncio
async def test_await_warm_returns_when_warm(tmp_path: Path) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("ok"))
    state = await registry.await_warm(key, timeout_s=1.0, interval_s=0.01)
    assert state.phase is CapabilityPhase.WARM


@pytest.mark.parametrize("field_name", ["timeout_s", "interval_s"])
@pytest.mark.parametrize("value", [0.0, -0.1, float("nan"), float("inf"), float("-inf")])
@pytest.mark.asyncio
async def test_await_warm_rejects_invalid_poll_bound_before_polling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    value: float,
) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("ok"))
    poll_calls = 0

    async def unexpected_poll(*, key: str, deadline: float, interval_s: float) -> CapabilityState:
        del key, deadline, interval_s
        nonlocal poll_calls
        poll_calls += 1
        msg = "invalid await_warm bounds reached the polling boundary"
        raise AssertionError(msg)

    monkeypatch.setattr(registry, "_poll_until_warm", unexpected_poll)
    timeout_s = value if field_name == "timeout_s" else 1.0
    interval_s = value if field_name == "interval_s" else 0.01

    with pytest.raises(ValueError, match=field_name):
        await registry.await_warm(key, timeout_s=timeout_s, interval_s=interval_s)

    assert poll_calls == 0


@pytest.mark.asyncio
async def test_await_warm_times_out_on_persistent_warming(tmp_path: Path) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("loading"))
    with pytest.raises(ActivationTimeout, match="activation timed out before warm"):
        await registry.await_warm(key, timeout_s=0.05, interval_s=0.01)


@pytest.mark.asyncio
async def test_await_warm_timeout_abandons_adapter_observation_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("loading"))
    abandoned: list[str] = []

    async def abandon(_animator: Any, spec: Any) -> None:
        abandoned.append(spec.key)

    monkeypatch.setattr(registry._runtime_adapters, "abandon_activation", abandon)  # pyright: ignore[reportPrivateUsage]

    with pytest.raises(ActivationTimeout):
        await registry.await_warm(key, timeout_s=0.02, interval_s=0.005)

    assert abandoned == [key]


@pytest.mark.asyncio
async def test_await_warm_raises_on_error(tmp_path: Path) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("error"))
    with pytest.raises(ActivationFailed):
        await registry.await_warm(key, timeout_s=1.0, interval_s=0.01)


@pytest.mark.asyncio
async def test_await_warm_cleanup_failure_does_not_mask_activation_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("error"))
    calls = 0

    async def fail_cleanup(_animator: Any, _spec: Any) -> None:
        nonlocal calls
        calls += 1
        msg = "cleanup failed"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        registry._runtime_adapters,  # pyright: ignore[reportPrivateUsage]
        "abandon_activation",
        fail_cleanup,
    )

    with pytest.raises(ActivationFailed):
        await registry.await_warm(key, timeout_s=1.0, interval_s=0.01)

    assert calls == 1


@pytest.mark.asyncio
async def test_await_warm_cancellation_shields_observer_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry, key = _single_registry(tmp_path, _SingleControl("loading"))
    probe_started = anyio.Event()
    cleanup_finished = anyio.Event()
    cancel_scope: anyio.CancelScope | None = None

    async def block_probe(_key: str) -> None:
        probe_started.set()
        await anyio.sleep_forever()

    async def abandon(_animator: Any, _spec: Any) -> None:
        await anyio.sleep(0)  # noqa: ASYNC115 - explicit cancellation checkpoint in the shield test
        cleanup_finished.set()

    monkeypatch.setattr(registry, "refresh_capability_state", block_probe)
    monkeypatch.setattr(
        registry._runtime_adapters,  # pyright: ignore[reportPrivateUsage]
        "abandon_activation",
        abandon,
    )

    async def wait_until_cancelled() -> None:
        nonlocal cancel_scope
        with anyio.CancelScope() as local_scope:
            cancel_scope = local_scope
            await registry.await_warm(key, timeout_s=10.0, interval_s=1.0)

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(wait_until_cancelled)
        await probe_started.wait()
        assert cancel_scope is not None
        cancel_scope.cancel()

    assert cleanup_finished.is_set()


@pytest.mark.asyncio
async def test_await_warm_unknown_capability(tmp_path: Path) -> None:
    registry, _ = _single_registry(tmp_path, _SingleControl("ok"))
    with pytest.raises(CapabilityUnavailable):
        await registry.await_warm("nope", timeout_s=0.1)


def test_generation_profile_overlay_prefers_non_none() -> None:
    base = GenerationProfile(temperature=0.7, max_tokens=1024)
    override = GenerationProfile(temperature=0.2)
    merged = base.overlay(override)
    assert merged.temperature == 0.2
    assert merged.max_tokens == 1024
    assert base.overlay(None) == base


@pytest.mark.parametrize("field_name", ["temperature", "top_p"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_generation_profile_rejects_non_finite_floats(field_name: str, value: float) -> None:
    with pytest.raises(ValidationError):
        GenerationProfile.model_validate({field_name: value})
