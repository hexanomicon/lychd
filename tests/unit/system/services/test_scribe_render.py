"""Render-assertion tests for the Scribe (Wave 1 hardening F1-F4).

These assert the *rendered* systemd/Quadlet unit-file strings produced through the
real Jinja templates, which is the layer where the confirmed defects lived and the
gap that hid them. They drive Transmuter output through the public ScribeService
API (``generate_all``) so the fix is proven end to end (transmute -> template ->
file on disk), not just at the model layer.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from lychd.config.settings.root import get_settings
from lychd.domain.animation.schemas import ConcurrencyIntent, GenericSoulstoneConfig, SoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import RuntimePlan
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.system.services.scribe import ScribeService
from lychd.system.unit_names import animator_service_unit, animator_target_unit, coven_target_unit

if TYPE_CHECKING:
    from lychd.system.schemas import QuadletBase

_QUADLET_GENERATOR = Path("/usr/libexec/podman/quadlet")


class SoulstoneFactory(ModelFactory[GenericSoulstoneConfig]):
    """Factory for generating valid concrete Soulstone config instances."""

    __model__ = GenericSoulstoneConfig
    groups: list[str] = []  # noqa: RUF012 - deterministic valid declaration
    concurrency: ConcurrencyIntent = ConcurrencyIntent()
    volumes: list[str] = []  # noqa: RUF012 - override the instance attribute


def _inscribe(manifests: list[QuadletBase], tmp_path: Path) -> tuple[Path, Path]:
    """Drive the full public inscription rite into isolated tmp dirs (git disabled)."""
    output_dir = tmp_path / "quadlet"
    systemd_dir = tmp_path / "systemd"
    output_dir.mkdir()
    systemd_dir.mkdir()
    scribe = ScribeService(output_dir=output_dir, systemd_dir=systemd_dir)
    scribe.generate_all(manifests)
    return output_dir, systemd_dir


def test_f2_control_plane_mounts_render_options_and_do_not_leak(tmp_path: Path) -> None:
    """Trusted mounts retain options on Vessel and never leak into a Soulstone.

    MountData sets mirror=True whenever host==container (every system mount); the
    old mirror branch dropped all options, losing `:ro,Z` -> SELinux EACCES /
    read-only law lost.
    """
    transmuter = Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry())
    stone = SoulstoneFactory.build(name="hermes", image="ollama/ollama", groups=[])

    output_dir, _ = _inscribe(transmuter.transmute_all([stone]), tmp_path)
    content = (output_dir / "lychd-vessel.container").read_text(encoding="utf-8")
    soulstone = (output_dir / "lychd-hermes.container").read_text(encoding="utf-8")

    volume_lines = [line for line in content.splitlines() if line.startswith("Volume=")]
    # Read-only Codex and bounded writable control-plane mounts carry options.
    assert any(line.endswith(":ro,Z") for line in volume_lines), volume_lines
    assert any(line.endswith(":rw,Z") for line in volume_lines), volume_lines
    # No system mount may render bare (host:container with no options).
    ro_codex = [line for line in volume_lines if "config/lychd" in line]
    assert ro_codex, volume_lines
    assert all(line.endswith(":ro,Z") for line in ro_codex), volume_lines
    assert "config/lychd" not in soulstone
    assert "share/lychd/triggers" not in soulstone


def test_container_user_is_scoped_to_vessel_and_soulstones(tmp_path: Path) -> None:
    """Host identity is explicit for agent containers, never forced on Postgres."""
    transmuter = Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry())
    stone = SoulstoneFactory.build(name="hermes", image="ollama/ollama", groups=[])

    output_dir, _ = _inscribe(transmuter.transmute_all([stone]), tmp_path)
    vessel = (output_dir / "lychd-vessel.container").read_text(encoding="utf-8").splitlines()
    phylactery = (output_dir / "lychd-phylactery.container").read_text(encoding="utf-8").splitlines()
    soulstone = (output_dir / "lychd-hermes.container").read_text(encoding="utf-8").splitlines()
    pod = (output_dir / "lychd.pod").read_text(encoding="utf-8").splitlines()

    assert "User=%U" in vessel
    assert "User=%U" in soulstone
    assert not any(line.startswith("User=") for line in phylactery)
    assert "UserNS=keep-id" in pod
    assert not any(line.startswith("UserNS=") for line in vessel)
    assert not any(line.startswith("UserNS=") for line in soulstone)


def test_migration_gate_renders_as_required_oneshot(tmp_path: Path) -> None:
    """Vessel starts only after the in-pod, secret-bearing Alembic gate succeeds."""
    transmuter = Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry())

    output_dir, _ = _inscribe(transmuter.transmute_all([]), tmp_path)
    vessel = (output_dir / "lychd-vessel.container").read_text(encoding="utf-8").splitlines()
    migrate = (output_dir / "lychd-migrate.container").read_text(encoding="utf-8").splitlines()

    assert "Requires=lychd-migrate.service lychd-reactor.path" in vessel
    assert "After=lychd-migrate.service lychd-reactor.path" in vessel
    assert "Type=oneshot" in migrate
    assert "Requires=lychd-phylactery.service" in migrate
    assert "Exec=lychd database --wait-seconds 60 upgrade head --no-prompt" in migrate
    assert "WantedBy=default.target" not in migrate


def test_f3_exec_and_env_are_systemd_quoted_not_html_escaped(tmp_path: Path) -> None:
    """F3: preserve shell Exec quoting and safely quote systemd environment values."""

    class StubRuntimePlanner:
        def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
            _ = soulstone
            # An arg with a space forces shlex to quote with `'`; a URL with `&`
            # is the classic autoescape victim (`&` -> `&amp;`, `'` -> `&#39;`).
            return RuntimePlan(
                exec_args=["serve", "--chat-template", "role: user"],
                env_overrides={"UPSTREAM_URL": 'http://x/y?a=1&b=2 label="two words" token=${HOST_TOKEN}'},
            )

    transmuter = Transmuter(settings=get_settings(), runtime_planner=StubRuntimePlanner())
    stone = SoulstoneFactory.build(name="qwen", image="vllm/vllm-openai:latest", groups=[])

    output_dir, _ = _inscribe(transmuter.transmute_all([stone]), tmp_path)
    content = (output_dir / "lychd-qwen.container").read_text(encoding="utf-8")

    assert "&#39;" not in content
    assert "&amp;" not in content
    exec_line = next(line for line in content.splitlines() if line.startswith("Exec="))
    assert "'role: user'" in exec_line
    env_line = next(line for line in content.splitlines() if line.startswith('Environment="UPSTREAM_URL='))
    assert env_line == ('Environment="UPSTREAM_URL=http://x/y?a=1&b=2 label=\\"two words\\" token=$${HOST_TOKEN}"')


@pytest.mark.skipif(not _QUADLET_GENERATOR.is_file(), reason="Podman Quadlet generator is unavailable")
def test_real_quadlet_generator_preserves_literal_environment_and_command_boundary(tmp_path: Path) -> None:
    """Exercise the real generator after LychD's source-level boundary validation."""

    class StubRuntimePlanner:
        def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
            _ = soulstone
            return RuntimePlan(
                exec_args=["serve", "value;still-one-argument"],
                env_overrides={"LITERAL": "${HOST_TOKEN}"},
            )

    stone = SoulstoneFactory.build(name="generator", image="example/runtime")
    output_dir, _ = _inscribe(
        Transmuter(settings=get_settings(), runtime_planner=StubRuntimePlanner()).transmute_all([stone]),
        tmp_path,
    )
    environment = os.environ.copy()
    environment.update(
        {
            "HOST_TOKEN": "host-secret-must-not-expand",
            "QUADLET_UNIT_DIRS": str(output_dir),
        }
    )

    result = subprocess.run(  # noqa: S603 - pinned local system generator, no shell
        [str(_QUADLET_GENERATOR), "-dryrun", "-user"],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )
    generated = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 0, generated
    assert "host-secret-must-not-expand" not in generated
    assert "$${HOST_TOKEN}" in generated
    assert re.search(r"(?:^|\\s);(?:$|\\s)", generated) is None


