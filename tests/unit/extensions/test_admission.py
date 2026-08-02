from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import ClassVar

import pytest

from lychd.config.runes import RuneConfig
from lychd.extensions.context import ExtensionContext
from lychd.extensions.manager import ExtensionManager


class _AnchorFamily(RuneConfig):
    path_fragment: ClassVar[Path] = Path("anchor-family")


class _AnchorLeaf(_AnchorFamily):
    path_fragment: ClassVar[Path] = Path("leaf")


class _UnrelatedAnchorFamily(RuneConfig):
    path_fragment: ClassVar[Path] = Path("anchor-family")


class _UnrelatedAnchorLeaf(_UnrelatedAnchorFamily):
    path_fragment: ClassVar[Path] = Path("leaf")


def _write_crypt_register(root: Path, extension_id: str, source: str) -> Path:
    register_path = root.joinpath(*extension_id.split("/"), "register.py")
    register_path.parent.mkdir(parents=True, exist_ok=True)
    register_path.write_text(dedent(source).lstrip(), encoding="utf-8")
    return register_path


def _rune_register_source(class_name: str, anchor: str) -> str:
    return f"""
        from pathlib import Path
        from typing import ClassVar

        from lychd.config.runes import RuneConfig


        class {class_name}(RuneConfig):
            path_fragment: ClassVar[Path] = Path({anchor!r})


        def register(context):
            context.runes.add_schema({class_name})
    """


def test_rune_registration_rejects_unrelated_exact_anchor_owner() -> None:
    context = ExtensionContext()
    with context.provenance("first"):
        context.runes.add_schema(_AnchorLeaf)

    with context.provenance("second"), pytest.raises(ValueError, match="anchor-family/leaf") as exc_info:
        context.runes.add_schema(_UnrelatedAnchorLeaf)

    message = str(exc_info.value)
    assert "anchor-family/leaf" in message
    assert "_AnchorLeaf" in message
    assert "'first'" in message
    assert "_UnrelatedAnchorLeaf" in message
    assert "'second'" in message


def test_rune_registration_allows_declared_class_ancestry() -> None:
    context = ExtensionContext()
    with context.provenance("family"):
        context.runes.add_schema(_AnchorFamily)
        context.runes.add_schema(_AnchorLeaf)

    assert context.runes.rune_schemas == (_AnchorFamily, _AnchorLeaf)


def test_crypt_activation_id_cannot_impersonate_core_provenance(tmp_path: Path) -> None:
    _write_crypt_register(
        tmp_path,
        "core",
        """
        from lychd.domain.cortex.operations import AGENT_RUN_OPERATION

        def register(context):
            context.run_operations.add(AGENT_RUN_OPERATION)
        """,
    )

    with pytest.raises(ValueError, match="crypt:core") as exc_info:
        ExtensionManager(builtins=[], crypt=["core"], crypt_root=tmp_path).assemble()

    message = str(exc_info.value)
    assert "'crypt:core'" in message
    assert "registered by 'core'" in message


def test_same_builtin_and_crypt_activation_ids_have_distinct_provenance(tmp_path: Path) -> None:
    _write_crypt_register(
        tmp_path,
        "simulation",
        """
        from lychd.extensions.builtin.simulation.config import ShadowSimulationConfig

        def register(context):
            context.runes.add_schema(ShadowSimulationConfig)
        """,
    )

    with pytest.raises(ValueError, match="crypt:simulation") as exc_info:
        ExtensionManager(
            builtins=["simulation"],
            crypt=["simulation"],
            crypt_root=tmp_path,
        ).assemble()

    message = str(exc_info.value)
    assert "'crypt:simulation'" in message
    assert "'builtin:simulation'" in message


def test_crypt_module_names_are_injective_for_legal_activation_ids(tmp_path: Path) -> None:
    _write_crypt_register(tmp_path, "a-b", _rune_register_source("HyphenRune", "hyphen-rune"))
    _write_crypt_register(tmp_path, "a_b", _rune_register_source("UnderscoreRune", "underscore-rune"))

    context = ExtensionManager(
        builtins=[],
        crypt=["a-b", "a_b"],
        crypt_root=tmp_path,
    ).assemble()
    selected = [schema for schema in context.runes.rune_schemas if schema.__name__ in {"HyphenRune", "UnderscoreRune"}]

    assert {schema.__name__ for schema in selected} == {"HyphenRune", "UnderscoreRune"}
    assert len({schema.__module__ for schema in selected}) == 2


@pytest.mark.parametrize("activation_id", ["alias//id", "alias/./id", "alias/../id"])
def test_direct_crypt_manager_rejects_noncanonical_activation_ids(
    tmp_path: Path,
    activation_id: str,
) -> None:
    with pytest.raises(ValueError, match="Invalid extension id"):
        ExtensionManager(builtins=[], crypt=[activation_id], crypt_root=tmp_path).assemble()


def test_selected_crypt_register_is_a_package_with_relative_sibling_imports(tmp_path: Path) -> None:
    register_path = _write_crypt_register(
        tmp_path,
        "relative",
        """
        from .schema import RelativeRune

        def register(context):
            context.runes.add_schema(RelativeRune)
        """,
    )
    register_path.with_name("schema.py").write_text(
        dedent(
            """
            from pathlib import Path
            from typing import ClassVar

            from lychd.config.runes import RuneConfig


            class RelativeRune(RuneConfig):
                path_fragment: ClassVar[Path] = Path("relative-rune")
            """
        ).lstrip(),
        encoding="utf-8",
    )
    _write_crypt_register(
        tmp_path,
        "unselected",
        """
        raise AssertionError("Crypt discovery imported an unselected package")
        """,
    )

    context = ExtensionManager(
        builtins=[],
        crypt=["relative"],
        crypt_root=tmp_path,
    ).assemble()
    relative_schema = next(schema for schema in context.runes.rune_schemas if schema.__name__ == "RelativeRune")

    assert relative_schema.__module__.endswith(".schema")


def test_failed_crypt_register_clears_its_synthetic_import_generation(tmp_path: Path) -> None:
    activation_id = "partial"
    _write_crypt_register(
        tmp_path,
        activation_id,
        """
        from pathlib import Path
        from typing import ClassVar

        from lychd.config.runes import RuneConfig

        class PartialRune(RuneConfig):
            path_fragment: ClassVar[Path] = Path("partial-rune")

        def register(context):
            context.runes.add_schema(PartialRune)
            raise RuntimeError("partial register failed")
        """,
    )
    package_name = f"lychd_crypt_extension_{activation_id.encode('utf-8').hex()}"

    with pytest.raises(RuntimeError, match="partial register failed"):
        ExtensionManager(builtins=[], crypt=[activation_id], crypt_root=tmp_path).assemble()

    assert not any(name == package_name or name.startswith(f"{package_name}.") for name in sys.modules)


def test_async_crypt_register_is_rejected_and_its_module_generation_is_cleared(tmp_path: Path) -> None:
    activation_id = "async-register"
    _write_crypt_register(
        tmp_path,
        activation_id,
        """
        async def register(context):
            raise AssertionError("an async registration body must never be scheduled")
        """,
    )
    package_name = f"lychd_crypt_extension_{activation_id.encode('utf-8').hex()}"

    with pytest.raises(TypeError, match="must be synchronous and return None"):
        ExtensionManager(builtins=[], crypt=[activation_id], crypt_root=tmp_path).assemble()

    assert not any(name == package_name or name.startswith(f"{package_name}.") for name in sys.modules)
