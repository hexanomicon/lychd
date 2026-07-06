from __future__ import annotations

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from lychd.config.settings import get_settings
from lychd.domain.animation.schemas import ConcurrencyIntent, GenericSoulstoneConfig, SoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import RuntimePlan
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.system.schemas import QuadletContainer, QuadletPod, QuadletTarget


class SoulstoneFactory(ModelFactory[GenericSoulstoneConfig]):
    """Factory for generating valid concrete Soulstone config instances."""

    __model__ = GenericSoulstoneConfig
    volumes: list[str] = []  # noqa: RUF012 Override the instance attribute


@pytest.fixture
def transmuter() -> Transmuter:
    return Transmuter(runtime_planner=RuntimeAdapterRegistry())


def test_transmute_core_infrastructure(transmuter: Transmuter) -> None:
    """Verify that the Pod and core Quadlet manifests are always generated."""
    manifests = transmuter.transmute_all([])
    settings = get_settings()

    # 1. Check Pod
    pods = [manifest for manifest in manifests if isinstance(manifest, QuadletPod)]
    assert len(pods) == 1
    assert pods[0].pod_name == "lychd"

    # 2. Check Core Containers
    containers = {manifest.container_name: manifest for manifest in manifests if isinstance(manifest, QuadletContainer)}
    assert "lychd-vessel" in containers
    assert "lychd-phylactery" in containers
    # The Oculus (Phoenix) is no longer an unconditional core container; it is
    # emitted only when an observability extension rune is active.
    vessel = containers["lychd-vessel"]
    assert settings.app.secret_key_secret in vessel.secrets
    assert settings.db.password_secret in vessel.secrets
    assert vessel.env_vars["APP__SECRET_KEY_FILE"] == f"/run/secrets/{settings.app.secret_key_secret}"
    assert vessel.env_vars["DB__PASSWORD_FILE"] == f"/run/secrets/{settings.db.password_secret}"


def test_transmute_soulstone_to_manifest(transmuter: Transmuter) -> None:
    """Verify a Soulstone Rune is correctly transmuted."""
    stone = SoulstoneFactory.build(
        name="hermes",
        image="ollama/ollama",
        groups=[],
        env_vars={"CTX_SIZE": "4096"},
    )
    manifests = transmuter.transmute_all([stone])

    soul_manifests = [
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-hermes"
    ]
    assert len(soul_manifests) == 1
    manifest = soul_manifests[0]
    assert manifest.image == "ollama/ollama"
    assert manifest.env_vars["CTX_SIZE"] == "4096"

    # 3. Check System Mounts (ADR 13)
    volumes = [str(v) for v in manifest.volumes]
    assert any("config/lychd:ro" in v for v in volumes)
    assert any("share/lychd:rw" in v for v in volumes)
    assert any("share/lychd/core:ro" in v for v in volumes)


def test_transmute_hydrates_soulstone_secret_env_files(transmuter: Transmuter) -> None:
    """Soulstone secret mappings should become Secret= mounts and env file paths."""
    stone = SoulstoneFactory.build(
        name="vault",
        image="vllm/vllm-openai:latest",
        groups=[],
        secret_env_files={"HF_TOKEN_FILE": "hf_runtime_token"},
    )

    manifests = transmuter.transmute_all([stone])
    manifest = next(
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-vault"
    )

    assert manifest.env_vars["HF_TOKEN_FILE"] == "/run/secrets/hf_runtime_token"  # noqa: S105 - fixture secret path
    assert manifest.secrets == ["hf_runtime_token"]


def test_transmute_merges_runtime_podman_args() -> None:
    """Runtime adapter podman args are merged with base container defaults."""

    class StubRuntimePlanner:
        def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
            _ = soulstone
            return RuntimePlan(exec_args=["serve", "qwen"], podman_args=["--ipc=host"])

    transmuter = Transmuter(runtime_planner=StubRuntimePlanner())
    stone = SoulstoneFactory.build(name="qwen", image="vllm/vllm-openai:latest")

    manifests = transmuter.transmute_all([stone])
    manifest = next(
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-qwen"
    )

    assert "--replace" in manifest.podman_args
    assert "--ipc=host" in manifest.podman_args


