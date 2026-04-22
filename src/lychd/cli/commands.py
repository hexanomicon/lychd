from __future__ import annotations

import click


@click.command(name="init", help="Initialize the Codex config files and system layout.")
def init_codex() -> None:
    """Perform the Initialization Ritual (I. The Inscription).

    1. Creates the XDG directory structure (Codex, Crypt, Forge).
    2. Speculatively creates Btrfs subvolumes (Phylactery).
    3. Establishes the Intent Registry (Triggers).
    4. Inscribes default configuration files.
    """
    from rich.console import Console

    from lychd.system.services.codex import CodexService
    from lychd.system.services.layout import LayoutService
    from lychd.system.services.privilege import PrivilegeService

    console = Console()
    console.print("[bold blue]🕯️  Beginning the Inscription (lych init)...[/]")

    try:
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

    except Exception as e:
        console.print(f"\n[bold red]✖ Ritual Failed:[/][red] {e}[/]")
        raise click.Abort from e


@click.command(name="bind", help="Transmute configs into Systemd units.")
def bind_quadlets() -> None:
    """Perform the Binding Ritual (III. The Transmutation).

    1. Loads Settings and Soulstones from the Codex.
    2. Calculates the Law of Exclusivity (Animation Domain).
    3. Generates Systemd Quadlet files (Runes) with Git versioning (System Domain).
    4. Reloads the Systemd User Daemon.
    """
    import shutil
    import subprocess

    from rich.console import Console

    from lychd.domain.animation.services.loader import AnimatorLoader
    from lychd.domain.animation.transmute import Transmuter
    from lychd.system.services.scribe import ScribeService

    console = Console()
    console.print("[bold blue]🔮 Beginning the Transmutation (lych bind)...[/]")

    try:
        # 1. Summon the Librarian (Loads & Validates Config)
        loader = AnimatorLoader()
        soulstones, _ = loader.load_all()

        # 2. Summon the Alchemist (Transmutes Soulstones into Runes)
        transmuter = Transmuter()
        runes = transmuter.transmute_all(soulstones)

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
        console.print("  [dim]You may now summon the vessel: systemctl --user start lychd[/]")

    except Exception as e:
        console.print(f"\n[bold red]✖ Ritual Failed:[/][red] {e}[/]")
        raise click.Abort from e
