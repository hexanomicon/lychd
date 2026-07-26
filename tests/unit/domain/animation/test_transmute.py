from __future__ import annotations

from pathlib import Path

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from lychd.config.settings.orchestration import OrchestrationSettings, SwitchingSettings
from lychd.config.settings.root import Settings, get_settings
from lychd.domain.animation.schemas import (
    ConcurrencyIntent,
    GenericSoulstoneConfig,
    OpenAIPortalConfig,
    SoulstoneConfig,
)
from lychd.domain.animation.services.adapters.contracts import RuntimePlan
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.system import constants
from lychd.system.schemas import QuadletContainer, QuadletPod, QuadletTarget


class SoulstoneFactory(ModelFactory[GenericSoulstoneConfig]):
    """Factory for generating valid concrete Soulstone config instances."""

    __model__ = GenericSoulstoneConfig
    volumes: list[str] = []  # noqa: RUF012 Override the instance attribute


@pytest.fixture
def transmuter() -> Transmuter:
    return Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry())


def test_transmute_core_infrastructure(transmuter: Transmuter) -> None:
    """Verify that the Pod and core Quadlet manifests are always generated."""
    manifests = transmuter.transmute_all([])
    settings = get_settings()

    # 1. Check Pod
    pods = [manifest for manifest in manifests if isinstance(manifest, QuadletPod)]
    assert len(pods) == 1
    assert pods[0].pod_name == "lychd"
    assert pods[0].shm_size is None

    # 2. Check Core Containers
    containers = {manifest.container_name: manifest for manifest in manifests if isinstance(manifest, QuadletContainer)}
    assert "lychd-vessel" in containers
    assert "lychd-phylactery" in containers
    assert "lychd-migrate" in containers
    # The Oculus (Phoenix) is no longer an unconditional core container; it is
    # emitted only when an observability extension rune is active.
    vessel = containers["lychd-vessel"]
    assert settings.server.web.secret_key_secret in vessel.secrets
    assert settings.server.database.password_secret in vessel.secrets
    assert vessel.env_vars["LYCHD_APP_SECRET_KEY_FILE"] == f"/run/secrets/{settings.server.web.secret_key_secret}"
    assert vessel.env_vars["LYCHD_DB_PASSWORD_FILE"] == f"/run/secrets/{settings.server.database.password_secret}"
    assert vessel.user == "%U"
    assert vessel.requires == ["lychd-migrate.service", "lychd-reactor.path"]
    assert vessel.after == ["lychd-migrate.service", "lychd-reactor.path"]
    assert vessel.env_vars["HOME"] == str(constants.PATH_CODEX_ROOT.parents[1])
    vessel_mounts = {mount.host_path: mount for mount in vessel.volumes}
    reactor_inbox = settings.orchestration.switching.host_reactor_dir
    reactor_journal = settings.orchestration.switching.host_reactor_journal_dir
    assert vessel_mounts[reactor_inbox].container_path == reactor_inbox
    assert vessel_mounts[reactor_inbox].options == ["rw", "Z"]
    assert vessel_mounts[reactor_journal].container_path == reactor_journal
    assert vessel_mounts[reactor_journal].options == ["ro", "Z"]

    phylactery = containers["lychd-phylactery"]
    assert phylactery.user is None
    assert phylactery.secrets == [settings.server.database.password_secret]
    assert phylactery.env_vars["POSTGRES_PASSWORD_FILE"] == f"/run/secrets/{settings.server.database.password_secret}"
    assert phylactery.wants == ["lychd-pod.service"]
    assert phylactery.after == ["lychd-pod.service"]
    assert phylactery.volumes[0].host_path == constants.PATH_POSTGRESS_DATA_DIR
    assert phylactery.volumes[0].container_path.as_posix() == "/var/lib/postgresql/data"
    assert phylactery.volumes[0].options == ["U", "Z"]
    assert phylactery.volumes[1].host_path == constants.PATH_POSTGRES_ROOT_DIR / "init_db.sh"
    assert phylactery.volumes[1].container_path.as_posix() == "/docker-entrypoint-initdb.d/10-lychd-init.sh"

    migrator = containers["lychd-migrate"]
    assert migrator.service_type == "oneshot"
    assert migrator.restart_policy == "no"
    assert migrator.requires == ["lychd-phylactery.service"]
    assert migrator.after == ["lychd-phylactery.service"]
    assert migrator.exec == "lychd database --wait-seconds 60 upgrade head --no-prompt"
    assert migrator.wanted_by == []
    assert migrator.user == "%U"


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
    assert manifest.user == "%U"
    assert manifest.pod_service == "lychd-pod.service"
    assert manifest.wants == ["lychd-pod.service"]
    assert manifest.after == ["lychd-pod.service"]
    assert manifest.env_vars["XDG_CONFIG_HOME"] == str(constants.PATH_XDG_CONFIG_HOME)
    assert manifest.env_vars["XDG_DATA_HOME"] == str(constants.PATH_XDG_DATA_HOME)

    # Data-plane runtimes never inherit the trusted control-plane mounts. Only
    # explicit model/runtime volumes are present.
    volumes = [str(v) for v in manifest.volumes]
    assert not any("config/lychd" in v for v in volumes)
    assert not any("share/lychd/triggers" in v for v in volumes)


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

    transmuter = Transmuter(settings=get_settings(), runtime_planner=StubRuntimePlanner())
    stone = SoulstoneFactory.build(name="qwen", image="vllm/vllm-openai:latest")

    manifests = transmuter.transmute_all([stone])
    manifest = next(
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-qwen"
    )

    assert "--replace" in manifest.podman_args
    assert "--ipc=host" in manifest.podman_args


