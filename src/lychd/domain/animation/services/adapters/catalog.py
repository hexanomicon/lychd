"""Runtime-derived model and capability synthesis for Soulstone adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.domain.animation.capabilities import CapabilityFamily, CapabilitySpec, SourceKind
from lychd.domain.animation.schemas import (
    GenerationProfile,
    ModelCapabilityHints,
    ModelInfo,
    ModelSurface,
    SoulstoneConfig,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lychd.domain.animation.schemas import LocalModelConfig, PortalModelConfig


@dataclass(frozen=True, slots=True)
class _CapabilityProfile:
    surface: ModelSurface
    modalities_in: tuple[str, ...]
    supports_tools: bool | None


_DEFAULT_PROFILE = _CapabilityProfile(
    surface=ModelSurface.CHAT,
    modalities_in=("text",),
    supports_tools=None,
)
_RUNTIME_PROFILES: dict[str, _CapabilityProfile] = {
    "exllamav3": _CapabilityProfile(
        surface=ModelSurface.CHAT,
        modalities_in=("text",),
        supports_tools=True,
    ),
    "llamacpp": _CapabilityProfile(
        surface=ModelSurface.CHAT,
        modalities_in=("text",),
        supports_tools=True,
    ),
    "vllm": _CapabilityProfile(
        surface=ModelSurface.CHAT,
        modalities_in=("text",),
        supports_tools=True,
    ),
    "sglang": _CapabilityProfile(
        surface=ModelSurface.CHAT,
        modalities_in=("text",),
        supports_tools=True,
    ),
}


def default_model_id_for_soulstone(soulstone: SoulstoneConfig, model_infos: Sequence[ModelInfo]) -> str | None:
    """Deterministic model id inferred from runtime facts."""
    if soulstone.models:
        return soulstone.models[0].id
    if soulstone.served_model_id:
        return soulstone.served_model_id
    if soulstone.model_path:
        return Path(soulstone.model_path).stem
    if model_infos:
        return model_infos[0].id
    return soulstone.name


def model_infos_from_soulstone(
    soulstone: SoulstoneConfig,
    discovered: Sequence[ModelInfo] | None = None,
) -> list[ModelInfo]:
    """Build the connector catalogue, treating explicit Rune models as an allowlist."""
    profile = _RUNTIME_PROFILES.get(soulstone.runtime, _DEFAULT_PROFILE)
    if soulstone.models:
        discovered_by_id = {info.id: info for info in discovered or ()}
        admitted: list[ModelInfo] = []
        for model in soulstone.models:
            observed = discovered_by_id.get(model.id) or _build_model_info(model_id=model.id, profile=profile)
            # Connectors and capability synthesis consume this same projection;
            # an admitted surface hint must also select the executable API.
            admitted.append(_hydrate_model_info(info=observed, hints=model.capabilities, profile=profile))
        return admitted
    if discovered is not None:
        return list(discovered)

    model_id = soulstone.served_model_id or (
        Path(soulstone.model_path).stem if soulstone.model_path else soulstone.name
    )
    return [_build_model_info(model_id=model_id, profile=profile)]


def model_info_from_portal_model(model: PortalModelConfig) -> ModelInfo:
    """Build the one connector/capability projection of a declared Portal model."""
    hints = model.capabilities
    return ModelInfo(
        id=model.id,
        surface=(hints.surface if hints is not None else None) or ModelSurface.CHAT,
        modalities_in=tuple((hints.modalities_in if hints is not None else None) or ("text",)),
        supports_tools=hints.supports_tools if hints is not None else None,
    )


def capability_specs_from_model_infos(
    soulstone: SoulstoneConfig,
    model_infos: Sequence[ModelInfo],
    *,
    runtime_defaults: dict[str, object] | None = None,
    is_dynamic: bool = False,
) -> list[CapabilitySpec]:
    """Build capability specs from adapter-discovered model info.

    Merges Rune hints over runtime profile defaults and synthesizes families
    under the two-axis law. A non-empty Rune
    ``[[models]]`` table is the exact admitted model set: undeclared discoveries
    are ignored and declarations absent from discovery still synthesize specs.
    """
    profile = _RUNTIME_PROFILES.get(soulstone.runtime, _DEFAULT_PROFILE)
    base_generation = GenerationProfile.model_validate(runtime_defaults or {}).overlay(soulstone.generation)

    models_by_id: dict[str, LocalModelConfig] = {model.id: model for model in soulstone.models}
    resolved_hints = {model.id: model.capabilities for model in soulstone.models if model.capabilities is not None}
    specs: list[CapabilitySpec] = []
    admitted_infos = model_infos_from_soulstone(soulstone, discovered=model_infos)
    for info in admitted_infos:
        specs.extend(
            _specs_for_model(
                soulstone=soulstone,
                info=info,
                hints=resolved_hints.get(info.id),
                profile=profile,
                base_generation=base_generation,
                model_generation=models_by_id[info.id].generation if info.id in models_by_id else None,
                is_dynamic=is_dynamic,
            )
        )

    return specs


def _specs_for_model(
    *,
    soulstone: SoulstoneConfig,
    info: ModelInfo,
    hints: ModelCapabilityHints | None,
    profile: _CapabilityProfile,
    base_generation: GenerationProfile,
    model_generation: GenerationProfile | None,
    is_dynamic: bool,
) -> list[CapabilitySpec]:
    hydrated = _hydrate_model_info(info=info, hints=hints, profile=profile)
    families = synthesize_families(hydrated, hints)
    generation = base_generation.overlay(model_generation)
    concurrency = soulstone.concurrency
    return [
        CapabilitySpec(
            key=f"{soulstone.name}:{family}:{hydrated.id}",
            animator_name=soulstone.name,
            runtime=soulstone.runtime,
            source_kind=SourceKind.SOULSTONE,
            family=family,
            model_id=hydrated.id,
            max_context=hydrated.max_context,
            modalities_in=hydrated.modalities_in,
            supports_tools=hydrated.supports_tools,
            generation_profile=generation,
            is_dynamic=is_dynamic,
            concurrency=concurrency,
        )
        for family in families
    ]


def _build_model_info(
    *,
    model_id: str,
    profile: _CapabilityProfile,
    max_context: int | None = None,
) -> ModelInfo:
    """Create one ``ModelInfo`` from adapter/runtime defaults."""
    return ModelInfo(
        id=model_id,
        surface=profile.surface,
        modalities_in=profile.modalities_in,
        supports_tools=profile.supports_tools,
        max_context=max_context,
    )


def _hydrate_model_info(
    *,
    info: ModelInfo,
    hints: ModelCapabilityHints | None,
    profile: _CapabilityProfile,
) -> ModelInfo:
    """Overlay explicit Rune hints on discovered/runtime model facts."""
    surface = (hints.surface if hints is not None else None) or info.surface or profile.surface
    modalities_in = _resolve_modalities(
        hint=hints.modalities_in if hints is not None else None,
        base=list(info.modalities_in) or list(profile.modalities_in),
    )
    supports_tools = _resolve_optional_bool(
        hint=hints.supports_tools if hints is not None else None,
        base=info.supports_tools,
        fallback=profile.supports_tools,
    )
    return ModelInfo(
        id=info.id,
        surface=surface,
        modalities_in=tuple(modalities_in),
        supports_tools=supports_tools,
        max_context=info.max_context,
    )


def _resolve_modalities(
    *,
    hint: Sequence[str] | None,
    base: Sequence[str],
) -> list[str]:
    if hint is not None:
        return list(dict.fromkeys(hint))
    return list(dict.fromkeys(base))


def _resolve_optional_bool(*, hint: bool | None, base: bool | None, fallback: bool | None) -> bool | None:
    if hint is not None:
        return hint
    return base if base is not None else fallback


def synthesize_families(
    info: ModelInfo,
    hints: ModelCapabilityHints | None,
) -> list[CapabilityFamily]:
    """Synthesize routable families under the two-axis law (spec §2.4).

    Explicit rune ``families`` win verbatim. Otherwise CHAT is synthesized from a
    chat surface / text-in. Other families are never inferred from modalities;
    they require explicit Rune hints.
    """
    if hints is not None and hints.families is not None:
        return list(dict.fromkeys(hints.families))
    families: list[CapabilityFamily] = []
    if info.surface is not None or "text" in info.modalities_in:
        families.append(CapabilityFamily.CHAT)
    return families or [CapabilityFamily.CHAT]


__all__ = [
    "default_model_id_for_soulstone",
    "model_infos_from_soulstone",
    "synthesize_families",
]
