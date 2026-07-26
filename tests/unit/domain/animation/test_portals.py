"""A4: portals become real — synthesis, opt-in probe, factory inversion, grant."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from pydantic_ai.models.openai import OpenAIChatModel

from lychd.config.runes import ConfigLoader, RuneConfig
from lychd.config.runes.extension import RuneConfigStore
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.capabilities import CapabilityFamily
from lychd.domain.animation.extension import PortalStore
from lychd.domain.animation.schemas import (
    AnimatorConfig,
    OpenAIPortalConfig,
    PortalConfig,
)
from lychd.domain.animation.services.adapters.contracts import PortalDefinition
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.declarations import (
    AnimatorDeclarations,
    compile_animator_declarations,
)
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger
from lychd.extensions.builtin.animator.register import build_openai_portal
from lychd.extensions.context import ExtensionContext
from lychd.extensions.host import AssembledExtensions

_PORTAL_SCHEMAS: list[type[RuneConfig]] = [
    AnimatorConfig,
    PortalConfig,
    OpenAIPortalConfig,
]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{content.strip()}\n", encoding="utf-8")


def _portal_declarations(runes_dir: Path) -> AnimatorDeclarations:
    return compile_animator_declarations(
        settings=get_settings(),
        runes=RuneRegistry(ConfigLoader(runes_dir).load_all(_PORTAL_SCHEMAS)),
        core_reserved_ports={},
    )


# --- synthesis --------------------------------------------------------------


def test_portal_zero_models_yields_zero_specs() -> None:
    portal = OpenAIPortalConfig.model_validate({"name": "empty"})
    adapters = RuntimeAdapterRegistry(portal_factories=[build_openai_portal])
    runtime = adapters.build_runtime(portal)
    assert adapters.build_capability_specs(portal, runtime) == []


def test_portal_synthesizes_static_chat_spec_with_overlay() -> None:
    portal = OpenAIPortalConfig.model_validate(
        {
            "name": "openai-main",
            "generation": {"temperature": 0.5},
            "models": [
                {
                    "id": "gpt-5.2",
                    "capabilities": {"supports_tools": True, "modalities_in": ["text", "image"]},
                    "generation": {"max_tokens": 4096},
                }
            ],
        }
    )
    adapters = RuntimeAdapterRegistry(portal_factories=[build_openai_portal])
    specs = adapters.build_capability_specs(portal, adapters.build_runtime(portal))

    assert len(specs) == 1
    spec = specs[0]
    assert spec.key == "openai-main:chat:gpt-5.2"
    assert spec.family == CapabilityFamily.CHAT
    assert spec.is_dynamic is False
    assert spec.supports_tools is True
    assert "image" in spec.modalities_in
    assert spec.generation_profile.max_tokens == 4096
    assert spec.generation_profile.temperature == 0.5


# --- opt-in probe (respx: no surprise egress) ------------------------------


@respx.mock
def test_probe_false_portal_performs_no_http(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "portals" / "openai" / "quiet.toml",
        """
        name = "quiet"
        [[models]]
        id = "gpt-x"
        """,
    )
    registry = AnimatorRegistry(
        settings=get_settings(),
        declarations=_portal_declarations(runes_dir),
        runtime_adapters=[],
        portal_factories=[build_openai_portal],
    )
    registry.load()  # probe=False ⇒ no live probe; respx would raise on any egress

    assert respx.calls.call_count == 0
    assert len(registry.list_capabilities()) == 1


@respx.mock
def test_probe_true_portal_exercises_live_probe(tmp_path: Path) -> None:
    route = respx.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": []})
    )
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "portals" / "openai" / "live.toml",
        """
        name = "live"
        probe = true
        [[models]]
        id = "gpt-x"
        """,
    )
    registry = AnimatorRegistry(
        settings=get_settings(),
        declarations=_portal_declarations(runes_dir),
        runtime_adapters=[],
        portal_factories=[build_openai_portal],
    )
    registry.load()

    assert route.called


# --- factory inversion + store discipline ----------------------------------


def test_portal_store_dedups_by_schema_and_factory_type() -> None:
    runes = RuneConfigStore()
    store = PortalStore(runes)
    store.add(PortalDefinition(rune_schema=OpenAIPortalConfig, factory=build_openai_portal))
    store.add(PortalDefinition(rune_schema=OpenAIPortalConfig, factory=build_openai_portal))

    assert len(store.definitions) == 1
    assert runes.rune_schemas.count(OpenAIPortalConfig) == 1


def test_register_adds_portal_schema_exactly_once() -> None:
    from lychd.extensions.builtin.animator.register import register

    context = ExtensionContext()
    register(context)
    register(context)  # idempotent across the per-runtime register() fan-in

    assert context.runes.rune_schemas.count(OpenAIPortalConfig) == 1


def test_assembled_extensions_surface_builtin_portal_factory() -> None:
    context = ExtensionContext()
    from lychd.extensions.builtin.animator.register import register

    register(context)
    assembled = AssembledExtensions(context=context, active_ids=())

    assert build_openai_portal in assembled.portal_factories


# --- end-to-end grant (A4.7) ------------------------------------------------


@pytest.mark.asyncio
async def test_portal_grant_hydrates_openai_model_with_overlay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir(parents=True, exist_ok=True)
    (secrets / "portal_openai_main").write_text("sk-test\n", encoding="utf-8")
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(secrets))

    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "portals" / "openai" / "main.toml",
        """
        name = "openai-main"
        api_key_secret_name = "portal_openai_main"

        [generation]
        temperature = 0.5

        [[models]]
        id = "gpt-5.2"
        [models.capabilities]
        supports_tools = true
        modalities_in = ["text", "image"]
        [models.generation]
        max_tokens = 4096
        """,
    )
    registry = AnimatorRegistry(
        settings=get_settings(),
        declarations=_portal_declarations(runes_dir),
        runtime_adapters=[],
        portal_factories=[build_openai_portal],
    )
    dispatcher = Dispatcher(registry=registry, leases=LeaseLedger())

    async with dispatcher.lease_grant(family="chat", model_name="gpt-5.2", run_id="r1") as grant:
        assert isinstance(grant.model, OpenAIChatModel)
        assert grant.generation.max_tokens == 4096
        assert grant.generation.temperature == 0.5
        settings = grant.model_settings()
        assert settings is not None
        assert settings.get("max_tokens") == 4096