def test_law_of_exclusivity_solitary(transmuter: Transmuter) -> None:
    """Solitary stones should conflict with each other's services."""
    stone_a = SoulstoneFactory.build(name="alpha", groups=[])
    stone_b = SoulstoneFactory.build(name="beta", groups=[])

    manifests = transmuter.transmute_all([stone_a, stone_b])

    alpha_manifest = next(
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-alpha"
    )
    assert "lychd-beta.service" in alpha_manifest.conflicts


def test_law_of_exclusivity_covens(transmuter: Transmuter) -> None:
    """Grouped stones should conflict with other COVENS (targets) if multi-member."""
    # Members of Coven 'logic'
    alpha = SoulstoneFactory.build(name="alpha", groups=["logic"])
    beta = SoulstoneFactory.build(name="beta", groups=["logic"])

    # Member of Coven 'creative'
    gamma = SoulstoneFactory.build(name="gamma", groups=["creative"])
    delta = SoulstoneFactory.build(name="delta", groups=["creative"])

    manifests = transmuter.transmute_all([alpha, beta, gamma, delta])

    # Alpha should conflict with 'creative' target, but NOT with Beta
    alpha_manifest = next(
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-alpha"
    )
    assert "lychd-coven-creative.target" in alpha_manifest.conflicts
    assert "lychd-beta.service" not in alpha_manifest.conflicts

    # Verify targets are generated
    targets = {manifest.name: manifest for manifest in manifests if isinstance(manifest, QuadletTarget)}
    assert "logic" in targets
    assert "creative" in targets


def test_dedicated_soulstone_not_wanted_at_boot(transmuter: Transmuter) -> None:
    """F4: dedicated stones must not be auto-WantedBy=default.target (nondeterministic boot)."""
    dedicated = SoulstoneFactory.build(name="loner", groups=[], concurrency=ConcurrencyIntent(dedicated=True))

    manifests = transmuter.transmute_all([dedicated])
    manifest = next(m for m in manifests if isinstance(m, QuadletContainer) and m.container_name == "lychd-loner")
    assert manifest.wanted_by == []


def test_persistent_resident_soulstone_wanted_at_boot(transmuter: Transmuter) -> None:
    """F4: persistent-resident stones keep WantedBy=default.target."""
    resident = SoulstoneFactory.build(
        name="resident",
        groups=[],
        concurrency=ConcurrencyIntent(dedicated=False, persistent_resident=True),
    )

    manifests = transmuter.transmute_all([resident])
    manifest = next(m for m in manifests if isinstance(m, QuadletContainer) and m.container_name == "lychd-resident")
    assert manifest.wanted_by == ["default.target"]


def test_core_containers_remain_wanted_at_boot(transmuter: Transmuter) -> None:
    """F4 guard: vessel/phylactery core units must stay WantedBy=default.target."""
    manifests = transmuter.transmute_all([])
    containers = {m.container_name: m for m in manifests if isinstance(m, QuadletContainer)}
    assert containers["lychd-vessel"].wanted_by == ["default.target"]
    assert containers["lychd-phylactery"].wanted_by == ["default.target"]


def test_coven_of_one_no_target(transmuter: Transmuter) -> None:
    """A group with only one member should NOT generate a target unit."""
    stone = SoulstoneFactory.build(name="hermes", groups=["logic"])

    manifests = transmuter.transmute_all([stone])

    # No Quadlet target named 'logic'
    targets = [manifest for manifest in manifests if isinstance(manifest, QuadletTarget) and manifest.name == "logic"]
    assert len(targets) == 0

    # Hermes manifest should not have targets list set to 'logic' if it's not a real coven
    hermes_manifest = next(
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-hermes"
    )
    assert "logic" not in hermes_manifest.targets
