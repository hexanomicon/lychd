from lychd.extensions.context import ExtensionRegistrationContext


def register(context: ExtensionRegistrationContext) -> None:
    """Register the closed Tether Rune and its intent contributor."""
    from lychd.extensions.builtin.tether.config import TetherSettings
    from lychd.extensions.builtin.tether.contributor import TetherQuadletContributor

    context.runes.add_schema(TetherSettings)
    context.transmutation.add_contributor(TetherQuadletContributor())
