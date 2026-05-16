"""Model summary synthesis for Soulstone runtimes.

This module turns rune-declared local models into connector-facing ``ModelInfo``
records. It applies runtime defaults first, then Soulstone/model capability
hints as explicit overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.animation.capabilities import CapabilityFamily, CapabilitySpec
from lychd.domain.animation.schemas import (
    ConcurrencyIntent,
    GenerationProfile,
    LLMGenerationDefaults,
    ModelCapabilityHints,
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
    """Select deterministic default model id for connector hydration."""
    if soulstone.models:
        first_declared = next(iter(soulstone.models.values()))
        return first_declared.id
    if soulstone.model_path:
        return Path(soulstone.model_path).stem
    if model_infos:
        return model_infos[0].id
    return soulstone.name


def model_infos_from_soulstone(soulstone: SoulstoneConfig) -> list[ModelInfo]:
    """Build connector-facing model summaries from Soulstone declarations."""
    profile = _RUNTIME_PROFILES.get(soulstone.runtime_name, _DEFAULT_PROFILE)

    if soulstone.models:
        infos: list[ModelInfo] = []
        for model in soulstone.models.values():
            metadata: dict[str, object] = {"path": str(model.path)}
            if model.format is not None:
                metadata["format"] = model.format.value
            if model.tags:
                metadata["tags"] = list(model.tags)
            if model.llm_defaults is not None:
                metadata["llm_defaults"] = model.llm_defaults.model_dump(exclude_none=True)
            max_context = model.llm_defaults.max_context if model.llm_defaults is not None else None
            infos.append(
                _build_model_info(
                    model_id=model.id,
                    description=model.description,
                    metadata=metadata,
                    max_context=max_context,
                    profile=profile,
                    soulstone_hints=soulstone.capabilities,
                    model_hints=model.capabilities,
                )
            )
        return infos

    if soulstone.model_path:
        inferred_id = Path(soulstone.model_path).stem
        model_metadata: dict[str, object] = {"path": soulstone.model_path}
        if soulstone.model_format is not None:
            model_metadata["format"] = soulstone.model_format.value
        return [
            _build_model_info(
                model_id=inferred_id,
                metadata=model_metadata,
                profile=profile,
                soulstone_hints=soulstone.capabilities,
                model_hints=None,
            )
        ]

    return [
        _build_model_info(
            model_id=soulstone.name,
            profile=profile,
            soulstone_hints=soulstone.capabilities,
            model_hints=None,
        )
    ]


def capability_specs_from_soulstone(
    soulstone: SoulstoneConfig,
    *,
    runtime_metadata: dict[str, object] | None = None,
    runtime_defaults: dict[str, object] | None = None,
    lifecycle_mode: str = "static",
) -> list[CapabilitySpec]:
    """Build capability specs from a soulstone declaration plus runtime metadata."""
    profile = _RUNTIME_PROFILES.get(soulstone.runtime_name, _DEFAULT_PROFILE)
    specs: list[CapabilitySpec] = []
    runtime_meta = runtime_metadata or {}
    generation_runtime_defaults = runtime_defaults or {}

    if soulstone.models:
        for model in soulstone.models.values():
            info = _build_model_info(
                model_id=model.id,
                description=model.description,
                metadata=_model_metadata(model.path, model.format.value if model.format else None, model.tags),
                max_context=model.llm_defaults.max_context if model.llm_defaults is not None else None,
                profile=profile,
                soulstone_hints=soulstone.capabilities,
                model_hints=model.capabilities,
            )
            specs.extend(
                _capability_specs_from_model_info(
                    soulstone=soulstone,
                    info=info,
                    generation_defaults=_merge_generation_defaults(
                        runtime_defaults=generation_runtime_defaults,
                        animator_defaults=soulstone.llm_defaults,
                        model_defaults=model.llm_defaults,
                    ),
                    lifecycle_mode=lifecycle_mode,
                    runtime_metadata=runtime_meta,
                    families_hint=model.capabilities.families if model.capabilities is not None else None,
                )
            )
        return specs

    inferred_infos = model_infos_from_soulstone(soulstone)
    for info in inferred_infos:
        specs.extend(
            _capability_specs_from_model_info(
                soulstone=soulstone,
                info=info,
                generation_defaults=_merge_generation_defaults(
                    runtime_defaults=generation_runtime_defaults,
                    animator_defaults=soulstone.llm_defaults,
                    model_defaults=None,
                ),
                lifecycle_mode=lifecycle_mode,
                runtime_metadata=runtime_meta,
                families_hint=soulstone.capabilities.families if soulstone.capabilities is not None else None,
            )
        )
    return specs


def capability_specs_from_model_infos(
    soulstone: SoulstoneConfig,
    model_infos: Sequence[ModelInfo],
    *,
    runtime_metadata: dict[str, object] | None = None,
    runtime_defaults: dict[str, object] | None = None,
    lifecycle_mode: str = "static",
) -> list[CapabilitySpec]:
    """Build capability specs from runtime-discovered model infos plus rune overrides."""
    profile = _RUNTIME_PROFILES.get(soulstone.runtime_name, _DEFAULT_PROFILE)
    runtime_meta = runtime_metadata or {}
    generation_runtime_defaults = runtime_defaults or {}
    declared_models = {model.id: model for model in soulstone.models.values()} if soulstone.models else {}

    specs: list[CapabilitySpec] = []
    for info in model_infos:
        declared = declared_models.get(info.id)
        if declared is not None:
            hydrated_info = _build_model_info(
                model_id=declared.id,
                description=declared.description or info.description,
                metadata={**_model_metadata(declared.path, declared.format.value if declared.format else None, declared.tags), **dict(info.metadata)},
                max_context=declared.llm_defaults.max_context if declared.llm_defaults is not None else info.max_context,
                profile=profile,
                soulstone_hints=soulstone.capabilities,
                model_hints=declared.capabilities,
            )
            model_defaults = declared.llm_defaults
            families_hint = declared.capabilities.families if declared.capabilities is not None else None
        else:
            hydrated_info = _build_model_info(
                model_id=info.id,
                description=info.description,
                metadata=dict(info.metadata),
                max_context=info.max_context,
                profile=profile,
                soulstone_hints=soulstone.capabilities,
                model_hints=None,
            )
            model_defaults = None
            families_hint = soulstone.capabilities.families if soulstone.capabilities is not None else None

        specs.extend(
            _capability_specs_from_model_info(
                soulstone=soulstone,
                info=hydrated_info,
                generation_defaults=_merge_generation_defaults(
                    runtime_defaults=generation_runtime_defaults,
                    animator_defaults=soulstone.llm_defaults,
                    model_defaults=model_defaults,
                ),
                lifecycle_mode=lifecycle_mode,
                runtime_metadata=runtime_meta,
                families_hint=families_hint,
            )
        )
    return specs


def _build_model_info(
    *,
    model_id: str,
    profile: _CapabilityProfile,
    soulstone_hints: ModelCapabilityHints | None,
    model_hints: ModelCapabilityHints | None,
    description: str | None = None,
    max_context: int | None = None,
    metadata: dict[str, object] | None = None,
    ) -> ModelInfo:
    """Create one ``ModelInfo`` with layered capability defaults/overrides."""
    return ModelInfo(
        id=model_id,
        description=description,
        surface=_pick_surface(profile=profile, soulstone_hints=soulstone_hints, model_hints=model_hints),
        modalities_in=_pick_modalities(
            default=list(profile.modalities_in),
            soulstone_hints=soulstone_hints,
            model_hints=model_hints,
            field="modalities_in",
        ),
        modalities_out=_pick_modalities(
            default=list(profile.modalities_out),
            soulstone_hints=soulstone_hints,
            model_hints=model_hints,
            field="modalities_out",
        ),
        supports_tools=_pick_flag(
            default=profile.supports_tools,
            soulstone_hints=soulstone_hints,
            model_hints=model_hints,
            field="supports_tools",
        ),
        supports_streaming=_pick_flag(
            default=profile.supports_streaming,
            soulstone_hints=soulstone_hints,
            model_hints=model_hints,
            field="supports_streaming",
        ),
        max_context=max_context,
        metadata=metadata or {},
    )


def _capability_specs_from_model_info(
    *,
    soulstone: SoulstoneConfig,
    info: ModelInfo,
    generation_defaults: GenerationProfile,
    lifecycle_mode: str,
    runtime_metadata: dict[str, object],
    families_hint: list[CapabilityFamily] | None,
) -> list[CapabilitySpec]:
    families = families_hint or _infer_families_from_model_info(info)
    concurrency = ConcurrencyIntent(
        matrix_sets=list(soulstone.matrix_sets),
        evict_cost=soulstone.evict_cost,
        dedicated=soulstone.dedicated,
        persistent_resident=soulstone.persistent_resident,
    )
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
        for family in families
    ]


def _infer_families_from_model_info(info: ModelInfo) -> list[CapabilityFamily]:
    families: list[CapabilityFamily] = []
    if info.surface is not None or "text" in info.modalities_in or "text" in info.modalities_out:
        families.append(CapabilityFamily.CHAT)
    if "image" in info.modalities_in:
        families.append(CapabilityFamily.VISION)
    return list(dict.fromkeys(families or [CapabilityFamily.CHAT]))


def _merge_generation_defaults(
    *,
    runtime_defaults: dict[str, object],
    animator_defaults: LLMGenerationDefaults | None,
    model_defaults: LLMGenerationDefaults | None,
) -> GenerationProfile:
    data = dict(runtime_defaults)
    if animator_defaults is not None:
        data.update(animator_defaults.model_dump(exclude_none=True))
    if model_defaults is not None:
        data.update(model_defaults.model_dump(exclude_none=True))
    return GenerationProfile.model_validate(data)


def _model_metadata(path: Path, model_format: str | None, tags: list[str]) -> dict[str, object]:
    metadata: dict[str, object] = {"path": str(path)}
    if model_format is not None:
        metadata["format"] = model_format
    if tags:
        metadata["tags"] = list(tags)
    return metadata


def _pick_surface(
    *,
    profile: _CapabilityProfile,
    soulstone_hints: ModelCapabilityHints | None,
    model_hints: ModelCapabilityHints | None,
) -> ModelSurface:
    """Resolve model surface with precedence: model hint > soulstone hint > runtime."""
    if model_hints is not None and model_hints.surface is not None:
        return model_hints.surface
    if soulstone_hints is not None and soulstone_hints.surface is not None:
        return soulstone_hints.surface
    return profile.surface


def _pick_modalities(
    *,
    default: list[str],
    soulstone_hints: ModelCapabilityHints | None,
    model_hints: ModelCapabilityHints | None,
    field: str,
) -> list[str]:
    """Resolve modality list with precedence: model hint > soulstone hint > runtime."""
    model_value = getattr(model_hints, field) if model_hints is not None else None
    if model_value is not None:
        return list(model_value)

    soulstone_value = getattr(soulstone_hints, field) if soulstone_hints is not None else None
    if soulstone_value is not None:
        return list(soulstone_value)

    return default


def _pick_flag(
    *,
    default: bool | None,
    soulstone_hints: ModelCapabilityHints | None,
    model_hints: ModelCapabilityHints | None,
    field: str,
) -> bool | None:
    """Resolve optional bool flag with precedence: model hint > soulstone hint > runtime."""
    model_value = getattr(model_hints, field) if model_hints is not None else None
    if model_value is not None:
        return bool(model_value)

    soulstone_value = getattr(soulstone_hints, field) if soulstone_hints is not None else None
    if soulstone_value is not None:
        return bool(soulstone_value)

    return default


__all__ = [
    "capability_specs_from_soulstone",
    "default_model_id_for_soulstone",
    "model_infos_from_soulstone",
]
