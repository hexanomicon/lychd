"""Configured routing retains exact legacy and configured execution revisions."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

import pytest

from lychd.agents.router import Intent
from lychd.agents.workflows import (
    BRIDGE_CHAT,
    BRIDGE_CHAT_BOUND,
    DELEGATED_RITE,
    builtin_workflow_registry,
    resolve_pinned_workflow,
)
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings import BridgeCastingSettings, Settings, WeaverSettings
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.engine import RunQueue
from lychd.interface.web.altar_services import build_altar_services


def _weaver() -> WeaverSettings:
    return WeaverSettings(bridge=BridgeCastingSettings(revision="2", capability_key="desk:chat:assistant"))


def test_configured_bridge_routes_new_runs_and_retains_v1() -> None:
    registry = builtin_workflow_registry(weaver=_weaver())

    assert registry.route(Intent(session_id="session", prompt="hello")) is BRIDGE_CHAT_BOUND
    assert registry.route(Intent(session_id="session", prompt="/delegate inspect")) is DELEGATED_RITE
    assert registry.is_active("bridge_chat", "1") is False
    assert registry.is_active("bridge_chat", "2") is True
    assert registry.is_default("bridge_chat", "2") is True
    assert (
        resolve_pinned_workflow(registry, workflow_name="bridge_chat", snapshot=BRIDGE_CHAT.manifest.snapshot())
        is BRIDGE_CHAT
    )


def test_disabling_configuration_preserves_previously_admitted_v2() -> None:
    registry = builtin_workflow_registry()

    assert registry.default is BRIDGE_CHAT
    assert registry.is_active("bridge_chat", "2") is False
    assert (
        resolve_pinned_workflow(registry, workflow_name="bridge_chat", snapshot=BRIDGE_CHAT_BOUND.manifest.snapshot())
        is BRIDGE_CHAT_BOUND
    )


def test_explicit_registry_cannot_silently_override_configured_bridge() -> None:
    with pytest.raises(ValueError, match=r"workflow registry injection.*\[weaver.bridge\]"):
        build_altar_services(
            queues={},
            runes=RuneRegistry(()),
            runtime_adapters=(),
            workflows=builtin_workflow_registry(),
            settings=Settings(weaver=_weaver()),
            profile="memory",
        )


@pytest.mark.asyncio
async def test_assembly_shares_selected_registry_without_probing_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_load(_registry: AnimatorRegistry) -> None:
        pytest.fail("Selecting a Bridge revision must not start runtime readiness probes.")

    monkeypatch.setattr(AnimatorRegistry, "load", reject_load)
    queue = cast("RunQueue", MagicMock(spec=RunQueue))
    services = build_altar_services(
        queues={"runs": queue, "rites": queue},
        runes=RuneRegistry(()),
        runtime_adapters=(),
        settings=Settings(weaver=_weaver()),
        profile="memory",
    )
    try:
        assert services.workflows.default is BRIDGE_CHAT_BOUND
        assert services.run_engine.workflows is services.workflows
        assert services.substrate.workflows is services.workflows
    finally:
        await services.aclose()
