"""Runtime-derived model and capability synthesis for Soulstone adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.animation.capabilities import CapabilityFamily, CapabilitySpec
from lychd.domain.animation.schemas import (
    ConcurrencyIntent,
    GenerationProfile,
    ModelInfo,
    ModelSurface,
    SoulstoneConfig,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class _CapabilityProfile:
    surface: ModelSurface
    modalities_in: tuple[str, ...]
    modalities_out: tuple[str, ...]
    supports_tools: bool | None
    supports_streaming: bool | None


_DEFAULT_PROFILE = _CapabilityProfile(
    surface=ModelSurface.CHAT,
    modalities_in=("text",),
    modalities_out=("text",),
    supports_tools=None,
    supports_streaming=True,
)
_RUNTIME_PROFILES: dict[str, _CapabilityProfile] = {
    "llamacpp": _CapabilityProfile(
        surface=ModelSurface.CHAT,
        modalities_in=("text",),
        modalities_out=("text",),
        supports_tools=True,
        supports_streaming=True,
    ),
    "vllm": _CapabilityProfile(
        surface=ModelSurface.CHAT,
        modalities_in=("text",),
        modalities_out=("text",),
        supports_tools=True,
        supports_streaming=True,
    ),
    "sglang": _CapabilityProfile(
        surface=ModelSurface.CHAT,
        modalities_in=("text",),
        modalities_out=("text",),
        supports_tools=True,
        supports_streaming=True,
    ),
}


def default_model_id_for_soulstone(soulstone: SoulstoneConfig, model_infos: Sequence[ModelInfo]) -> str | None:
    """Deterministic model id inferred from runtime facts."""
    if soulstone.model_path:
        return Path(soulstone.model_path).stem
    if model_infos:
        return model_infos[0].id
    return soulstone.name


def model_infos_from_soulstone(soulstone: SoulstoneConfig) -> list[ModelInfo]:
    """Build connector-facing model summaries from runtime-local facts."""
    profile = _RUNTIME_PROFILES.get(soulstone.runtime_name, _DEFAULT_PROFILE)
    model_id = Path(soulstone.model_path).stem if soulstone.model_path else soulstone.name
    metadata: dict[str, object] = {}
    if soulstone.model_path:
        metadata["path"] = soulstone.model_path
    if soulstone.model_format is not None:
        metadata["format"] = soulstone.model_format.value
    return [_build_model_info(model_id=model_id, profile=profile, metadata=metadata)]


def capability_specs_from_soulstone(
    soulstone: SoulstoneConfig,
    *,
    runtime_metadata: dict[str, object] | None = None,
    runtime_defaults: dict[str, object] | None = None,
    lifecycle_mode: str = "static",
) -> list[CapabilitySpec]:
    """Build capability specs from runtime-derived model info."""
    return capability_specs_from_model_infos(
        soulstone,
        model_infos_from_soulstone(soulstone),
        runtime_metadata=runtime_metadata,
        runtime_defaults=runtime_defaults,
        lifecycle_mode=lifecycle_mode,
    )


def capability_specs_from_model_infos(
    soulstone: SoulstoneConfig,
    model_infos: Sequence[ModelInfo],
    *,
    runtime_metadata: dict[str, object] | None = None,
    runtime_defaults: dict[str, object] | None = None,
    lifecycle_mode: str = "static",
) -> list[CapabilitySpec]:
    """Build capability specs from adapter-discovered model info."""
    profile = _RUNTIME_PROFILES.get(soulstone.runtime_name, _DEFAULT_PROFILE)
    runtime_meta = runtime_metadata or {}
    generation_defaults = GenerationProfile.model_validate(runtime_defaults or {})

    specs: list[CapabilitySpec] = []
    for info in model_infos:
        hydrated_info = _hydrate_model_info(info=info, profile=profile)
        specs.extend(
            _capability_specs_from_model_info(
                soulstone=soulstone,
                info=hydrated_info,
                generation_defaults=generation_defaults,
                lifecycle_mode=lifecycle_mode,
                runtime_metadata=runtime_meta,
            )
        )
    return specs


def _build_model_info(
    *,
    model_id: str,
    profile: _CapabilityProfile,
    description: str | None = None,
    max_context: int | None = None,
    metadata: dict[str, object] | None = None,
) -> ModelInfo:
    """Create one ``ModelInfo`` from adapter/runtime defaults."""
    return ModelInfo(
        id=model_id,
        description=description,
        surface=profile.surface,
        modalities_in=list(profile.modalities_in),
        modalities_out=list(profile.modalities_out),
        supports_tools=profile.supports_tools,
        supports_streaming=profile.supports_streaming,
        max_context=max_context,
        metadata=metadata or {},
    )


def _hydrate_model_info(*, info: ModelInfo, profile: _CapabilityProfile) -> ModelInfo:
    """Fill missing model-info fields from runtime profile defaults."""
    return ModelInfo(
        id=info.id,
        description=info.description,
        surface=info.surface or profile.surface,
        modalities_in=list(info.modalities_in or profile.modalities_in),
        modalities_out=list(info.modalities_out or profile.modalities_out),
        supports_tools=info.supports_tools if info.supports_tools is not None else profile.supports_tools,
        supports_streaming=(
            info.supports_streaming if info.supports_streaming is not None else profile.supports_streaming
        ),
        max_context=info.max_context,
        metadata=dict(info.metadata),
    )


def _capability_specs_from_model_info(
    *,
    soulstone: SoulstoneConfig,
    info: ModelInfo,
    generation_defaults: GenerationProfile,
    lifecycle_mode: str,
    runtime_metadata: dict[str, object],
) -> list[CapabilitySpec]:
    concurrency = ConcurrencyIntent()
    return [
        CapabilitySpec(
            key=f"{soulstone.name}:{family}:{info.id}",
            animator_name=soulstone.name,
            runtime=soulstone.runtime_name,
            source_kind="soulstone",
            family=family,
            model_id=info.id,
            surface=info.surface,
            modalities_in=list(info.modalities_in),
            modalities_out=list(info.modalities_out),
            supports_tools=info.supports_tools,
            supports_streaming=info.supports_streaming,
            generation_profile=generation_defaults,
            lifecycle_mode=lifecycle_mode,
            concurrency=concurrency,
            metadata={**runtime_metadata, **dict(info.metadata)},
        )
        for family in _infer_families_from_model_info(info)
    ]


def _infer_families_from_model_info(info: ModelInfo) -> list[CapabilityFamily]:
    families: list[CapabilityFamily] = []
    if info.surface is not None or "text" in info.modalities_in or "text" in info.modalities_out:
        families.append(CapabilityFamily.CHAT)
    if "image" in info.modalities_in:
        families.append(CapabilityFamily.VISION)
    return list(dict.fromkeys(families or [CapabilityFamily.CHAT]))


__all__ = [
    "capability_specs_from_soulstone",
    "default_model_id_for_soulstone",
    "model_infos_from_soulstone",
]
