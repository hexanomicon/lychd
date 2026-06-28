from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field

from lychd.config.runes import ConfigWriter, RuneConfig


class WriterRootConfig(RuneConfig):
    path_fragment: ClassVar[Path] = Path("writer")

    marker: str = "root"


class WriterSampleConfig(WriterRootConfig):
    path_fragment: ClassVar[Path] = Path("sample")

    required_name: str
    groups: list[str] = Field(default_factory=list)
    env_vars: dict[str, str] = Field(default_factory=dict)
    optional_port: int | None = None
    retries: int = 3
    enabled: bool = True


class WriterCustomTemplateConfig(WriterRootConfig):
    path_fragment: ClassVar[Path] = Path("custom")
    sample_template: ClassVar[str | None] = 'name = "custom"\n'

    name: str
    required_value: str


class WriterParentConfig(WriterRootConfig):
    path_fragment: ClassVar[Path] = Path("tree")

    marker: str = "root"


class WriterChildConfig(WriterParentConfig):
    path_fragment: ClassVar[Path] = Path("child")

    value: str


class WriterGrandChildConfig(WriterChildConfig):
    path_fragment: ClassVar[Path] = Path("grandchild")

    marker: str = "g1"


def test_writer_generates_commented_defaults(tmp_path: Path) -> None:
    """Defaulted fields are commented and required fields stay active."""
    writer = ConfigWriter(runes_dir=tmp_path)

    writer.initialize_anchors([WriterSampleConfig])
    created = writer.inscribe_samples([WriterSampleConfig])

    assert len(created) == 1
    target = tmp_path / "writer" / "sample" / "writersampleconfig.toml"
    assert created[0] == target

    content = target.read_text(encoding="utf-8")
    assert "[model]" not in content
    assert 'required_name = "<required:str>"' in content
    assert "# groups = []" in content
    assert "# env_vars = {}" in content
    assert "# optional_port = 0" in content
    assert "# default: 3" in content
    assert "# retries = 0" in content
    assert "# default: True" in content
    assert "# enabled = false" in content


def test_writer_prefers_custom_sample_template(tmp_path: Path) -> None:
    """Schema-local sample templates replace the generic field scaffold."""
    writer = ConfigWriter(runes_dir=tmp_path)

    writer.initialize_anchors([WriterCustomTemplateConfig])
    created = writer.inscribe_samples([WriterCustomTemplateConfig])

    assert len(created) == 1
    content = created[0].read_text(encoding="utf-8")
    # Custom sample templates are wrapped with the placeholder marker too, so a
    # generated sample stays inert until the operator removes the marker.
    assert content == (
        "# lychd: sample-rune\n"
        "# Edit this file, then remove this marker to activate it.\n"
        "\n"
        'name = "custom"\n'
    )
    assert "required_value" not in content


def test_writer_only_creates_leaf_samples(tmp_path: Path) -> None:
    """Branch samples are not created; leaf descendants still get samples."""
    writer = ConfigWriter(runes_dir=tmp_path)

    writer.initialize_anchors([WriterGrandChildConfig, WriterChildConfig, WriterParentConfig])
    created = writer.inscribe_samples([WriterGrandChildConfig, WriterChildConfig, WriterParentConfig])

    assert tmp_path / "writer" / "tree" / "child" / "grandchild" / "writergrandchildconfig.toml" in created
    assert tmp_path / "writer" / "tree" / "child" / "writerchildconfig.toml" not in created
    assert tmp_path / "writer" / "tree" / "writerparentconfig.toml" not in created


def test_writer_keeps_parent_anchor_distinct_from_grandchild_anchor(tmp_path: Path) -> None:
    """Branch samples are not created even when descendants have files."""
    writer = ConfigWriter(runes_dir=tmp_path)

    writer.initialize_anchors([WriterParentConfig, WriterChildConfig, WriterGrandChildConfig])
    grandchild_sample = tmp_path / "writer" / "tree" / "child" / "grandchild" / "writergrandchildconfig.toml"
    grandchild_sample.parent.mkdir(parents=True, exist_ok=True)
    grandchild_sample.write_text('marker = "g1"\nvalue = "child"\n', encoding="utf-8")

    created = writer.inscribe_samples([WriterParentConfig])

    assert tmp_path / "writer" / "tree" / "writerparentconfig.toml" not in created
