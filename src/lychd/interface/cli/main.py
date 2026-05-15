import click
from pathlib import Path
from lychd.domain.codex.service import CodexService
from lychd.domain.infrastructure.service import InfrastructureService

@click.group()
def cli() -> None:
    """
    The Hand of LychD.
    Sovereign daemon for agentic orchestration.
    """
    pass

@cli.command()
@click.option("--crypt-path", type=click.Path(path_type=Path), help="Path to the extensions directory.")
@click.option("--runes-dir", type=click.Path(path_type=Path), help="Path to the runes config directory.")
def init(crypt_path: Path | None, runes_dir: Path | None) -> None:
    """
    Inscribe the Codex. 
    Scans the Crypt, discovers schemas, and writes TOML templates.
    """
    click.echo("Summoning the CryptMachinery...")
    CodexService.inscribe(crypt_path=crypt_path, runes_dir=runes_dir)
    click.secho("Codex inscribed successfully.", fg="green")

@cli.command()
@click.option("--runes-dir", type=click.Path(path_type=Path), help="Path to the runes config directory.")
@click.option("--units-dir", type=click.Path(path_type=Path), help="Path to the systemd units directory.")
def bind(runes_dir: Path | None, units_dir: Path | None) -> None:
    """
    Transmute the Codex into immutable kernel constraints.
    Generates Systemd Quadlet files with strict Conflicts= directives.
    """
    click.echo("Forging physical constraints...")
    InfrastructureService.transmute(runes_dir=runes_dir, units_dir=units_dir)
    click.secho("Quadlets bound. Physical reality aligned.", fg="green")

if __name__ == "__main__":
    cli()
