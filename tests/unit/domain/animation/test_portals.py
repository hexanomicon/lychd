"""A4: Portal synthesis, opt-in probes, factory inversion, and grant quarantine."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from pydantic import ValidationError

from lychd.config.runes import RuneConfig
from lychd.config.runes.extension import RuneConfigStore
from lychd.config.runes.loader import ConfigLoader
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.capabilities import CapabilityFamily, CapabilityPhase
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.extension import PortalStore
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import (
    AnimatorConfig,
    OpenAIPortalConfig,
    PortalConfig,
)
from lychd.domain.animation.services.adapters.contracts import PortalDefinition, RuntimeAnimator
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector
from lychd.domain.animation.services.declarations import (
    AnimatorDeclarations,
    compile_animator_declarations,
)
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger
from lychd.extensions.builtin.animator.register import build_openai_portal, probe_openai_portal
from lychd.extensions.context import ExtensionContext

_PORTAL_SCHEMAS: list[type[RuneConfig]] = [
    AnimatorConfig,
    PortalConfig,
    OpenAIPortalConfig,
]
_OPENAI_PORTAL = PortalDefinition(
    rune_schema=OpenAIPortalConfig,
    factory=build_openai_portal,
    probe=probe_openai_portal,
)


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
    adapters = RuntimeAdapterRegistry(portal_definitions=[_OPENAI_PORTAL])
    runtime = adapters.build_runtime(portal)
    assert runtime is not None
    assert adapters.build_capability_specs(runtime) == []


def test_portal_synthesizes_static_chat_spec_with_overlay() -> None:
    portal = OpenAIPortalConfig.model_validate(
        {
            "name": "openai-main",
            "generation": {"temperature": 0.5},
            "models": [
                {
                    "id": "gpt-5.2",
                    "capabilities": {
                        "supports_tools": True,
                        "modalities_in": ["text", "image"],
                    },
                    "generation": {"max_tokens": 4096},
                }
            ],
        }
    )
    adapters = RuntimeAdapterRegistry(portal_definitions=[_OPENAI_PORTAL])
    runtime = adapters.build_runtime(portal)
    assert runtime is not None
    specs = adapters.build_capability_specs(runtime)

    assert len(specs) == 1
    spec = specs[0]
    assert spec.key == "openai-main:chat:gpt-5.2"
    assert spec.family == CapabilityFamily.CHAT
    assert spec.is_dynamic is False
    assert spec.supports_tools is True
    assert "image" in spec.modalities_in
    assert spec.generation_profile.max_tokens == 4096
    assert spec.generation_profile.temperature == 0.5


def test_openai_portal_schema_rejects_alias_without_factory_support() -> None:
    with pytest.raises(ValidationError, match="provider_name"):
        OpenAIPortalConfig.model_validate(
            {
                "name": "unsupported",
                "provider_name": "not-a-provider",
            }
        )


@pytest.mark.parametrize(
    ("base_url", "message"),
    [
        ("https://user:secret@provider.test/v1", "embedded credentials"),
        ("https://provider.test/v1?region=eu", "query or fragment"),
        ("https://provider.test/v1?", "query or fragment"),
        ("https://provider.test/v1#models", "query or fragment"),
        ("https://provider.test/v1#", "query or fragment"),
        ("https://provider.test:0/v1", "port must be between"),
    ],
)
def test_portal_base_url_must_be_a_composable_endpoint_root(base_url: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        OpenAIPortalConfig.model_validate({"name": "invalid-root", "base_url": base_url})


def test_portal_base_url_allows_provider_prefix_paths() -> None:
    portal = OpenAIPortalConfig.model_validate(
        {
            "name": "prefix",
            "base_url": "https://provider.test/v1beta/openai/",
        }
    )

    assert str(portal.base_url) == "https://provider.test/v1beta/openai/"


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
        declarations=_portal_declarations(runes_dir),
        runtime_adapters=[],
        portal_definitions=[_OPENAI_PORTAL],
    )
    registry.load()  # probe=False ⇒ no live probe; respx would raise on any egress

    assert respx.calls.call_count == 0
    assert len(registry.list_capabilities()) == 1
    state = registry.list_capability_states()[0]
    assert state.phase is CapabilityPhase.UNKNOWN
    assert state.health == "unverified"


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
        declarations=_portal_declarations(runes_dir),
        runtime_adapters=[],
        portal_definitions=[_OPENAI_PORTAL],
    )
    registry.load()

    assert route.called
    state = registry.list_capability_states()[0]
    assert state.phase is CapabilityPhase.ERROR
    assert state.health == "model_missing"


@respx.mock
def test_probe_true_portal_separates_live_link_from_invalid_inventory(tmp_path: Path) -> None:
    respx.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": [{"object": "model"}]})
    )
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "portals" / "openai" / "invalid-inventory.toml",
        """
        name = "invalid-inventory"
        probe = true
        [[models]]
        id = "gpt-x"
        """,
    )
    registry = AnimatorRegistry(
        declarations=_portal_declarations(runes_dir),
        runtime_adapters=[],
        portal_definitions=[_OPENAI_PORTAL],
    )
    registry.load()

    state = registry.list_capability_states()[0]
    assert state.phase is CapabilityPhase.ERROR
    assert state.health == "inventory_invalid"
    assert "non-empty string id" in (state.reason or "")


@respx.mock
def test_probe_true_requires_the_exact_portal_probe_strategy(tmp_path: Path) -> None:
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
        declarations=_portal_declarations(runes_dir),
        runtime_adapters=[],
        portal_definitions=[
            PortalDefinition(
                rune_schema=OpenAIPortalConfig,
                factory=build_openai_portal,
            )
        ],
    )

    with pytest.raises(RuntimeError, match="has no exact probe strategy"):
        registry.load()

    assert respx.calls.call_count == 0


def test_failed_initial_probe_leaves_registry_retryable_and_unpublished(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "portals" / "openai" / "flaky.toml",
        """
        name = "flaky"
        probe = true
        [[models]]
        id = "gpt-x"
        """,
    )
    attempts = 0

    async def flaky_probe(animator: RuntimeAnimator) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            message = "probe failed once"
            raise RuntimeError(message)
        connector = animator.connector
        assert isinstance(connector, OpenAICompatibleConnector)
        connector.set_link(Link(up=True))

    registry = AnimatorRegistry(
        declarations=_portal_declarations(runes_dir),
        runtime_adapters=[],
        portal_definitions=[
            PortalDefinition(
                rune_schema=OpenAIPortalConfig,
                factory=build_openai_portal,
                probe=flaky_probe,
            )
        ],
    )

    with pytest.raises(RuntimeError, match="probe failed once"):
        registry.load()

    registry.load()

    assert attempts == 2
    assert registry.list_capability_states()[0].warm is True


def test_successful_registry_generation_cannot_be_hot_reloaded(tmp_path: Path) -> None:
    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "portals" / "openai" / "stable.toml",
        """
        name = "stable"
        [[models]]
        id = "gpt-x"
        """,
    )
    factory_calls = 0

    def counting_factory(portal: PortalConfig) -> RuntimeAnimator:
        nonlocal factory_calls
        factory_calls += 1
        return build_openai_portal(portal)

    registry = AnimatorRegistry(
        declarations=_portal_declarations(runes_dir),
        runtime_adapters=[],
        portal_definitions=[
            PortalDefinition(
                rune_schema=OpenAIPortalConfig,
                factory=counting_factory,
            )
        ],
    )
    registry.load()
    with pytest.raises(RuntimeError, match="generation is already loaded"):
        registry.load()

    assert factory_calls == 1


# --- factory inversion + store discipline ----------------------------------


def test_portal_store_is_idempotent_for_the_exact_definition() -> None:
    runes = RuneConfigStore()
    store = PortalStore(runes)
    store.add(PortalDefinition(rune_schema=OpenAIPortalConfig, factory=build_openai_portal))
    store.add(PortalDefinition(rune_schema=OpenAIPortalConfig, factory=build_openai_portal))

    assert len(store.definitions) == 1
    assert runes.rune_schemas.count(OpenAIPortalConfig) == 1


def test_portal_store_rejects_conflicting_factory_for_one_schema() -> None:
    def conflicting_factory(portal: PortalConfig) -> RuntimeAnimator:
        return build_openai_portal(portal)

    context = ExtensionContext()
    with context.provenance("one"):
        context.portals.add(PortalDefinition(rune_schema=OpenAIPortalConfig, factory=build_openai_portal))

    with (
        context.provenance("two"),
        pytest.raises(
            ValueError,
            match="Portal schema OpenAIPortalConfig from 'two' conflicts with the schema registered by 'one'",
        ),
    ):
        context.portals.add(PortalDefinition(rune_schema=OpenAIPortalConfig, factory=conflicting_factory))


def test_portal_store_rejects_cross_registrant_replay() -> None:
    context = ExtensionContext()
    with context.provenance("one"):
        context.portals.add(_OPENAI_PORTAL)
    with context.provenance("two"), pytest.raises(ValueError, match="registered by 'one'"):
        context.portals.add(_OPENAI_PORTAL)


def test_register_adds_portal_schema_exactly_once() -> None:
    from lychd.extensions.builtin.animator.register import register

    context = ExtensionContext()
    registration = context.registration_view("builtin:animator")
    register(registration)
    register(registration)  # idempotent across the per-runtime register() fan-in

    assert context.runes.rune_schemas.count(OpenAIPortalConfig) == 1


# --- mechanical hydration + dispatch quarantine -----------------------------


@pytest.mark.asyncio
async def test_portal_hydrates_but_dispatch_remains_quarantined(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": [{"id": "gpt-5.2"}]})
    )
    secrets = tmp_path / "secrets"
    secrets.mkdir(parents=True, exist_ok=True)
    (secrets / "portal_openai_main").write_text("sk-test\n", encoding="utf-8")
    monkeypatch.setenv("LYCHD_SECRET_ROOT", str(secrets))

    runes_dir = tmp_path / "runes"
    _write(
        runes_dir / "animator" / "portals" / "openai" / "main.toml",
        """
        name = "openai-main"
        probe = true
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
        declarations=_portal_declarations(runes_dir),
        runtime_adapters=[],
        portal_definitions=[_OPENAI_PORTAL],
    )
    dispatcher = Dispatcher(registry=registry, leases=LeaseLedger())

    spec = registry.get_capability("openai-main:chat:gpt-5.2")
    assert spec is not None
    assert spec.generation_profile.max_tokens == 4096
    assert spec.generation_profile.temperature == 0.5

    with pytest.raises(CapabilityUnavailable, match="portal egress admission"):
        await registry.issue_grant("openai-main:chat:gpt-5.2", holder="test:mechanics")

    with pytest.raises(CapabilityUnavailable, match="portal egress admission"):
        async with dispatcher.lease_grant(family="chat", model_name="gpt-5.2", run_id="r1"):
            pytest.fail("portal dispatch must remain quarantined")
