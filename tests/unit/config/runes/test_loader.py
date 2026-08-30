from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest
from pydantic import ValidationError

from lychd.config.runes import RuneConfig
from lychd.config.runes.loader import ConfigLoader


class RootConfig(RuneConfig):
    path_fragment: ClassVar[Path] = Path("test")

    marker: str = "root"


class LeafConfig(RootConfig):
    path_fragment: ClassVar[Path] = Path("leaf")

    value: str


class ParentConfig(RootConfig):
    path_fragment: ClassVar[Path] = Path("tree")

    title: str = "parent"


class ChildConfig(ParentConfig):
    path_fragment: ClassVar[Path] = Path("child")

    value: str


def test_leaf_schema_loads_multiple_instances(tmp_path: Path) -> None:
    """Leaf rune classes are multi-instance by topology."""
    first = tmp_path / "test" / "leaf" / "alpha.toml"
    second = tmp_path / "test" / "leaf" / "beta.toml"
    first.parent.mkdir(parents=True, exist_ok=True)
    first.write_text('value = "alpha"\n', encoding="utf-8")
    second.write_text('value = "beta"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)
    instances = [i for i in loader.load_all([LeafConfig]) if isinstance(i, LeafConfig)]

    assert [instance.value for instance in instances] == ["alpha", "beta"]
    assert [instance.source_file for instance in instances] == [first, second]


def test_source_file_is_provenance_not_toml_field(tmp_path: Path) -> None:
    """source_file is derived from the filesystem, never from TOML payload."""
    target = tmp_path / "test" / "leaf" / "alpha.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('value = "alpha"\nsource_file = "/tmp/forged.toml"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)

    with pytest.raises(ValidationError, match="source_file"):
        loader.load_all([LeafConfig])


def test_source_file_binding_marks_validated_instance(tmp_path: Path) -> None:
    """Source binding records provenance on the validated rune itself."""
    target = tmp_path / "test" / "leaf" / "alpha.toml"
    instance = LeafConfig(value="alpha")

    bound = instance.bind_source_file(target)

    assert bound is instance
    assert instance.source_file == target
    with pytest.raises(ValueError, match="already bound"):
        instance.bind_source_file(tmp_path / "beta.toml")


def test_loaded_runes_are_frozen(tmp_path: Path) -> None:
    """Validated Codex intent must not drift after loading."""
    target = tmp_path / "test" / "leaf" / "alpha.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('value = "alpha"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)
    instance = next(i for i in loader.load_all([LeafConfig]) if isinstance(i, LeafConfig))

    with pytest.raises(ValidationError, match="frozen"):
        instance.value = "changed"


def test_parent_schema_does_not_consume_grandchild_anchor_files(tmp_path: Path) -> None:
    """Recursive descendant anchors must also be excluded from parent loading."""

    class GrandChildConfig(ChildConfig):
        path_fragment: ClassVar[Path] = Path("grandchild")

        marker: str = ""

    target = tmp_path / "test" / "tree" / "child" / "grandchild" / "alpha.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('value = "alpha"\nmarker = "g1"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)
    loaded = loader.load_all([ParentConfig, ChildConfig, GrandChildConfig])

    parent_instances = [i for i in loaded if type(i) is ParentConfig]
    child_instances = [i for i in loaded if type(i) is ChildConfig]
    grandchild_instances = [i for i in loaded if type(i) is GrandChildConfig]

    assert len(parent_instances) == 0
    assert len(child_instances) == 0
    assert len(grandchild_instances) == 1


def test_loader_rejects_files_owned_by_an_admitted_branch(tmp_path: Path) -> None:
    """A schema admitted with its child is a namespace, not a TOML owner."""
    a = tmp_path / "test" / "tree" / "a.toml"
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_text('title = "one"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)

    with pytest.raises(ValueError, match="cannot own TOML files"):
        loader.load_all([ParentConfig, ChildConfig])


def test_unadmitted_subclass_does_not_change_leaf_ownership(tmp_path: Path) -> None:
    """An unrelated imported child cannot alter an admitted schema generation."""
    target = tmp_path / "test" / "tree" / "parent.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('title = "one"\n', encoding="utf-8")

    loaded = ConfigLoader(runes_dir=tmp_path).load_all([ParentConfig])

    assert len(loaded) == 1
    assert type(loaded[0]) is ParentConfig
    assert loaded[0].source_file == target


@pytest.mark.parametrize(
    ("fragment", "error_type", "match"),
    [
        ("animator", TypeError, None),
        (Path("/outside"), ValueError, "invalid path_fragment"),
        (Path(".."), ValueError, "invalid path_fragment part"),
        (Path("safe/outside"), ValueError, "multi-part path_fragment"),
        (Path(), ValueError, "invalid path_fragment"),
        (Path("Soulstones"), ValueError, "invalid path_fragment part"),
        (Path("a" * 51), ValueError, "invalid path_fragment part"),
    ],
)
def test_path_fragment_requires_one_safe_lowercase_path(
    fragment: object,
    error_type: type[Exception],
    match: str | None,
) -> None:
    def define_bad_schema() -> type[RuneConfig]:
        class InvalidFragmentConfig(RuneConfig):
            path_fragment: ClassVar[Path] = fragment  # type: ignore[assignment]

            value: str

        return InvalidFragmentConfig

    with pytest.raises(error_type, match=match):
        define_bad_schema()


def test_rune_class_rejects_multiple_rune_parents() -> None:
    """Rune ancestry is a single linked list, not a diamond graph."""

    class OtherRootConfig(RuneConfig):
        path_fragment: ClassVar[Path] = Path("other")

    def define_bad_schema() -> type[RuneConfig]:
        class AmbiguousConfig(ParentConfig, OtherRootConfig):
            path_fragment: ClassVar[Path] = Path("ambiguous")

        return AmbiguousConfig

    with pytest.raises(TypeError, match="multiple rune parents"):
        define_bad_schema()


def test_path_fragment_is_required_for_all_subclasses() -> None:
    """No rune type may place TOML files directly in the rune root."""

    def define_bad_schema() -> type[RuneConfig]:
        class RootFileConfig(RuneConfig):
            value: str

        return RootFileConfig

    with pytest.raises(ValueError, match="declares no path_fragment"):
        define_bad_schema()


def test_child_path_fragment_must_be_declared_locally() -> None:
    """Child rune classes must not inherit the parent's path fragment."""

    def define_bad_schema() -> type[RuneConfig]:
        class MissingChildDirConfig(ParentConfig):
            value: str

        return MissingChildDirConfig

    with pytest.raises(ValueError, match="declares no path_fragment"):
        define_bad_schema()
