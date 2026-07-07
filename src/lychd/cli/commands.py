"""CLI command entrypoints for Codex initialization and bind workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

import click

from lychd.cli.base import get_console, ritual_command

if TYPE_CHECKING:
    from rich.console import Console

    from lychd.config.settings import Settings
    from lychd.domain.animation.schemas import SoulstoneConfig
    from lychd.system.services.scribe import ScribeService


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


def _required_secret_names_from_soulstones(soulstones: Sequence[SoulstoneConfig]) -> list[str]:
    """Collect Podman secret names declared by soulstone secret env mappings."""
    names: set[str] = set()
    for stone in soulstones:
        for secret_name in stone.secret_env_files.values():
            if secret_name:
                names.add(secret_name)
    return sorted(names)


@ritual_command(
    name="init",
    help_text="Initialize the Codex config files and system layout.",
    start_message="[bold blue]🕯️  Beginning the Inscription (lychd init)...[/]",
)
def init_codex() -> None:
    """Perform the Initialization Ritual (I. The Inscription).

    1. Creates the XDG directory structure (Codex, Crypt, Forge).
    2. Speculatively creates Btrfs subvolumes (Phylactery).
    3. Establishes the Intent Registry (Triggers).
    4. Inscribes default configuration files.
    """
    from lychd.extensions.host import get_extensions
    from lychd.system.services.codex import CodexService
    from lychd.system.services.layout import LayoutService
    from lychd.system.services.privilege import PrivilegeService

    console = get_console()
    # 1. Physical Layout & Speculative Btrfs (ADR 13 & ADR 08)
    console.print("[dim]  Establishing the XDG Trinity (Codex, Crypt, Forge) + Btrfs...[/]")
    LayoutService().initialize()

    # 2. Intent Registry (ADR 10)
    console.print("[dim]  Performing the Rite of Signaling (Intent Registry)...[/]")
    PrivilegeService().initialize()

    # 3. Inscribe the Laws (Settings)
    console.print("[dim]  Inscribing the Prime Directive (lychd.toml)...[/]")
    CodexService(rune_schemas=get_extensions().rune_schemas).inscribe()

    console.print("\n[bold green]✓ Initialization complete.[/]")
    console.print("  [dim]You may now edit your scrolls in ~/.config/lychd/[/]")


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
def bind_quadlets(uncaged: bool) -> None:  # noqa: FBT001 - click passes flags as kwargs; the option owns the bool contract
    """Perform the Binding Ritual (III. The Transmutation).

    1. Loads Settings and Soulstones from the Codex.
    2. Reconciles secret references against Podman secret storage.
    3. Calculates the Law of Exclusivity (Animation Domain).
    4. Generates Systemd Quadlet manifest files with Git versioning (System Domain).
    5. Reloads the Systemd User Daemon.
    6. If ``--uncaged``: also inscribe the plain systemd --user vessel unit.
    """
    import secrets
    import shutil
    import subprocess

    from lychd.config.runes.registry import load_rune_registry
    from lychd.config.settings import get_settings
    from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
    from lychd.domain.animation.services.loader import AnimatorLoader
    from lychd.domain.animation.transmute import Transmuter
    from lychd.extensions.host import get_extensions
    from lychd.system.services.scribe import ScribeService
    from lychd.system.services.secrets import PodmanSecretStore

    console = get_console()

    extensions = get_extensions()
    settings = get_settings()
    # ONE ConfigLoader pass, reused for both reserved-port honesty and the
    # transmute context (D5): no second load, no duck-typing.
    runes = load_rune_registry(extensions)
    reserved_ports = _merge_reserved_ports(settings.reserved_ports_map, runes.reserved_ports())

    # 1. Summon the Librarian (Loads & Validates Config)
    loader = AnimatorLoader(rune_schemas=list(extensions.rune_schemas), reserved_ports=reserved_ports)
    soulstones, portals = loader.load_all()

    # 1.5. Ensure required Podman secrets exist before rendering units.
    secret_store = PodmanSecretStore()
    created: list[str] = []
    if secret_store.ensure_present(settings.app.secret_key_secret, secrets.token_hex(32)):
        created.append(settings.app.secret_key_secret)
    if secret_store.ensure_present(settings.db.password_secret, secrets.token_urlsafe(16)):
        created.append(settings.db.password_secret)

    required_soulstone_secrets = _required_secret_names_from_soulstones(soulstones)
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
    runtime_planner = RuntimeAdapterRegistry(adapters=extensions.runtime_adapters)
    transmuter = Transmuter(runtime_planner=runtime_planner, contributors=extensions.quadlet_contributors)
    manifests = transmuter.transmute_all(soulstones, portals=portals, runes=runes)

    # 3. Summon the Scribe (Writes Quadlet manifests with Atomic Inscription)
    scribe = ScribeService()
    with console.status("[bold blue]Transmuting Soulstone Runes into Quadlet manifests...", spinner="moon"):
        scribe.generate_all(manifests)

    # 4. Reload Daemon (The "Bind" part)
    systemctl = shutil.which("systemctl")
    if systemctl:
        console.print("  [dim]Invoking systemd daemon-reload...[/]")
        subprocess.run([systemctl, "--user", "daemon-reload"], check=True)  # noqa: S603
    else:
        console.print("  [yellow]![/] [dim]Systemctl not found. Manual daemon-reload required.[/]")

    console.print("\n[bold green]✓ The circle is bound.[/]")
    console.print("  [dim]You may now summon the vessel: systemctl --user start lychd-vessel.service[/]")

    # 5. (Optional) Uncaged daemonhood — a plain systemd --user unit that runs
    # lychd directly on the host, bypassing the Podman pod entirely. Separate,
    # obvious path: no Quadlet staging/sentinel involved.
    if uncaged:
        _inscribe_uncaged_vessel(scribe=scribe, settings=settings, systemctl=systemctl, console=console)


def _inscribe_uncaged_vessel(
    *,
    scribe: ScribeService,
    settings: Settings,
    systemctl: str | None,
    console: Console,
) -> None:
    """Inscribe the uncaged vessel systemd ``--user`` unit and hint the enable step.

    A deliberately separate path from the Quadlet bind: the vessel runs ``lychd``
    directly on the host. We reload the daemon (when systemd is present) but NEVER
    auto-enable — the Magus flips the switch. Without systemd, the unit is still
    written and daemon-reload is skipped with a warning.
    """
    import subprocess

    from lychd.domain.animation.transmute import transmute_uncaged_vessel

    service = transmute_uncaged_vessel(settings)
    unit_path = scribe.write_user_unit(service)
    console.print(f"\n  [dim]Uncaged vessel unit inscribed: {unit_path}[/]")
    if systemctl:
        console.print("  [dim]Invoking systemd daemon-reload...[/]")
        subprocess.run([systemctl, "--user", "daemon-reload"], check=True)  # noqa: S603
    else:
        console.print("  [yellow]![/] [dim]Systemctl not found. daemon-reload skipped.[/]")
    console.print("  [bold green]✓ The uncaged vessel is inscribed.[/]")
    console.print("  [dim]To awaken it (you flip the switch):[/]")
    console.print("  [bold]systemctl --user enable --now lychd-vessel.service[/]")


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

    from lychd.config.settings import get_settings

    console = get_console()
    settings = get_settings()
    if settings.db.profile == "memory":
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

    await ledger.decide(consent_id, approved=approved, decided_by=settings.sigil.name)
    engine = _build_cli_engine(settings, factory)
    await engine.approve(consent_id, approved=approved)
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


COMMANDS: tuple[click.Command, ...] = (init_codex, bind_quadlets, inspect_animators, runs_group)
