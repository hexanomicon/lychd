from __future__ import annotations

# pyright: reportPrivateUsage=false
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import ANY, MagicMock

import pytest
from click.testing import CliRunner

from lychd.__main__ import _effectful_init_requested, _run_litestar, cli, run_cli
from lychd.cli.commands import (
    _consume_reactor_intents,
    bind_quadlets,
    init_codex,
)
from lychd.config.runes.registry import RuneRegistry
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import RuntimePlan
from lychd.domain.animation.services.declarations import (
    AnimatorDeclarations,
    merge_reserved_ports,
)
from lychd.system.binding_sites import (
    AttestedBindingSite,
    AttestedBindingSites,
)
from lychd.system.host_tools import TrustedExecutable
from lychd.system.readiness import (
    BindingFoundation,
    HostFoundationInspection,
    HostReadinessItem,
    HostReadinessReport,
    HostReadinessTools,
    ReadinessSection,
    ReadinessState,
)
from lychd.system.services.bind_compilation import required_secret_names_from_soulstones
from lychd.system.services.binding_preflight import (
    BindingPreflightIssue,
    BindingPreflightReport,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _binding_foundation() -> BindingFoundation:
    return BindingFoundation(
        systemctl=TrustedExecutable(
            path="/usr/bin/systemctl",
            device=1,
            inode=1,
        ),
        podman=TrustedExecutable(
            path="/usr/bin/podman",
            device=1,
            inode=2,
        ),
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
    )


def _animator_declarations(
    *,
    soulstones: tuple[object, ...] = (),
    portals: tuple[object, ...] = (),
) -> AnimatorDeclarations:
    """Build one detached compiler result for CLI boundary tests."""
    return AnimatorDeclarations(
        runes=RuneRegistry(()),
        soulstones=soulstones,  # type: ignore[arg-type]
        portals=portals,  # type: ignore[arg-type]
        port_reservations=(),
    )


def test_merge_reserved_ports_disjoint() -> None:
    core = {"LychD Server": 8000, "Phylactery (Postgres)": 5432}
    extension = {"Oculus (Phoenix UI)": 6006}
    assert merge_reserved_ports(core, extension) == {
        "LychD Server": 8000,
        "Phylactery (Postgres)": 5432,
        "Oculus (Phoenix UI)": 6006,
    }


def test_merge_reserved_ports_core_extension_collision_names_both() -> None:
    """An extension rune claiming a core service port fails at bind, naming both."""
    core = {"LychD Server": 8000}
    extension = {"Oculus (Phoenix UI)": 8000}
    with pytest.raises(ValueError, match="8000") as exc:
        merge_reserved_ports(core, extension)
    message = str(exc.value)
    assert "LychD Server" in message
    assert "Oculus (Phoenix UI)" in message


def test_merge_reserved_ports_repeated_label_raises() -> None:
    """An extension reusing a core service's label (different port) must not silently
    overwrite the core reservation — it fails at bind, naming both ports."""
    core = {"Oculus (Phoenix UI)": 6006}
    extension = {"Oculus (Phoenix UI)": 7007}
    with pytest.raises(ValueError, match="Oculus") as exc:
        merge_reserved_ports(core, extension)
    message = str(exc.value)
    assert "6006" in message
    assert "7007" in message


@pytest.mark.asyncio
async def test_reactor_consumer_uses_the_configured_journal_path(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """The host consumer must not derive a sibling that configuration did not declare."""
    # Import this lazy composition module before replacing the root accessor so
    # its own stable alias cannot retain a test-local mock after teardown.
    from lychd.extensions import host as _extension_host

    _ = _extension_host

    inbox = tmp_path / "custom" / "intent-inbox"
    journal = tmp_path / "elsewhere" / "outcomes"
    switching = SimpleNamespace(
        host_reactor_dir=inbox,
        host_reactor_journal_dir=journal,
        policy="evict-idle",
    )
    settings = SimpleNamespace(
        orchestration=SimpleNamespace(switching=switching),
    )
    extensions = SimpleNamespace(
        runtime_adapters=(),
        portal_factories=(),
    )
    runes = RuneRegistry(())
    declarations = _animator_declarations()
    registry = MagicMock()
    policy = object()

    async def run_inline(function: Callable[[], object]) -> object:
        return function()

    to_thread = mocker.patch(
        "asyncio.to_thread",
        side_effect=run_inline,
    )
    mocker.patch(
        "lychd.config.settings.root.get_settings",
        return_value=settings,
    )
    mocker.patch(
        "lychd.extensions.host.get_extensions",
        return_value=extensions,
    )
    mocker.patch(
        "lychd.config.runes.registry.load_rune_registry",
        return_value=runes,
    )
    mocker.patch(
        "lychd.domain.animation.services.declarations.compile_animator_declarations",
        return_value=declarations,
    )
    registry_type = mocker.patch(
        "lychd.domain.animation.services.registry.AnimatorRegistry",
        return_value=registry,
    )
    resolve_policy = mocker.patch(
        "lychd.domain.orchestration.policies.resolve_switch_policy",
        return_value=policy,
    )
    reactor_type = mocker.patch("lychd.system.services.reactor.HostReactor")
    reactor_type.return_value.consume_all = mocker.AsyncMock(return_value=0)
    mocker.patch(
        "lychd.system.host_tools.trusted_host_tool",
        return_value="/usr/bin/systemctl",
    )

    await _consume_reactor_intents()

    registry_type.assert_called_once_with(
        settings=settings,
        declarations=declarations,
        runtime_adapters=extensions.runtime_adapters,
        portal_factories=extensions.portal_factories,
    )
    resolve_policy.assert_called_once_with(switching.policy)
    reactor_type.assert_called_once_with(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        systemctl_bin="/usr/bin/systemctl",
        policy=policy,
    )
    reactor_type.return_value.consume_all.assert_awaited_once_with()
    to_thread.assert_awaited_once_with(registry.ensure_loaded)


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for invoking command-line interfaces."""
    return CliRunner()


@pytest.fixture(autouse=True)
def binding_preflight(mocker: MockerFixture) -> MagicMock:
    """Keep legacy bind tests focused while service tests own host inspection."""
    service = mocker.patch("lychd.system.services.binding_preflight.BindingPreflightService").return_value
    service.inspect.return_value = BindingPreflightReport(
        issues=(),
        foundation=_binding_foundation(),
    )
    return service


@pytest.fixture(autouse=True)
def host_readiness(mocker: MockerFixture) -> MagicMock:
    """Keep CLI orchestration tests independent from the developer host."""
    foundation = _binding_foundation()
    service = mocker.patch("lychd.system.readiness.HostReadinessService").return_value
    service.inspect.return_value = HostFoundationInspection(
        report=HostReadinessReport(
            items=(
                HostReadinessItem(
                    key="systemd-user",
                    label="systemd user manager",
                    section=ReadinessSection.FOUNDATION,
                    state=ReadinessState.VERIFIED,
                    detail="reachable",
                    required_for_bind=True,
                ),
                HostReadinessItem(
                    key="podman-quadlet",
                    label="Podman / Quadlet",
                    section=ReadinessSection.FOUNDATION,
                    state=ReadinessState.VERIFIED,
                    detail="compatible",
                    required_for_bind=True,
                ),
                *(
                    HostReadinessItem(
                        key=key,
                        label=label,
                        section=ReadinessSection.BINDING_SITES,
                        state=ReadinessState.VERIFIED,
                        detail="prepared",
                        required_for_bind=True,
                        target=identity.path,
                        site_identity=identity,
                    )
                    for key, label, identity in (
                        (
                            "quadlet-sources",
                            "Quadlet sources",
                            foundation.sites.quadlet,
                        ),
                        (
                            "systemd-user-units",
                            "systemd user units",
                            foundation.sites.systemd_user,
                        ),
                    )
                ),
            )
        ),
        tools=HostReadinessTools(
            systemctl=foundation.systemctl,
            podman=foundation.podman,
            quadlet_user_generator=foundation.quadlet_user_generator,
            findmnt=None,
            btrfs=None,
            chattr=None,
            lsattr=None,
            getenforce=None,
        ),
    )
    return service


def test_root_help_does_not_construct_asgi_app(runner: CliRunner, mocker: MockerFixture) -> None:
    """The public Pulse stays closed and usable before the server can boot."""
    create_app = mocker.patch("lychd.app.create_app")

    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert {name for name, command in cli.commands.items() if not command.hidden} == {
        "init",
        "bind",
        "start",
        "stop",
        "status",
        "logs",
        "run",
        "del",
    }
    assert {name for name, command in cli.commands.items() if command.hidden} == {"serve", "database", "reactor"}
    for command in ("init", "bind", "start", "stop", "status", "logs", "run", "del"):
        assert command in result.output
    positions = [
        result.output.index(f"\n  {command}")
        for command in ("init", "bind", "start", "stop", "status", "logs", "run", "del")
    ]
    assert positions == sorted(positions)
    for internal in ("destroy", "doctor", "animators", "runs", "reactor", "serve", "database"):
        assert internal not in result.output
    create_app.assert_not_called()


def test_status_lookup_alias_does_not_become_a_ninth_public_root(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["st", "--help"])

    assert result.exit_code == 0
    assert "Show installation, runtime, storage, and readiness truth." in result.output


def test_run_help_survives_malformed_operator_settings(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Core operation discovery remains a bootstrap and recovery surface."""
    from lychd.config.settings.root import get_settings
    from lychd.extensions.host import reset_extensions

    monkeypatch.setenv("SERVER__LOGGING__LEVEL", "NOPE")
    get_settings.cache_clear()
    reset_extensions()
    try:
        result = runner.invoke(cli, ["run", "--help"])
    finally:
        get_settings.cache_clear()
        reset_extensions()

    assert result.exit_code == 0
    assert "agent" in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize("obsolete", ["destroy", "doctor", "animators", "runs"])
def test_obsolete_operator_roots_are_not_addressable(runner: CliRunner, obsolete: str) -> None:
    result = runner.invoke(cli, [obsolete])

    assert result.exit_code != 0
    assert "No such command" in result.output


def test_installed_entrypoint_configures_shared_logging_before_click(mocker: MockerFixture) -> None:
    """CLI processes use the same Structlog pipeline as the Litestar application."""
    apply_logging = mocker.patch("lychd.config.logging.apply_logging")
    root = mocker.patch("lychd.__main__.cli")

    run_cli()

    apply_logging.assert_called_once_with()
    root.assert_called_once_with()


@pytest.mark.parametrize(
    ("arguments", "expected_mode"),
    [
        (("init",), "effectful"),
        (("--", "init"), "effectful"),
        (("init", "--verbose"), "effectful"),
        (("init", "--dry-run"), "safe"),
        (("init", "--help"), "safe"),
        (("init", "-vh"), "safe"),
        (("init", "-hv"), "safe"),
        (("init", "-v"), "effectful"),
        (("--help",), "safe"),
        (("bind",), "safe"),
    ],
)
def test_entrypoint_recognizes_only_effectful_init(
    arguments: tuple[str, ...],
    expected_mode: str,
) -> None:
    assert _effectful_init_requested(arguments) is (expected_mode == "effectful")


def test_installed_entrypoint_rejects_effective_root_init_before_logging_or_click(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The installed path must not load Settings before the rootless authority gate."""
    monkeypatch.setattr("sys.argv", ["lychd", "init"])
    mocker.patch("lychd.__main__.os.geteuid", return_value=0)
    apply_logging = mocker.patch("lychd.config.logging.apply_logging")
    root = mocker.patch("lychd.__main__.cli")

    with pytest.raises(SystemExit) as raised:
        run_cli()

    assert raised.value.code == 1
    apply_logging.assert_not_called()
    root.assert_not_called()


def test_installed_entrypoint_keeps_effective_root_dry_run_observable(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.argv", ["lychd", "init", "--dry-run"])
    mocker.patch("lychd.__main__.os.geteuid", return_value=0)
    apply_logging = mocker.patch("lychd.config.logging.apply_logging")
    root = mocker.patch("lychd.__main__.cli")

    run_cli()

    apply_logging.assert_called_once_with()
    root.assert_called_once_with()


def test_serve_delegates_to_litestar_lazily(runner: CliRunner, mocker: MockerFixture) -> None:
    delegated = mocker.patch("lychd.__main__._run_litestar")

    result = runner.invoke(cli, ["serve", "--host", "127.0.0.1", "--port", "7134"])

    assert result.exit_code == 0
    delegated.assert_called_once_with(
        ("run", "--host", "127.0.0.1", "--port", "7134"),
        prog_name="lychd serve",
    )


def test_litestar_entrypoint_ignores_ambient_foreign_app(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LITESTAR_APP", "foreign.app:application")
    group = mocker.patch("litestar.cli.main.litestar_group")

    _run_litestar(("run", "--port", "7134"), prog_name="lychd serve")

    group.main.assert_called_once_with(
        args=[
            "--app",
            "lychd.app:create_app",
            "run",
            "--port",
            "7134",
        ],
        prog_name="lychd serve",
    )


@pytest.mark.parametrize(
    "args",
    [
        ("--workers", "2"),
        ("--workers=3",),
        ("-W", "2"),
        ("-W2",),
        ("--wc=2",),
        ("--web-concurrency", "3"),
    ],
)
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


@pytest.mark.parametrize(
    "variable",
    ["GRANIAN_WORKERS", "LITESTAR_WEB_CONCURRENCY", "WEB_CONCURRENCY"],
)
def test_serve_rejects_multiworker_environment(
    runner: CliRunner,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
) -> None:
    delegated = mocker.patch("lychd.__main__._run_litestar")
    monkeypatch.setenv(variable, "4")

    result = runner.invoke(cli, ["serve"])

    assert result.exit_code != 0
    assert f"{variable}=1" in result.output
    delegated.assert_not_called()


@pytest.mark.parametrize(
    "args",
    [
        ("-r",),
        ("--reload",),
        ("-R", "src"),
        ("-Rsrc",),
        ("--reload-dir=src",),
        ("-I*.py",),
        ("--reload-include", "*.py"),
        ("-E*.tmp",),
        ("--reload-exclude=*.tmp",),
    ],
)
def test_serve_rejects_reload_supervisor(
    runner: CliRunner,
    mocker: MockerFixture,
    args: tuple[str, ...],
) -> None:
    delegated = mocker.patch("lychd.__main__._run_litestar")

    result = runner.invoke(cli, ["serve", *args])

    assert result.exit_code != 0
    assert "does not support Litestar reload mode" in result.output
    delegated.assert_not_called()


@pytest.mark.parametrize(
    "variable",
    [
        "LITESTAR_RELOAD",
        "LITESTAR_RELOAD_DIRS",
        "LITESTAR_RELOAD_INCLUDES",
        "LITESTAR_RELOAD_EXCLUDES",
    ],
)
def test_serve_rejects_reload_environment(
    runner: CliRunner,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
) -> None:
    delegated = mocker.patch("lychd.__main__._run_litestar")
    monkeypatch.setenv(variable, "enabled")

    result = runner.invoke(cli, ["serve"])

    assert result.exit_code != 0
    assert "does not support" in result.output
    delegated.assert_not_called()


def test_database_waits_before_delegating(runner: CliRunner, mocker: MockerFixture) -> None:
    wait = mocker.patch("lychd.__main__._wait_for_database")
    delegated = mocker.patch("lychd.__main__._run_litestar")

    result = runner.invoke(cli, ["database", "--wait-seconds", "12", "upgrade"])

    assert result.exit_code == 0
    wait.assert_called_once_with(12.0)
    delegated.assert_called_once_with(("database", "upgrade"), prog_name="lychd database")


def test_init_codex_success(
    runner: CliRunner,
    mocker: MockerFixture,
    tmp_path: Path,
    host_readiness: MagicMock,
) -> None:
    """A real-root/effective-user process may perform the rootless init rite."""
    from lychd.system.services.lifecycle import (
        CreatedResources,
        LifecycleAction,
        LifecycleDisposition,
        LifecyclePlan,
        LifecycleResourceKind,
    )

    mocker.patch("lychd.cli.commands.os.getuid", return_value=0)
    mocker.patch("lychd.cli.commands.os.geteuid", return_value=1000)

    # Patch the classes inside the command
    mocker.patch("lychd.system.services.lifecycle.LifecycleLock")
    layout = mocker.patch("lychd.system.services.layout.LayoutService")
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
    receipt = mocker.patch("lychd.system.services.lifecycle.LifecycleReceiptStore").return_value
    receipt.path = tmp_path / "codex" / ".lychd-lifecycle.json"
    planner = mocker.patch("lychd.system.services.lifecycle.InitializationPlanner").return_value
    planner.plan.return_value = LifecyclePlan(
        actions=(
            LifecycleAction(
                LifecycleDisposition.PRESERVE,
                LifecycleResourceKind.RECEIPT,
                str(receipt.path),
                "valid lifecycle receipt",
            ),
        )
    )
    layout.return_value.initialize.return_value = CreatedResources()
    privilege.return_value.initialize.return_value = CreatedResources()
    mock_codex_instance.inscribe.return_value = CreatedResources()

    result = runner.invoke(init_codex)

    assert result.exit_code == 0
    assert "Beginning the Inscription" in result.output
    assert "Initialization complete" in result.output

    # Verify interaction
    mock_codex_cls.assert_called_once()
    mock_codex_instance.inscribe.assert_called_once_with(on_created=ANY)
    layout.return_value.initialize.assert_called_once_with(on_created=ANY)
    assert [entry.args[0] for entry in privilege.call_args_list] == [inbox, journal]
    assert privilege.return_value.initialize.call_count == 2
    assert all(callable(call.kwargs["on_created"]) for call in privilege.return_value.initialize.call_args_list)
    receipt.seal_dedicated_roots.assert_called_once_with()
    assert host_readiness.inspect.call_count == 2


def test_init_apply_rejects_effective_root_before_host_effects(
    runner: CliRunner,
    mocker: MockerFixture,
    host_readiness: MagicMock,
) -> None:
    """Effective UID owns effect authority even when the real UID is ordinary."""
    mocker.patch("lychd.cli.commands.os.getuid", return_value=1000)
    mocker.patch("lychd.cli.commands.os.geteuid", return_value=0)
    settings = mocker.patch("lychd.config.settings.root.get_settings")
    extensions = mocker.patch("lychd.extensions.host.get_extensions")
    planner = mocker.patch("lychd.system.services.lifecycle.InitializationPlanner")
    lock = mocker.patch("lychd.system.services.lifecycle.LifecycleLock")

    result = runner.invoke(init_codex)

    assert result.exit_code != 0
    assert "rootless" in result.output
    assert "ordinary user" in result.output
    settings.assert_not_called()
    extensions.assert_not_called()
    planner.assert_not_called()
    lock.assert_not_called()
    host_readiness.inspect.assert_not_called()


def test_init_dry_run_never_invokes_effect_services(
    runner: CliRunner,
    mocker: MockerFixture,
    tmp_path: Path,
    host_readiness: MagicMock,
) -> None:
    """Even effective root may observe the exact plan without effect authority."""
    from lychd.system.services.lifecycle import (
        LifecycleAction,
        LifecycleDisposition,
        LifecyclePlan,
        LifecycleResourceKind,
    )

    settings = SimpleNamespace(
        orchestration=SimpleNamespace(
            switching=SimpleNamespace(
                host_reactor_dir=tmp_path / "inbox",
                host_reactor_journal_dir=tmp_path / "journal",
            )
        )
    )
    mocker.patch("lychd.cli.commands.os.geteuid", return_value=0)
    mocker.patch("lychd.config.settings.root.get_settings", return_value=settings)
    mocker.patch("lychd.extensions.host.get_extensions", return_value=SimpleNamespace(rune_schemas=()))
    planner = mocker.patch("lychd.system.services.lifecycle.InitializationPlanner").return_value
    planner.plan.return_value = LifecyclePlan(
        actions=(
            LifecycleAction(
                LifecycleDisposition.WOULD_CREATE,
                LifecycleResourceKind.DIRECTORY,
                str(tmp_path / "codex"),
                "managed directory is absent",
            ),
        )
    )
    layout = mocker.patch("lychd.system.services.layout.LayoutService")
    privilege = mocker.patch("lychd.system.services.privilege.PrivilegeService")
    codex = mocker.patch("lychd.system.services.codex.CodexService")
    receipt = mocker.patch("lychd.system.services.lifecycle.LifecycleReceiptStore")

    result = runner.invoke(init_codex, ["--dry-run"])

    assert result.exit_code == 0
    assert "PLAN   1 create" in result.output
    assert "Create 1" not in result.output
    assert "└──" in result.output
    assert "managed directory is absent" not in result.output
    assert "No LychD-managed changes made" in result.output
    layout.assert_not_called()
    privilege.assert_not_called()
    codex.assert_not_called()
    receipt.return_value.record.assert_not_called()
    host_readiness.inspect.assert_called_once_with()


def test_init_dry_run_reports_bind_blockers_without_blocking_layout(
    runner: CliRunner,
    mocker: MockerFixture,
    tmp_path: Path,
    host_readiness: MagicMock,
) -> None:
    """Bind capabilities are reported but do not govern safe layout creation."""
    from lychd.system.services.lifecycle import LifecyclePlan

    host_readiness.inspect.return_value = HostFoundationInspection(
        report=HostReadinessReport(
            items=(
                HostReadinessItem(
                    key="podman-quadlet",
                    label="Podman / Quadlet",
                    section=ReadinessSection.FOUNDATION,
                    state=ReadinessState.BLOCKED,
                    detail="trusted Podman unavailable",
                    required_for_bind=True,
                ),
            )
        ),
        tools=HostReadinessTools(
            systemctl=None,
            podman=None,
            quadlet_user_generator=None,
            findmnt=None,
            btrfs=None,
            chattr=None,
            lsattr=None,
            getenforce=None,
        ),
    )
    settings = SimpleNamespace(
        orchestration=SimpleNamespace(
            switching=SimpleNamespace(
                host_reactor_dir=tmp_path / "inbox",
                host_reactor_journal_dir=tmp_path / "journal",
            )
        )
    )
    mocker.patch("lychd.config.settings.root.get_settings", return_value=settings)
    mocker.patch(
        "lychd.extensions.host.get_extensions",
        return_value=SimpleNamespace(rune_schemas=()),
    )
    mocker.patch(
        "lychd.system.services.lifecycle.InitializationPlanner",
    ).return_value.plan.return_value = LifecyclePlan()
    layout = mocker.patch("lychd.system.services.layout.LayoutService")

    result = runner.invoke(init_codex, ["--dry-run"])

    assert result.exit_code == 0
    assert "host prerequisites incomplete" in result.output
    assert "Initialization plan is safe" in result.output
    layout.assert_not_called()


def test_init_codex_failure(
    runner: CliRunner,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Verify transaction failures cross the ritual boundary visibly."""
    from lychd.system.services.lifecycle import LifecyclePlan

    mocker.patch("lychd.system.services.lifecycle.LifecycleLock")
    settings = SimpleNamespace(
        orchestration=SimpleNamespace(
            switching=SimpleNamespace(
                host_reactor_dir=tmp_path / "inbox",
                host_reactor_journal_dir=tmp_path / "journal",
            )
        ),
    )
    mocker.patch("lychd.config.settings.root.get_settings", return_value=settings)
    mocker.patch(
        "lychd.extensions.host.get_extensions",
        return_value=SimpleNamespace(rune_schemas=()),
    )
    receipt = mocker.patch("lychd.system.services.lifecycle.LifecycleReceiptStore").return_value
    receipt.path = tmp_path / "codex" / ".lychd-lifecycle.json"
    planner = mocker.patch("lychd.system.services.lifecycle.InitializationPlanner").return_value
    planner.plan.return_value = LifecyclePlan()
    executor = mocker.patch("lychd.system.services.lifecycle.InitializationExecutor").return_value
    executor.execute.side_effect = PermissionError("Access Denied")
    logger = mocker.patch("lychd.cli.base.logger")

    result = runner.invoke(init_codex)

    assert result.exit_code != 0
    assert "Ritual Failed" in result.output
    assert "Access Denied" in result.output
    logger.exception.assert_called_once_with(
        "cli_command_failed",
        command="init",
        error_type="PermissionError",
    )


def test_bind_quadlets_success(runner: CliRunner, mocker: MockerFixture) -> None:
    """Verify bind orchestrates declaration compilation, Scribe, and systemd."""
    mocker.patch("lychd.system.services.lifecycle.lock.LifecycleLock")
    registry = RuneRegistry(())
    load_registry = mocker.patch(
        "lychd.config.runes.registry.load_rune_registry",
        return_value=registry,
    )
    stone = GenericSoulstoneConfig(name="test", image="example/runtime")
    portal = SimpleNamespace(api_key_secret_name=None)
    compiler = mocker.patch(
        "lychd.cli.binding.compile_animator_declarations",
        return_value=_animator_declarations(
            soulstones=(stone,),
            portals=(portal,),
        ),
    )

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
    mock_scribe_cls = mocker.patch(
        "lychd.system.services.scribe.facade.ScribeService",
    )
    mock_scribe = mock_scribe_cls.return_value

    # 4. Mock the verified, bounded systemctl invocation.
    systemd = mocker.patch("lychd.system.services.systemd.SystemdUserManager")

    result = runner.invoke(bind_quadlets)

    assert result.exit_code == 0
    assert "Transmutation" in result.output
    assert "The circle is bound" in result.output
    assert "lychd start" in result.output
    assert "systemctl --user start" not in result.output

    # Verify interactions
    load_registry.assert_called_once()
    assert compiler.call_args.kwargs["runes"] is registry

    mock_transmuter_cls.assert_called_once()

    transmute_call = mock_transmuter.transmute_all.call_args
    assert transmute_call.args == ((stone,),)
    assert transmute_call.kwargs["portals"] == (portal,)
    assert isinstance(transmute_call.kwargs["runes"], RuneRegistry)
    assert len(transmute_call.kwargs["runtime_plans"]) == 1

    mock_secret_store_cls.assert_called_once_with("/usr/bin/podman")
    mock_scribe_cls.assert_called_once_with(
        expected_sites=_binding_foundation().sites,
    )
    mock_scribe.reconcile_all.assert_called_once()
    reconcile = mock_scribe.reconcile_all.call_args
    assert reconcile.args == (("rune1",),)
    assert sorted(reconcile.kwargs["plain_units"]) == [
        "lychd-reactor.path",
        "lychd-reactor.service",
    ]
    mock_scribe.generate_all.assert_not_called()
    mock_scribe.write_plain_unit.assert_not_called()

    systemd.assert_called_once_with(systemctl_bin="/usr/bin/systemctl")
    systemd.return_value.daemon_reload.assert_called_once_with()


def test_bind_dry_run_uses_real_planner_without_effects(
    runner: CliRunner,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Preview renders the execution transaction without secrets, locking, or writes."""
    from lychd.system.services.scribe import BindingChange, BindingReconcilePlan

    lock = mocker.patch("lychd.system.services.lifecycle.lock.LifecycleLock")
    stone = GenericSoulstoneConfig(name="test", image="example/runtime")
    mocker.patch(
        "lychd.cli.binding.compile_animator_declarations",
        return_value=_animator_declarations(soulstones=(stone,)),
    )
    mocker.patch(
        "lychd.domain.animation.services.adapters.registry.RuntimeAdapterRegistry",
    ).return_value.plan.return_value = RuntimePlan()
    transmuter = mocker.patch("lychd.domain.animation.transmute.Transmuter").return_value
    transmuter.transmute_all.return_value = ["rune1"]
    scribe = mocker.patch(
        "lychd.system.services.scribe.facade.ScribeService",
    ).return_value
    scribe.plan_reconcile_all.return_value = BindingReconcilePlan(
        changes=(
            BindingChange(
                "create",
                tmp_path / "lychd-vessel.container",
                "desired binding is absent",
            ),
        ),
        observed_generation="generation",
        desired_generation="desired",
    )
    secret_store = mocker.patch("lychd.system.services.secrets.PodmanSecretStore").return_value
    secret_store.exists.return_value = False
    systemd = mocker.patch("lychd.system.services.systemd.SystemdUserManager")

    result = runner.invoke(bind_quadlets, ["--dry-run"])

    assert result.exit_code == 0
    assert "No LychD-managed changes made." in result.output
    assert "WOULD CREATE" in result.output
    assert "Binding plan is coherent" in result.output
    scribe.plan_reconcile_all.assert_called_once()
    scribe.reconcile_all.assert_not_called()
    secret_store.ensure_present.assert_not_called()
    lock.assert_not_called()
    systemd.assert_not_called()


def test_bind_apply_rejects_generation_only_drift_before_effects(
    runner: CliRunner,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Apply treats the dry-run observation fingerprint as a lock-time precondition."""
    from lychd.system.services.scribe import BindingChange, BindingReconcilePlan

    mocker.patch("lychd.system.services.lifecycle.lock.LifecycleLock")
    mocker.patch(
        "lychd.cli.binding.compile_animator_declarations",
        return_value=_animator_declarations(),
    )
    mocker.patch(
        "lychd.domain.animation.transmute.Transmuter",
    ).return_value.transmute_all.return_value = []
    secret_store = mocker.patch("lychd.system.services.secrets.PodmanSecretStore").return_value
    secret_store.exists.return_value = True
    scribe = mocker.patch(
        "lychd.system.services.scribe.facade.ScribeService",
    ).return_value
    unchanged_disposition = (
        BindingChange(
            "update",
            tmp_path / "lychd-reactor.service",
            "owned binding differs from intent",
        ),
    )
    scribe.plan_reconcile_all.side_effect = (
        BindingReconcilePlan(
            changes=unchanged_disposition,
            observed_generation="drift-a",
            desired_generation="desired",
        ),
        BindingReconcilePlan(
            changes=unchanged_disposition,
            observed_generation="drift-b",
            desired_generation="desired",
        ),
    )
    systemd = mocker.patch("lychd.system.services.systemd.SystemdUserManager")

    result = runner.invoke(bind_quadlets)

    assert result.exit_code != 0
    assert "Binding state changed after planning" in result.output
    secret_store.ensure_present.assert_not_called()
    scribe.reconcile_all.assert_not_called()
    systemd.assert_not_called()


def test_bind_apply_rejects_secret_generation_drift_before_effects(
    runner: CliRunner,
    mocker: MockerFixture,
) -> None:
    """A required secret cannot disappear between preview and binding commit."""
    from lychd.system.services.scribe import BindingReconcilePlan

    mocker.patch("lychd.system.services.lifecycle.lock.LifecycleLock")
    mocker.patch(
        "lychd.cli.binding.compile_animator_declarations",
        return_value=_animator_declarations(),
    )
    mocker.patch(
        "lychd.domain.animation.transmute.Transmuter",
    ).return_value.transmute_all.return_value = []
    secret_store = mocker.patch("lychd.system.services.secrets.PodmanSecretStore").return_value
    secret_store.exists.side_effect = (True, True, True, False)
    scribe = mocker.patch(
        "lychd.system.services.scribe.facade.ScribeService",
    ).return_value
    scribe.plan_reconcile_all.return_value = BindingReconcilePlan(
        changes=(),
        observed_generation="stable",
        desired_generation="desired",
    )
    systemd = mocker.patch("lychd.system.services.systemd.SystemdUserManager")

    result = runner.invoke(bind_quadlets)

    assert result.exit_code != 0
    assert "Podman secret state changed after planning" in result.output
    secret_store.ensure_present.assert_not_called()
    scribe.reconcile_all.assert_not_called()
    systemd.assert_not_called()


def test_bind_dry_run_renders_structured_preflight_and_blocks_before_effects(
    runner: CliRunner,
    mocker: MockerFixture,
    binding_preflight: MagicMock,
) -> None:
    """Preview and apply share the same fail-closed host prerequisite report."""
    binding_preflight.inspect.return_value = BindingPreflightReport(
        issues=(
            BindingPreflightIssue(
                code="host-foundation",
                target="systemd user manager",
                detail="systemd user manager is not reachable",
            ),
        ),
        foundation=None,
    )
    mocker.patch(
        "lychd.cli.binding.compile_animator_declarations",
        return_value=_animator_declarations(),
    )
    scribe = mocker.patch(
        "lychd.system.services.scribe.facade.ScribeService",
    )
    secret_store = mocker.patch("lychd.system.services.secrets.PodmanSecretStore")
    lock = mocker.patch("lychd.system.services.lifecycle.lock.LifecycleLock")

    result = runner.invoke(bind_quadlets, ["--dry-run"])

    assert result.exit_code != 0
    assert "PREFLIGHT" in result.output
    assert "BLOCKED" in result.output
    assert "host-foundation" in result.output
    assert "Binding preflight failed" in result.output
    scribe.assert_not_called()
    secret_store.assert_not_called()
    lock.assert_not_called()


def test_bind_quadlets_systemd_failure(runner: CliRunner, mocker: MockerFixture) -> None:
    """Verify typed daemon-reload failures remain visible at the CLI boundary."""
    mocker.patch("lychd.system.services.lifecycle.lock.LifecycleLock")
    mocker.patch(
        "lychd.cli.binding.compile_animator_declarations",
        return_value=_animator_declarations(
            soulstones=(
                GenericSoulstoneConfig(
                    name="test",
                    image="example/runtime",
                ),
            ),
        ),
    )
    mock_transmuter_cls = mocker.patch("lychd.domain.animation.transmute.Transmuter")
    mock_transmuter_cls.return_value.transmute_all.return_value = ["rune1"]
    mock_secret_store_cls = mocker.patch("lychd.system.services.secrets.PodmanSecretStore")
    mock_secret_store = mock_secret_store_cls.return_value
    mock_secret_store.ensure_present.return_value = False
    mock_secret_store.exists.return_value = True
    scribe = mocker.patch(
        "lychd.system.services.scribe.facade.ScribeService",
    ).return_value
    scribe.reconcile_all.return_value = "bindings-after"

    from lychd.system.services.systemd import SystemdUserManagerError

    systemd = mocker.patch("lychd.system.services.systemd.SystemdUserManager")
    systemd.return_value.daemon_reload.side_effect = SystemdUserManagerError(
        "systemd user daemon-reload failed: Failed to connect to bus"
    )

    result = runner.invoke(bind_quadlets)

    assert result.exit_code != 0
    assert "Ritual Failed" in result.output
    assert "Failed to connect to bus" in result.output


def test_bind_quadlets_fails_when_soulstone_secret_missing(runner: CliRunner, mocker: MockerFixture) -> None:
    """Bind must fail closed when a soulstone references a missing Podman secret."""
    stone = GenericSoulstoneConfig(
        name="test",
        image="example/runtime",
        secret_env_files={"HF_TOKEN_FILE": "hf_runtime_token"},
    )
    mocker.patch(
        "lychd.cli.binding.compile_animator_declarations",
        return_value=_animator_declarations(soulstones=(stone,)),
    )

    mocker.patch("lychd.domain.animation.transmute.Transmuter")
    mocker.patch("lychd.system.services.scribe.facade.ScribeService")

    mock_secret_store_cls = mocker.patch("lychd.system.services.secrets.PodmanSecretStore")
    mock_secret_store = mock_secret_store_cls.return_value
    mock_secret_store.ensure_present.return_value = False
    mock_secret_store.exists.return_value = False

    result = runner.invoke(bind_quadlets)

    assert result.exit_code != 0
    assert "Missing required Podman secrets" in result.output


def test_runtime_plan_secrets_are_included_in_generic_preflight() -> None:
    stone = GenericSoulstoneConfig(name="test", image="example/runtime")
    plan = RuntimePlan(secrets=["adapter_token,target=/run/adapter-token,mode=0444"])

    assert required_secret_names_from_soulstones([stone], [plan]) == ["adapter_token"]


def test_bind_quadlets_fails_when_adapter_planned_secret_is_missing(
    runner: CliRunner,
    mocker: MockerFixture,
) -> None:
    stone = GenericSoulstoneConfig(name="test", image="example/runtime")
    mocker.patch(
        "lychd.cli.binding.compile_animator_declarations",
        return_value=_animator_declarations(soulstones=(stone,)),
    )
    planner = mocker.patch("lychd.domain.animation.services.adapters.registry.RuntimeAdapterRegistry").return_value
    planner.plan.return_value = RuntimePlan(secrets=["adapter_token,target=/run/adapter-token,mode=0444"])
    mocker.patch("lychd.domain.animation.transmute.Transmuter")
    mocker.patch("lychd.system.services.scribe.facade.ScribeService")
    secret_store = mocker.patch("lychd.system.services.secrets.PodmanSecretStore").return_value
    secret_store.ensure_present.return_value = False

    def secret_exists(name: str) -> bool:
        return name != "adapter_token"

    secret_store.exists.side_effect = secret_exists

    result = runner.invoke(bind_quadlets)

    assert result.exit_code != 0
    assert "Missing required Podman secrets: adapter_token" in result.output


def test_bind_quadlets_rejects_uncaged_control_plane_secrets(
    runner: CliRunner,
    mocker: MockerFixture,
    binding_preflight: MagicMock,
) -> None:
    """An uncaged Vessel has no Podman secret mount for authenticated runtimes."""
    stone = SimpleNamespace(
        secret_env_files={},
        control_plane_secret_names=("tabby_exl3_auth",),
    )
    mocker.patch(
        "lychd.cli.binding.compile_animator_declarations",
        return_value=_animator_declarations(soulstones=(stone,)),
    )
    mock_transmuter = mocker.patch("lychd.domain.animation.transmute.Transmuter")
    binding_preflight.inspect.return_value = BindingPreflightReport(
        issues=(
            BindingPreflightIssue(
                code="uncaged-control-secret",
                target="Soulstone control plane",
                detail="uncaged Vessel cannot receive Podman-mounted secrets: tabby_exl3_auth",
            ),
        ),
        foundation=_binding_foundation(),
    )

    result = runner.invoke(bind_quadlets, ["--uncaged"])

    assert result.exit_code != 0
    assert "uncaged Vessel cannot receive Podman-mounted" in result.output
    assert "tabby_exl3_auth" in result.output
    mock_transmuter.assert_not_called()
