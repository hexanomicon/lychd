"""Register Tether's typed intent without a filesystem-owning contributor."""

from __future__ import annotations

from lychd.extensions.context import ExtensionRegistrationContext


def register(context: ExtensionRegistrationContext) -> None:
    """Expose only the Rune; the complete host bind compiler supplies admission."""
    from lychd.domain.tether.models import TetherRune

    context.runes.add_schema(TetherRune)
