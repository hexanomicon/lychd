from __future__ import annotations

import pytest

from lychd.extensions.builtin.catalog import BUILTIN_EXTENSIONS, builtin_register_module


def test_catalog_has_only_explicitly_supported_builtin_ids() -> None:
    assert set(BUILTIN_EXTENSIONS) == {
        "animator",
        "animator/llamacpp",
        "animator/vllm",
        "animator/sglang",
        "observability/phoenix",
        "simulation",
    }
    assert builtin_register_module("animator/llamacpp").endswith("animator.llamacpp.register")


def test_unknown_builtin_is_rejected_before_import() -> None:
    with pytest.raises(ValueError, match="Known built-ins"):
        builtin_register_module("animator/not-real")
