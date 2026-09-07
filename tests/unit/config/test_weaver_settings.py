"""Configuration selects one exact registered Bridge revision without resolving runtimes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from lychd.config.settings import BridgeCastingSettings, Settings, SettingsSnapshot, WeaverSettings


def test_absent_bridge_selection_preserves_legacy_configuration() -> None:
    assert WeaverSettings().bridge is None


@pytest.mark.parametrize(
    "selection",
    [
        {},
        {"capability_key": "desk:chat:assistant"},
        {"revision": "2"},
        {"revision": "1", "capability_key": "desk:chat:assistant"},
        {"revision": 2, "capability_key": "desk:chat:assistant"},
        {"revision": "latest", "capability_key": "desk:chat:assistant"},
        {"revision": "2", "capability_key": ""},
        {"revision": "2", "capability_key": "  "},
        {"revision": "2", "capability_key": " desk:chat:assistant"},
        {"revision": "2", "capability_key": "desk:chat:assistant\n"},
        {"revision": "2", "capability_key": "desk:chat:assistant", "model_name": "assistant"},
        {"revision": "2", "capability_key": "desk:chat:assistant", "fallback": "other:chat:assistant"},
        {"revision": "2", "capability_key": "desk:chat:assistant", "implementation": "custom.workflow"},
    ],
)
def test_bridge_casting_refuses_implicit_versions_empty_keys_and_undeclared_policy(selection: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        BridgeCastingSettings.model_validate(selection)


def test_weaver_refuses_unimplemented_application_selection() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        WeaverSettings.model_validate({"application": "custom"})


def test_bridge_selection_obeys_settings_precedence_and_snapshot_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "lychd.toml"
    config_path.write_text('[weaver.bridge]\nrevision = "2"\ncapability_key = "toml:chat:assistant"\n')
    monkeypatch.setattr("lychd.config.settings.root.PATH_LYCHD_TOML", config_path)

    from_toml = Settings()
    assert from_toml.weaver.bridge == BridgeCastingSettings(revision="2", capability_key="toml:chat:assistant")

    monkeypatch.setenv("WEAVER__BRIDGE__CAPABILITY_KEY", "environment:chat:assistant")
    from_environment = Settings()
    assert from_environment.weaver.bridge is not None
    assert from_environment.weaver.bridge.capability_key == "environment:chat:assistant"

    explicit = Settings(
        weaver=WeaverSettings(bridge=BridgeCastingSettings(revision="2", capability_key="explicit:chat:assistant"))
    )
    snapshot = SettingsSnapshot.capture(explicit)
    assert explicit.weaver.bridge is not None
    explicit.weaver.bridge.capability_key = "mutated:chat:assistant"
    monkeypatch.setenv("WEAVER__BRIDGE__CAPABILITY_KEY", "changed:chat:assistant")
    restored = snapshot.materialize()
    assert restored.weaver.bridge is not None
    assert restored.weaver.bridge.capability_key == "explicit:chat:assistant"
