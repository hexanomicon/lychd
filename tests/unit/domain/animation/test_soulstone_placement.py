"""Rune placement, installation binding and intent generation contracts."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.orchestration import DesktopContainerBinding, SwitchingSettings
from lychd.config.settings.root import Settings
from lychd.domain.animation.schemas import OpenAIPortalConfig
from lychd.domain.animation.services.adapters.catalog import default_model_id_for_soulstone, model_infos_from_soulstone
from lychd.domain.animation.services.declarations import compile_animator_declarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.orchestration.actuator import capability_config_generation
from lychd.extensions.builtin.animator.runtimes import LlamaCppRuntimeAdapter
from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstoneConfig, VllmSoulstoneConfig

if TYPE_CHECKING:
    from pathlib import Path


def _stone(**overrides: object) -> LlamaCppSoulstoneConfig:
    return LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "local",
            "model_path": "/shelf/a.gguf",
            "startup_mode": "single",
            "served_model_id": "stable",
            "port": 25001,
            "base_url": "http://127.0.0.1:25001/v1",
            **overrides,
        }
    )


def _registry(
    stone: LlamaCppSoulstoneConfig,
    switching: SwitchingSettings,
    *,
    replica: str | None = None,
) -> AnimatorRegistry:
    settings = Settings()
    settings.orchestration.switching = switching
    declarations = compile_animator_declarations(
        settings=settings, runes=RuneRegistry((stone,)), lifecycle_binding_digest=replica
    )
    registry = AnimatorRegistry(declarations=declarations, runtime_adapters=(LlamaCppRuntimeAdapter(),))
    registry.load(probe_readiness=False)
    return registry


def test_placement_is_a_local_runtime_choice() -> None:
    legacy = _stone()
    assert legacy.placement is None
    assert legacy.resolved_placement("native") == "native"
    assert legacy.resolved_placement("container") == "container"
    assert _stone(placement="container").resolved_placement("native") == "container"
    assert _stone(placement="native").resolved_placement("container") == "native"
    with pytest.raises(ValidationError, match="placement"):
        _stone(placement="auto")
    with pytest.raises(ValidationError, match="placement"):
        OpenAIPortalConfig.model_validate({"name": "remote", "placement": "native"})
    with pytest.raises(ValidationError, match="no supported native placement"):
        VllmSoulstoneConfig.model_validate({"name": "other", "placement": "native"})


@pytest.mark.parametrize(
    ("model_path", "model_id"),
    [(r"C:\models\a.q4.gguf", "a.q4"), ("/models/a.q4.gguf", "a.q4"), (r"relative/a\b.gguf", r"a\b")],
)
def test_replicas_use_the_same_model_path_fallback_in_catalog_and_command(model_path: str, model_id: str) -> None:
    stone = _stone(served_model_id=None, model_path=model_path)
    assert default_model_id_for_soulstone(stone, ()) == model_id
    assert [info.id for info in model_infos_from_soulstone(stone)] == [model_id]
    command = LlamaCppRuntimeAdapter().plan(stone).exec_args
    assert command[command.index("--alias") + 1] == model_id
    registry = _registry(stone, SwitchingSettings(actuator="host-reactor"))
    assert [spec.model_id for spec in registry.list_capabilities()] == [model_id]


@pytest.mark.parametrize(
    "override",
    [
        {"quadlet": {"image": "example/model"}},
        {"volumes": ["/shelf:/models:ro"]},
        {"devices": ["nvidia.com/gpu=all"]},
        {"security_label_disable": True},
        {"secret_env_files": {"TOKEN": "example_secret"}},
        {"env_vars": {"CONFIG": "example"}},
        {"exec": ["--sleep-idle-seconds", "-1"]},
        {"extra_args": ["--threads", "8"]},
        {"chat_template": "template"},
        {"lora_adapters": ["/shelf/test.gguf"]},
        {"models_preset": "preset.ini"},
        {"models_max": 2},
        {"embedding_profile": "qwen3-06b-q8-b9445@1"},
    ],
)
def test_native_placement_refuses_other_launch_authorities(override: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="Native"):
        _stone(placement="native", **override)


def test_legacy_journal_digest_is_preserved_without_local_lifecycle_authority() -> None:
    old = _registry(_stone(concurrency={"dedicated": False}), SwitchingSettings(actuator="host-reactor"))
    (rune,) = old.list_soulstone_runes()
    old_payload = {
        "capabilities": [spec.model_dump(mode="json") for spec in old.list_capabilities()],
        "runtime_topology": [
            {
                "name": rune.name,
                "groups": sorted(rune.groups),
                "concurrency": rune.concurrency.model_dump(mode="json"),
            }
        ],
    }
    encoded = json.dumps(old_payload, sort_keys=True, separators=(",", ":")).encode()
    assert capability_config_generation(old) == "sha256:" + hashlib.sha256(encoded).hexdigest()


def test_default_managed_placement_fences_material_changes_without_changing_identity() -> None:
    settings = SwitchingSettings(actuator="host-reactor")
    registry = _registry(_stone(), settings)
    for changed in (_stone(placement="container"), _stone(quadlet={"image": "updated/image"})):
        replacement = _registry(changed, settings)
        assert registry.list_capabilities() == replacement.list_capabilities()
        assert capability_config_generation(registry) != capability_config_generation(replacement)


def test_native_owners_and_material_rune_changes_fence_an_identical_capability(tmp_path: Path) -> None:
    switching = SwitchingSettings(
        actuator="native-process",
        native_state_dir=tmp_path,
        native_llama_server=tmp_path / "llama-server",
        native_model_root=tmp_path,
    )
    rune = _stone(placement="native")
    host = _registry(rune, switching)
    digest = host.lifecycle_binding_digest
    assert digest is not None
    replica = _registry(rune, SwitchingSettings(actuator="host-reactor"), replica=digest)
    assert capability_config_generation(replica) == capability_config_generation(host)

    for changed in (
        _registry(rune, switching.model_copy(update={"native_llama_server": tmp_path / "other" / "llama-server"})),
        _registry(rune, switching.model_copy(update={"native_model_root": tmp_path / "other"})),
        _registry(_stone(placement="native", model_path="/shelf/b.gguf"), switching),
        _registry(_stone(placement="native", n_gpu_layers=1), SwitchingSettings(), replica=digest),
        _registry(_stone(placement="container"), SwitchingSettings(actuator="host-reactor")),
        _registry(_stone(), switching),
    ):
        assert host.list_capabilities() == changed.list_capabilities()
        assert capability_config_generation(host) != capability_config_generation(changed)


def test_container_ownership_is_exact_and_fenced(tmp_path: Path) -> None:
    binding = DesktopContainerBinding(
        animator="local",
        engine="podman",
        endpoint="unix:///run/user/1000/podman.sock",
        container_id="1" * 64,
        container_port=8080,
        host_port=5443,
        tls_sha256="f" * 64,
    )
    switching = SwitchingSettings(actuator="native-process", native_state_dir=tmp_path, containers=(binding,))
    stone = _stone(placement="container")
    registry = _registry(stone, switching)
    for update in ({"engine": "docker"}, {"container_id": "2" * 64}, {"tls_sha256": "0" * 64}):
        replacement = binding.model_copy(update=update)
        changed = _registry(stone, switching.model_copy(update={"containers": (replacement,)}))
        assert changed.list_capabilities() == registry.list_capabilities()
        assert capability_config_generation(changed) != capability_config_generation(registry)
    for bindings in ((), (binding.model_copy(update={"animator": "wrong"}),)):
        with pytest.raises(ValueError, match="must match"):
            _registry(stone, switching.model_copy(update={"containers": bindings}))
