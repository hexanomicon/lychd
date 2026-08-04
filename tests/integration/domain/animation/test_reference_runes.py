"""A5: the reference rune fixtures resolve to exactly the five canonical keys."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lychd.config.runes import ConfigLoader, RuneConfig
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.capabilities import CapabilityFamily
from lychd.domain.animation.schemas import (
    AnimatorConfig,
    GenericSoulstoneConfig,
    GoogleGeminiPortalConfig,
    OpenAIPortalConfig,
    PortalConfig,
    SoulstoneConfig,
)
from lychd.domain.animation.services.adapters.contracts import PortalDefinition
from lychd.domain.animation.services.declarations import (
    compile_animator_declarations,
)
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.extensions.builtin.animator import (
    LlamaCppSoulstoneConfig,
    SglangSoulstoneConfig,
    VllmSoulstoneConfig,
)
from lychd.extensions.builtin.animator.register import build_openai_portal
from lychd.extensions.builtin.animator.runtimes import (
    LlamaCppRuntimeAdapter,
    SglangRuntimeAdapter,
    VllmRuntimeAdapter,
)
from lychd.lib.http import HttpJsonError

_REF_RUNES = Path(__file__).resolve().parents[3] / "fixtures" / "runes"

_SCHEMAS: list[type[RuneConfig]] = [
    AnimatorConfig,
    SoulstoneConfig,
    PortalConfig,
    GenericSoulstoneConfig,
    LlamaCppSoulstoneConfig,
    VllmSoulstoneConfig,
    SglangSoulstoneConfig,
    OpenAIPortalConfig,
    GoogleGeminiPortalConfig,
]
_PORTAL_DEFINITIONS = (
    PortalDefinition(rune_schema=OpenAIPortalConfig, factory=build_openai_portal),
    PortalDefinition(rune_schema=GoogleGeminiPortalConfig, factory=build_openai_portal),
)


@pytest.fixture(autouse=True)
def isolate_reference_runes_from_live_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep declaration-contract tests independent of services on localhost."""

    async def unavailable(*_args: Any, **_kwargs: Any) -> dict[str, object]:
        message = "reference probe is intentionally offline"
        raise HttpJsonError(message, transport=True)

    monkeypatch.setattr(
        "lychd.extensions.builtin.animator.llamacpp.control_plane.request_json",
        unavailable,
    )
    monkeypatch.setattr(
        "lychd.domain.animation.services.adapters.runtimes.shared.request_json",
        unavailable,
    )


def _reference_registry() -> AnimatorRegistry:
    settings = get_settings()
    return AnimatorRegistry(
        declarations=compile_animator_declarations(
            settings=settings,
            runes=RuneRegistry(ConfigLoader(_REF_RUNES).load_all(_SCHEMAS)),
            core_reserved_ports={},
        ),
        runtime_adapters=[LlamaCppRuntimeAdapter(), VllmRuntimeAdapter(), SglangRuntimeAdapter()],
        portal_definitions=_PORTAL_DEFINITIONS,
    )


def test_reference_runes_resolve_exactly_the_five_keys() -> None:
    specs = {spec.key: spec for spec in _reference_registry().list_capabilities()}

    assert set(specs) == {
        "atelier:chat:qwen3-vl-8b",
        "atelier:embedding:bge-m3",
        "atelier:vision:the-eye",
        "glm:chat:GLM-4.6",
        "openai-main:chat:gpt-5.2",
    }

    # is_dynamic per key: the atelier router is dynamic; vLLM + portal are not.
    assert specs["atelier:chat:qwen3-vl-8b"].is_dynamic is True
    assert specs["atelier:embedding:bge-m3"].is_dynamic is True
    assert specs["atelier:vision:the-eye"].is_dynamic is True
    assert specs["glm:chat:GLM-4.6"].is_dynamic is False
    assert specs["openai-main:chat:gpt-5.2"].is_dynamic is False


def test_reference_runes_per_key_families_and_modalities() -> None:
    specs = {spec.key: spec for spec in _reference_registry().list_capabilities()}

    # The multimodal chat model stays CHAT (image is admission only, never VISION).
    chat = specs["atelier:chat:qwen3-vl-8b"]
    assert chat.family == CapabilityFamily.CHAT
    assert "image" in chat.modalities_in

    assert specs["atelier:embedding:bge-m3"].family == CapabilityFamily.EMBEDDING
    # The Eye is VISION only because the rune declares it explicitly.
    assert specs["atelier:vision:the-eye"].family == CapabilityFamily.VISION

    portal = specs["openai-main:chat:gpt-5.2"]
    assert portal.family == CapabilityFamily.CHAT
    assert portal.supports_tools is True
    assert "image" in portal.modalities_in
