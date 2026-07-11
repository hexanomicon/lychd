from __future__ import annotations

# This unit suite intentionally exercises the module's pure port-merge helper.
# pyright: reportPrivateUsage=false
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from lychd.__main__ import cli
from lychd.cli.commands import _decide_consent, _merge_reserved_ports, bind_quadlets, doctor, init_codex

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_merge_reserved_ports_disjoint() -> None:
    core = {"LychD Server": 8000, "Phylactery (Postgres)": 5432}
    extension = {"Oculus (Phoenix UI)": 6006}
    assert _merge_reserved_ports(core, extension) == {
        "LychD Server": 8000,
        "Phylactery (Postgres)": 5432,
        "Oculus (Phoenix UI)": 6006,
    }


def test_merge_reserved_ports_core_extension_collision_names_both() -> None:
    """An extension rune claiming a core service port fails at bind, naming both."""
    core = {"LychD Server": 8000}
    extension = {"Oculus (Phoenix UI)": 8000}
    with pytest.raises(ValueError, match="8000") as exc:
        _merge_reserved_ports(core, extension)
    message = str(exc.value)
    assert "LychD Server" in message
    assert "Oculus (Phoenix UI)" in message


def test_merge_reserved_ports_repeated_label_raises() -> None:
    """An extension reusing a core service's label (different port) must not silently
    overwrite the core reservation — it fails at bind, naming both ports."""
    core = {"Oculus (Phoenix UI)": 6006}
    extension = {"Oculus (Phoenix UI)": 7007}
    with pytest.raises(ValueError, match="Oculus") as exc:
        _merge_reserved_ports(core, extension)
    message = str(exc.value)
    assert "6006" in message
    assert "7007" in message


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for invoking command-line interfaces."""
    return CliRunner()


def test_root_help_does_not_construct_asgi_app(runner: CliRunner, mocker: MockerFixture) -> None:
    """Local CLI discovery remains usable before the server can boot."""
    create_app = mocker.patch("lychd.app.create_app")

    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    for command in ("init", "bind", "doctor", "animators", "reactor", "serve", "database"):
        assert command in result.output
    create_app.assert_not_called()


def test_serve_delegates_to_litestar_lazily(runner: CliRunner, mocker: MockerFixture) -> None:
    delegated = mocker.patch("lychd.__main__._run_litestar")

    result = runner.invoke(cli, ["serve", "--host", "127.0.0.1", "--port", "7134"])

    assert result.exit_code == 0
    delegated.assert_called_once_with(
        ("run", "--host", "127.0.0.1", "--port", "7134"),
        prog_name="lychd serve",
    )


@pytest.mark.parametrize("args", [("--workers", "2"), ("--workers=3",)])
def test_serve_rejects_multiple_process_workers(
    runner: CliRunner,
    mocker: MockerFixture,
    args: tuple[str, ...],
) -> None:
    delegated = mocker.patch("lychd.__main__._run_litestar")

    result = runner.invoke(cli, ["serve", *args])

    assert result.exit_code != 0
    assert "exactly one ASGI worker" in result.output
    delegated.assert_not_called()


def test_serve_rejects_multiworker_environment(
    runner: CliRunner,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated = mocker.patch("lychd.__main__._run_litestar")
    monkeypatch.setenv("GRANIAN_WORKERS", "4")

    result = runner.invoke(cli, ["serve"])

    assert result.exit_code != 0
    assert "GRANIAN_WORKERS=1" in result.output
    delegated.assert_not_called()


def test_database_waits_before_delegating(runner: CliRunner, mocker: MockerFixture) -> None:
    wait = mocker.patch("lychd.__main__._wait_for_database")
    delegated = mocker.patch("lychd.__main__._run_litestar")

    result = runner.invoke(cli, ["database", "--wait-seconds", "12", "upgrade"])

    assert result.exit_code == 0
    wait.assert_called_once_with(12.0)
    delegated.assert_called_once_with(("database", "upgrade"), prog_name="lychd database")


def test_doctor_validates_foundation_without_mutation(
    runner: CliRunner,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    codex = tmp_path / "lychd.toml"
    codex.write_text("", encoding="utf-8")
    codex.chmod(0o600)
    inbox = tmp_path / "triggers" / "inbox"
    journal = tmp_path / "triggers" / "journal"
    units = tmp_path / "systemd"
    for directory in (inbox, journal, units):
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        directory.chmod(0o700)
    for unit_name in ("lychd-reactor.path", "lychd-reactor.service"):
        (units / unit_name).write_text("test", encoding="utf-8")

    from lychd.config.settings.root import Settings

    settings = Settings()
    settings.orchestration.switching.host_reactor_dir = inbox
    mocker.patch("lychd.config.settings.root.get_settings", return_value=settings)
    mocker.patch("lychd.system.constants.PATH_LYCHD_TOML", codex)
    mocker.patch("lychd.system.constants.PATH_SYSTEMD_USER_UNITS_DIR", units)
    mocker.patch("shutil.which", return_value="/usr/bin/systemctl")
    secret_store = mocker.patch("lychd.system.services.secrets.PodmanSecretStore").return_value
    secret_store.exists.return_value = True
    loader = mocker.patch("lychd.domain.animation.services.loader.AnimatorLoader").return_value
    loader.load_all.return_value = ([], [])
    runes = SimpleNamespace(reserved_ports=dict, all=tuple)
    mocker.patch("lychd.config.runes.registry.load_rune_registry", return_value=runes)

    result = runner.invoke(doctor)

    assert result.exit_code == 0
    assert "Foundation is coherent" in result.output
    secret_store.ensure_present.assert_not_called()


def test_init_codex_success(runner: CliRunner, mocker: MockerFixture, tmp_path: Path) -> None:
    """Verify init command orchestrates Codex properly."""
    # Patch the classes inside the command
    mocker.patch("lychd.system.services.layout.LayoutService")
    privilege = mocker.patch("lychd.system.services.privilege.PrivilegeService")
    inbox = tmp_path / "reactor" / "inbox"
    journal = tmp_path / "reactor" / "journal"
    settings = SimpleNamespace(
        orchestration=SimpleNamespace(
            switching=SimpleNamespace(
                host_reactor_dir=inbox,
                host_reactor_journal_dir=journal,
            )
        ),
        extensions=SimpleNamespace(builtins=(), crypt=()),
    )
    mocker.patch("lychd.config.settings.root.get_settings", return_value=settings)
    mock_codex_cls = mocker.patch("lychd.system.services.codex.CodexService")
    mock_codex_instance = mock_codex_cls.return_value

    result = runner.invoke(init_codex)

    assert result.exit_code == 0
    assert "Beginning the Inscription" in result.output
    assert "Initialization complete" in result.output

    # Verify interaction
    mock_codex_cls.assert_called_once()
    mock_codex_instance.inscribe.assert_called_once()
    assert [entry.args[0] for entry in privilege.call_args_list] == [inbox, journal]
    assert privilege.return_value.initialize.call_count == 2


def test_init_codex_failure(runner: CliRunner, mocker: MockerFixture) -> None:
    """Verify error handling when Codex fails."""
    mocker.patch("lychd.system.services.layout.LayoutService")
    mocker.patch("lychd.system.services.privilege.PrivilegeService")
    mock_codex_cls = mocker.patch("lychd.system.services.codex.CodexService")
    mock_codex_instance = mock_codex_cls.return_value
    # Simulate a filesystem permission error
    mock_codex_instance.inscribe.side_effect = PermissionError("Access Denied")

    result = runner.invoke(init_codex)

    assert result.exit_code != 0
    assert "Ritual Failed" in result.output
    assert "Access Denied" in result.output


@pytest.mark.asyncio
async def test_consent_cli_connects_queue_before_enqueue_and_disconnects(
    mocker: MockerFixture,
) -> None:
    from lychd.config.settings.root import Settings

    settings = Settings()
    settings.server.database.profile = "postgres"
    mocker.patch("lychd.config.settings.root.get_settings", return_value=settings)
    mocker.patch("lychd.db.engine.get_session_factory", return_value=object())
    consent_ledger = mocker.patch("lychd.domain.codex.ledger.CodexConsentLedger").return_value
    consent_ledger.get = AsyncMock(return_value=SimpleNamespace(status="pending"))
    consent_ledger.decide = AsyncMock()
    events: list[str] = []

    class _Queue:
        def __init__(self, name: str) -> None:
            self.name = name

        async def connect(self) -> None:
            events.append(f"connect:{self.name}")

        async def disconnect(self) -> None:
            events.append(f"disconnect:{self.name}")

    async def approve(_consent_id: str, *, approved: bool) -> None:
        assert approved is True
        events.append("approve")

    engine = SimpleNamespace(
        queues={"runs": _Queue("runs"), "rites": _Queue("rites")},
        approve=approve,
    )
    mocker.patch("lychd.cli.commands._build_cli_engine", return_value=engine)

    await _decide_consent("a" * 32, approved=True)

    assert events == [
        "connect:runs",
        "connect:rites",
        "approve",
        "disconnect:rites",
        "disconnect:runs",
    ]


def test_bind_quadlets_success(runner: CliRunner, mocker: MockerFixture) -> None:
    """Verify bind command orchestrates Loader, Scribe, and Systemd."""
    # 1. Mock Loader
    mock_loader_cls = mocker.patch("lychd.domain.animation.services.loader.AnimatorLoader")
    mock_loader = mock_loader_cls.return_value
    stone = SimpleNamespace(secret_env_files={})
    portal = SimpleNamespace(api_key_secret_name=None)
    mock_loader.load_all.return_value = ([stone], [portal])

    # 1.5. Mock Podman secret provisioning
    mock_secret_store_cls = mocker.patch("lychd.system.services.secrets.PodmanSecretStore")
    mock_secret_store = mock_secret_store_cls.return_value
    mock_secret_store.ensure_present.return_value = False
    mock_secret_store.exists.return_value = True

    # 2. Mock Transmuter
    mock_transmuter_cls = mocker.patch("lychd.domain.animation.transmute.Transmuter")
    mock_transmuter = mock_transmuter_cls.return_value
    mock_transmuter.transmute_all.return_value = ["rune1"]

    # 3. Mock Scribe
    mock_scribe_cls = mocker.patch("lychd.system.services.scribe.ScribeService")
    mock_scribe = mock_scribe_cls.return_value

    # 4. Mock Subprocess & Which
    mock_subprocess = mocker.patch("subprocess.run")
    mock_which = mocker.patch("shutil.which")
    mock_which.return_value = "/usr/bin/systemctl"

    result = runner.invoke(bind_quadlets)

    assert result.exit_code == 0
    assert "Transmutation" in result.output
    assert "The circle is bound" in result.output

    # Verify interactions
    mock_loader_cls.assert_called_once()
    mock_loader.load_all.assert_called_once()

    mock_transmuter_cls.assert_called_once()
    from lychd.config.runes.registry import RuneRegistry

    transmute_call = mock_transmuter.transmute_all.call_args
    assert transmute_call.args == ([stone],)
    assert transmute_call.kwargs["portals"] == [portal]
    assert isinstance(transmute_call.kwargs["runes"], RuneRegistry)

    mock_scribe_cls.assert_called_once()
    mock_scribe.reconcile_all.assert_called_once()
    reconcile = mock_scribe.reconcile_all.call_args
    assert reconcile.args == (["rune1"],)
    assert sorted(reconcile.kwargs["plain_units"]) == [
        "lychd-reactor.path",
        "lychd-reactor.service",
    ]
    mock_scribe.generate_all.assert_not_called()
    mock_scribe.write_plain_unit.assert_not_called()

    mock_subprocess.assert_called_once_with(["/usr/bin/systemctl", "--user", "daemon-reload"], check=True)


def test_bind_quadlets_systemd_failure(runner: CliRunner, mocker: MockerFixture) -> None:
    """Verify we catch subprocess errors if systemd fails."""
    mock_loader_cls = mocker.patch("lychd.domain.animation.services.loader.AnimatorLoader")
    mock_loader_cls.return_value.load_all.return_value = ([SimpleNamespace(secret_env_files={})], [])
    mock_transmuter_cls = mocker.patch("lychd.domain.animation.transmute.Transmuter")
    mock_transmuter_cls.return_value.transmute_all.return_value = ["rune1"]
    mock_secret_store_cls = mocker.patch("lychd.system.services.secrets.PodmanSecretStore")
    mock_secret_store = mock_secret_store_cls.return_value
    mock_secret_store.ensure_present.return_value = False
    mock_secret_store.exists.return_value = True
    mocker.patch("lychd.system.services.scribe.ScribeService")
    mocker.patch("shutil.which").return_value = "/usr/bin/systemctl"

    # Simulate systemd failure
    mock_subprocess = mocker.patch("subprocess.run")
    from subprocess import CalledProcessError

    mock_subprocess.side_effect = CalledProcessError(1, "systemctl")

    result = runner.invoke(bind_quadlets)

    assert result.exit_code != 0
    assert "Ritual Failed" in result.output


def test_bind_quadlets_fails_when_soulstone_secret_missing(runner: CliRunner, mocker: MockerFixture) -> None:
    """Bind must fail closed when a soulstone references a missing Podman secret."""
    stone = SimpleNamespace(secret_env_files={"HF_TOKEN_FILE": "hf_runtime_token"})
    mock_loader_cls = mocker.patch("lychd.domain.animation.services.loader.AnimatorLoader")
    mock_loader_cls.return_value.load_all.return_value = ([stone], [])

    mocker.patch("lychd.domain.animation.transmute.Transmuter")
    mocker.patch("lychd.system.services.scribe.ScribeService")
    mocker.patch("shutil.which").return_value = "/usr/bin/systemctl"
    mocker.patch("subprocess.run")

    mock_secret_store_cls = mocker.patch("lychd.system.services.secrets.PodmanSecretStore")
    mock_secret_store = mock_secret_store_cls.return_value
    mock_secret_store.ensure_present.return_value = False
    mock_secret_store.exists.return_value = False

    result = runner.invoke(bind_quadlets)

    assert result.exit_code != 0
    assert "Missing required Podman secrets" in result.output
