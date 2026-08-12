from __future__ import annotations

import pytest

from lychd.domain.animation.services.adapters.contracts import SoulstoneDefinition
from lychd.extensions.builtin.animator import LlamaCppSoulstoneConfig
from lychd.extensions.builtin.catalog import (
    BUILTIN_EXTENSIONS,
    builtin_register_module,
    builtin_registration_order,
)
from lychd.extensions.context import ExtensionContext
from lychd.extensions.manager import ExtensionManager


def test_catalog_has_only_explicitly_supported_builtin_ids() -> None:
    assert set(BUILTIN_EXTENSIONS) == {
        "animator",
        "animator/exllamav3",
        "animator/llamacpp",
        "animator/vllm",
        "animator/sglang",
        "observability/phoenix",
        "simulation",
        "delegation",
    }
    assert builtin_register_module("animator/exllamav3").endswith("animator.exllamav3.register")
    assert builtin_register_module("animator/llamacpp").endswith("animator.llamacpp.register")


def test_unknown_builtin_is_rejected_before_import() -> None:
    with pytest.raises(ValueError, match="Known built-ins"):
        builtin_register_module("animator/not-real")


def test_runtime_builtins_expand_shared_animator_dependency_once() -> None:
    assert builtin_registration_order(("animator/vllm", "animator/llamacpp")) == (
        "animator",
        "animator/vllm",
        "animator/llamacpp",
    )


def test_phoenix_builtin_registers_one_owned_quadlet_contributor() -> None:
    context = ExtensionManager(
        builtins=["observability/phoenix"],
        crypt=[],
    ).assemble()

    assert len(context.transmutation.registrations) == 1
    registration = context.transmutation.registrations[0]
    assert registration.provider_id == "builtin:observability/phoenix"
    assert type(registration.contributor).__name__ == "PhoenixQuadletContributor"
    with pytest.raises(RuntimeError, match="frozen after extension assembly"):
        context.transmutation.add_contributor(registration.contributor)


def test_multiple_animator_runtimes_keep_exact_provider_ownership() -> None:
    context = ExtensionManager(
        builtins=["animator/vllm", "animator/llamacpp"],
        crypt=[],
    ).assemble()

    assert [registration.provider_id for registration in context.soulstones.registrations] == [
        "builtin:animator/vllm",
        "builtin:animator/llamacpp",
    ]
    assert {definition.runtime_adapter.runtime for definition in context.soulstones.definitions} == {
        "vllm",
        "llamacpp",
    }
    assert len(context.portals.registrations) == 2
    assert {registration.provider_id for registration in context.portals.registrations} == {"builtin:animator"}


def test_exllamav3_builtin_registers_one_runtime_definition() -> None:
    context = ExtensionManager(builtins=["animator/exllamav3"], crypt=[]).assemble()

    assert len(context.soulstones.definitions) == 1
    definition = context.soulstones.definitions[0]
    assert definition.rune_schema.__name__ == "ExLlamaV3SoulstoneConfig"
    assert definition.runtime_adapter.runtime == "exllamav3"

    from lychd.extensions.builtin.animator.exllamav3.register import register

    with pytest.raises(RuntimeError, match="frozen after extension assembly"):
        register(context.registration_view("builtin:animator/exllamav3"))
    with pytest.raises(RuntimeError, match="frozen after extension assembly"):
        context.soulstones.add(definition)


def test_soulstone_definition_cannot_be_replayed_by_another_provider() -> None:
    assembled = ExtensionManager(builtins=["animator/exllamav3"], crypt=[]).assemble()
    definition = assembled.soulstones.definitions[0]
    context = ExtensionContext()
    with context.provenance("one"):
        context.soulstones.add(definition)
    with context.provenance("two"), pytest.raises(ValueError, match="owned by 'one'"):
        context.soulstones.add(definition)

    collision = SoulstoneDefinition(
        rune_schema=LlamaCppSoulstoneConfig,
        runtime_adapter=definition.runtime_adapter,
    )
    with (
        context.provenance("one"),
        pytest.raises(
            ValueError,
            match="Soulstone runtime 'exllamav3' is already registered",
        ),
    ):
        context.soulstones.add(collision)


def test_registration_view_keeps_immutable_provider_and_hides_root_provenance() -> None:
    assembled = ExtensionManager(builtins=["animator/exllamav3"], crypt=[]).assemble()
    definition = assembled.soulstones.definitions[0]
    context = ExtensionContext()
    registrant = context.registration_view("one")

    assert not hasattr(registrant, "provenance")
    assert not hasattr(registrant.soulstones, "_root")
    assert not hasattr(registrant.soulstones, "_store")
    assert not hasattr(registrant.soulstones, "freeze")
    with context.provenance("two"):
        registrant.soulstones.add(definition)

    assert [registration.provider_id for registration in context.soulstones.registrations] == ["one"]
