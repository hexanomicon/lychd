"""Configuration selects one exact registered Bridge revision without resolving runtimes."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from lychd.agents.workflows import BRIDGE_CHAT, BRIDGE_CHAT_ARCHIVE, BRIDGE_CHAT_BOUND, builtin_workflow_registry
from lychd.config.settings import BridgeCastingSettings, Settings, SettingsSnapshot, WeaverSettings
from lychd.domain.archive import ArchiveProfile, ArchiveSubject
from lychd.domain.cortex.bridge_preference import BridgePreference, BridgePreferenceRoute
from tests.webcrawler_fixtures import webcrawler_profile


def test_absent_bridge_selection_preserves_legacy_configuration() -> None:
    assert WeaverSettings().bridge is None


def _preference() -> BridgePreference:
    return BridgePreference(
        schema_version=1,
        routes=(
            BridgePreferenceRoute(capability_key="desk:chat:answer", weight=100),
            BridgePreferenceRoute(capability_key="backup:chat:answer", weight=1),
        ),
    )


def test_preference_is_opt_in_revision_two_and_snapshot_retains_typed_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "preference.toml"
    config_path.write_text(
        '[weaver.bridge]\nrevision="2"\n[weaver.bridge.preference]\nschema_version=1\n'
        '[[weaver.bridge.preference.routes]]\ncapability_key="desk:chat:answer"\nweight=100\n'
        '[[weaver.bridge.preference.routes]]\ncapability_key="backup:chat:answer"\nweight=1\n'
    )
    monkeypatch.setattr("lychd.config.settings.root.PATH_LYCHD_TOML", config_path)
    settings = Settings()
    assert settings.weaver.bridge is not None
    assert settings.weaver.bridge.capability_key is None
    assert settings.weaver.bridge.preference == _preference()
    assert builtin_workflow_registry(weaver=settings.weaver).default is BRIDGE_CHAT_BOUND
    snapshot = SettingsSnapshot.capture(settings)
    settings.weaver.bridge.preference = _preference().model_copy(update={"schema_version": 99})
    restored = snapshot.materialize()
    assert restored.weaver.bridge is not None
    assert restored.weaver.bridge.preference == _preference()


@pytest.mark.parametrize("revision", ["2", "3", "4"])
def test_preference_never_combines_with_exact_mode_or_other_revisions(revision: str) -> None:
    with pytest.raises(ValidationError):
        BridgeCastingSettings.model_validate(
            {"revision": revision, "capability_key": "desk:chat:answer", "preference": _preference()}
        )


@pytest.mark.parametrize(
    "patch",
    [
        {"schema_version": True},
        {"schema_version": "1"},
        {"schema_version": 2},
        {"schema_version": None},
        {"routes": [{"capability_key": "a:chat:x", "weight": 1}]},
        {"routes": [{"capability_key": "a:chat:x", "weight": 1}] * 3},
        {"routes": [{"capability_key": "a:chat:x", "weight": 1}] * 2},
        {"routes": [{"capability_key": "a:chat:x", "weight": 0}, {"capability_key": "b:chat:x", "weight": 0}]},
        {"routes": [{"capability_key": "x" * 513, "weight": 1}, {"capability_key": "b:chat:x", "weight": 0}]},
        {"routes": [{"capability_key": " a:chat:x", "weight": 1}, {"capability_key": "b:chat:x", "weight": 0}]},
    ],
)
def test_preference_refuses_unversioned_or_unbounded_policy(patch: dict[str, Any]) -> None:
    payload = _preference().model_dump() | patch
    with pytest.raises(ValidationError):
        BridgePreference.model_validate(payload)


def test_page_config_accepts_old_spelling_and_emits_only_webcrawler() -> None:
    profile = webcrawler_profile()
    raw = {"revision": "4", "capability_key": "local:chat:answer", "scout": profile}
    settings = BridgeCastingSettings.model_validate(raw)
    assert settings.webcrawler == profile
    assert "webcrawler" in settings.model_dump()
    assert "scout" not in settings.model_dump()
    with pytest.raises(ValidationError, match="Extra inputs"):
        BridgeCastingSettings.model_validate(raw | {"webcrawler": profile})


def test_webcrawler_profile_requires_revision_four_and_keeps_older_revisions_retained() -> None:
    profile = webcrawler_profile()
    with pytest.raises(ValidationError, match="requires webcrawler"):
        BridgeCastingSettings(revision="4", capability_key="local:chat:answer")
    with pytest.raises(ValidationError, match="other revisions do not accept"):
        BridgeCastingSettings(revision="2", capability_key="local:chat:answer", webcrawler=profile)
    registry = builtin_workflow_registry(
        weaver=WeaverSettings(
            bridge=BridgeCastingSettings(revision="4", capability_key="local:chat:answer", webcrawler=profile)
        )
    )
    assert registry.default.manifest.revision == "4"
    assert registry.get_revision("bridge_chat", "3") is BRIDGE_CHAT_ARCHIVE
    assert registry.get_revision("bridge_chat", "2") is BRIDGE_CHAT_BOUND
    assert registry.get_revision("bridge_chat", "1") is BRIDGE_CHAT
    assert (
        profile.resolver_custody_digest
        != profile.model_copy(
            update={"resolver_custody_statement": "A changed custody assertion"}
        ).resolver_custody_digest
    )


def test_archive_selection_requires_the_exact_revision_and_retains_legacy_routes() -> None:
    profile = ArchiveProfile(
        namespace_id=UUID("9d340d97-7a12-47ed-af2b-c4742ed690f6"),
        owner_subject=ArchiveSubject(identity="local-notes-owner"),
        policy_revision="local-notes-policy@1",
    )
    with pytest.raises(ValidationError, match="requires archive"):
        BridgeCastingSettings(revision="3", capability_key="desk:chat:assistant")
    with pytest.raises(ValidationError, match="revision 2 does not accept"):
        BridgeCastingSettings(revision="2", capability_key="desk:chat:assistant", archive=profile)
    selection = BridgeCastingSettings(revision="3", capability_key="desk:chat:assistant", archive=profile)
    settings = Settings(weaver=WeaverSettings(bridge=selection))
    snapshot = SettingsSnapshot.capture(settings)
    selection.archive = profile.model_copy(update={"policy_revision": "changed@2"})
    restored = snapshot.materialize()
    assert restored.weaver.bridge is not None
    assert restored.weaver.bridge.archive == profile
    registry = builtin_workflow_registry(weaver=restored.weaver)
    assert registry.default is BRIDGE_CHAT_ARCHIVE
    assert registry.get_revision("bridge_chat", "1") is BRIDGE_CHAT
    assert registry.get_revision("bridge_chat", "2") is BRIDGE_CHAT_BOUND


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
