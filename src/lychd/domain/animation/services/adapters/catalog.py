"""Model summary synthesis for Soulstone runtimes.

This module turns rune-declared local models into connector-facing ``ModelInfo``
records. It applies runtime defaults first, then Soulstone/model capability
hints as explicit overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.animation.schemas import ModelCapabilityHints, ModelInfo, ModelSurface, SoulstoneConfig

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


__all__ = ["default_model_id_for_soulstone", "model_infos_from_soulstone"]
