from __future__ import annotations

import pytest

from lychd.extensions.builtin.catalog import BUILTIN_EXTENSIONS, builtin_register_module
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


def test_exllamav3_builtin_registers_one_runtime_definition() -> None:
    context = ExtensionManager(builtins=["animator/exllamav3"], crypt=[]).assemble()

    assert len(context.soulstones.definitions) == 1
    definition = context.soulstones.definitions[0]
    assert definition.rune_schema.__name__ == "ExLlamaV3SoulstoneConfig"
    assert definition.runtime_adapter.runtime == "exllamav3"