def test_soulstone_exec_rejects_standalone_systemd_command_separator() -> None:
    with pytest.raises(ValueError, match="standalone systemd command separator"):
        GenericSoulstoneConfig(
            name="separator",
            image="example/runtime",
            exec=[";", "/bin/touch", "/tmp/pwned"],  # noqa: S108
        )


def test_runtime_plan_podman_args_reject_standalone_systemd_command_separator() -> None:
    class UnsafeRuntimePlanner:
        def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
            _ = soulstone
            return RuntimePlan(podman_args=["';'"])

    stone = SoulstoneFactory.build(name="separator", image="example/runtime")
    with pytest.raises(ValueError, match="standalone systemd command separator"):
        Transmuter(settings=get_settings(), runtime_planner=UnsafeRuntimePlanner()).transmute_all([stone])


def test_transmute_aggregates_runtime_shared_memory_requirement() -> None:
    class StubRuntimePlanner:
        def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
            requested = 8 * 1024**3 if soulstone.name == "large" else 2 * 1024**3
            return RuntimePlan(pod_shared_memory_bytes=requested)

    stones = [
        SoulstoneFactory.build(name="small", image="example/small"),
        SoulstoneFactory.build(name="large", image="example/large"),
    ]
    manifests = Transmuter(settings=get_settings(), runtime_planner=StubRuntimePlanner()).transmute_all(stones)
    pod = next(manifest for manifest in manifests if isinstance(manifest, QuadletPod))

    assert pod.shm_size == "10g"


def test_transmute_rejects_any_negative_shared_memory_requirement() -> None:
    class StubRuntimePlanner:
        def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
            requested = 8 * 1024**3 if soulstone.name == "large" else -1
            return RuntimePlan(pod_shared_memory_bytes=requested)

    stones = [
        SoulstoneFactory.build(name="large", image="example/large"),
        SoulstoneFactory.build(name="invalid", image="example/invalid"),
    ]
    with pytest.raises(ValueError, match="negative pod shared-memory"):
        Transmuter(settings=get_settings(), runtime_planner=StubRuntimePlanner()).transmute_all(stones)


def test_soulstone_cannot_receive_a_core_secret(transmuter: Transmuter) -> None:
    settings = get_settings()
    stone = SoulstoneFactory.build(
        name="leak",
        image="example/runtime",
        secret_env_files={"LEAK": settings.server.database.password_secret},
    )

    with pytest.raises(ValueError, match="distinct from core and Portal secrets"):
        transmuter.transmute_all([stone])


def test_portal_cannot_receive_a_core_secret(transmuter: Transmuter) -> None:
    settings = get_settings()
    portal = OpenAIPortalConfig(
        name="stolen-core",
        api_key_secret_name=settings.server.database.password_secret,
    )

    with pytest.raises(ValueError, match="cannot alias core application or database secrets"):
        transmuter.transmute_all([], portals=[portal])


