"""Model-catalog admission, hint overlays, and family synthesis."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lychd.domain.animation.capabilities import CapabilityFamily, CapabilitySpec
from lychd.domain.animation.schemas import (
    GenericSoulstoneConfig,
    ModelInfo,
    ModelSurface,
    OpenAIPortalConfig,
)
from lychd.domain.animation.services.adapters.catalog import (
    capability_specs_from_model_infos,
)


def _soulstone(**overrides: object) -> GenericSoulstoneConfig:
    payload: dict[str, object] = {"name": "s", "quadlet": {"image": "img:latest"}, "runtime": "llamacpp"}
    payload.update(overrides)
    return GenericSoulstoneConfig.model_validate(payload)


def test_animator_rune_nested_values_are_immutable() -> None:
    stone = _soulstone(
        groups=["primary"],
        env_vars={"MODE": "safe"},
        concurrency={"conflict_domains": ["gpu"]},
        models=[
            {
                "id": "declared",
                "path": "/models/declared",
                "capabilities": {"modalities_in": ["text"]},
            }
        ],
    )

    assert stone.groups == ("primary",)
    assert stone.concurrency.conflict_domains == ("gpu",)
    assert stone.models[0].capabilities is not None
    assert stone.models[0].capabilities.modalities_in == ("text",)
    with pytest.raises(TypeError, match="immutable"):
        stone.env_vars["MODE"] = "forged"
    with pytest.raises(ValidationError, match="frozen"):
        stone.concurrency.dedicated = False


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (
            GenericSoulstoneConfig,
            {
                "name": "duplicates",
                "quadlet": {"image": "img:latest"},
                "runtime": "llamacpp",
                "models": [
                    {"id": "same", "path": "/models/one"},
                    {"id": "same", "path": "/models/two"},
                ],
            },
        ),
        (
            OpenAIPortalConfig,
            {
                "name": "duplicates",
                "models": [{"id": "same"}, {"id": "same"}],
            },
        ),
    ],
)
def test_animator_runes_reject_duplicate_model_ids(
    schema: type[GenericSoulstoneConfig | OpenAIPortalConfig],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="models contains duplicate ids"):
        schema.model_validate(payload)


# --- capability_specs_from_model_infos: end-to-end two-axis + concurrency ---


def test_explicit_family_and_modalities_flow_to_synthesized_spec() -> None:
    soulstone = _soulstone(
        models=[
            {
                "id": "m",
                "path": "/models/m",
                "capabilities": {
                    "families": ["vision"],
                    "modalities_in": ["text"],
                },
            }
        ]
    )

    specs = capability_specs_from_model_infos(
        soulstone,
        [ModelInfo(id="m", modalities_in=("image",))],
    )

    assert [(spec.family, spec.modalities_in) for spec in specs] == [(CapabilityFamily.VISION, ("text",))]


def test_two_axis_regression_image_in_is_chat_with_both_modalities() -> None:
    soulstone = _soulstone(
        models=[
            {
                "id": "m",
                "path": "/models/m",
                "capabilities": {"modalities_in": ["text", "image"]},
            }
        ]
    )
    specs = capability_specs_from_model_infos(
        soulstone,
        [ModelInfo(id="m")],
    )
    assert {spec.family for spec in specs} == {CapabilityFamily.CHAT}
    assert specs[0].modalities_in == ("text", "image")


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


def test_declared_model_catalog_ignores_undeclared_discovery() -> None:
    soulstone = _soulstone(
        models=[{"id": "ghost", "path": "/models/ghost", "generation": {"max_tokens": 321}}],
    )
    specs = capability_specs_from_model_infos(soulstone, [ModelInfo(id="real")])
    assert {spec.model_id for spec in specs} == {"ghost"}
    assert specs[0].generation_profile.max_tokens == 321


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (
            GenericSoulstoneConfig,
            {
                "name": "local",
                "quadlet": {"image": "img:latest"},
                "runtime": "vllm",
                "generation": {"thinking": "qwen3.8-non-thinking"},
            },
        ),
        (OpenAIPortalConfig, {"name": "remote", "generation": {"thinking": "qwen3.8-non-thinking"}}),
        (
            OpenAIPortalConfig,
            {"name": "remote", "models": [{"id": "Qwen3.8-27B", "generation": {"thinking": "qwen3.8-non-thinking"}}]},
        ),
    ],
)
def test_thinking_policy_refuses_non_model_local_defaults(
    schema: type[GenericSoulstoneConfig | OpenAIPortalConfig], payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError, match="thinking policy"):
        schema.model_validate(payload)


def test_runtime_defaults_cannot_supply_a_model_local_thinking_policy() -> None:
    with pytest.raises(ValueError, match="thinking policy cannot be supplied by runtime defaults"):
        capability_specs_from_model_infos(
            _soulstone(runtime="vllm"), [], runtime_defaults={"thinking": "qwen3.8-non-thinking"}
        )


@pytest.mark.parametrize(
    "generation",
    [
        {"thinking": False},
        {"thinking": "disabled"},
        {"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}},
    ],
)
def test_model_generation_rejects_open_ended_thinking_settings(generation: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _soulstone(
            runtime="vllm",
            models=[{"id": "Qwen3.8-27B", "path": "/models/qwen", "generation": generation}],
        )


@pytest.mark.parametrize(
    ("runtime", "model_id", "surface"),
    [("llamacpp", "Qwen3.8-27B", "chat"), ("vllm", "Qwen3.8-27B-alias", "chat"), ("vllm", "Qwen3.8-27B", "responses")],
)
def test_thinking_policy_refuses_unqualified_local_bindings(runtime: str, model_id: str, surface: str) -> None:
    with pytest.raises(ValidationError, match="thinking policy requires local"):
        _soulstone(
            runtime=runtime,
            models=[
                {
                    "id": model_id,
                    "path": "/models/qwen",
                    "capabilities": {"surface": surface},
                    "generation": {"thinking": "qwen3.8-non-thinking"},
                }
            ],
        )


def test_thinking_policy_checks_the_resolved_surface_before_synthesizing_specs() -> None:
    soulstone = _soulstone(
        runtime="vllm",
        models=[{"id": "Qwen3.8-27B", "path": "/models/qwen", "generation": {"thinking": "qwen3.8-non-thinking"}}],
    )
    with pytest.raises(ValueError, match="resolved Chat surface"):
        capability_specs_from_model_infos(soulstone, [ModelInfo(id="Qwen3.8-27B", surface=ModelSurface.RESPONSES)])


@pytest.mark.parametrize(
    "changed",
    [{"source_kind": "portal"}, {"runtime": "sglang"}, {"model_id": "other"}, {"family": "vision"}],
)
def test_adapter_cannot_publish_an_unqualified_thinking_spec(changed: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="thinking policy requires local"):
        CapabilitySpec.model_validate(
            {
                "key": "desk:chat:Qwen3.8-27B",
                "animator_name": "desk",
                "source_kind": "soulstone",
                "runtime": "vllm",
                "model_id": "Qwen3.8-27B",
                "family": "chat",
                "generation_profile": {"thinking": "qwen3.8-non-thinking"},
            }
            | changed
        )


def test_model_local_thinking_overlay_does_not_reach_a_sibling_or_mutate_its_inputs() -> None:
    overlay: dict[str, object] = {"thinking": "qwen3.8-non-thinking", "temperature": 0.2}
    soulstone = _soulstone(
        runtime="vllm",
        generation={"max_tokens": 200},
        models=[
            {"id": "Qwen3.8-27B", "path": "/models/qwen", "generation": overlay, "capabilities": {"surface": "chat"}},
            {"id": "sibling", "path": "/models/sibling"},
        ],
    )
    overlay["thinking"] = None
    specs = capability_specs_from_model_infos(
        soulstone,
        [ModelInfo(id="Qwen3.8-27B", surface=ModelSurface.RESPONSES)],
        runtime_defaults={"max_tokens": 100, "top_p": 0.9},
    )
    selected, sibling = (spec.generation_profile for spec in specs)
    assert selected.model_dump(exclude_none=True) == {
        "max_tokens": 200,
        "temperature": 0.2,
        "top_p": 0.9,
        "thinking": "qwen3.8-non-thinking",
    }
    assert sibling.model_dump(exclude_none=True) == {"max_tokens": 200, "top_p": 0.9}
    with pytest.raises(ValidationError, match="frozen"):
        selected.thinking = None
