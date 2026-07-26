"""Contract tests for the single Animator declaration compiler."""

from __future__ import annotations

import pytest

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
                    image="example/runtime",
                ),
            )
        ),
    )

    assert declarations.soulstones[0].port == 20001
    assert declarations.reserved_ports["Oculus (Phoenix UI)"] == 20000


def test_core_and_extension_port_collision_has_one_fail_closed_policy() -> None:
    settings = Settings()
    settings.server.port = 6006

    with pytest.raises(ValueError, match=r"LychD Server.*Oculus|Oculus.*LychD Server"):
        compile_animator_declarations(
            settings=settings,
            runes=RuneRegistry((PhoenixSettings(),)),
        )
