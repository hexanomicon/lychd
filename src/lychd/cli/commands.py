"""CLI entrypoints for initialization, binding, and the internal Host Reactor."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

import click

from lychd.cli.base import get_console, ritual_command

if TYPE_CHECKING:
    from rich.console import Console

    from lychd.config.settings.root import Settings
    from lychd.domain.animation.schemas import SoulstoneConfig
    from lychd.domain.animation.services.adapters.contracts import RuntimePlan
    from lychd.system.services.binding_preflight import BindingPreflightReport
    from lychd.system.services.secrets import PodmanSecretStore


def _raise_missing_portal_secrets_error(secret_names: list[str]) -> None:
    missing = ", ".join(secret_names)
    msg = f"Missing required Podman secrets: {missing}. Create them with `podman secret create <name> -` before bind."
    raise RuntimeError(msg)


def _merge_reserved_ports(core: Mapping[str, int], extension: Mapping[str, int]) -> dict[str, int]:
    """Merge core-service and extension-rune port claims across the boundary.

    Extends the settings-level ``check_port_conflicts`` across the core/extension
    boundary: a port — or a LABEL — claimed by BOTH a core service and an extension
    rune fails loudly at bind, naming both claimants (before any unit file is
    written). A repeated label must raise too: silently overwriting ``merged[label]``
    would drop an earlier reservation and evade the §8.1 fail-at-bind guarantee.

    Raises:
        ValueError: If a core service and an extension rune claim the same port,
            or reuse the same label.

    """
    by_port = {port: label for label, port in core.items()}
    merged: dict[str, int] = dict(core)
    for label, port in extension.items():
        if label in merged:
            msg = (
                f"Port label '{label}' is claimed by both a core service (port {merged[label]}) "
                f"and an extension rune (port {port})."
            )
            raise ValueError(msg)
        if port in by_port and by_port[port] != label:
            msg = f"Port {port} is claimed by both '{by_port[port]}' (core) and '{label}' (extension)."
            raise ValueError(msg)
        by_port[port] = label
        merged[label] = port
    return merged


def _required_secret_names_from_soulstones(
    soulstones: Sequence[SoulstoneConfig],
    runtime_plans: Sequence[RuntimePlan] = (),
) -> list[str]:
    """Collect every Rune-, control-, and adapter-planned Soulstone secret."""
    from lychd.system.schemas import podman_secret_source

    if runtime_plans and len(runtime_plans) != len(soulstones):
        msg = "Runtime plan count must match the Soulstone count"
        raise ValueError(msg)
    names: set[str] = set()
    for stone in soulstones:
        for secret_name in stone.secret_env_files.values():
            if secret_name:
                names.add(secret_name)
        names.update(stone.control_plane_secret_names)
    for plan in runtime_plans:
        names.update(podman_secret_source(spec) for spec in plan.secrets)
    return sorted(names)


def _uncaged_control_plane_secrets(soulstones: Sequence[SoulstoneConfig]) -> list[str]:
    """Return secrets that only the caged Vessel can receive from Podman."""
    return sorted({name for stone in soulstones for name in stone.control_plane_secret_names})


def _observe_secret_presence(
    secret_store: PodmanSecretStore,
    names: Sequence[str],
) -> tuple[tuple[str, bool], ...]:
    """Capture one deterministic bind-time secret generation."""
    return tuple((name, secret_store.exists(name)) for name in sorted(set(names)))


@ritual_command(
    name="init",
    help_text="Initialize the Codex config files and system layout.",
    start_message="[bold blue]🕯️  Beginning the Inscription (lychd init)...[/]",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show the exact initialization plan without changing files, modes, mounts, or services.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show every inspected host anchor with its source-owned description.",
)
def init_codex(
    dry_run: bool,  # noqa: FBT001 - Click owns these boolean option contracts
    verbose: bool,  # noqa: FBT001
) -> None:
    """Plan, attest, and converge the complete host inscription.

    Host-foundation probes remain read-only and outside lifecycle equality.
    Apply journals every created resource, revalidates the exact plan, seals
    dedicated-root authority, then reinspects Binding and storage readiness.
    """
    import os
    from contextlib import nullcontext

    from lychd.cli.lifecycle_view import render_lifecycle_plan
    from lychd.cli.readiness_view import (
        render_host_readiness,
        render_readiness_changes,
    )
    from lychd.config.runes import ConfigWriter
    from lychd.config.settings.root import get_settings
    from lychd.extensions.host import get_extensions
    from lychd.system.constants import PATH_CODEX_ROOT, PATH_RUNES_DIR
    from lychd.system.readiness import HostReadinessService
    from lychd.system.services.codex import CodexService
    from lychd.system.services.layout import LayoutService
    from lychd.system.services.lifecycle import (
        CreatedResources,
        InitializationExecutor,
        InitializationPlanner,
        InitializationRecorder,
        LifecycleLock,
        LifecycleReceiptStore,
    )
    from lychd.system.services.privilege import PrivilegeService

    console = get_console()
    lock = nullcontext() if dry_run else LifecycleLock()
    with lock:
        settings = get_settings()
        extensions = get_extensions()
        schemas = list(extensions.rune_schemas)
        writer = ConfigWriter(runes_dir=PATH_RUNES_DIR)
        receipt = LifecycleReceiptStore()
        planner = InitializationPlanner(
            reactor_directories=(
                settings.orchestration.switching.host_reactor_dir,
                settings.orchestration.switching.host_reactor_journal_dir,
            ),
            anchor_paths=tuple(schema.anchor_dir(PATH_RUNES_DIR) for schema in schemas),
            sample_paths=writer.planned_sample_paths(schemas),
            receipt_store=receipt,
        )
        readiness_service = HostReadinessService()
        readiness = readiness_service.inspect()
        render_host_readiness(report=readiness, console=console)
        plan = planner.plan()
        render_lifecycle_plan(
            plan=plan,
            console=console,
            path_descriptions=writer.planned_path_descriptions(schemas),
            verbose=verbose,
        )
        plan.require_executable()
        if dry_run:
            console.print("\n[bold green]✓ Initialization plan is safe.[/] [dim]No changes made.[/]")
            return
        if os.geteuid() == 0:
            msg = "LychD initialization is rootless; rerun `lychd init` as your ordinary user."
            raise RuntimeError(msg)

        def establish_layout(record: InitializationRecorder) -> CreatedResources:
            console.print("[dim]  Establishing the XDG Trinity (Codex, Crypt, Forge) + Btrfs...[/]")
            return LayoutService().initialize(on_created=record)

        def establish_reactor(record: InitializationRecorder) -> CreatedResources:
            console.print("[dim]  Performing the Rite of Signaling (Intent Registry)...[/]")
            return CreatedResources.combine(
                *(
                    PrivilegeService(signals_dir).initialize(on_created=record)
                    for signals_dir in (
                        settings.orchestration.switching.host_reactor_dir,
                        settings.orchestration.switching.host_reactor_journal_dir,
                    )
                )
            )

        def inscribe_codex(record: InitializationRecorder) -> CreatedResources:
            console.print("[dim]  Inscribing the Prime Directive (lychd.toml)...[/]")
            return CodexService(rune_schemas=schemas).inscribe(on_created=record)

        InitializationExecutor(
            planner=planner,
            receipt=receipt,
        ).execute(
            plan,
            effects=(
                establish_layout,
                establish_reactor,
                inscribe_codex,
            ),
        )

        converged_readiness = readiness_service.inspect()
        render_readiness_changes(
            before=readiness,
            after=converged_readiness,
            console=console,
        )
        console.print("\n[bold green]✓ Initialization complete.[/]")
        console.print(f"  [dim]You may now edit your scrolls in {PATH_CODEX_ROOT}[/]")
        if converged_readiness.ready_for_bind:
            console.print("  [dim]Next: lychd bind --dry-run[/]")
        else:
            console.print("  [yellow]Resolve the red HOST checks before binding.[/]")


@ritual_command(
    name="bind",
    help_text="Compile declared intent into owned host bindings.",
    start_message="[bold blue]🔮 Beginning the Transmutation (lychd bind)...[/]",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate and show the exact binding plan without creating secrets, files, or units.",
)
@click.option(
    "--uncaged",
    is_flag=True,
    default=False,
    help="Also inscribe the uncaged vessel systemd --user unit (runs lychd directly on the host, no Podman).",
)
def bind_quadlets(  # noqa: PLR0915 - the command intentionally narrates one linear binding transaction
    dry_run: bool,  # noqa: FBT001 - Click owns these boolean option contracts
    uncaged: bool,  # noqa: FBT001 - Click owns this boolean option contract
) -> None:
    """Perform the Binding Ritual (III. The Transmutation).

    1. Loads Settings and Soulstones from the Codex.
    2. Reconciles secret references against Podman secret storage.
    3. Calculates the Law of Exclusivity (Animation Domain).
    4. Reconciles the complete owned Quadlet/plain-unit set atomically.
    5. Reloads the Systemd User Daemon.
    6. If ``--uncaged``: also inscribe the plain systemd --user vessel unit.
    """
    import secrets

    from lychd.config.runes.registry import load_rune_registry
    from lychd.config.settings.root import get_settings
    from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
    from lychd.domain.animation.services.loader import AnimatorLoader
    from lychd.domain.animation.transmute import Transmuter
    from lychd.extensions.host import get_extensions
    from lychd.system.constants import PATH_SYSTEMD_USER_UNITS_DIR
    from lychd.system.services.binding_preflight import BindingPreflightService
    from lychd.system.services.lifecycle import LifecycleLock
    from lychd.system.services.scribe import ScribeService
    from lychd.system.services.secrets import PodmanSecretStore
    from lychd.system.services.systemd import SystemdUserManager

    console = get_console()

    extensions = get_extensions()
    settings = get_settings()
    legacy_uncaged_unit = PATH_SYSTEMD_USER_UNITS_DIR / "lychd-vessel.service"
    if legacy_uncaged_unit.exists() or legacy_uncaged_unit.is_symlink():
        msg = (
            f"Legacy static unit {legacy_uncaged_unit} shadows the caged Quadlet service. "
            "Disable and remove it before binding; uncaged mode now uses "
            "lychd-uncaged-vessel.service."
        )
        raise RuntimeError(msg)
    # ONE ConfigLoader pass, reused for both reserved-port honesty and the
    # transmute context (D5): no second load, no duck-typing.
    runes = load_rune_registry(extensions)
    reserved_ports = _merge_reserved_ports(settings.server.reserved_ports_map, runes.reserved_ports())

    # 1. Summon the Librarian (Loads & Validates Config)
    loader = AnimatorLoader(rune_schemas=list(extensions.rune_schemas), reserved_ports=reserved_ports)
    soulstones, portals = loader.load_all()
    preflight = BindingPreflightService().inspect(
        settings,
        uncaged=uncaged,
        uncaged_control_plane_secrets=(_uncaged_control_plane_secrets(soulstones) if uncaged else ()),
    )
    _render_binding_preflight(preflight=preflight, console=console)
    systemctl = preflight.require_ready()
    runtime_planner = RuntimeAdapterRegistry(adapters=extensions.runtime_adapters)
    runtime_plans = [runtime_planner.plan(stone) for stone in soulstones]

    # 1.5. Ensure required Podman secrets exist before rendering units.
    secret_store = PodmanSecretStore()
    secret_store.require_quadlet_version()
    core_secrets = {
        settings.server.web.secret_key_secret: lambda: secrets.token_hex(32),
        settings.server.database.password_secret: lambda: secrets.token_urlsafe(16),
    }
    required_soulstone_secrets = _required_secret_names_from_soulstones(soulstones, runtime_plans)
    portal_secret_names = {portal.api_key_secret_name for portal in portals if portal.api_key_secret_name is not None}
    observed_secret_state = _observe_secret_presence(
        secret_store,
        (
            *core_secrets,
            *required_soulstone_secrets,
            *portal_secret_names,
        ),
    )
    secret_presence = dict(observed_secret_state)
    missing_core_secrets = sorted(name for name in core_secrets if not secret_presence[name])
    missing_portal_secrets = sorted(name for name in portal_secret_names if not secret_presence[name])
    missing_soulstone_secrets = [name for name in required_soulstone_secrets if not secret_presence[name]]
    missing_secrets = sorted({*missing_portal_secrets, *missing_soulstone_secrets})

    # 2. Summon the Alchemist (Transmutes Soulstone Runes into Quadlet manifests)
    transmuter = Transmuter(runtime_planner=runtime_planner, contributors=extensions.quadlet_contributors)
    manifests = transmuter.transmute_all(
        soulstones,
        portals=portals,
        runes=runes,
        runtime_plans=runtime_plans,
    )

    # 3. Compute the COMPLETE desired plain-unit set before touching either
    # binding site. One Scribe transaction owns generation, stale removal, and
    # rollback across Quadlet and systemd-user directories.
    plain_units = _desired_plain_units(settings=settings, uncaged=uncaged)

    # 4. Preview the same complete desired-fileset transaction execution uses.
    scribe = ScribeService()
    binding_plan = scribe.plan_reconcile_all(manifests, plain_units=plain_units)
    _render_binding_plan(
        binding_plan=binding_plan,
        missing_core_secrets=missing_core_secrets,
        missing_required_secrets=missing_secrets,
        console=console,
    )
    if missing_secrets:
        _raise_missing_portal_secrets_error(missing_secrets)
    if dry_run:
        console.print("\n[bold green]✓ Binding plan is coherent.[/] [dim]No changes made.[/]")
        return

    with LifecycleLock():
        # Recheck filesystem and secret generations under the same lifecycle
        # lock as secret creation, binding commit, and daemon reload.
        if scribe.plan_reconcile_all(manifests, plain_units=plain_units) != binding_plan:
            msg = "Binding state changed after planning; rerun `lychd bind`."
            raise RuntimeError(msg)
        if (
            _observe_secret_presence(
                secret_store,
                tuple(name for name, _present in observed_secret_state),
            )
            != observed_secret_state
        ):
            msg = "Podman secret state changed after planning; rerun `lychd bind`."
            raise RuntimeError(msg)

        created = [name for name in missing_core_secrets if secret_store.ensure_present(name, core_secrets[name]())]
        if created:
            console.print(f"  [dim]Provisioned secrets: {', '.join(created)}[/]")
        commit_secret_state = _observe_secret_presence(
            secret_store,
            tuple(name for name, _present in observed_secret_state),
        )
        missing_at_commit = [name for name, present in commit_secret_state if not present]
        if missing_at_commit:
            msg = f"Podman secrets disappeared before binding commit: {', '.join(missing_at_commit)}"
            raise RuntimeError(msg)

        with console.status("[bold blue]Transmuting Soulstone Runes into Quadlet manifests...", spinner="moon"):
            scribe.reconcile_all(manifests, plain_units=plain_units)

        # 5. Reload Daemon (The "Bind" part) exactly once while the lifecycle
        # lock still prevents deletion from inspecting an intermediate generation.
        console.print("  [dim]Invoking systemd daemon-reload...[/]")
        SystemdUserManager(systemctl_bin=systemctl).daemon_reload()

    console.print("\n[bold green]✓ The circle is bound.[/]")
    console.print("  [dim]You may now summon the declared system: lychd start[/]")

    # 6. The optional uncaged unit was part of the same desired-fileset
    # transaction. It is never enabled automatically.
    if uncaged:
        _describe_uncaged_vessel(console=console)


def _render_binding_plan(
    *,
    binding_plan: Any,
    missing_core_secrets: Sequence[str],
    missing_required_secrets: Sequence[str],
    console: Console,
) -> None:
    """Render the shared bind transaction and secret preflight by category."""
    styles = {
        "create": ("WOULD CREATE", "cyan"),
        "update": ("WOULD UPDATE", "yellow"),
        "remove": ("WOULD REMOVE", "yellow"),
        "preserve": ("PRESERVE", "dim"),
    }
    console.print()
    if missing_core_secrets or missing_required_secrets:
        console.print("[bold]SECRETS[/]")
        for name in missing_core_secrets:
            console.print(f"  [cyan]WOULD CREATE[/] {name} [dim]— generated core secret is absent[/]")
        for name in missing_required_secrets:
            console.print(f"  [bold red]BLOCKED[/] {name} [dim]— referenced operator secret is absent[/]")

    console.print("[bold]BINDINGS[/]")
    for change in binding_plan.changes:
        label, style = styles[change.kind]
        console.print(f"  [{style}]{label}[/] {change.path} [dim]— {change.detail}[/]")
    console.print("  [cyan]WOULD RELOAD[/] systemd --user [dim]— after a successful binding commit[/]")


def _render_binding_preflight(
    *,
    preflight: BindingPreflightReport,
    console: Console,
) -> None:
    """Render host and secret-boundary prerequisites before planning effects."""
    console.print()
    console.print("[bold]PREFLIGHT[/]")
    if not preflight.issues:
        console.print(f"  [green]READY[/] host prerequisites [dim]— systemctl at {preflight.systemctl_bin}[/]")
        return
    for issue in preflight.issues:
        console.print(f"  [bold red]BLOCKED[/] {issue.target} [dim]— {issue.detail} ({issue.code})[/]")


def _describe_uncaged_vessel(*, console: Console) -> None:
    """Report the reconciled uncaged unit without auto-enabling it."""
    from lychd.system.constants import PATH_SYSTEMD_USER_UNITS_DIR

    unit_path = PATH_SYSTEMD_USER_UNITS_DIR / "lychd-uncaged-vessel.service"
    console.print(f"\n  [dim]Uncaged vessel unit inscribed: {unit_path}[/]")
    console.print("  [bold green]✓ The uncaged vessel is inscribed.[/]")
    console.print("  [dim]To awaken it (you flip the switch):[/]")
    console.print("  [bold]lychd start[/]")


def _host_reactor_units(*, settings: Settings) -> dict[str, str]:
    """Render the host-only trigger/consumer into the desired plain-unit set."""
    import sys
    from pathlib import Path

    from lychd.system.constants import (
        PATH_XDG_CACHE_HOME,
        PATH_XDG_CONFIG_HOME,
        PATH_XDG_DATA_HOME,
    )
    from lychd.system.services.reactor import render_reactor_path_unit, render_reactor_service_unit

    executable = Path(sys.prefix) / "bin" / "lychd"
    environment = {
        "HOME": str(Path.home()),
        "XDG_CACHE_HOME": str(PATH_XDG_CACHE_HOME),
        "XDG_CONFIG_HOME": str(PATH_XDG_CONFIG_HOME),
        "XDG_DATA_HOME": str(PATH_XDG_DATA_HOME),
    }
    return {
        "lychd-reactor.service": render_reactor_service_unit(executable=executable, environment=environment),
        "lychd-reactor.path": render_reactor_path_unit(
            inbox_dir=settings.orchestration.switching.host_reactor_dir,
            journal_dir=settings.orchestration.switching.host_reactor_journal_dir,
        ),
    }


def _desired_plain_units(
    *,
    settings: Settings,
    uncaged: bool,
) -> dict[str, str]:
    """Compile the complete non-Quadlet unit set for one binding plan."""
    from lychd.domain.animation.transmute import transmute_uncaged_vessel

    plain_units = (
        _host_reactor_units(settings=settings) if settings.orchestration.switching.actuator == "host-reactor" else {}
    )
    if uncaged:
        service = transmute_uncaged_vessel(settings)
        plain_units[service.filename] = service.render()
    return plain_units


@click.group(name="reactor", hidden=True)
def reactor_group() -> None:
    """Operate the host-only typed transition consumer."""


@reactor_group.command(name="consume")
def reactor_consume() -> None:
    """Consume pending caged transition intents once."""
    import asyncio

    asyncio.run(_consume_reactor_intents())


async def _consume_reactor_intents() -> None:
    """Build host registry truth and drain the configured Reactor inbox."""
    import asyncio

    from lychd.config.settings.root import get_settings
    from lychd.domain.animation.services.registry import AnimatorRegistry
    from lychd.domain.orchestration.policies import resolve_switch_policy
    from lychd.extensions.host import get_extensions
    from lychd.system.services.reactor import HostReactor

    settings = get_settings()
    extensions = get_extensions()
    registry = AnimatorRegistry(
        rune_schemas=extensions.rune_schemas,
        runtime_adapters=extensions.runtime_adapters,
        portal_factories=extensions.portal_factories,
    )
    await asyncio.to_thread(registry.ensure_loaded)
    inbox = settings.orchestration.switching.host_reactor_dir
    processed = await HostReactor(
        registry,
        inbox_dir=inbox,
        journal_dir=inbox.parent / "journal",
        policy=resolve_switch_policy(settings.orchestration.switching.policy),
    ).consume_all()
    get_console().print(f"[green]✓[/] Host Reactor consumed {processed} transition(s).")


COMMANDS: tuple[click.Command, ...] = (
    init_codex,
    bind_quadlets,
    reactor_group,
)
