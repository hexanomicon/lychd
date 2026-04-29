from __future__ import annotations

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from lychd.config.settings import get_settings
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import RuntimePlan
from lychd.domain.animation.transmute import Transmuter
from lychd.system.schemas import QuadletContainer, QuadletPod, QuadletTarget


class SoulstoneFactory(ModelFactory[SoulstoneConfig]):
    """Factory for generating valid Soulstone instances."""

    __model__ = SoulstoneConfig
    volumes: list[str] = []  # noqa: RUF012 Override the instance attribute


@pytest.fixture
def transmuter() -> Transmuter:
    return Transmuter()


def test_transmute_core_infrastructure(transmuter: Transmuter) -> None:
    """Verify that the Pod and Core Runes are always generated."""
    runes = transmuter.transmute_all([])
    settings = get_settings()

    # 1. Check Pod
    pods = [r for r in runes if isinstance(r, QuadletPod)]
    assert len(pods) == 1
    assert pods[0].pod_name == "lychd"

    # 2. Check Core Containers
    containers = {r.container_name: r for r in runes if isinstance(r, QuadletContainer)}
    assert "lychd-vessel" in containers
    assert "lychd-phylactery" in containers
    assert "lychd-oculus" in containers
    vessel = containers["lychd-vessel"]
    assert settings.app.secret_key_secret in vessel.secrets
    assert settings.db.password_secret in vessel.secrets
    assert vessel.env_vars["APP__SECRET_KEY_FILE"] == f"/run/secrets/{settings.app.secret_key_secret}"
    assert vessel.env_vars["DB__PASSWORD_FILE"] == f"/run/secrets/{settings.db.password_secret}"


def test_transmute_soulstone_to_rune(transmuter: Transmuter) -> None:
    """Verify a soulstone is correctly transmuted."""
    stone = SoulstoneFactory.build(
        name="hermes",
        image="ollama/ollama",
        groups=[],
        env_vars={"CTX_SIZE": "4096"},
    )
    runes = transmuter.transmute_all([stone])

    soul_runes = [r for r in runes if isinstance(r, QuadletContainer) and r.container_name == "lychd-hermes"]
    assert len(soul_runes) == 1
    rune = soul_runes[0]
    assert rune.image == "ollama/ollama"
    assert rune.env_vars["CTX_SIZE"] == "4096"

    # 3. Check System Mounts (ADR 13)
    volumes = [str(v) for v in rune.volumes]
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

    runes = transmuter.transmute_all([stone])
    rune = next(r for r in runes if isinstance(r, QuadletContainer) and r.container_name == "lychd-vault")

    assert rune.env_vars["HF_TOKEN_FILE"] == "/run/secrets/hf_runtime_token"  # noqa: S105 - fixture secret path
    assert rune.secrets == ["hf_runtime_token"]


def test_transmute_merges_runtime_podman_args() -> None:
    """Runtime adapter podman args are merged with base container defaults."""

    class StubRuntimePlanner:
        def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
            _ = soulstone
            return RuntimePlan(exec_args=["serve", "qwen"], podman_args=["--ipc=host"])

    transmuter = Transmuter(runtime_planner=StubRuntimePlanner())
    stone = SoulstoneFactory.build(name="qwen", image="vllm/vllm-openai:latest")

    runes = transmuter.transmute_all([stone])
    rune = next(r for r in runes if isinstance(r, QuadletContainer) and r.container_name == "lychd-qwen")

    assert "--replace" in rune.podman_args
    assert "--ipc=host" in rune.podman_args


def test_law_of_exclusivity_solitary(transmuter: Transmuter) -> None:
    """Solitary stones should conflict with each other's services."""
    stone_a = SoulstoneFactory.build(name="alpha", groups=[])
    stone_b = SoulstoneFactory.build(name="beta", groups=[])

    runes = transmuter.transmute_all([stone_a, stone_b])

    # Find Alpha's rune
    alpha_rune = next(r for r in runes if isinstance(r, QuadletContainer) and r.container_name == "lychd-alpha")
    assert "lychd-beta.service" in alpha_rune.conflicts


def test_law_of_exclusivity_covens(transmuter: Transmuter) -> None:
    """Grouped stones should conflict with other COVENS (targets) if multi-member."""
    # Members of Coven 'logic'
    alpha = SoulstoneFactory.build(name="alpha", groups=["logic"])
    beta = SoulstoneFactory.build(name="beta", groups=["logic"])

    # Member of Coven 'creative'
    gamma = SoulstoneFactory.build(name="gamma", groups=["creative"])
    delta = SoulstoneFactory.build(name="delta", groups=["creative"])

    runes = transmuter.transmute_all([alpha, beta, gamma, delta])

    # Alpha should conflict with 'creative' target, but NOT with Beta
    alpha_rune = next(r for r in runes if isinstance(r, QuadletContainer) and r.container_name == "lychd-alpha")
    assert "lychd-coven-creative.target" in alpha_rune.conflicts
    assert "lychd-beta.service" not in alpha_rune.conflicts

    # Verify targets are generated
    targets = {r.name: r for r in runes if isinstance(r, QuadletTarget)}
    assert "logic" in targets
    assert "creative" in targets


def test_coven_of_one_no_target(transmuter: Transmuter) -> None:
    """A group with only one member should NOT generate a target unit."""
    stone = SoulstoneFactory.build(name="hermes", groups=["logic"])

    runes = transmuter.transmute_all([stone])

    # No TargetRune named 'logic'
    targets = [r for r in runes if isinstance(r, QuadletTarget) and r.name == "logic"]
    assert len(targets) == 0

    # Hermes rune should not have targets list set to 'logic' if it's not a real coven
    hermes_rune = next(r for r in runes if isinstance(r, QuadletContainer) and r.container_name == "lychd-hermes")
    assert "logic" not in hermes_rune.targets