def test_f4_wanted_by_reflects_concurrency(tmp_path: Path) -> None:
    """F4: dedicated stones must NOT be WantedBy=default.target; persistent residents must be."""
    transmuter = Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry())

    dedicated = SoulstoneFactory.build(
        name="loner", image="ollama/ollama", groups=[], concurrency=ConcurrencyIntent(dedicated=True)
    )
    resident = SoulstoneFactory.build(
        name="resident",
        image="ollama/ollama",
        groups=[],
        concurrency=ConcurrencyIntent(dedicated=False, persistent_resident=True),
    )

    output_dir, systemd_dir = _inscribe(transmuter.transmute_all([dedicated, resident]), tmp_path)
    dedicated_unit = (output_dir / "lychd-loner.container").read_text(encoding="utf-8")
    resident_unit = (output_dir / "lychd-resident.container").read_text(encoding="utf-8")
    resident_target = (systemd_dir / animator_target_unit("resident")).read_text(encoding="utf-8")

    assert "WantedBy=default.target" not in dedicated_unit
    assert "WantedBy=default.target" in resident_unit
    assert f"BindsTo={animator_target_unit('resident')}" in resident_unit
    assert "[Install]" not in resident_target


def test_f1_coven_units_routed_and_referenced(tmp_path: Path) -> None:
    """F1: Coven aggregates compose explicit compatible Animator gates."""
    transmuter = Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry())

    compatible = ConcurrencyIntent(conflict_domains=[])
    alpha = SoulstoneFactory.build(
        name="alpha",
        image="ollama/ollama",
        groups=["logic"],
        concurrency=compatible,
    )
    beta = SoulstoneFactory.build(
        name="beta",
        image="ollama/ollama",
        groups=["logic"],
        concurrency=compatible,
    )
    gamma = SoulstoneFactory.build(
        name="gamma",
        image="ollama/ollama",
        groups=["creative"],
        concurrency=compatible,
    )
    delta = SoulstoneFactory.build(
        name="delta",
        image="ollama/ollama",
        groups=["creative"],
        concurrency=compatible,
    )

    output_dir, systemd_dir = _inscribe(transmuter.transmute_all([alpha, beta, gamma, delta]), tmp_path)

    # `.target` units land in the loadable systemd user dir, not the Quadlet dir.
    assert (systemd_dir / "lychd-coven-logic.target").exists()
    assert (systemd_dir / "lychd-coven-creative.target").exists()
    assert not (output_dir / "lychd-coven-logic.target").exists()
    for name in ("alpha", "beta", "gamma", "delta"):
        assert (systemd_dir / animator_target_unit(name)).exists()

    # Covens aggregate lifecycle targets and never enable themselves globally.
    target_text = (systemd_dir / "lychd-coven-logic.target").read_text(encoding="utf-8")
    assert "PartOf=lychd-pod.service" in target_text
    assert f"Wants={animator_target_unit('alpha')} {animator_target_unit('beta')}" in target_text
    assert f"After={animator_target_unit('alpha')} {animator_target_unit('beta')}" in target_text
    assert "[Install]" not in target_text

    # Services bind their own gate; membership belongs to the gate, not the
    # restartable service.
    alpha_lines = (output_dir / "lychd-alpha.container").read_text(encoding="utf-8").splitlines()
    alpha_target_lines = (systemd_dir / animator_target_unit("alpha")).read_text(encoding="utf-8").splitlines()
    assert f"BindsTo={animator_target_unit('alpha')}" in alpha_lines
    assert f"After=lychd-pod.service {animator_target_unit('alpha')}" in alpha_lines
    assert f"PartOf=lychd-pod.service {coven_target_unit('logic')}" in alpha_target_lines
    assert f"Requires={animator_service_unit('alpha')}" in alpha_target_lines
    assert f"Before={animator_service_unit('alpha')}" in alpha_target_lines
    assert not any(line.startswith("Conflicts=") for line in alpha_lines)
    assert not any(line.startswith("WantedBy=") for line in alpha_lines)
    assert "BindsTo=lychd-pod.service" in alpha_lines
    # No directive line may carry a second `=` directive fused onto it.
    for line in alpha_lines:
        if "=" in line and not line.startswith("#"):
            key = line.split("=", 1)[0]
            assert key.replace("-", "").replace("_", "").isalnum(), f"fused directive line: {line!r}"


