"""Embedded Quadlet-backed Rune configuration contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lychd.config import QuadletConfig
from lychd.domain.animation.schemas import GenericSoulstoneConfig, OpenAIPortalConfig
from lychd.extensions.builtin.observability.phoenix.config import PhoenixSettings


def test_current_quadlet_backed_runes_embed_one_explicit_value_object() -> None:
    """Soulstone and Phoenix compose deployment intent without inheriting its identity."""
    assert not issubclass(GenericSoulstoneConfig, QuadletConfig)
    assert not issubclass(PhoenixSettings, QuadletConfig)
    assert not issubclass(OpenAIPortalConfig, QuadletConfig)
    stone = GenericSoulstoneConfig(name="local", quadlet=QuadletConfig(image="example/runtime"))
    assert isinstance(stone.quadlet, QuadletConfig)
    assert isinstance(PhoenixSettings().quadlet, QuadletConfig)


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (GenericSoulstoneConfig, {"name": "local", "quadlet": {"image": ""}}),
        (PhoenixSettings, {"quadlet": {"image": ""}}),
    ],
)
def test_quadlet_backed_runes_reject_an_empty_image(
    schema: type[QuadletConfig],
    payload: dict[str, str],
) -> None:
    with pytest.raises(ValidationError, match="image"):
        schema.model_validate(payload)


def test_embedded_quadlet_preserves_owner_specific_defaults() -> None:
    assert PhoenixSettings().quadlet.image == "docker.io/arize-ai/phoenix:latest"
    stone = GenericSoulstoneConfig(name="local", quadlet=QuadletConfig(image="example/runtime"))
    assert stone.quadlet.image == "example/runtime"


def test_quadlet_rejects_raw_or_unknown_manifest_authority() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        QuadletConfig.model_validate({"image": "example/runtime", "unit_text": "[Service]"})


def test_quadlet_backed_rune_rejects_the_old_flat_image_shape() -> None:
    with pytest.raises(ValidationError, match="image"):
        GenericSoulstoneConfig.model_validate({"name": "local", "image": "example/runtime"})
