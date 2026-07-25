"""Track 4-D: uncaged daemonhood — SystemdService model, transmute, write_user_unit, CLI flag.

Real ``systemctl``/``systemd-analyze`` verification is [LINUX] (plan §8) and lives
outside this DB-free suite; here we assert the rendered text, the atomic write,
and the CLI flag path (write + enable-hint, NEVER auto-enable).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from lychd.cli.commands import bind_quadlets
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.animation.transmute import transmute_uncaged_vessel
from lychd.system.schemas import SystemdService
from lychd.system.services.scribe import ScribeService

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Golden unit text (D1). exec_start is injected so the golden is stable across venvs.
_GOLDEN_EXEC = "/venv/bin/lychd serve --host 127.0.0.1 --port 7134"
_GOLDEN_UNIT = (
    "[Unit]\n"
    "Description=LychD Vessel (uncaged)\n"
    "\n"
    "[Service]\n"
    f"ExecStart={_GOLDEN_EXEC}\n"
    'Environment="LYCHD_MODE=uncaged"\n'
    "Restart=on-failure\n"
    "\n"
    "[Install]\n"
    "WantedBy=default.target\n"
)


# ---------------------------------------------------------------------------
# D1 — SystemdService model
# ---------------------------------------------------------------------------


def test_systemd_service_filename() -> None:
    """The unit filename is ``<name>.service`` (default lychd-vessel)."""
    assert SystemdService(exec_start=_GOLDEN_EXEC).filename == "lychd-vessel.service"


def test_systemd_service_render_golden() -> None:
    """render() matches the golden [Unit]/[Service]/[Install] text byte-for-byte."""
    assert SystemdService(exec_start=_GOLDEN_EXEC).render() == _GOLDEN_UNIT


def test_systemd_service_env_render() -> None:
    """The default environment renders the LYCHD_MODE=uncaged Environment= line."""
    rendered = SystemdService(exec_start=_GOLDEN_EXEC).render()
    assert 'Environment="LYCHD_MODE=uncaged"' in rendered


def test_systemd_service_env_deterministic_order() -> None:
    """Multiple env keys render in a stable (sorted) order regardless of insertion order."""
    service = SystemdService(exec_start=_GOLDEN_EXEC, environment={"ZED": "2", "ALPHA": "1"})
    rendered = service.render()
    assert rendered.index('Environment="ALPHA=1"') < rendered.index('Environment="ZED=2"')


def test_systemd_service_quotes_environment_as_one_assignment() -> None:
    service = SystemdService(
        exec_start=_GOLDEN_EXEC,
        environment={"LABEL": 'two words and "quoted" ${LITERAL}'},
    )

    assert 'Environment="LABEL=two words and \\"quoted\\" ${LITERAL}"' in service.render()


@pytest.mark.parametrize(
    "override",
    [
        {"description": "swallow-next-directive\\"},
        {"exec_start": r"/bin/echo\x0aExecStart=/bin/sh"},
        {"environment": {"SAFE": r"value\x22 MALICE=1"}},
        {"environment": {"NOT SAFE": "value"}},
        {"name": "../foreign"},
    ],
)
def test_systemd_service_rejects_directive_escape_and_unsafe_names(
    override: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="backslash|environment variable|unit-name"):
        SystemdService.model_validate({"exec_start": _GOLDEN_EXEC, **override})


# ---------------------------------------------------------------------------
# D2 — transmute_uncaged_vessel (pure domain, writes nothing)
# ---------------------------------------------------------------------------


def test_transmute_uncaged_vessel_builds_from_settings() -> None:
    """The exec line boots the venv lychd entrypoint on loopback at the settings port."""
    fake_settings = SimpleNamespace(server=SimpleNamespace(port=9999))
    service = transmute_uncaged_vessel(fake_settings)  # type: ignore[arg-type]

    assert isinstance(service, SystemdService)
    expected_bin = str(Path(sys.prefix) / "bin" / "lychd")
    assert service.exec_start == f"{expected_bin} serve --host 127.0.0.1 --port 9999"
    assert service.environment == {"LYCHD_MODE": "uncaged"}
    assert service.filename == "lychd-uncaged-vessel.service"


# ---------------------------------------------------------------------------
# D2 — ScribeService.write_user_unit (atomic, idempotent, isolated)
# ---------------------------------------------------------------------------


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    d = tmp_path / "templates"
    d.mkdir()
    (d / "container.jinja").write_text("ContainerName={{ container_name }}", encoding="utf-8")
    (d / "pod.jinja").write_text("PodName={{ pod_name }}", encoding="utf-8")
    (d / "target.jinja").write_text("Description={{ description }}", encoding="utf-8")
    return d


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir()
    return d


@pytest.fixture
def systemd_dir(tmp_path: Path) -> Path:
    d = tmp_path / "systemd"
    d.mkdir()
    return d


@pytest.fixture
def scribe(templates_dir: Path, output_dir: Path, systemd_dir: Path) -> ScribeService:
    return ScribeService(templates_dir=templates_dir, output_dir=output_dir, systemd_dir=systemd_dir)


def test_write_user_unit_writes_atomically(scribe: ScribeService, systemd_dir: Path) -> None:
    """The unit lands in the systemd user dir with the rendered content; no temp files linger."""
    service = SystemdService(exec_start=_GOLDEN_EXEC)
    path = scribe.write_user_unit(service)

    assert path == systemd_dir / "lychd-vessel.service"
    assert path.read_text(encoding="utf-8") == service.render()
    # No staging temp file left behind.
    assert [p.name for p in systemd_dir.iterdir()] == ["lychd-vessel.service"]


def test_write_user_unit_is_byte_stable(scribe: ScribeService, systemd_dir: Path) -> None:
    """Re-writing the same service is idempotent (byte-stable)."""
    service = SystemdService(exec_start=_GOLDEN_EXEC)
    first = scribe.write_user_unit(service).read_text(encoding="utf-8")
    second = scribe.write_user_unit(service).read_text(encoding="utf-8")
    assert first == second == _GOLDEN_UNIT


def test_write_user_unit_does_not_disturb_other_state(
    scribe: ScribeService, systemd_dir: Path, output_dir: Path
) -> None:
    """Plain-unit writes never touch .container/.target/sentinel state (separate path)."""
    stale_container = output_dir / "lychd-vessel.container"
    stale_container.write_text("[Container]\n", encoding="utf-8")
    coexisting_target = systemd_dir / "lychd-coven-logic.target"
    coexisting_target.write_text("[Unit]\n", encoding="utf-8")

    scribe.write_user_unit(SystemdService(exec_start=_GOLDEN_EXEC))

    # Quadlet dir untouched; unrelated systemd units preserved.
    assert stale_container.read_text(encoding="utf-8") == "[Container]\n"
    assert coexisting_target.read_text(encoding="utf-8") == "[Unit]\n"


# ---------------------------------------------------------------------------
# D3 — CLI `lychd bind --uncaged`
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _mock_bind_pass(mocker: MockerFixture, *, systemctl: str | None) -> SimpleNamespace:
    """Stub the normal bind pass so the uncaged branch can be exercised in isolation."""
    stone = GenericSoulstoneConfig(name="test", image="example/runtime")
    portal = SimpleNamespace(api_key_secret_name=None)
    mock_loader_cls = mocker.patch("lychd.domain.animation.services.loader.AnimatorLoader")
    mock_loader_cls.return_value.load_all.return_value = ([stone], [portal])

    mock_secret_store = mocker.patch("lychd.system.services.secrets.PodmanSecretStore").return_value
    mock_secret_store.ensure_present.return_value = False
    mock_secret_store.exists.return_value = True

    mock_transmuter = mocker.patch("lychd.domain.animation.transmute.Transmuter").return_value
    mock_transmuter.transmute_all.return_value = ["rune1"]

    mock_scribe = mocker.patch("lychd.system.services.scribe.ScribeService").return_value
    mocker.patch("lychd.system.services.lifecycle.LifecycleLock")
    mock_subprocess = mocker.patch("subprocess.run")
    mocker.patch("shutil.which").return_value = systemctl
    return SimpleNamespace(scribe=mock_scribe, subprocess=mock_subprocess)


def test_bind_uncaged_writes_unit_and_prints_enable_hint(runner: CliRunner, mocker: MockerFixture) -> None:
    """--uncaged writes the unit + hints enable, but NEVER auto-enables."""
    mocks = _mock_bind_pass(mocker, systemctl="/usr/bin/systemctl")

    result = runner.invoke(bind_quadlets, ["--uncaged"])

    assert result.exit_code == 0
    mocks.scribe.reconcile_all.assert_called_once()
    plain_units = mocks.scribe.reconcile_all.call_args.kwargs["plain_units"]
    assert "lychd-uncaged-vessel.service" in plain_units
    assert "systemctl --user enable --now lychd-uncaged-vessel.service" in result.output
    assert "flip the switch" in result.output
    # daemon-reload runs; enable/start is NEVER auto-invoked.
    reload_calls = [c for c in mocks.subprocess.call_args_list if c.args and "daemon-reload" in c.args[0]]
    enable_calls = [c for c in mocks.subprocess.call_args_list if c.args and "enable" in c.args[0]]
    assert reload_calls, "expected a systemd daemon-reload"
    assert not enable_calls, "the Magus flips the switch — bind must not auto-enable"


def test_bind_uncaged_no_systemd_degrades_to_file_and_warning(runner: CliRunner, mocker: MockerFixture) -> None:
    """Without systemd the unit is still written; daemon-reload is skipped with a warning."""
    mocks = _mock_bind_pass(mocker, systemctl=None)

    result = runner.invoke(bind_quadlets, ["--uncaged"])

    assert result.exit_code == 0
    mocks.scribe.reconcile_all.assert_called_once()
    assert "lychd-uncaged-vessel.service" in mocks.scribe.reconcile_all.call_args.kwargs["plain_units"]
    assert "Manual daemon-reload required" in result.output
    assert mocks.subprocess.call_args_list == []  # nothing invoked without systemctl


def test_bind_without_uncaged_writes_no_user_unit(runner: CliRunner, mocker: MockerFixture) -> None:
    """The default bind (no flag) never touches the uncaged path."""
    mocks = _mock_bind_pass(mocker, systemctl="/usr/bin/systemctl")

    result = runner.invoke(bind_quadlets)

    assert result.exit_code == 0
    mocks.scribe.reconcile_all.assert_called_once()
    assert "lychd-uncaged-vessel.service" not in mocks.scribe.reconcile_all.call_args.kwargs["plain_units"]
    assert "uncaged" not in result.output.lower()


# ---------------------------------------------------------------------------
# [LINUX] — real systemd validation (plan §8): written, marked, deferred.
# Skips off-Linux / without systemd-analyze (e.g. the Mac dev box).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    sys.platform != "linux" or shutil.which("systemd-analyze") is None,
    reason="[LINUX] real systemd-analyze verification (plan §8)",
)
def test_uncaged_unit_passes_systemd_analyze(tmp_path: Path) -> None:
    """The rendered unit is a valid systemd --user unit (systemd-analyze verify exits 0)."""
    unit = tmp_path / "lychd-vessel.service"
    unit.write_text(
        SystemdService(exec_start=f"{Path(sys.prefix) / 'bin' / 'lychd'} run --host 127.0.0.1 --port 7134").render(),
        encoding="utf-8",
    )
    result = subprocess.run(  # noqa: S603
        [shutil.which("systemd-analyze") or "systemd-analyze", "--user", "verify", str(unit)],
        capture_output=True,
        check=False,
    )
    stderr = result.stderr.decode()
    if result.returncode != 0 and "Operation not permitted" in stderr and "SO_PASS" in stderr:
        pytest.skip("systemd-analyze user-manager socket operations are blocked by the sandbox")
    assert result.returncode == 0, stderr
