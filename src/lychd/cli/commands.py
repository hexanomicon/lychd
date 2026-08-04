"""CLI entrypoints for initialization, binding, and the internal Host Reactor."""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import TYPE_CHECKING

import click

from lychd.cli.base import get_console, ritual_command

if TYPE_CHECKING:
    from rich.console import Console

    from lychd.system.services.binding_preflight import BindingPreflightReport
    from lychd.system.services.scribe import BindingReconcilePlan


def _raise_missing_portal_secrets_error(secret_names: Sequence[str]) -> None:
    missing = ", ".join(secret_names)
    msg = f"Missing required Podman secrets: {missing}. Create them with `podman secret create <name> -` before bind."
    raise RuntimeError(msg)


@ritual_command(
    name="init",
    help_text="Initialize the Codex config files and system layout.",
    start_message="[bold blue]🕯️  Beginning the Inscription (lychd init)...[/]",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show the exact plan without LychD-managed changes; host probes may update tool-owned metadata.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show intermediate host anchors and source-owned path descriptions.",
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
    if not dry_run and os.geteuid() == 0:
        msg = "LychD initialization is rootless; rerun `lychd init` as your ordinary user."
        raise RuntimeError(msg)

    from contextlib import nullcontext

    from lychd.cli.lifecycle_view import render_lifecycle_plan
    from lychd.cli.readiness_view import (
        render_host_readiness,
        render_readiness_changes,
    )
    from lychd.config.runes.writer import ConfigWriter
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
        render_host_readiness(report=readiness.report, console=console)
        plan = planner.plan()
        render_lifecycle_plan(
            plan=plan,
            console=console,
            path_descriptions=writer.planned_path_descriptions(schemas),
            verbose=verbose,
        )
        plan.require_executable()
        if dry_run:
            console.print("\n[bold green]✓ Initialization plan is safe.[/] [dim]No LychD-managed changes made.[/]")
            return

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
            before=readiness.report,
            after=converged_readiness.report,
            console=console,
        )
        console.print("\n[bold green]✓ Initialization complete.[/]")
        console.print(f"  [dim]You may now edit your scrolls in {PATH_CODEX_ROOT}[/]")
        if converged_readiness.report.ready_for_bind:
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
    help="Show the exact plan without LychD-managed changes; host probes may update tool-owned metadata.",
)
@click.option(
    "--uncaged",
    is_flag=True,
    default=False,
    help="Also inscribe the uncaged vessel systemd --user unit (runs lychd directly on the host, no Podman).",
)
def bind_quadlets(
    dry_run: bool,  # noqa: FBT001 - Click owns these boolean option contracts
    uncaged: bool,  # noqa: FBT001 - Click owns this boolean option contract
) -> None:
    """Compile intent, preview one generation, then bind it transactionally.

    Click owns loading and operator narration. ``BindUseCase`` owns lock-time
    revalidation, core-secret creation, the atomic Scribe commit, and exactly
    one user-manager reload. The optional uncaged unit is merely another member
    of the same complete desired binding set and is never enabled implicitly.
    """
    from lychd.cli.binding import BindingCommandSession

    console = get_console()
    session = BindingCommandSession.inspect(uncaged=uncaged)
    _render_binding_preflight(preflight=session.preflight, console=console)
    prepared = session.prepare()
    _render_binding_plan(
        binding_plan=prepared.plan.bindings,
        missing_core_secrets=prepared.plan.missing_core_secrets,
        missing_required_secrets=prepared.plan.missing_required_secrets,
        console=console,
    )
    if prepared.plan.missing_required_secrets:
        _raise_missing_portal_secrets_error(prepared.plan.missing_required_secrets)
    if dry_run:
        console.print("\n[bold green]✓ Binding plan is coherent.[/] [dim]No LychD-managed changes made.[/]")
        return

    with console.status(
        "[bold blue]Committing bindings and reloading the user manager...",
        spinner="moon",
    ):
        result = prepared.use_case.apply(prepared.request, prepared.plan)
    if result.created_secrets:
        console.print(f"  [dim]Provisioned secrets: {', '.join(result.created_secrets)}[/]")

    console.print("\n[bold green]✓ The circle is bound.[/]")
    console.print("  [dim]You may now summon the declared system: lychd start[/]")

    if uncaged:
        _describe_uncaged_vessel(console=console)


def _render_binding_plan(
    *,
    binding_plan: BindingReconcilePlan,
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

    from lychd.config.runes.registry import load_rune_registry
    from lychd.config.settings.root import get_settings
    from lychd.domain.animation.services.declarations import (
        compile_animator_declarations,
    )
    from lychd.domain.animation.services.registry import AnimatorRegistry
    from lychd.domain.orchestration.policies import resolve_switch_policy
    from lychd.extensions.host import get_extensions
    from lychd.system.host_tools import trusted_host_tool
    from lychd.system.services.reactor import HostReactor

    settings = get_settings()
    extensions = get_extensions()
    runes = load_rune_registry(extensions)
    registry = AnimatorRegistry(
        declarations=compile_animator_declarations(
            settings=settings,
            runes=runes,
        ),
        runtime_adapters=extensions.runtime_adapters,
        portal_definitions=extensions.portal_definitions,
    )
    await asyncio.to_thread(registry.ensure_loaded)
    switching = settings.orchestration.switching
    systemctl_bin = trusted_host_tool("systemctl")
    if systemctl_bin is None:
        msg = "Host Reactor cannot resolve a trusted systemctl executable."
        raise RuntimeError(msg)
    processed = await HostReactor(
        registry,
        inbox_dir=switching.host_reactor_dir,
        journal_dir=switching.host_reactor_journal_dir,
        systemctl_bin=systemctl_bin,
        systemctl_timeout_s=switching.systemctl_timeout_s,
        policy=resolve_switch_policy(switching.policy),
    ).consume_all()
    get_console().print(f"[green]✓[/] Host Reactor consumed {processed} transition(s).")


COMMANDS: tuple[click.Command, ...] = (
    init_codex,
    bind_quadlets,
    reactor_group,
)
