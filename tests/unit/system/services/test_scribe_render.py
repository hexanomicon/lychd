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
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from lychd.domain.animation.schemas import ConcurrencyIntent, GenericSoulstoneConfig, SoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import RuntimePlan
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.system.services.scribe import ScribeService

if TYPE_CHECKING:
    from lychd.system.schemas import QuadletBase

_QUADLET_GENERATOR = Path("/usr/libexec/podman/quadlet")


class SoulstoneFactory(ModelFactory[GenericSoulstoneConfig]):
    """Factory for generating valid concrete Soulstone config instances."""

    __model__ = GenericSoulstoneConfig
    volumes: list[str] = []  # noqa: RUF012 - override the instance attribute


def _inscribe(manifests: list[QuadletBase], tmp_path: Path) -> tuple[Path, Path]:
    """Drive the full public inscription rite into isolated tmp dirs (git disabled)."""
    output_dir = tmp_path / "quadlet"
    systemd_dir = tmp_path / "systemd"
    output_dir.mkdir()
    systemd_dir.mkdir()
    scribe = ScribeService(output_dir=output_dir, systemd_dir=systemd_dir)
    with patch("lychd.system.services.scribe.shutil.which", return_value=None):
        scribe.generate_all(manifests)
    return output_dir, systemd_dir


def test_f2_control_plane_mounts_render_options_and_do_not_leak(tmp_path: Path) -> None:
    """Trusted mounts retain options on Vessel and never leak into a Soulstone.

    MountData sets mirror=True whenever host==container (every system mount); the
    old mirror branch dropped all options, losing `:ro,Z` -> SELinux EACCES /
    read-only law lost.
    """
    transmuter = Transmuter(runtime_planner=RuntimeAdapterRegistry())
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
    transmuter = Transmuter(runtime_planner=RuntimeAdapterRegistry())
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
    transmuter = Transmuter(runtime_planner=RuntimeAdapterRegistry())

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

    transmuter = Transmuter(runtime_planner=StubRuntimePlanner())
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
        Transmuter(runtime_planner=StubRuntimePlanner()).transmute_all([stone]),
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
    transmuter = Transmuter(runtime_planner=RuntimeAdapterRegistry())

    dedicated = SoulstoneFactory.build(
        name="loner", image="ollama/ollama", groups=[], concurrency=ConcurrencyIntent(dedicated=True)
    )
    resident = SoulstoneFactory.build(
        name="resident",
        image="ollama/ollama",
        groups=[],
        concurrency=ConcurrencyIntent(dedicated=False, persistent_resident=True),
    )

    output_dir, _ = _inscribe(transmuter.transmute_all([dedicated, resident]), tmp_path)
    dedicated_unit = (output_dir / "lychd-loner.container").read_text(encoding="utf-8")
    resident_unit = (output_dir / "lychd-resident.container").read_text(encoding="utf-8")

    assert "WantedBy=default.target" not in dedicated_unit
    assert "WantedBy=default.target" in resident_unit


def test_f1_coven_units_routed_and_referenced(tmp_path: Path) -> None:
    """F1: `.target` units go to the systemd user dir; containers reference them there."""
    transmuter = Transmuter(runtime_planner=RuntimeAdapterRegistry())

    alpha = SoulstoneFactory.build(name="alpha", image="ollama/ollama", groups=["logic"])
    beta = SoulstoneFactory.build(name="beta", image="ollama/ollama", groups=["logic"])
    gamma = SoulstoneFactory.build(name="gamma", image="ollama/ollama", groups=["creative"])
    delta = SoulstoneFactory.build(name="delta", image="ollama/ollama", groups=["creative"])

    output_dir, systemd_dir = _inscribe(transmuter.transmute_all([alpha, beta, gamma, delta]), tmp_path)

    # `.target` units land in the loadable systemd user dir, not the Quadlet dir.
    assert (systemd_dir / "lychd-coven-logic.target").exists()
    assert (systemd_dir / "lychd-coven-creative.target").exists()
    assert not (output_dir / "lychd-coven-logic.target").exists()

    # The target references the *generated pod service*, not the Quadlet source name.
    target_text = (systemd_dir / "lychd-coven-logic.target").read_text(encoding="utf-8")
    assert "PartOf=lychd-pod.service" in target_text

    # The member container's install/unit edges reference the coven target name
    # that now lives in a loadable location. Assert whole LINES (not substrings):
    # trim_blocks used to concatenate directives (e.g. `BindsTo=lychd.podPartOf=...`),
    # which merged the PartOf edge into BindsTo and defeated the coven wiring.
    alpha_lines = (output_dir / "lychd-alpha.container").read_text(encoding="utf-8").splitlines()
    assert "PartOf=lychd-coven-logic.target" in alpha_lines
    assert not any(line.startswith("Conflicts=") for line in alpha_lines)
    assert "WantedBy=lychd-coven-logic.target" in alpha_lines
    assert "BindsTo=lychd-pod.service" in alpha_lines
    # No directive line may carry a second `=` directive fused onto it.
    for line in alpha_lines:
        if "=" in line and not line.startswith("#"):
            key = line.split("=", 1)[0]
            assert key.replace("-", "").replace("_", "").isalnum(), f"fused directive line: {line!r}"
