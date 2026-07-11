"""The configuration package exposes its stable import surface."""

from lychd.config.settings import (
    ExtensionSettings,
    ServerSettings,
    Settings,
    SwitchingSettings,
    get_settings,
)


def test_settings_package_exposes_root_and_section_models() -> None:
    """Callers import configuration types from one public doorway."""
    settings = Settings()

    assert isinstance(settings.server, ServerSettings)
    assert isinstance(settings.orchestration.switching, SwitchingSettings)
    assert isinstance(settings.extensions, ExtensionSettings)
    assert callable(get_settings)