def test_soulstone_secret_env_file_rejects_podman_target_options() -> None:
    settings = get_settings()
    with pytest.raises(ValueError, match="option-free Podman secret names"):
        GenericSoulstoneConfig.model_validate(
            {
                "name": "secret-option-injection",
                "image": "example/runtime",
                "secret_env_files": {"LEAK": f"{settings.server.database.password_secret},target=/data/stolen"},
            }
        )


@pytest.mark.parametrize("source", ["rune", "adapter"])
@pytest.mark.parametrize(
    "protected_root",
    [
        constants.PATH_CODEX_ROOT,
        constants.PATH_CRYPT_ROOT,
        constants.PATH_SYSTEMD_UNITS_DIR,
        constants.PATH_SYSTEMD_USER_UNITS_DIR,
    ],
)
@pytest.mark.parametrize("side", ["host", "container"])
def test_soulstone_mount_sources_cannot_overlap_control_roots(
    source: str,
    protected_root: Path,
    side: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rune and adapter volumes share one fail-closed boundary."""
    safe_host = tmp_path / "models"
    malicious_mount = f"{protected_root}:/models:ro" if side == "host" else f"{safe_host}:{protected_root}:ro"
    rune_volumes = [malicious_mount] if source == "rune" else []
    adapter_volumes = [malicious_mount] if source == "adapter" else []

    class StubRuntimePlanner:
        def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
            _ = soulstone
            return RuntimePlan(volumes=adapter_volumes)

    transmuter = Transmuter(settings=get_settings(), runtime_planner=StubRuntimePlanner())
    stone = SoulstoneFactory.build(name="confined", image="example/runtime", volumes=rune_volumes)

    with pytest.raises(ValueError, match="overlaps protected control root"):
        transmuter.transmute_all([stone])


def test_soulstone_mount_check_resolves_host_symlink_aliases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alias = tmp_path / "codex-alias"
    alias.symlink_to(constants.PATH_CODEX_ROOT, target_is_directory=True)
    stone = SoulstoneFactory.build(name="alias", image="example/runtime", volumes=[f"{alias}:/models:ro"])

    with pytest.raises(ValueError, match="overlaps protected control root"):
        Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry()).transmute_all([stone])


def test_safe_host_symlink_is_pinned_to_its_canonical_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "model-target"
    target.mkdir()
    alias = tmp_path / "model-alias"
    alias.symlink_to(target, target_is_directory=True)
    stone = SoulstoneFactory.build(name="safe-alias", image="example/runtime", volumes=[f"{alias}:/models:ro"])

    manifests = Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry()).transmute_all([stone])
    manifest = next(
        item for item in manifests if isinstance(item, QuadletContainer) and item.container_name == "lychd-safe-alias"
    )

    assert manifest.volumes[0].host_path == target
    assert manifest.volumes[0].container_path == Path("/models")


@pytest.mark.parametrize("control_path", ["inbox", "journal"])
@pytest.mark.parametrize("side", ["host", "container"])
def test_soulstone_mounts_respect_configured_control_paths(
    control_path: str,
    side: str,
    tmp_path: Path,
) -> None:
    switching = SwitchingSettings(host_reactor_dir=tmp_path / "control" / "reactor" / "inbox")
    settings = Settings(orchestration=OrchestrationSettings(switching=switching))
    selected = {
        "inbox": switching.host_reactor_dir,
        "journal": switching.host_reactor_journal_dir,
    }[control_path]
    safe_host = tmp_path / "models"
    mounts = [f"{selected}:/models:ro"] if side == "host" else [f"{safe_host}:{selected}:ro"]
    stone = SoulstoneFactory.build(name="configured-control", image="example/runtime", volumes=mounts)

    with pytest.raises(ValueError, match="overlaps protected control root"):
        Transmuter(settings=settings, runtime_planner=RuntimeAdapterRegistry()).transmute_all([stone])


def test_soulstone_mounts_require_absolute_endpoints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stone = SoulstoneFactory.build(
        name="relative",
        image="example/runtime",
        volumes=[f"{tmp_path / 'models'}:relative/models:ro"],
    )

    with pytest.raises(ValueError, match="container path must be absolute"):
        Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry()).transmute_all([stone])


def test_soulstone_container_mount_cannot_use_double_slash_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doubled_codex = f"/{constants.PATH_CODEX_ROOT}"
    stone = SoulstoneFactory.build(
        name="double-slash",
        image="example/runtime",
        volumes=[f"{tmp_path / 'models'}:{doubled_codex}:ro"],
    )

    with pytest.raises(ValueError, match="overlaps protected control root"):
        Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry()).transmute_all([stone])


def test_soulstone_mounts_reject_systemd_path_specifiers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stone = SoulstoneFactory.build(
        name="specifier",
        image="example/runtime",
        volumes=[f"{tmp_path / 'models'}:/%h/.config/lychd:ro"],
    )

    with pytest.raises(ValueError, match="systemd specifier"):
        Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry()).transmute_all([stone])


def test_soulstone_mounts_reject_systemd_environment_aliases() -> None:
    stone = SoulstoneFactory.build(
        name="environment-alias",
        image="example/runtime",
        volumes=["/${HOME}/.config/lychd:/models:ro"],
    )

    with pytest.raises(ValueError, match="systemd environment expansion"):
        Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry()).transmute_all([stone])


def test_soulstone_rejects_duplicate_container_mount_destinations(tmp_path: Path) -> None:
    stone = SoulstoneFactory.build(
        name="duplicate-target",
        image="example/runtime",
        volumes=[
            f"{tmp_path / 'first'}:/models:ro",
            f"{tmp_path / 'second'}:/models:rw",
        ],
    )

    with pytest.raises(ValueError, match="more than one mount for container path /models"):
        Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry()).transmute_all([stone])


def test_ordinary_model_and_runtime_mounts_are_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rune_host = tmp_path / "runtime-cache"
    adapter_host = tmp_path / "adapter-data"

    class StubRuntimePlanner:
        def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
            _ = soulstone
            return RuntimePlan(volumes=[f"{adapter_host}:/adapter-data:ro"])

    stone = SoulstoneFactory.build(
        name="ordinary",
        image="example/runtime",
        volumes=[f"{rune_host}:/runtime-cache:rw", f"{tmp_path / 'models'}:/models:ro,Z"],
    )
    manifests = Transmuter(settings=get_settings(), runtime_planner=StubRuntimePlanner()).transmute_all([stone])
    manifest = next(
        item for item in manifests if isinstance(item, QuadletContainer) and item.container_name == "lychd-ordinary"
    )

    assert [(mount.host_path, mount.container_path, mount.options) for mount in manifest.volumes] == [
        (rune_host, Path("/runtime-cache"), ["rw"]),
        (tmp_path / "models", Path("/models"), ["ro", "Z"]),
        (adapter_host, Path("/adapter-data"), ["ro"]),
    ]


def test_solitary_stones_have_no_implicit_systemd_conflicts(transmuter: Transmuter) -> None:
    """Only the orchestrator may stop managed runtimes during a transition."""
    stone_a = SoulstoneFactory.build(name="alpha", groups=[])
    stone_b = SoulstoneFactory.build(name="beta", groups=[])

    manifests = transmuter.transmute_all([stone_a, stone_b])

    alpha_manifest = next(
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-alpha"
    )
    assert alpha_manifest.conflicts == []


def test_covens_are_operator_targets_not_implicit_conflict_graphs(transmuter: Transmuter) -> None:
    """Coven targets group units without bypassing orchestrator drain ownership."""
    # Members of Coven 'logic'
    alpha = SoulstoneFactory.build(name="alpha", groups=["logic"])
    beta = SoulstoneFactory.build(name="beta", groups=["logic"])

    # Member of Coven 'creative'
    gamma = SoulstoneFactory.build(name="gamma", groups=["creative"])
    delta = SoulstoneFactory.build(name="delta", groups=["creative"])

    manifests = transmuter.transmute_all([alpha, beta, gamma, delta])

    alpha_manifest = next(
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-alpha"
    )
    assert alpha_manifest.conflicts == []

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
    assert containers["lychd-migrate"].wanted_by == []


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
