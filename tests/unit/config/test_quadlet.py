"""Embedded Quadlet-backed Rune configuration contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lychd.config import QuadletConfig
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.animation.transmute import TransmutationContext
from lychd.extensions.builtin.observability.phoenix.config import PhoenixSettings
from lychd.extensions.builtin.observability.phoenix.contributor import PhoenixQuadletContributor


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


def test_phoenix_quadlet_image_override_reaches_compiled_container() -> None:
    image = "registry.example/phoenix:verified"
    phoenix = PhoenixSettings(quadlet=QuadletConfig(image=image))
    contribution = PhoenixQuadletContributor().contribute(
        TransmutationContext(
            settings=get_settings(),
            soulstones=(),
            portals=(),
            runes=RuneRegistry((phoenix,)),
        )
    )

    assert [container.image for container in contribution.containers] == [image]


@pytest.mark.parametrize("name", ["../phoenix", "phoenix/sidecar", r"phoenix\sidecar"])
def test_phoenix_rejects_unsafe_service_name_components(name: str) -> None:
    with pytest.raises(ValidationError, match="safe unit-name component"):
        PhoenixSettings(name=name)


def test_quadlet_rejects_raw_or_unknown_manifest_authority() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        QuadletConfig.model_validate({"image": "example/runtime", "unit_text": "[Service]"})
