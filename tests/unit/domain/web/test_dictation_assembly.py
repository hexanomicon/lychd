"""Physical dictation configuration requires durable custody before assembly."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from lychd.config.settings.root import Settings, SettingsSnapshot
from lychd.config.settings.server import DatabaseSettings, ServerSettings, WebSettings
from lychd.interface.web.altar_services import (
    _build_dictation_services,  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
    build_altar_services,
)
from tests.unit.domain.test_dictation_service import profile

if TYPE_CHECKING:
    from lychd.config.runes.registry import RuneRegistry


def test_settings_snapshot_rejects_physical_dictation_with_memory() -> None:
    payload = json.dumps(
        {
            "server": {
                "database": {"profile": "memory"},
                "web": {
                    "dictation": profile().model_dump(mode="json"),
                },
            }
        }
    )
    with pytest.raises(ValueError, match="Configured dictation requires PostgreSQL"):
        SettingsSnapshot(payload=payload).materialize()


def test_configured_profile_accepts_settings_arrays_and_survives_snapshot_round_trip() -> None:
    pinned = profile()
    payload = json.dumps(
        {"server": {"database": {"profile": "postgres"}, "web": {"dictation": pinned.model_dump(mode="json")}}}
    )
    settings = SettingsSnapshot(payload=payload).materialize()
    assert settings.server.web.dictation == pinned
    restored = SettingsSnapshot.capture(settings).materialize()
    assert restored.server.web.dictation == pinned
    assert restored.server.web.dictation is not settings.server.web.dictation


def test_profile_override_refuses_before_service_construction() -> None:
    settings = Settings.model_construct(server=ServerSettings(web=WebSettings(dictation=profile())))
    # Invalid downstream inputs ensure rejection precedes queue, registry or DB construction.
    with pytest.raises(ValueError, match="Configured dictation requires PostgreSQL"):
        build_altar_services(queues={}, runes=cast("RuneRegistry", object()), settings=settings, profile="memory")


def test_direct_factory_also_refuses_memory_physical_binding() -> None:
    settings = Settings.model_construct(server=ServerSettings(web=WebSettings(dictation=profile())))
    with pytest.raises(ValueError, match="Configured dictation requires PostgreSQL"):
        _build_dictation_services("memory", settings)


def test_memory_without_binding_stays_unavailable_and_shares_attempt_store() -> None:
    settings = Settings.model_construct(server=ServerSettings(database=DatabaseSettings(profile="memory")))
    dictation, lexicon = _build_dictation_services("memory", settings)
    assert dictation.discovery().status == "unavailable"
    assert dictation.transcriber is None
    assert lexicon.attempts is dictation.store
