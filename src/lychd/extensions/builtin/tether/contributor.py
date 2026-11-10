"""The built-in declares intent; only the attributed compiler grants its body."""

from lychd.domain.animation.transmute import QuadletContribution, TransmutationContext
from lychd.extensions.builtin.tether.config import TetherSettings


class TetherQuadletContributor:
    """Submit the sole static envelope without raw units, capabilities or commands."""

    def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
        rune = ctx.runes.one_or_none(TetherSettings)
        if rune is None:
            return QuadletContribution()
        return QuadletContribution(tether=rune.envelope(altar_port=ctx.settings.server.port))
