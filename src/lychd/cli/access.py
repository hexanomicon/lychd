"""Explicit local credential display, separate from ordinary status and logs."""

from __future__ import annotations

import click


@click.command(name="access", help="Display the local Altar address and operator login credential.")
def access() -> None:
    """Reveal the password only for this explicit host-operator command."""
    from lychd.system.services.local_access import load_local_access

    try:
        details = load_local_access()
    except ValueError:
        # Settings/secret failures can contain sensitive validation input. The
        # explicit success path is the only path allowed to reveal a credential.
        msg = "Local access is unavailable. Run as the ordinary operator with a bound installation."
        raise click.ClickException(msg) from None
    click.echo(f"Altar: {details.url}")
    click.echo(f"Username: {details.username}")
    click.echo(f"Password: {details.password.get_secret_value()}")
