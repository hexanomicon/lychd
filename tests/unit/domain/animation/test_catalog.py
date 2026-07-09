"""A2/A3: probe facts, the three-source merge, and the family-synthesis law."""

from __future__ import annotations

# Catalog/control-plane white-box tests pin private merge invariants directly.
# pyright: reportPrivateUsage=false
import json
from pathlib import Path

from lychd.domain.animation.capabilities import CapabilityFamily
from lychd.domain.animation.lifecycle import AnimatorLifecycle
from lychd.domain.animation.schemas import (
    GenericSoulstoneConfig,
    ModelCapabilityHints,
    ModelInfo,
    ModelSurface,
)
from lychd.domain.animation.services.adapters.catalog import (
    ProbedModelFacts,
    capability_specs_from_model_infos,
    hydrate_model_info,
    synthesize_families,
)
from lychd.extensions.builtin.animator.llamacpp.control_plane import LlamaCppControlPlane
from lychd.extensions.builtin.animator.llamacpp.parser_models import facts_from_markers

_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


def _soulstone(**overrides: object) -> GenericSoulstoneConfig:
    payload: dict[str, object] = {"name": "s", "image": "img:latest", "runtime": "llamacpp"}
    payload.update(overrides)
    return GenericSoulstoneConfig.model_validate(payload)


# --- synthesize_families: the two-axis law ---------------------------------


def test_image_in_without_hints_is_chat_only() -> None:
    info = ModelInfo(id="m", surface=ModelSurface.CHAT, modalities_in=["text", "image"])
    families = synthesize_families(info, hints=None, probed=None)
    assert families == [CapabilityFamily.CHAT]


def test_explicit_vision_hint_wins_verbatim() -> None:
    info = ModelInfo(id="m", surface=ModelSurface.CHAT, modalities_in=["text"])
    families = synthesize_families(info, ModelCapabilityHints(families=[CapabilityFamily.VISION]), None)
    assert families == [CapabilityFamily.VISION]


def test_probed_embedding_synthesizes_embedding_family() -> None:
    info = ModelInfo(id="m", surface=ModelSurface.CHAT, modalities_in=["text"])
    families = synthesize_families(info, hints=None, probed=ProbedModelFacts(embedding=True))
    assert CapabilityFamily.EMBEDDING in families


def test_probed_rerank_synthesizes_rerank_family() -> None:
    info = ModelInfo(id="m", surface=ModelSurface.CHAT, modalities_in=["text"])
    families = synthesize_families(info, hints=None, probed=ProbedModelFacts(rerank=True))
    assert CapabilityFamily.RERANK in families


# --- hydrate_model_info: field-wise precedence + modality union ------------


def test_probed_image_unions_with_profile_text() -> None:
    from lychd.domain.animation.services.adapters.catalog import _DEFAULT_PROFILE

    info = ModelInfo(id="m")
    hydrated = hydrate_model_info(
        info=info,
        hints=None,
        probed=ProbedModelFacts(modalities_in=("image",)),
        profile=_DEFAULT_PROFILE,
    )
    assert hydrated.modalities_in == ["text", "image"]


def test_explicit_hint_modalities_replace() -> None:
    from lychd.domain.animation.services.adapters.catalog import _DEFAULT_PROFILE

    info = ModelInfo(id="m")
    hydrated = hydrate_model_info(
        info=info,
        hints=ModelCapabilityHints(modalities_in=["text"]),
        probed=ProbedModelFacts(modalities_in=("image",)),
        profile=_DEFAULT_PROFILE,
    )
    assert hydrated.modalities_in == ["text"]


# --- capability_specs_from_model_infos: end-to-end two-axis + concurrency ---


def test_two_axis_regression_image_in_is_chat_with_both_modalities() -> None:
    specs = capability_specs_from_model_infos(
        _soulstone(),
        [ModelInfo(id="m")],
        probed_by_id={"m": ProbedModelFacts(modalities_in=("image",))},
    )
    assert {spec.family for spec in specs} == {CapabilityFamily.CHAT}
    assert specs[0].modalities_in == ["text", "image"]


def test_concurrency_flows_from_soulstone_intent() -> None:
    soulstone = _soulstone(concurrency={"dedicated": True, "persistent_resident": True})
    specs = capability_specs_from_model_infos(soulstone, [ModelInfo(id="m")])
    assert specs[0].concurrency.persistent_resident is True