def test_conflict_domain_renders_one_reciprocal_ordered_edge(tmp_path: Path) -> None:
    """Each physical conflict pair renders once, on the lexical higher endpoint."""
    transmuter = Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry())
    gpu = ConcurrencyIntent(conflict_domains=["gpu"])
    alpha = SoulstoneFactory.build(name="alpha", image="example/runtime", concurrency=gpu)
    gamma = SoulstoneFactory.build(name="gamma", image="example/runtime", concurrency=gpu)

    output_dir, systemd_dir = _inscribe(transmuter.transmute_all([gamma, alpha]), tmp_path)
    alpha_target = (systemd_dir / animator_target_unit("alpha")).read_text(encoding="utf-8").splitlines()
    gamma_target = (systemd_dir / animator_target_unit("gamma")).read_text(encoding="utf-8").splitlines()
    gamma_container = (output_dir / "lychd-gamma.container").read_text(encoding="utf-8").splitlines()

    assert not any(line.startswith(("After=lychd-animator-", "Conflicts=")) for line in alpha_target)
    assert f"After={animator_target_unit('alpha')}" in gamma_target
    assert f"Conflicts={animator_target_unit('alpha')}" in gamma_target
    assert f"BindsTo={animator_target_unit('gamma')}" in gamma_container
    assert f"After=lychd-pod.service {animator_target_unit('gamma')}" in gamma_container


