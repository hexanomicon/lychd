"""CLI command entrypoints for Codex initialization and bind workflows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from lychd.cli.base import get_console, ritual_command

if TYPE_CHECKING:
    import click

    from lychd.domain.animation.schemas import SoulstoneConfig


def _raise_missing_portal_secrets_error(secret_names: list[str]) -> None:
    missing = ", ".join(secret_names)
    msg = f"Missing required Podman secrets: {missing}. Create them with `podman secret create <name> -` before bind."
    raise RuntimeError(msg)


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
    start_message="[bold blue]🕯️  Beginning the Inscription (lych init)...[/]",
)
def init_codex() -> None:
    """Perform the Initialization Ritual (I. The Inscription).

    1. Creates the XDG directory structure (Codex, Crypt, Forge).
    2. Speculatively creates Btrfs subvolumes (Phylactery).
    3. Establishes the Intent Registry (Triggers).
    4. Inscribes default configuration files.
    """
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
    CodexService().inscribe()

    console.print("\n[bold green]✓ Initialization complete.[/]")
    console.print("  [dim]You may now edit your scrolls in ~/.config/lychd/[/]")


@ritual_command(
    name="bind",
    help_text="Transmute configs into Systemd units.",
    start_message="[bold blue]🔮 Beginning the Transmutation (lych bind)...[/]",
)
def bind_quadlets() -> None:
    """Perform the Binding Ritual (III. The Transmutation).

    1. Loads Settings and Soulstones from the Codex.
    2. Reconciles secret references against Podman secret storage.
    3. Calculates the Law of Exclusivity (Animation Domain).
    4. Generates Systemd Quadlet files (Runes) with Git versioning (System Domain).
    5. Reloads the Systemd User Daemon.
    """
    import secrets
    import shutil
    import subprocess

    from lychd.config.settings import get_settings
    from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
    from lychd.domain.animation.services.loader import AnimatorLoader
    from lychd.domain.animation.transmute import Transmuter
    from lychd.system.services.scribe import ScribeService
    from lychd.system.services.secrets import PodmanSecretStore

    console = get_console()

    # 1. Summon the Librarian (Loads & Validates Config)
    loader = AnimatorLoader()
    soulstones, portals = loader.load_all()

    # 1.5. Ensure required Podman secrets exist before rendering units.
    settings = get_settings()
    secret_store = PodmanSecretStore()
    created: list[str] = []
    if secret_store.ensure_present(settings.app.secret_key_secret, secrets.token_hex(32)):
        created.append(settings.app.secret_key_secret)
    if secret_store.ensure_present(settings.db.password_secret, secrets.token_urlsafe(16)):
        created.append(settings.db.password_secret)

    required_soulstone_secrets = _required_secret_names_from_soulstones(soulstones)
    missing_portal_secrets = sorted(
        {
            portal.api_key_secret
            for portal in portals
            if portal.api_key_secret is not None and not secret_store.exists(portal.api_key_secret)
        }
    )
    missing_soulstone_secrets = [name for name in required_soulstone_secrets if not secret_store.exists(name)]
    missing_secrets = sorted({*missing_portal_secrets, *missing_soulstone_secrets})
    if missing_secrets:
        _raise_missing_portal_secrets_error(missing_secrets)
    if created:
        console.print(f"  [dim]Provisioned secrets: {', '.join(created)}[/]")

    # 2. Summon the Alchemist (Transmutes Soulstones into Runes)
    runtime_planner = RuntimeAdapterRegistry()
    transmuter = Transmuter(runtime_planner=runtime_planner)
    runes = transmuter.transmute_all(soulstones, portals=portals)

    # 3. Summon the Scribe (Writes Runes with Atomic Inscription)
    scribe = ScribeService()
    with console.status("[bold blue]Transmuting Soulstones into Runes...", spinner="moon"):
        scribe.generate_all(runes)

    # 4. Reload Daemon (The "Bind" part)
    systemctl = shutil.which("systemctl")
    if systemctl:
        console.print("  [dim]Invoking systemd daemon-reload...[/]")
        subprocess.run([systemctl, "--user", "daemon-reload"], check=True)  # noqa: S603
    else:
        console.print("  [yellow]![/] [dim]Systemctl not found. Manual daemon-reload required.[/]")

    console.print("\n[bold green]✓ The circle is bound.[/]")
    console.print("  [dim]You may now summon the vessel: systemctl --user start lychd-vessel.service[/]")


COMMANDS: tuple[click.Command, ...] = (init_codex, bind_quadlets)
