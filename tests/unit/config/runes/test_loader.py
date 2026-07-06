from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest
from pydantic import ValidationError

from lychd.config.runes import ConfigLoader, RuneConfig


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


def test_loader_parses_top_level_payload_one_file(tmp_path: Path) -> None:
    """One file with top-level payload loads as one instance."""
    target = tmp_path / "test" / "leaf" / "alpha.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('value = "alpha"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)
    instances = [i for i in loader.load_all([LeafConfig]) if isinstance(i, LeafConfig)]

    assert len(instances) == 1
    assert instances[0].value == "alpha"
    assert instances[0].source_file == target


def test_source_file_is_provenance_not_toml_field(tmp_path: Path) -> None:
    """source_file is derived from the filesystem, never from TOML payload."""
    assert "source_file" not in LeafConfig.model_fields

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


def test_source_file_binding_rejects_rebinding(tmp_path: Path) -> None:
    """A rune source can be bound once during loading."""
    instance = LeafConfig(value="alpha").bind_source_file(tmp_path / "alpha.toml")

    with pytest.raises(ValueError, match="already bound"):
        instance.bind_source_file(tmp_path / "beta.toml")


def test_source_file_binding_rejects_branch_classes(tmp_path: Path) -> None:
    """Only leaf rune classes become file-backed runes."""
    instance = ParentConfig()

    with pytest.raises(TypeError, match="Branch rune class"):
        instance.bind_source_file(tmp_path / "parent.toml")


def test_loaded_runes_are_frozen(tmp_path: Path) -> None:
    """Validated Codex intent must not drift after loading."""
    target = tmp_path / "test" / "leaf" / "alpha.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('value = "alpha"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)
    instance = next(i for i in loader.load_all([LeafConfig]) if isinstance(i, LeafConfig))

    with pytest.raises(ValidationError, match="frozen"):
        instance.value = "changed"


def test_parent_schema_does_not_consume_child_anchor_files(tmp_path: Path) -> None:
    """Parent anchors must not recursively load child anchor instances."""
    target = tmp_path / "test" / "tree" / "child" / "alpha.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('value = "alpha"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)
    loaded = loader.load_all([ParentConfig, ChildConfig])

    parent_instances = [i for i in loaded if type(i) is ParentConfig]
    child_instances = [i for i in loaded if type(i) is ChildConfig]

    assert len(parent_instances) == 0
    assert len(child_instances) == 1


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


def test_loader_rejects_legacy_model_envelope(tmp_path: Path) -> None:
    """Legacy [model] envelope syntax is rejected after top-level payload pivot."""
    target = tmp_path / "test" / "leaf" / "broken.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('[model]\nvalue = "alpha"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)

    with pytest.raises(ValueError, match="legacy"):
        loader.load_all([LeafConfig])


def test_loader_rejects_branch_rune_files(tmp_path: Path) -> None:
    """Branch rune classes are namespaces, not TOML owners."""
    a = tmp_path / "test" / "tree" / "a.toml"
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_text('title = "one"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)

    with pytest.raises(ValueError, match="cannot own TOML files"):
        loader.load_all([ParentConfig])


def test_path_fragment_rejects_string_values() -> None:
    """RuneConfig subclasses declare path fragments as Paths."""

    def define_bad_schema() -> type[RuneConfig]:
        class StringAnchorConfig(RuneConfig):
            path_fragment: ClassVar[Path] = "animator"  # type: ignore[assignment]

            value: str

        return StringAnchorConfig

    with pytest.raises(TypeError):
        define_bad_schema()


def test_relative_path_is_assembled_from_parent_chain() -> None:
    """Rune fragments are resolved through Python ancestry."""
    assert ParentConfig.relative_path == Path("test/tree")
    assert ChildConfig.relative_path == Path("test/tree/child")


def test_anchor_dir_resolves_under_active_rune_root(tmp_path: Path) -> None:
    """RuneConfig resolves anchors only under a caller-provided root."""
    assert ChildConfig.anchor_dir(tmp_path) == tmp_path / "test" / "tree" / "child"


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


def test_path_fragment_rejects_absolute_paths() -> None:
    """Rune fragments are relative to their parent rune anchor."""

    def define_bad_schema() -> type[RuneConfig]:
        class AbsoluteAnchorConfig(RuneConfig):
            path_fragment: ClassVar[Path] = Path("/outside")

            value: str

        return AbsoluteAnchorConfig

    with pytest.raises(ValueError, match="invalid path_fragment"):
        define_bad_schema()


def test_path_fragment_rejects_parent_traversal() -> None:
    """Rune fragments reject traversal parts."""

    def define_bad_schema() -> type[RuneConfig]:
        class TraversalAnchorConfig(RuneConfig):
            path_fragment: ClassVar[Path] = Path("..")

            value: str

        return TraversalAnchorConfig

    with pytest.raises(ValueError, match="invalid path_fragment part"):
        define_bad_schema()


def test_path_fragment_rejects_multiple_parts() -> None:
    """One rune class contributes exactly one path segment."""

    def define_bad_schema() -> type[RuneConfig]:
        class MultiPartAnchorConfig(RuneConfig):
            path_fragment: ClassVar[Path] = Path("safe/outside")

            value: str

        return MultiPartAnchorConfig

    with pytest.raises(ValueError, match="multi-part path_fragment"):
        define_bad_schema()


def test_path_fragment_rejects_empty_fragment() -> None:
    """Rune fragments must not be empty."""

    def define_bad_schema() -> type[RuneConfig]:
        class EmptyAnchorConfig(RuneConfig):
            path_fragment: ClassVar[Path] = Path()

            value: str

        return EmptyAnchorConfig

    with pytest.raises(ValueError, match="invalid path_fragment"):
        define_bad_schema()


def test_path_fragment_rejects_uppercase_parts() -> None:
    """Rune fragments are lowercase Codex identifiers."""

    def define_bad_schema() -> type[RuneConfig]:
        class UppercaseConfig(RuneConfig):
            path_fragment: ClassVar[Path] = Path("Soulstones")

            value: str

        return UppercaseConfig

    with pytest.raises(ValueError, match="invalid path_fragment part"):
        define_bad_schema()


def test_path_fragment_rejects_long_parts() -> None:
    """Rune fragment segments are bounded so extension namespaces stay readable."""

    def define_bad_schema() -> type[RuneConfig]:
        class LongNameConfig(RuneConfig):
            path_fragment: ClassVar[Path] = Path("a" * 51)

            value: str

        return LongNameConfig

    with pytest.raises(ValueError, match="invalid path_fragment part"):
        define_bad_schema()
