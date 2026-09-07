from __future__ import annotations

import pytest

from lychd.domain.animation.services.adapters.contracts import SoulstoneDefinition
from lychd.extensions.builtin.animator import LlamaCppSoulstoneConfig
from lychd.extensions.builtin.animator.runtimes import LlamaCppRuntimeAdapter
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
        "delegation",
    }


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
    assert registration.registrant_id == "builtin:observability/phoenix"
    assert type(registration.contributor).__name__ == "PhoenixQuadletContributor"


def test_multiple_animator_runtimes_register_exact_definitions() -> None:
    context = ExtensionManager(
        builtins=["animator/vllm", "animator/llamacpp"],
        crypt=[],
    ).assemble()

    assert {definition.runtime_adapter.runtime for definition in context.soulstones.definitions} == {
        "vllm",
        "llamacpp",
    }
    assert len(context.portals.definitions) == 2


def test_exllamav3_builtin_registers_one_runtime_definition() -> None:
    context = ExtensionManager(builtins=["animator/exllamav3"], crypt=[]).assemble()

    assert len(context.soulstones.definitions) == 1
    definition = context.soulstones.definitions[0]
    assert definition.rune_schema.__name__ == "ExLlamaV3SoulstoneConfig"
    assert definition.runtime_adapter.runtime == "exllamav3"

    with pytest.raises(RuntimeError, match="frozen after extension assembly"):
        context.soulstones.add(definition)


def test_root_context_rejects_every_unattributed_registration() -> None:
    assembled = ExtensionManager(
        builtins=["animator/exllamav3", "observability/phoenix", "delegation"],
        crypt=[],
    ).assemble()
    context = ExtensionContext()

    attempts = (
        lambda: context.runes.add_schema(LlamaCppSoulstoneConfig),
        lambda: context.soulstones.add(assembled.soulstones.definitions[0]),
        lambda: context.portals.add(assembled.portals.definitions[0]),
        lambda: context.transmutation.add_contributor(assembled.transmutation.contributors[0]),
        lambda: context.delegated_runtimes.add(assembled.delegated_runtimes.registrations[0].definition),
    )
    for attempt in attempts:
        with pytest.raises(RuntimeError, match=r"only defined inside an ExtensionContext\.provenance"):
            attempt()


def test_soulstone_definition_cannot_be_replayed_by_another_registrant() -> None:
    assembled = ExtensionManager(builtins=["animator/exllamav3"], crypt=[]).assemble()
    definition = assembled.soulstones.definitions[0]
    context = ExtensionContext()
    with context.provenance("one"):
        context.soulstones.add(definition)
    with context.provenance("two"), pytest.raises(ValueError, match="registered by 'one'"):
        context.soulstones.add(definition)

    collision = SoulstoneDefinition(
        rune_schema=LlamaCppSoulstoneConfig,
        runtime_adapter=definition.runtime_adapter,
    )
    with (
        context.provenance("two"),
        pytest.raises(
            ValueError,
            match="Soulstone runtime 'exllamav3' from 'two' conflicts with the runtime registered by 'one'",
        ),
    ):
        context.soulstones.add(collision)

    schema_collision = SoulstoneDefinition(
        rune_schema=definition.rune_schema,
        runtime_adapter=LlamaCppRuntimeAdapter(),
    )
    with (
        context.provenance("two"),
        pytest.raises(
            ValueError,
            match="Soulstone schema ExLlamaV3SoulstoneConfig from 'two' conflicts with the schema registered by 'one'",
        ),
    ):
        context.soulstones.add(schema_collision)


def test_registration_view_keeps_immutable_registrant() -> None:
    assembled = ExtensionManager(builtins=["animator/exllamav3"], crypt=[]).assemble()
    definition = assembled.soulstones.definitions[0]
    context = ExtensionContext()
    registrant = context.registration_view("one")

    with context.provenance("two"):
        registrant.soulstones.add(definition)

    with context.provenance("two"), pytest.raises(ValueError, match="registered by 'one'"):
        context.soulstones.add(definition)
