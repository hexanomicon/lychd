"""Track 4-D: uncaged daemonhood — SystemdService model and CLI flag.

Real ``systemctl``/``systemd-analyze`` verification is [LINUX] (plan §8) and lives
outside this DB-free suite; here we assert the rendered text and CLI projection.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from lychd.cli.commands import bind_quadlets
from lychd.system.binding_sites import (
    AttestedBindingSite,
    AttestedBindingSites,
)
from lychd.system.host_tools import TrustedExecutable
from lychd.system.readiness import BindingFoundation
from lychd.system.schemas import SystemdService
from lychd.system.services.binding_preflight import (
    BindingPreflightReport,
)
from lychd.system.services.scribe.models import BindingReconcilePlan

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


def test_systemd_service_render_golden() -> None:
    """render() matches the golden [Unit]/[Service]/[Install] text byte-for-byte."""
    assert SystemdService(exec_start=_GOLDEN_EXEC).render() == _GOLDEN_UNIT


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
        {"name": "foreign..service"},
        {"wanted_by": ".."},
    ],
)
def test_systemd_service_rejects_directive_escape_and_unsafe_names(
    override: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match=r"backslash|environment variable|unit-name"):
        SystemdService.model_validate({"exec_start": _GOLDEN_EXEC, **override})


# ---------------------------------------------------------------------------
# D2 — CLI `lychd bind --uncaged`
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _mock_bind_pass(mocker: MockerFixture) -> SimpleNamespace:
    """Stub the normal bind pass so the uncaged branch can be exercised in isolation."""
    mock_loader_cls = mocker.patch("lychd.domain.animation.services.loader.AnimatorLoader")
    mock_loader_cls.return_value.hydrate_all.return_value = ([], [])

    mock_secret_store = mocker.patch("lychd.system.services.secrets.PodmanSecretStore").return_value
    mock_secret_store.ensure_present.return_value = False
    mock_secret_store.exists.return_value = True

    mock_transmuter = mocker.patch("lychd.domain.animation.transmute.Transmuter").return_value
    mock_transmuter.transmute_all.return_value = []

    mock_scribe = mocker.patch(
        "lychd.system.services.scribe.facade.ScribeService",
    ).return_value
    mock_scribe.plan_reconcile_all.return_value = BindingReconcilePlan(
        changes=(),
        observed_generation="before",
        desired_generation="after",
    )
    mock_scribe.reconcile_all.return_value = "after"
    preflight = mocker.patch("lychd.system.services.binding_preflight.BindingPreflightService").return_value
    preflight.inspect.return_value = BindingPreflightReport(
        issues=(),
        foundation=BindingFoundation(
            systemctl=TrustedExecutable(path="/usr/bin/systemctl", device=1, inode=1),
            podman=TrustedExecutable(path="/usr/bin/podman", device=1, inode=2),
            quadlet_user_generator=TrustedExecutable(
                path="/usr/lib/systemd/user-generators/podman-user-generator",
                device=1,
                inode=3,
            ),
            sites=AttestedBindingSites(
                quadlet=AttestedBindingSite(
                    path=Path.home() / ".config" / "containers" / "systemd",
                    device=1,
                    inode=4,
                ),
                systemd_user=AttestedBindingSite(
                    path=Path.home() / ".config" / "systemd" / "user",
                    device=1,
                    inode=5,
                ),
            ),
        ),
    )
    mocker.patch("lychd.system.services.lifecycle.lock.LifecycleLock")
    systemd = mocker.patch("lychd.system.services.systemd.SystemdUserManager")
    return SimpleNamespace(scribe=mock_scribe, systemd=systemd)


def test_bind_uncaged_writes_unit_and_reports_preparation_boundary(
    runner: CliRunner,
    mocker: MockerFixture,
) -> None:
    """--uncaged prepares its unit without promising public or manual startup."""
    mocks = _mock_bind_pass(mocker)

    result = runner.invoke(bind_quadlets, ["--uncaged"])

    assert result.exit_code == 0
    mocks.scribe.reconcile_all.assert_called_once()
    plain_units = mocks.scribe.reconcile_all.call_args.kwargs["plain_units"]
    assert "lychd-uncaged-vessel.service" in plain_units
    assert "Public start refuses mixed Vessel ownership." in result.output
    assert "Installed native startup remains unqualified." in result.output
    assert "lychd start" not in result.output
    assert "systemctl --user start" not in result.output
    assert "systemctl --user enable" not in result.output
    assert "flip the switch" not in result.output
    # Bind reloads its declared files without starting or enabling a unit.
    mocks.systemd.assert_called_once_with(systemctl_bin="/usr/bin/systemctl")
    assert mocks.systemd.return_value.method_calls == [mocker.call.daemon_reload()]
