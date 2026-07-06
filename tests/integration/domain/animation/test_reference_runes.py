"""A5: the reference rune fixtures resolve to exactly the five canonical keys."""

from __future__ import annotations

from pathlib import Path

from lychd.domain.animation.capabilities import CapabilityFamily, CapabilityLifecycle
from lychd.domain.animation.schemas import (
    AnimatorConfig,
    GenericSoulstoneConfig,
    GoogleGeminiPortalConfig,
    OpenAIPortalConfig,
    PortalConfig,
    SoulstoneConfig,
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

_REF_RUNES = Path(__file__).resolve().parents[3] / "fixtures" / "runes"

_SCHEMAS = [
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


def _reference_registry() -> AnimatorRegistry:
    return AnimatorRegistry(
        rune_schemas=_SCHEMAS,
        runtime_adapters=[LlamaCppRuntimeAdapter(), VllmRuntimeAdapter(), SglangRuntimeAdapter()],
        runes_dir=_REF_RUNES,
        reserved_ports={},
        portal_factories=[build_openai_portal],
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

    # Lifecycle per key: the atelier router is DYNAMIC; vLLM + portal are STATIC.
    assert specs["atelier:chat:qwen3-vl-8b"].lifecycle is CapabilityLifecycle.DYNAMIC
    assert specs["atelier:embedding:bge-m3"].lifecycle is CapabilityLifecycle.DYNAMIC
    assert specs["atelier:vision:the-eye"].lifecycle is CapabilityLifecycle.DYNAMIC
    assert specs["glm:chat:GLM-4.6"].lifecycle is CapabilityLifecycle.STATIC
    assert specs["openai-main:chat:gpt-5.2"].lifecycle is CapabilityLifecycle.STATIC


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