@pytest.mark.skipif(shutil.which("systemd-analyze") is None, reason="systemd-analyze is unavailable")
def test_systemd_analyze_accepts_compiled_conflict_graph(tmp_path: Path) -> None:
    """Ask systemd itself to reject requirement or ordering cycles."""
    transmuter = Transmuter(settings=get_settings(), runtime_planner=RuntimeAdapterRegistry())
    gpu = ConcurrencyIntent(conflict_domains=["gpu"])
    alpha = SoulstoneFactory.build(name="alpha", image="example/runtime", concurrency=gpu)
    gamma = SoulstoneFactory.build(name="gamma", image="example/runtime", concurrency=gpu)
    _, systemd_dir = _inscribe(transmuter.transmute_all([gamma, alpha]), tmp_path)

    (systemd_dir / "lychd-pod.service").write_text(
        "[Unit]\nDescription=LychD pod test double\n[Service]\nType=oneshot\nExecStart=/bin/true\n",
        encoding="utf-8",
    )
    for name in ("alpha", "gamma"):
        (systemd_dir / animator_service_unit(name)).write_text(
            (
                "[Unit]\n"
                f"Description=LychD {name} test double\n"
                f"BindsTo={animator_target_unit(name)}\n"
                f"After={animator_target_unit(name)}\n"
                "[Service]\n"
                "Type=oneshot\n"
                "ExecStart=/bin/true\n"
            ),
            encoding="utf-8",
        )

    analyzer = shutil.which("systemd-analyze")
    assert analyzer is not None
    unit_paths = sorted(str(path) for path in systemd_dir.iterdir())
    result = subprocess.run(  # noqa: S603 - resolved host systemd analyzer, no shell
        [analyzer, "--user", "verify", *unit_paths],
        check=False,
        capture_output=True,
        text=True,
    )
    diagnostics = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 0, diagnostics
