"""Opt-in finite observation selection; assembly tests never construct a DB connection."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from lychd.agents.router import Intent
from lychd.agents.workflows import BRIDGE_CHAT, OBSERVE_MARKET, builtin_workflow_registry, resolve_pinned_workflow
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings import (
    BridgeCastingSettings,
    ScavengerCastingSettings,
    Settings,
    SettingsSnapshot,
    WeaverSettings,
)
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.webcrawler.profile import WebcrawlerWorkflowError
from lychd.interface.web.altar_services import build_altar_services
from tests.runtime_guards import InertSoftActivationGuard
from tests.unit.domain.cortex.test_webcrawler_feed_admission import Queue
from tests.webcrawler_feed_fixtures import scenario
from tests.webcrawler_fixtures import webcrawler_profile

pytestmark = pytest.mark.asyncio


async def test_feed_config_accepts_old_spelling_and_emits_only_webcrawler() -> None:
    profile = (await scenario()).binding.profile
    raw = {"revision": "3", "scout": profile}
    settings = ScavengerCastingSettings.model_validate(raw)
    assert settings.webcrawler == profile
    assert "webcrawler" in settings.model_dump()
    assert "scout" not in settings.model_dump()
    with pytest.raises(ValidationError, match="Extra inputs"):
        ScavengerCastingSettings.model_validate(raw | {"webcrawler": profile})


async def test_omission_disables_new_feed_route_but_retains_exact_pattern_resolution() -> None:
    weaver = WeaverSettings()
    assert weaver.scavenger is None
    registry = builtin_workflow_registry(weaver=weaver)
    assert registry.default is BRIDGE_CHAT
    assert registry.is_active(OBSERVE_MARKET.name, "2") is False
    assert (
        resolve_pinned_workflow(
            registry, workflow_name=OBSERVE_MARKET.name, snapshot=OBSERVE_MARKET.manifest.snapshot()
        )
        is OBSERVE_MARKET
    )


async def test_explicit_feed_selection_is_separate_from_ordinary_bridge_and_snapshot_isolated() -> None:
    s = await scenario()
    selection = ScavengerCastingSettings(revision="3", webcrawler=s.binding.profile)
    weaver = WeaverSettings(
        scavenger=selection, bridge=BridgeCastingSettings(revision="2", capability_key="ordinary:chat:separate")
    )
    snapshot = SettingsSnapshot.capture(Settings(weaver=weaver))
    selection.webcrawler = s.binding.profile.model_copy(update={"binding_id": "changed-generation"})
    restored = snapshot.materialize()
    assert restored.weaver.scavenger is not None
    assert restored.weaver.scavenger.webcrawler == s.binding.profile
    registry = builtin_workflow_registry(weaver=restored.weaver)
    assert registry.default.manifest.revision == "2"
    assert registry.is_active(OBSERVE_MARKET.name, "2")
    assert registry.route(Intent(session_id="session", prompt="opaque", source="scavenger")) is OBSERVE_MARKET
    assert registry.get_revision("bridge_chat", "1") is BRIDGE_CHAT


@pytest.mark.parametrize(
    "patch",
    [
        {"revision": "2"},
        {"revision": 3},
        {"webcrawler": None},
        {"capability_key": "dummy"},
        {"source_url": "https://example.com/feed"},
        {"fallback": "other"},
        {"implementation": "custom"},
    ],
)
async def test_feed_selection_refuses_implicit_versions_model_demand_and_unowned_policy(patch: dict[str, Any]) -> None:
    s = await scenario()
    with pytest.raises(ValidationError):
        ScavengerCastingSettings.model_validate({"revision": "3", "webcrawler": s.binding.profile} | patch)


async def test_first_profile_cannot_coexist_with_page_webcrawler() -> None:
    s = await scenario()
    with pytest.raises(ValidationError, match="one active Webcrawler binding"):
        WeaverSettings(
            scavenger=ScavengerCastingSettings(revision="3", webcrawler=s.binding.profile),
            bridge=BridgeCastingSettings(
                revision="4", capability_key="local:chat:page", webcrawler=webcrawler_profile()
            ),
        )


@pytest.mark.parametrize("persistence", ["memory", "postgres"])
async def test_missing_native_persistence_or_credential_owner_refuses_before_any_factory(
    monkeypatch: pytest.MonkeyPatch,
    persistence: str,
) -> None:
    s = await scenario()
    forbidden = Mock(side_effect=AssertionError("Admission must refuse before DB/service construction."))
    monkeypatch.setattr("lychd.interface.web.altar_services._build_run_ledger", forbidden)
    with pytest.raises(ValueError, match="Scavenger requires PostgreSQL"):
        build_altar_services(
            queues={},
            runes=RuneRegistry(()),
            profile=persistence,
            settings=Settings(
                weaver=WeaverSettings(scavenger=ScavengerCastingSettings(revision="3", webcrawler=s.binding.profile))
            ),
            operator_access=s.access if persistence == "memory" else None,
            soft_activation_guard=InertSoftActivationGuard(),
        )
    forbidden.assert_not_called()


async def test_explicit_registry_cannot_override_configured_scavenger() -> None:
    s = await scenario()
    with pytest.raises(ValueError, match=r"workflow registry injection.*\[weaver.scavenger\]"):
        build_altar_services(
            queues={},
            runes=RuneRegistry(()),
            profile="postgres",
            workflows=builtin_workflow_registry(),
            settings=Settings(
                weaver=WeaverSettings(scavenger=ScavengerCastingSettings(revision="3", webcrawler=s.binding.profile))
            ),
            operator_access=s.access,
            soft_activation_guard=InertSoftActivationGuard(),
        )


async def test_selected_assembly_shares_one_actual_webcrawler_and_app_without_readiness_or_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = await scenario()
    factory = Mock(side_effect=AssertionError("Constructing selected services must not touch the database."))
    monkeypatch.setattr("lychd.db.engine.get_session_factory", lambda: factory)
    readiness = Mock(side_effect=AssertionError("Model-free assembly must not probe model readiness."))
    monkeypatch.setattr(AnimatorRegistry, "load", readiness)
    queue = Queue()
    services = build_altar_services(
        queues={"runs": queue, "rites": queue},
        runes=RuneRegistry(()),
        profile="postgres",
        settings=Settings(
            weaver=WeaverSettings(scavenger=ScavengerCastingSettings(revision="3", webcrawler=s.binding.profile))
        ),
        operator_access=s.access,
        soft_activation_guard=InertSoftActivationGuard(),
    )
    try:
        assert services.scavenger is not None
        assert services.webcrawler is not None
        assert services.feed_admission is not None
        assert services.webcrawler_admission is None
        assert services.substrate.webcrawler is None
        assert services.substrate.feed_webcrawler is services.webcrawler
        assert services.substrate.scavenger is services.scavenger
        assert services.substrate.effects is services.webcrawler
        assert services.run_engine.effects is services.webcrawler
        assert services.run_engine.feed_webcrawler == s.binding.profile
        assert services.run_engine.feed_webcrawler_admission is services.feed_admission
        assert services.run_engine.workflows is services.workflows
        assert services.substrate.workflows is services.workflows
        assert services.orchestrator.worker_broker.claim_gate.is_set()
        assert services.workflows.is_active(OBSERVE_MARKET.name, "2")
        readiness.assert_not_called()
        factory.assert_not_called()
    finally:
        await services.aclose()
    factory.assert_not_called()


async def test_disabled_scavenger_cannot_fall_through_to_chat_admission() -> None:
    ledger, bus, queue = InMemoryRunLedger(), InProcessEventBus(), Queue()
    engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter({"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": queue},
    )
    create = AsyncMock(wraps=ledger.create)
    ledger.create = create
    try:
        with pytest.raises(WebcrawlerWorkflowError):
            await engine.submit(Intent(session_id="unused", prompt="opaque", source="scavenger"))
        create.assert_not_awaited()
        assert not queue.enqueued
    finally:
        await bus.aclose()
