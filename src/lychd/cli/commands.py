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
    from lychd.system.services.lifecycle import initialization, lock, models, receipt
    from lychd.system.services.privilege import PrivilegeService

    console = get_console()
    lifecycle_lock = nullcontext() if dry_run else lock.LifecycleLock()
    with lifecycle_lock:
        settings = get_settings()
        extensions = get_extensions()
        schemas = list(extensions.rune_schemas)
        writer = ConfigWriter(runes_dir=PATH_RUNES_DIR)
        receipt_store = receipt.LifecycleReceiptStore()
        planner = initialization.InitializationPlanner(
            reactor_directories=(
                settings.orchestration.switching.host_reactor_dir,
                settings.orchestration.switching.host_reactor_journal_dir,
            ),
            anchor_paths=tuple(schema.anchor_dir(PATH_RUNES_DIR) for schema in schemas),
            sample_paths=writer.planned_sample_paths(schemas),
            receipt_store=receipt_store,
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

        def establish_layout(record: initialization.InitializationRecorder) -> models.CreatedResources:
            console.print("[dim]  Establishing the XDG Trinity (Codex, Crypt, Forge) + Btrfs...[/]")
            return LayoutService().initialize(on_created=record)

        def establish_reactor(record: initialization.InitializationRecorder) -> models.CreatedResources:
            console.print("[dim]  Performing the Rite of Signaling (Intent Registry)...[/]")
            return models.CreatedResources.combine(
                *(
                    PrivilegeService(signals_dir).initialize(on_created=record)
                    for signals_dir in (
                        settings.orchestration.switching.host_reactor_dir,
                        settings.orchestration.switching.host_reactor_journal_dir,
                    )
                )
            )

        def inscribe_codex(record: initialization.InitializationRecorder) -> models.CreatedResources:
            console.print("[dim]  Inscribing the Prime Directive (lychd.toml)...[/]")
            return CodexService(rune_schemas=schemas).inscribe(on_created=record)

        initialization.InitializationExecutor(
            planner=planner,
            receipt=receipt_store,
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
    if uncaged:
        _describe_uncaged_vessel(console=console)
    else:
        console.print("  [dim]You may now summon the declared system: lychd start[/]")


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
    """Report uncaged preparation and the mixed-ownership startup boundary."""
    from lychd.system.constants import PATH_SYSTEMD_USER_UNITS_DIR

    unit_path = PATH_SYSTEMD_USER_UNITS_DIR / "lychd-uncaged-vessel.service"
    console.print(f"\n  [dim]Uncaged vessel unit inscribed: {unit_path}[/]")
    console.print("  [bold green]✓ The uncaged vessel is inscribed.[/]")
    console.print("  [yellow]The complete binding includes both caged and uncaged Vessel units.[/]")
    console.print("  [yellow]Public start refuses mixed Vessel ownership.[/]")
    console.print("  [dim]Installed native startup remains unqualified.[/]")


@click.group(name="reactor", hidden=True)
def reactor_group() -> None:
    """Operate the host-only typed transition consumer."""


@reactor_group.command(name="consume")
def reactor_consume() -> None:
    """Consume pending caged transition intents once."""
    import asyncio

    asyncio.run(_consume_reactor_intents())


@reactor_group.command(name="recover-soft")
@click.argument("activation_id")
def reactor_recover_soft(activation_id: str) -> None:
    """Verify stopped runtime ownership and retire one exact soft activation."""
    import asyncio
    import re

    if re.fullmatch(r"[0-9a-f]{32}", activation_id) is None:
        message = "expected the exact 32-character activation ID"
        raise click.BadParameter(message, param_hint="activation_id")
    try:
        asyncio.run(_recover_soft_activation(activation_id))
    except (RuntimeError, ValueError, OSError, ExceptionGroup) as exc:
        raise click.ClickException(str(exc)) from exc
    get_console().print(f"[green]✓[/] Retired soft activation {activation_id} after verified host recovery.")


async def _recover_soft_activation(activation_id: str) -> None:
    """Compose the host recovery verifier without model probes or ASGI."""
    from contextlib import nullcontext

    from lychd.config.runes.registry import load_rune_registry
    from lychd.config.settings.root import get_settings
    from lychd.domain.animation.services.declarations import compile_animator_declarations
    from lychd.domain.animation.services.registry import AnimatorRegistry
    from lychd.extensions.host import get_extensions
    from lychd.system.constants import PATH_RUNTIME_GUARD_DIR
    from lychd.system.host_tools import trusted_host_tool
    from lychd.system.operator.process import SubprocessRunner
    from lychd.system.services.lifecycle.lock import LifecycleLock
    from lychd.system.services.runtime_guard import FileSoftActivationGuard
    from lychd.system.services.runtime_recovery import SoftActivationRecovery
    from lychd.system.services.runtime_topology import RuntimeTopologyAttestor
    from lychd.system.services.scribe import ScribeService

    with LifecycleLock():
        settings = get_settings()
        extensions = get_extensions()
        runes = load_rune_registry(extensions)
        registry = AnimatorRegistry(
            declarations=compile_animator_declarations(settings=settings, runes=runes),
            runtime_adapters=extensions.runtime_adapters,
            portal_definitions=extensions.portal_definitions,
        )
        registry.load(probe_readiness=False)
        systemctl_bin = trusted_host_tool("systemctl")
        if systemctl_bin is None:
            message = "Soft activation recovery cannot resolve a trusted systemctl executable."
            raise RuntimeError(message)
        scribe = ScribeService()
        timeout = settings.orchestration.switching.systemctl_timeout_s
        await SoftActivationRecovery(
            guard=FileSoftActivationGuard(PATH_RUNTIME_GUARD_DIR),
            registry=registry,
            topology=RuntimeTopologyAttestor(
                registry,
                systemctl_bin=systemctl_bin,
                systemctl_timeout_s=timeout,
                owned_bindings_provider=scribe.inspect_owned_bindings,
            ),
            owned_bindings=scribe.inspect_owned_bindings,
            runner=SubprocessRunner(),
            systemctl_bin=systemctl_bin,
            systemctl_timeout_s=timeout,
            lock_factory=nullcontext,
        ).recover(activation_id)


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
        soulstone_registrations=extensions.soulstone_registrations,
        portal_registrations=extensions.portal_registrations,
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
