"""Model-catalog admission, hint overlays, and family synthesis."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lychd.domain.animation.capabilities import CapabilityFamily
from lychd.domain.animation.schemas import (
    GenericSoulstoneConfig,
    ModelInfo,
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
