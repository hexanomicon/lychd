from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from lychd.config.runes import ConfigLoader, RuneConfig, RuneConfigError, RuneSchemaDiscovery


class LeafConfig(RuneConfig):
    relative_path: ClassVar[Path | None] = Path("test/leaf")

    value: str


class ParentConfig(RuneConfig):
    relative_path: ClassVar[Path | None] = Path("test/tree")

    title: str = "parent"


class ChildConfig(ParentConfig):
    relative_path: ClassVar[Path | None] = Path("test/tree/child")

    value: str


class ForcedSingletonConfig(RuneConfig):
    relative_path: ClassVar[Path | None] = Path("test/forced")
    singleton: ClassVar[bool | None] = True

    value: str


class TopLevelConfig(RuneConfig):
    relative_path: ClassVar[Path | None] = None

    marker: str


def test_singleton_auto_and_override_contract() -> None:
    """Validate singleton auto inference and explicit override behavior."""
    assert ParentConfig.effective_singleton() is True
    assert ChildConfig.effective_singleton() is False
    assert LeafConfig.effective_singleton() is False
    assert ForcedSingletonConfig.effective_singleton() is True
    assert TopLevelConfig.effective_singleton() is True


def test_loader_parses_top_level_payload_one_file(tmp_path: Path) -> None:
    """One file with top-level payload loads as one instance."""
    target = tmp_path / "test" / "leaf" / "alpha.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('value = "alpha"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)
    instances = [i for i in loader.load_all([LeafConfig]) if isinstance(i, LeafConfig)]

    assert len(instances) == 1
    assert instances[0].value == "alpha"
    assert instances[0].file_name == target
    assert LeafConfig.instance_id_from_path(target, root=tmp_path) == "test/leaf/alpha"


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
        relative_path: ClassVar[Path | None] = Path("test/tree/grandchild")

        marker: str

    target = tmp_path / "test" / "tree" / "grandchild" / "alpha.toml"
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

    with pytest.raises(RuneConfigError, match="legacy"):
        loader.load_all([LeafConfig])


def test_loader_enforces_singleton_conflicts(tmp_path: Path) -> None:
    """Singleton schemas fail fast when multiple instance files exist."""
    a = tmp_path / "test" / "forced" / "a.toml"
    b = tmp_path / "test" / "forced" / "b.toml"
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_text('value = "one"\n', encoding="utf-8")
    b.write_text('value = "two"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)

    with pytest.raises(RuneConfigError, match="singleton"):
        loader.load_all([ForcedSingletonConfig])


def test_loader_supports_top_level_singleton_file(tmp_path: Path) -> None:
    """Top-level schemas resolve default filename at runes root."""
    root_file = tmp_path / "toplevelconfig.toml"
    root_file.write_text('marker = "sentinel"\n', encoding="utf-8")

    loader = ConfigLoader(runes_dir=tmp_path)
    instances = [i for i in loader.load_all([TopLevelConfig]) if isinstance(i, TopLevelConfig)]

    assert len(instances) == 1
    assert instances[0].marker == "sentinel"


def test_extension_discovery_imports_builtin_configurable(tmp_path: Path) -> None:
    """Built-in extension config subclasses are discovered after runtime import."""
    classes = RuneSchemaDiscovery(include_builtin_extensions=True).discover_classes()

    names = {cls.__name__ for cls in classes}
    assert "ShadowSimulationConfig" in names
    assert "LeafConfig" not in names


def test_extension_discovery_is_deduplicated_and_stable() -> None:
    """Discovery should return deterministic, duplicate-free class lists."""
    classes = RuneSchemaDiscovery(include_builtin_extensions=True).discover_classes()
    keys = [(cls.__module__, cls.__qualname__) for cls in classes]

    assert len(classes) == len(set(classes))
    assert keys == sorted(keys)
