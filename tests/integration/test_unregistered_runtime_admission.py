"""Unregistered runtime labels cannot enter Bind or capability publication."""

from __future__ import annotations

import pytest

from lychd.config import QuadletConfig
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings import Settings
from lychd.domain.animation.conflicts import ConflictTopologyError
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.animation.services.declarations import compile_animator_declarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.extensions.host import assemble_extensions
from lychd.system.services.bind_compilation import compile_bind_request


@pytest.mark.parametrize("runtime_name", ["crawler", "openai_compatible", "openai-compatible", "openai"])
@pytest.mark.parametrize("boundary", ["registry", "bind"])
def test_unregistered_runtime_is_rejected_before_publication_or_binding(runtime_name: str, boundary: str) -> None:
    settings = Settings.model_validate({"extensions": {"builtins": ("animator",), "crypt": ()}})
    extensions = assemble_extensions(settings)
    runes = RuneRegistry(
        [
            GenericSoulstoneConfig(
                name="unregistered",
                runtime=runtime_name,
                quadlet=QuadletConfig(image="invalid.example/inert"),
                model_path="/models/qwen.gguf",
                port=18080,
            )
        ]
    )
    declarations = compile_animator_declarations(settings=settings, runes=runes)

    if boundary == "registry":
        registry = AnimatorRegistry(
            declarations=declarations,
            runtime_adapters=extensions.runtime_adapters,
            portal_definitions=extensions.portal_definitions,
        )
        with pytest.raises(ConflictTopologyError, match="unadvertised Soulstones: unregistered"):
            registry.load()
    else:
        with pytest.raises(ConflictTopologyError, match="unadvertised Soulstones: unregistered"):
            compile_bind_request(
                settings=settings,
                extensions=extensions,
                runes=runes,
                soulstones=declarations.soulstones,
                portals=declarations.portals,
                uncaged=True,
            )
