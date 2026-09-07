"""Contract tests for the single Animator declaration compiler."""

from __future__ import annotations

import pytest

from lychd.config import QuadletConfig
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import Settings
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.animation.services.declarations import (
    compile_animator_declarations,
)
from lychd.extensions.builtin.observability.phoenix.config import PhoenixSettings


def test_extension_port_claims_shape_auto_hydration() -> None:
    """A Rune reservation is visible before an automatic Soulstone port is chosen."""
    settings = Settings()
    declarations = compile_animator_declarations(
        settings=settings,
        runes=RuneRegistry(
            (
                PhoenixSettings(ui_port=20000, otlp_port=20002),
                GenericSoulstoneConfig(
                    name="local",
                    quadlet=QuadletConfig(image="example/runtime"),
                ),
            )
        ),
    )

    assert declarations.soulstones[0].port == 20001


def test_core_and_extension_port_collision_has_one_fail_closed_policy() -> None:
    settings = Settings()
    settings.server.port = 6006

    with pytest.raises(ValueError, match=r"LychD Server.*Phoenix Eye|Phoenix Eye.*LychD Server"):
        compile_animator_declarations(
            settings=settings,
            runes=RuneRegistry((PhoenixSettings(),)),
        )


@pytest.mark.parametrize("field_name", ["env_vars", "secret_env_files"])
@pytest.mark.parametrize("explicit_endpoint", [False, True])
def test_default_runtime_maps_remain_immutable_through_declaration_admission(
    *,
    field_name: str,
    explicit_endpoint: bool,
) -> None:
    """Omission must not permit post-validation command or secret injection."""
    rune = GenericSoulstoneConfig.model_validate(
        {
            "name": "local",
            "quadlet": {"image": "example/runtime"},
            **({"port": 23333, "base_url": "http://localhost:23333/v1"} if explicit_endpoint else {}),
        },
    )
    declarations = compile_animator_declarations(settings=Settings(), runes=RuneRegistry((rune,)))
    admitted = declarations.soulstones[0]
    serialized = admitted.model_dump_json()

    for projection in (rune, admitted, admitted.model_copy(deep=True)):
        with pytest.raises(TypeError, match="immutable"):
            getattr(projection, field_name)["INJECTED"] = "undeclared"

    assert admitted.model_dump_json() == serialized
    assert getattr(admitted, field_name) == {}
