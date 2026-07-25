"""CLI command entrypoints for Codex initialization and bind workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

import click

from lychd.cli.base import get_console, ritual_command

_REACTOR_DIRECTORY_MODE = 0o700

if TYPE_CHECKING:
    from rich.console import Console

    from lychd.config.settings.root import Settings
    from lychd.domain.animation.schemas import SoulstoneConfig
    from lychd.domain.animation.services.adapters.contracts import RuntimePlan
    from lychd.system.services.lifecycle import LifecyclePlan


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


def _raise_uncaged_control_plane_error(secret_names: Sequence[str]) -> None:
    names = ", ".join(secret_names)
    msg = (
        "Uncaged Vessel mode cannot host Soulstones with Podman-mounted control-plane secrets "
        f"({names}); use the caged Vessel until a host credential boundary is implemented."
    )
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
    help="Show the exact initialization plan without changing files, modes, mounts, or services.",
)
def init_codex(dry_run: bool) -> None:  # noqa: FBT001 - Click owns this boolean option contract
    """Perform the Initialization Ritual (I. The Inscription).

    1. Creates the XDG directory structure (Codex, Crypt, Forge).
    2. Speculatively creates Btrfs subvolumes (Phylactery).
    3. Establishes the Intent Registry (Triggers).
    4. Inscribes default configuration files.
    """
    from contextlib import nullcontext

    from lychd.config.runes import ConfigWriter
    from lychd.config.settings.root import get_settings
    from lychd.extensions.host import get_extensions
    from lychd.system.constants import PATH_RUNES_DIR
    from lychd.system.services.codex import CodexService
    from lychd.system.services.layout import LayoutService
    from lychd.system.services.lifecycle import (
        InitializationPlanner,
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
        plan = InitializationPlanner(
            reactor_directories=(
                settings.orchestration.switching.host_reactor_dir,
                settings.orchestration.switching.host_reactor_journal_dir,
            ),
            anchor_paths=tuple(schema.anchor_dir(PATH_RUNES_DIR) for schema in schemas),
            sample_paths=writer.planned_sample_paths(schemas),
        ).plan()
        _render_lifecycle_plan(plan=plan, console=console)
        plan.require_executable()
        if dry_run:
            console.print("\n[bold green]✓ Initialization plan is safe.[/] [dim]No changes made.[/]")
            return

        receipt = LifecycleReceiptStore()

        # 1. Physical Layout & Speculative Btrfs (ADR 13 & ADR 08)
        console.print("[dim]  Establishing the XDG Trinity (Codex, Crypt, Forge) + Btrfs...[/]")
        LayoutService().initialize(on_created=receipt.record)

        # 2. Provision validated control roots. Journal each successful effect
        # batch immediately rather than waiting until the whole ritual ends.
        console.print("[dim]  Performing the Rite of Signaling (Intent Registry)...[/]")
        for signals_dir in (
            settings.orchestration.switching.host_reactor_dir,
            settings.orchestration.switching.host_reactor_journal_dir,
        ):
            PrivilegeService(signals_dir).initialize(on_created=receipt.record)

        # 3. Inscribe the Laws (Settings)
        console.print("[dim]  Inscribing the Prime Directive (lychd.toml)...[/]")
        CodexService(rune_schemas=schemas).inscribe(on_created=receipt.record)

        console.print("\n[bold green]✓ Initialization complete.[/]")
        console.print("  [dim]You may now edit your scrolls in ~/.config/lychd/[/]")


def _render_lifecycle_plan(*, plan: LifecyclePlan, console: Console) -> None:
    """Render deterministic lifecycle categories without exposing implementation data."""
    from lychd.system.services.lifecycle import LifecycleDisposition

    console.print()
    for disposition in LifecycleDisposition:
        actions = tuple(action for action in plan.actions if action.disposition is disposition)
        if not actions:
            continue
        style = {
            LifecycleDisposition.WOULD_CREATE: "cyan",
            LifecycleDisposition.WOULD_REMOVE: "yellow",
            LifecycleDisposition.PRESERVE: "dim",
            LifecycleDisposition.BLOCKED: "bold red",
        }[disposition]
        console.print(f"[{style}]{disposition.value}[/]")
        for action in actions:
            console.print(f"  [{style}]•[/] {action.target} [dim]— {action.detail}[/]")


@ritual_command(
    name="destroy",
    help_text="Remove pristine resources recorded as created by LychD.",
    start_message="[bold blue]⌁ Beginning the Dissolution (lychd destroy)...[/]",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show the exact destruction plan without stopping services or changing host state.",
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm a safe destruction plan non-interactively; never bypasses blockers.",
)
def destroy(
    dry_run: bool,  # noqa: FBT001 - Click owns these boolean option contracts
    yes: bool,  # noqa: FBT001
) -> None:
    """Remove only inactive bindings and pristine init-owned resources.

    Edited files, foreign entries, active/enabled units, mounts, secrets, and
    unrecorded data are preserved or block the operation.
    """
    from contextlib import nullcontext

    from lychd.system.services.lifecycle import (
        BindingLifecycleService,
        LifecycleLock,
        LifecyclePlan,
        LifecycleReceiptStore,
    )
    from lychd.system.services.scribe import ScribeService

    console = get_console()
    lock = nullcontext() if dry_run else LifecycleLock()
    with lock:
        receipt = LifecycleReceiptStore()
        bindings = BindingLifecycleService(ScribeService())
        binding_plan = bindings.plan_destroy()
        receipt_plan = receipt.plan_destroy(anticipated_removals=binding_plan.removal_paths)
        plan = LifecyclePlan.combine(binding_plan, receipt_plan)
        _render_lifecycle_plan(plan=plan, console=console)
        plan.require_executable()

        if dry_run:
            console.print("\n[bold green]✓ Destruction plan is safe.[/] [dim]No changes made.[/]")
            return
        if not plan.mutates:
            console.print("\n[dim]Nothing owned by this installation needs removal.[/]")
            return
        if not yes and not click.confirm("\nApply this exact destruction plan?", default=False):
            console.print("[dim]Dissolution cancelled. No changes made.[/]")
            return

        bindings.destroy()
        receipt.destroy()
        console.print("\n[bold green]✓ Recorded LychD inscription destroyed.[/]")


@ritual_command(
    name="bind",
    help_text="Transmute configs into Systemd units.",
    start_message="[bold blue]🔮 Beginning the Transmutation (lychd bind)...[/]",
)
@click.option(
    "--uncaged",
    is_flag=True,
    default=False,
    help="Also inscribe the uncaged vessel systemd --user unit (runs lychd directly on the host, no Podman).",
)
def bind_quadlets(  # noqa: C901, PLR0915 - the command intentionally narrates one linear binding transaction
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
    import shutil
    import subprocess

    from lychd.config.runes.registry import load_rune_registry
    from lychd.config.settings.root import get_settings
    from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
    from lychd.domain.animation.services.loader import AnimatorLoader
    from lychd.domain.animation.transmute import Transmuter, transmute_uncaged_vessel
    from lychd.extensions.host import get_extensions
    from lychd.system.constants import PATH_SYSTEMD_USER_UNITS_DIR
    from lychd.system.services.lifecycle import LifecycleLock
    from lychd.system.services.scribe import ScribeService
    from lychd.system.services.secrets import PodmanSecretStore

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
    if uncaged and (uncaged_secrets := _uncaged_control_plane_secrets(soulstones)):
        _raise_uncaged_control_plane_error(uncaged_secrets)
    runtime_planner = RuntimeAdapterRegistry(adapters=extensions.runtime_adapters)
    runtime_plans = [runtime_planner.plan(stone) for stone in soulstones]

    # 1.5. Ensure required Podman secrets exist before rendering units.
    secret_store = PodmanSecretStore()
    secret_store.require_quadlet_version()
    created: list[str] = []
    if secret_store.ensure_present(settings.server.web.secret_key_secret, secrets.token_hex(32)):
        created.append(settings.server.web.secret_key_secret)
    if secret_store.ensure_present(settings.server.database.password_secret, secrets.token_urlsafe(16)):
        created.append(settings.server.database.password_secret)

    required_soulstone_secrets = _required_secret_names_from_soulstones(soulstones, runtime_plans)
    missing_portal_secrets = sorted(
        {
            portal.api_key_secret_name
            for portal in portals
            if portal.api_key_secret_name is not None and not secret_store.exists(portal.api_key_secret_name)
        }
    )
    missing_soulstone_secrets = [name for name in required_soulstone_secrets if not secret_store.exists(name)]
    missing_secrets = sorted({*missing_portal_secrets, *missing_soulstone_secrets})
    if missing_secrets:
        _raise_missing_portal_secrets_error(missing_secrets)
    if created:
        console.print(f"  [dim]Provisioned secrets: {', '.join(created)}[/]")

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
    plain_units: dict[str, str] = {}
    if settings.orchestration.switching.actuator == "host-reactor":
        plain_units.update(_host_reactor_units(settings=settings))
    if uncaged:
        uncaged_service = transmute_uncaged_vessel(settings)
        plain_units[uncaged_service.filename] = uncaged_service.render()

    # 4. Summon the Scribe (one complete desired-fileset transaction).
    scribe = ScribeService()
    with LifecycleLock():
        with console.status("[bold blue]Transmuting Soulstone Runes into Quadlet manifests...", spinner="moon"):
            scribe.reconcile_all(manifests, plain_units=plain_units)

        # 5. Reload Daemon (The "Bind" part) exactly once while the lifecycle
        # lock still prevents destroy from inspecting an intermediate generation.
        systemctl = shutil.which("systemctl")
        if systemctl:
            console.print("  [dim]Invoking systemd daemon-reload...[/]")
            subprocess.run([systemctl, "--user", "daemon-reload"], check=True)  # noqa: S603
        else:
            console.print("  [yellow]![/] [dim]Systemctl not found. Manual daemon-reload required.[/]")

    console.print("\n[bold green]✓ The circle is bound.[/]")
    console.print("  [dim]You may now summon the vessel: systemctl --user start lychd-vessel.service[/]")

    # 6. The optional uncaged unit was part of the same desired-fileset
    # transaction. It is never enabled automatically.
    if uncaged:
        _describe_uncaged_vessel(console=console)


def _describe_uncaged_vessel(*, console: Console) -> None:
    """Report the reconciled uncaged unit without auto-enabling it."""
    from lychd.system.constants import PATH_SYSTEMD_USER_UNITS_DIR

    unit_path = PATH_SYSTEMD_USER_UNITS_DIR / "lychd-uncaged-vessel.service"
    console.print(f"\n  [dim]Uncaged vessel unit inscribed: {unit_path}[/]")
    console.print("  [bold green]✓ The uncaged vessel is inscribed.[/]")
    console.print("  [dim]To awaken it (you flip the switch):[/]")
    console.print("  [bold]systemctl --user enable --now lychd-uncaged-vessel.service[/]")


def _host_reactor_units(*, settings: Settings) -> dict[str, str]:
    """Render the host-only trigger/consumer into the desired plain-unit set."""
    import sys
    from pathlib import Path

    from lychd.system.constants import PATH_CACHE_ROOT, PATH_CODEX_ROOT, PATH_CRYPT_ROOT
    from lychd.system.services.reactor import render_reactor_path_unit, render_reactor_service_unit

    executable = Path(sys.prefix) / "bin" / "lychd"
    environment = {
        "HOME": str(Path.home()),
        "XDG_CACHE_HOME": str(PATH_CACHE_ROOT.parent),
        "XDG_CONFIG_HOME": str(PATH_CODEX_ROOT.parent),
        "XDG_DATA_HOME": str(PATH_CRYPT_ROOT.parent),
    }
    return {
        "lychd-reactor.service": render_reactor_service_unit(executable=executable, environment=environment),
        "lychd-reactor.path": render_reactor_path_unit(
            inbox_dir=settings.orchestration.switching.host_reactor_dir,
            journal_dir=settings.orchestration.switching.host_reactor_journal_dir,
        ),
    }


@ritual_command(
    name="animators",
    help_text="Inspect loaded animator runes, their capabilities, and live readiness.",
    start_message="[bold blue]:material-visibility: Opening the Oculus (lychd animators)...[/]",
)
def inspect_animators() -> None:
    """Observe the assembled animator registry (II. The Awakening).

    Loads the active Codex Runes via the extension activation list, resolves a
    runtime animator for each, probes live readiness, and renders the
    synthesized capability specs alongside their current states.
    """
    from rich.table import Table

    from lychd.domain.animation.services.registry import AnimatorRegistry
    from lychd.extensions.host import get_extensions

    console = get_console()
    extensions = get_extensions()
    registry = AnimatorRegistry(
        rune_schemas=extensions.rune_schemas,
        runtime_adapters=extensions.runtime_adapters,
        portal_factories=extensions.portal_factories,
    )
    animators = registry.list_runtime_animators()

    if not animators:
        console.print(
            "  [yellow]No animators resolved.[/] [dim]Enable animator extensions in "
            "~/.config/lychd/lychd.toml and add runes under "
            "~/.config/lychd/runes/animator/.[/]"
        )
        return

    table = Table(title="Animators", show_lines=False, expand=False)
    table.add_column("Animator", style="bold", no_wrap=True)
    table.add_column("Runtime", no_wrap=True)
    table.add_column("Family", no_wrap=True)
    table.add_column("Model", no_wrap=True)
    table.add_column("Active", justify="center")
    table.add_column("Warm", justify="center")
    table.add_column("Health", no_wrap=True)
    table.add_column("Reason", overflow="fold")

    for animator in animators:
        specs = registry.list_capabilities_for_animator(animator.name)
        if not specs:
            table.add_row(
                animator.name,
                getattr(animator.connector, "kind", "-"),
                "-",
                "-",
                "-",
                "-",
                "no capabilities",
                "",
            )
            continue

        for spec in specs:
            state = registry.get_capability_state(spec.key)
            active = "[green]✓[/]" if state and state.is_active else "[dim]·[/]"
            warm = "[green]✓[/]" if state and state.warm else "[dim]·[/]"
            family = spec.family.value if hasattr(spec.family, "value") else str(spec.family)
            health = state.health if state else "unknown"
            reason = state.reason if state and state.reason else ""
            table.add_row(
                animator.name,
                spec.runtime,
                family,
                spec.model_id,
                active,
                warm,
                health,
                reason,
            )

    console.print(table)
    console.print(
        "  [dim]Live readiness probed via the OpenAI-compatible /models endpoint (vLLM/SGLang) "
        "and the llama.cpp control plane. Re-run after `lychd bind` + starting a unit.[/]"
    )


@ritual_command(
    name="doctor",
    help_text="Validate configuration, runes, host tools, and secret wiring without changing state.",
    start_message="[bold blue]🩺 Examining the LychD foundation (lychd doctor)...[/]",
)
@click.option(
    "--uncaged",
    is_flag=True,
    default=False,
    help="Validate direct host execution instead of the rootless Podman deployment.",
)
def doctor(uncaged: bool) -> None:  # noqa: C901, FBT001, PLR0912, PLR0915 - bounded read-only preflight
    """Run a read-only preflight over the minimum runnable configuration."""
    import os
    import shutil
    import stat

    from lychd.config.runes.registry import load_rune_registry
    from lychd.config.settings.root import get_settings
    from lychd.config.utils import codex_permission_issues
    from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
    from lychd.domain.animation.services.loader import AnimatorLoader
    from lychd.extensions.host import get_extensions
    from lychd.system.constants import PATH_LYCHD_TOML, PATH_SYSTEMD_USER_UNITS_DIR

    console = get_console()
    failures: list[str] = []
    if not PATH_LYCHD_TOML.is_file():
        failures.append(f"Codex is missing at {PATH_LYCHD_TOML}; run `lychd init` first")

    permission_issues = codex_permission_issues(PATH_LYCHD_TOML)
    if permission_issues:
        failures.append(f"Codex permissions are unsafe: {permission_issues}")

    settings = get_settings()
    extensions = get_extensions()
    runes = load_rune_registry(extensions)
    reserved_ports = _merge_reserved_ports(settings.server.reserved_ports_map, runes.reserved_ports())
    soulstones, portals = AnimatorLoader(
        rune_schemas=list(extensions.rune_schemas),
        reserved_ports=reserved_ports,
    ).load_all()
    runtime_planner = RuntimeAdapterRegistry(adapters=extensions.runtime_adapters)
    runtime_plans = [runtime_planner.plan(stone) for stone in soulstones]

    if shutil.which("systemctl") is None:
        failures.append("systemctl is not available on PATH")

    switching = settings.orchestration.switching
    if not uncaged:
        if switching.actuator != "host-reactor":
            failures.append("caged deployment requires orchestration.switching.actuator='host-reactor'")
        else:
            journal_dir = switching.host_reactor_journal_dir
            for label, directory in (
                ("Host Reactor inbox", switching.host_reactor_dir),
                ("Host Reactor journal", journal_dir),
            ):
                if directory.is_symlink() or not directory.is_dir():
                    failures.append(f"{label} is missing or unsafe: {directory}; run `lychd init`")
                    continue
                metadata = directory.stat()
                if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != _REACTOR_DIRECTORY_MODE:
                    failures.append(f"{label} must be owned by uid {os.getuid()} with mode 0o700: {directory}")
            failures.extend(
                f"Host Reactor unit is missing: {unit_name}; run `lychd bind`"
                for unit_name in ("lychd-reactor.path", "lychd-reactor.service")
                if not (PATH_SYSTEMD_USER_UNITS_DIR / unit_name).is_file()
            )

    if uncaged:
        uncaged_secrets = _uncaged_control_plane_secrets(soulstones)
        if uncaged_secrets:
            failures.append(
                "uncaged Vessel cannot resolve Podman-mounted Soulstone control-plane secrets: "
                f"{', '.join(uncaged_secrets)}"
            )
        from lychd.config.components import resolve_web_secret_key
        from lychd.db.factory import resolve_database_password

        secret_resolvers = (
            ("application signing key", lambda: resolve_web_secret_key(settings.server.web)),
            ("database password", lambda: resolve_database_password(settings.server.database)),
        )
        for label, resolver in secret_resolvers:
            try:
                resolver()
            except ValueError as exc:
                failures.append(f"{label}: {exc}")
    else:
        from lychd.system.services.secrets import PodmanSecretStore, PodmanSecretStoreError

        try:
            secret_store = PodmanSecretStore()
            secret_store.require_quadlet_version()
        except PodmanSecretStoreError as exc:
            failures.append(str(exc))
        else:
            referenced = {
                settings.server.web.secret_key_secret,
                settings.server.database.password_secret,
                *_required_secret_names_from_soulstones(soulstones, runtime_plans),
                *(portal.api_key_secret_name for portal in portals if portal.api_key_secret_name),
            }
            missing = sorted(name for name in referenced if not secret_store.exists(name))
            if missing:
                failures.append(f"missing Podman secrets: {', '.join(missing)}")

    if failures:
        raise RuntimeError("; ".join(failures))

    console.print(
        f"\n[bold green]✓ Foundation is coherent.[/] "
        f"[dim]{len(soulstones)} Soulstone(s), {len(portals)} Portal(s), {len(runes.all())} Rune(s).[/]"
    )


@click.group(name="runs")
def runs_group() -> None:
    """Manage runs: approve or deny a parked consent (Human-in-the-Loop)."""


@runs_group.command(name="approve")
@click.argument("consent_id")
def runs_approve(consent_id: str) -> None:
    """Approve a parked consent by id (resumes the run with the tool granted)."""
    import asyncio

    asyncio.run(_decide_consent(consent_id, approved=True))


@runs_group.command(name="deny")
@click.argument("consent_id")
def runs_deny(consent_id: str) -> None:
    """Deny a parked consent by id (the run resumes and settles honestly without the action)."""
    import asyncio

    asyncio.run(_decide_consent(consent_id, approved=False))


async def _decide_consent(consent_id: str, *, approved: bool) -> None:
    """Record a consent verdict + re-enqueue the parked run (register-shim doctrine)."""
    import sys

    from lychd.config.settings.root import get_settings

    console = get_console()
    settings = get_settings()
    if settings.server.database.profile == "memory":
        console.print(
            "  [red]✗[/] consent verdicts require the postgres profile (an in-memory ledger is process-local)."
        )
        sys.exit(1)

    from lychd.db.engine import get_session_factory
    from lychd.domain.codex.ledger import CodexConsentLedger

    factory = get_session_factory()
    ledger = CodexConsentLedger(session_factory=factory)
    view = await ledger.get(consent_id)
    if view is None:
        console.print(f"  [red]✗[/] Unknown consent id: {consent_id}")
        sys.exit(1)
    if view.status != "pending":
        console.print(f"  [dim]Consent {consent_id} is already {view.status} — nothing to do.[/]")
        return

    from lychd.domain.codex.sigil import default_local_sigil

    await ledger.decide(consent_id, approved=approved, decided_by=default_local_sigil().name)
    engine = _build_cli_engine(settings, factory)
    from lychd.system.services.queues import connect_run_queues, disconnect_run_queues

    connected = await connect_run_queues(engine.queues)
    try:
        await engine.approve(consent_id, approved=approved)
    finally:
        await disconnect_run_queues(connected)
    verdict = "approved" if approved else "denied"
    console.print(f"  [bold green]✓[/] Consent {consent_id} {verdict}; the run has been re-enqueued.")


def _build_cli_engine(settings: Settings, factory: Any) -> Any:
    """Build an inert-bus RunEngine whose `approve` touches only the ledger + queues."""
    from lychd.config.components import saq_queue_from_settings
    from lychd.domain.cortex.engine import QueueRouter, RunEngine
    from lychd.domain.cortex.events import InProcessEventBus
    from lychd.domain.cortex.ledger import DbRunLedger

    return RunEngine(
        ledger=DbRunLedger(session_factory=factory),
        bus=InProcessEventBus(),
        workflows=None,  # approve does not route; the inert workflows handle is unused
        queue_router=QueueRouter(),
        queues={name: saq_queue_from_settings(settings, name) for name in ("runs", "rites")},
    )


@click.group(name="reactor")
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
    destroy,
    bind_quadlets,
    doctor,
    inspect_animators,
    runs_group,
    reactor_group,
)
