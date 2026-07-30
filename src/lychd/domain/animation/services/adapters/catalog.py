"""Runtime-derived model and capability synthesis for Soulstone adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from lychd.domain.animation.capabilities import CapabilityFamily, CapabilitySpec, SourceKind
from lychd.domain.animation.schemas import (
    GenerationProfile,
    ModelCapabilityHints,
    ModelInfo,
    ModelSurface,
    SoulstoneConfig,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from lychd.domain.animation.schemas import LocalModelConfig, PortalModelConfig

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class ProbedModelFacts:
    """What a live runtime probe learned about one model."""

    modalities_in: tuple[str, ...] = ()
    modalities_out: tuple[str, ...] = ()
    embedding: bool = False
    rerank: bool = False
    max_context: int | None = None


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
    "exllamav3": _CapabilityProfile(
        surface=ModelSurface.CHAT,
        modalities_in=("text",),
        modalities_out=("text",),
        supports_tools=True,
        supports_streaming=True,
    ),
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


def model_info_from_portal_model(model: PortalModelConfig) -> ModelInfo:
    """Build the one connector/capability projection of a declared Portal model."""
    hints = model.capabilities
    return ModelInfo(
        id=model.id,
        description=model.description,
        surface=(hints.surface if hints is not None else None) or ModelSurface.CHAT,
        modalities_in=list((hints.modalities_in if hints is not None else None) or ["text"]),
        modalities_out=list((hints.modalities_out if hints is not None else None) or ["text"]),
        supports_tools=hints.supports_tools if hints is not None else None,
        supports_streaming=True if hints is None or hints.supports_streaming is None else hints.supports_streaming,
    )


def capability_specs_from_soulstone(
    soulstone: SoulstoneConfig,
    *,
    runtime_metadata: dict[str, object] | None = None,
    runtime_defaults: dict[str, object] | None = None,
    is_dynamic: bool = False,
) -> list[CapabilitySpec]:
    """Build capability specs from runtime-derived model info."""
    return capability_specs_from_model_infos(
        soulstone,
        model_infos_from_soulstone(soulstone),
        runtime_metadata=runtime_metadata,
        runtime_defaults=runtime_defaults,
        is_dynamic=is_dynamic,
    )


def capability_specs_from_model_infos(
    soulstone: SoulstoneConfig,
    model_infos: Sequence[ModelInfo],
    *,
    runtime_metadata: dict[str, object] | None = None,
    runtime_defaults: dict[str, object] | None = None,
    is_dynamic: bool = False,
    hints_by_id: Mapping[str, ModelCapabilityHints] | None = None,
    probed_by_id: Mapping[str, ProbedModelFacts] | None = None,
) -> list[CapabilitySpec]:
    """Build capability specs from adapter-discovered model info.

    Merges three sources per model id (rune hints > live probe > runtime profile
    default) and synthesizes families under the two-axis law. Rune ``[[models]]``
    entries matching no discovered model still synthesize a spec from the rune
    declaration alone (with a ``model_hint_unmatched`` warning).
    """
    profile = _RUNTIME_PROFILES.get(soulstone.runtime_name, _DEFAULT_PROFILE)
    runtime_meta = runtime_metadata or {}
    base_generation = GenerationProfile.model_validate(runtime_defaults or {}).overlay(soulstone.generation)

    models_by_id: dict[str, LocalModelConfig] = {model.id: model for model in soulstone.models}
    resolved_hints: dict[str, ModelCapabilityHints] = (
        dict(hints_by_id)
        if hints_by_id is not None
        else {model.id: model.capabilities for model in soulstone.models if model.capabilities is not None}
    )
    resolved_probed = dict(probed_by_id or {})

    specs: list[CapabilitySpec] = []
    seen_ids: set[str] = set()
    for info in model_infos:
        seen_ids.add(info.id)
        specs.extend(
            _specs_for_model(
                soulstone=soulstone,
                info=info,
                hints=resolved_hints.get(info.id),
                probed=resolved_probed.get(info.id),
                profile=profile,
                base_generation=base_generation,
                model_generation=models_by_id[info.id].generation if info.id in models_by_id else None,
                is_dynamic=is_dynamic,
                runtime_metadata=runtime_meta,
            )
        )

    for model_id, hints in resolved_hints.items():
        if model_id in seen_ids:
            continue
        logger.warning("model_hint_unmatched", model_id=model_id, animator=soulstone.name)
        local = models_by_id.get(model_id)
        info = _build_model_info(
            model_id=model_id,
            profile=profile,
            description=local.description if local is not None else None,
        )
        specs.extend(
            _specs_for_model(
                soulstone=soulstone,
                info=info,
                hints=hints,
                probed=resolved_probed.get(model_id),
                profile=profile,
                base_generation=base_generation,
                model_generation=local.generation if local is not None else None,
                is_dynamic=is_dynamic,
                runtime_metadata=runtime_meta,
            )
        )

    return specs


def _specs_for_model(
    *,
    soulstone: SoulstoneConfig,
    info: ModelInfo,
    hints: ModelCapabilityHints | None,
    probed: ProbedModelFacts | None,
    profile: _CapabilityProfile,
    base_generation: GenerationProfile,
    model_generation: GenerationProfile | None,
    is_dynamic: bool,
    runtime_metadata: dict[str, object],
) -> list[CapabilitySpec]:
    hydrated = hydrate_model_info(info=info, hints=hints, probed=probed, profile=profile)
    families = synthesize_families(hydrated, hints, probed)
    generation = base_generation.overlay(model_generation)
    concurrency = soulstone.concurrency
    return [
        CapabilitySpec(
            key=f"{soulstone.name}:{family}:{hydrated.id}",
            animator_name=soulstone.name,
            runtime=soulstone.runtime_name,
            source_kind=SourceKind.SOULSTONE,
            family=family,
            model_id=hydrated.id,
            surface=hydrated.surface,
            max_context=hydrated.max_context,
            modalities_in=list(hydrated.modalities_in),
            modalities_out=list(hydrated.modalities_out),
            supports_tools=hydrated.supports_tools,
            supports_streaming=hydrated.supports_streaming,
            generation_profile=generation,
            is_dynamic=is_dynamic,
            concurrency=concurrency,
            metadata={**runtime_metadata, **dict(hydrated.metadata)},
        )
        for family in families
    ]


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


def hydrate_model_info(
    *,
    info: ModelInfo,
    hints: ModelCapabilityHints | None,
    probed: ProbedModelFacts | None,
    profile: _CapabilityProfile,
) -> ModelInfo:
    """Field-wise merge of one model's facts: rune hints > live probe > runtime default.

    Modalities union the discovered/profile base with any probed additions unless
    a rune hint explicitly declares them (an operator override replaces).
    ``surface``/``supports_*`` follow strict precedence.
    """
    surface = (hints.surface if hints is not None else None) or info.surface or profile.surface
    modalities_in = _resolve_modalities(
        hint=hints.modalities_in if hints is not None else None,
        base=list(info.modalities_in) or list(profile.modalities_in),
        probed=list(probed.modalities_in) if probed is not None else [],
    )
    modalities_out = _resolve_modalities(
        hint=hints.modalities_out if hints is not None else None,
        base=list(info.modalities_out) or list(profile.modalities_out),
        probed=list(probed.modalities_out) if probed is not None else [],
    )
    supports_tools = _resolve_optional_bool(
        hint=hints.supports_tools if hints is not None else None,
        base=info.supports_tools,
        fallback=profile.supports_tools,
    )
    supports_streaming = _resolve_optional_bool(
        hint=hints.supports_streaming if hints is not None else None,
        base=info.supports_streaming,
        fallback=profile.supports_streaming,
    )
    max_context = info.max_context
    if max_context is None and probed is not None:
        max_context = probed.max_context
    return ModelInfo(
        id=info.id,
        description=info.description,
        surface=surface,
        modalities_in=modalities_in,
        modalities_out=modalities_out,
        supports_tools=supports_tools,
        supports_streaming=supports_streaming,
        max_context=max_context,
        metadata=dict(info.metadata),
    )


def _resolve_modalities(*, hint: list[str] | None, base: list[str], probed: list[str]) -> list[str]:
    if hint is not None:
        return list(dict.fromkeys(hint))
    return list(dict.fromkeys([*base, *probed]))


def _resolve_optional_bool(*, hint: bool | None, base: bool | None, fallback: bool | None) -> bool | None:
    if hint is not None:
        return hint
    return base if base is not None else fallback


def synthesize_families(
    info: ModelInfo,
    hints: ModelCapabilityHints | None,
    probed: ProbedModelFacts | None,
) -> list[CapabilityFamily]:
    """Synthesize routable families under the two-axis law (spec §2.4).

    Explicit rune ``families`` win verbatim. Otherwise CHAT is synthesized from a
    chat surface / text-in, EMBEDDING/RERANK from probed facts. VISION/STT/TTS/
    TOOL_EXECUTION are NEVER inferred — image/audio in ``modalities_in`` only
    enrich the CHAT spec's admission filter.
    """
    if hints is not None and hints.families is not None:
        return list(dict.fromkeys(hints.families))
    families: list[CapabilityFamily] = []
    if info.surface is not None or "text" in info.modalities_in:
        families.append(CapabilityFamily.CHAT)
    if probed is not None and probed.embedding:
        families.append(CapabilityFamily.EMBEDDING)
    if probed is not None and probed.rerank:
        families.append(CapabilityFamily.RERANK)
    return families or [CapabilityFamily.CHAT]


__all__ = [
    "ProbedModelFacts",
    "capability_specs_from_soulstone",
    "default_model_id_for_soulstone",
    "hydrate_model_info",
    "model_infos_from_soulstone",
    "synthesize_families",
]
