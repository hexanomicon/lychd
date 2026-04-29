from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from lychd.config.runes import ConfigWriter, RuneConfig


class WriterSampleConfig(RuneConfig):
    relative_path: ClassVar[Path | None] = Path("writer/sample")

    required_name: str
    retries: int = 3
    enabled: bool = True


class WriterParentConfig(RuneConfig):
    relative_path: ClassVar[Path | None] = Path("writer/tree")

    marker: str = "root"


class WriterChildConfig(WriterParentConfig):
    relative_path: ClassVar[Path | None] = Path("writer/tree/child")

    value: str


class WriterGrandChildConfig(WriterChildConfig):
    relative_path: ClassVar[Path | None] = Path("writer/tree/grandchild")

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
    assert "# default: 3" in content
    assert "# retries = 0" in content
    assert "# default: True" in content
    assert "# enabled = false" in content


def test_writer_keeps_parent_anchor_distinct_from_child_anchor(tmp_path: Path) -> None:
    """Parent sample should still be created when child anchor has instances."""
    writer = ConfigWriter(runes_dir=tmp_path)

    writer.initialize_anchors([WriterChildConfig, WriterParentConfig])
    created = writer.inscribe_samples([WriterChildConfig, WriterParentConfig])

    assert tmp_path / "writer" / "tree" / "child" / "writerchildconfig.toml" in created
    assert tmp_path / "writer" / "tree" / "writerparentconfig.toml" in created


def test_writer_keeps_parent_anchor_distinct_from_grandchild_anchor(tmp_path: Path) -> None:
    """Parent sample should not be blocked by grandchild anchor files."""
    writer = ConfigWriter(runes_dir=tmp_path)

    writer.initialize_anchors([WriterParentConfig, WriterChildConfig, WriterGrandChildConfig])
    grandchild_sample = tmp_path / "writer" / "tree" / "grandchild" / "writergrandchildconfig.toml"
    grandchild_sample.parent.mkdir(parents=True, exist_ok=True)
    grandchild_sample.write_text('marker = "g1"\nvalue = "child"\n', encoding="utf-8")

    created = writer.inscribe_samples([WriterParentConfig])

    assert tmp_path / "writer" / "tree" / "writerparentconfig.toml" in created