def test_generation_overlay_chain_model_wins_over_soulstone_over_runtime() -> None:
    soulstone = _soulstone(
        generation={"max_tokens": 200},
        models=[{"id": "m", "path": "/models/m", "generation": {"max_tokens": 300}}],
    )
    specs = capability_specs_from_model_infos(
        soulstone,
        [ModelInfo(id="m")],
        runtime_defaults={"max_tokens": 100},
    )
    assert specs[0].generation_profile.max_tokens == 300


def test_generation_overlay_soulstone_wins_over_runtime_when_no_model_overlay() -> None:
    soulstone = _soulstone(generation={"max_tokens": 200}, models=[{"id": "m", "path": "/models/m"}])
    specs = capability_specs_from_model_infos(
        soulstone,
        [ModelInfo(id="m")],
        runtime_defaults={"max_tokens": 100},
    )
    assert specs[0].generation_profile.max_tokens == 200


def test_model_hint_unmatched_still_synthesizes_from_declaration() -> None:
    soulstone = _soulstone(
        models=[{"id": "ghost", "path": "/models/ghost", "capabilities": {"families": ["chat"]}}],
    )
    specs = capability_specs_from_model_infos(soulstone, [ModelInfo(id="real")])
    model_ids = {spec.model_id for spec in specs}
    assert "ghost" in model_ids
    assert "real" in model_ids


# --- facts_from_markers: the marker table ----------------------------------


def test_facts_from_markers_table() -> None:
    assert facts_from_markers(["vision"]).modalities_in == ("image",)
    assert facts_from_markers(["multimodal"]).modalities_in == ("image",)
    assert facts_from_markers(["audio"]).modalities_in == ("audio",)
    assert facts_from_markers(["embedding"]).embedding is True
    assert facts_from_markers(["embeddings"]).embedding is True
    assert facts_from_markers(["reranking"]).rerank is True
    # completion / unknown markers never change anything and never raise.
    assert facts_from_markers(["completion", "totally-unknown"]) == ProbedModelFacts()


def test_audio_is_admission_only_never_a_family() -> None:
    info = ModelInfo(id="m", modalities_in=["text", "audio"])
    families = synthesize_families(info, hints=None, probed=facts_from_markers(["audio"]))
    assert CapabilityFamily.CHAT in families
    assert set(families) <= {CapabilityFamily.CHAT}


# --- A2 integration: parse against the A0 fixture --------------------------


def test_populate_router_models_reads_markers_from_fixture() -> None:
    payload = json.loads((_FIXTURES / "llamacpp" / "models_response.json").read_text(encoding="utf-8"))
    lifecycle = AnimatorLifecycle(runtime="llamacpp", base_url="http://localhost:8080/v1", mode="router")

    LlamaCppControlPlane()._populate_router_models(lifecycle, payload)

    assert lifecycle.model_capabilities["qwen3-vl-8b"] == ["completion", "vision", "multimodal"]
    assert lifecycle.available_models == ["qwen3-vl-8b", "bge-m3", "qwen3-8b"]
    assert lifecycle.loaded_models == ["qwen3-vl-8b"]

    facts = facts_from_markers(lifecycle.model_capabilities["qwen3-vl-8b"])
    assert "image" in facts.modalities_in
    assert facts_from_markers(lifecycle.model_capabilities["bge-m3"]).embedding is True


def test_populate_router_models_tolerates_garbage() -> None:
    lifecycle = AnimatorLifecycle(runtime="llamacpp", base_url="http://localhost:8080/v1", mode="router")
    payload: dict[str, object] = {
        "data": [{"id": "x", "capabilities": "not-a-list"}, {"id": "y"}, {"no-id": 1}]
    }

    LlamaCppControlPlane()._populate_router_models(lifecycle, payload)

    assert lifecycle.available_models == ["x", "y"]
    assert lifecycle.model_capabilities == {}


def test_no_audio_family_in_animation_source() -> None:
    # The grep gate: `"audio"` never appears near a CapabilityFamily in the domain.
    root = Path(__file__).resolve().parents[3].parent / "src" / "lychd" / "domain" / "animation"
    offenders = [
        f"{path.name}: {line.strip()}"
        for path in root.rglob("*.py")
        for line in path.read_text(encoding="utf-8").splitlines()
        if '"audio"' in line.lower() and "family" in line.lower()
    ]
    assert offenders == []
