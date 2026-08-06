from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import ClassVar

import pytest
from pydantic import Field

from lychd.config import QuadletConfig
from lychd.config.runes import ConfigWriter, RuneConfig
from lychd.system.services.lifecycle import CreatedResources
from lychd.system.services.publication import JournaledCreation


class WriterRootConfig(RuneConfig):
    """Writer test declarations."""

    path_fragment: ClassVar[Path] = Path("writer")

    marker: str = "root"


class WriterSampleConfig(WriterRootConfig):
    """Writer sample declarations.

    A longer explanation must not leak into the compact lifecycle tree.
    """

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


class WriterEmbeddedConfig(WriterRootConfig):
    path_fragment: ClassVar[Path] = Path("embedded")

    name: str
    quadlet: QuadletConfig


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


def test_writer_projects_first_docstring_line_onto_planned_paths(tmp_path: Path) -> None:
    writer = ConfigWriter(runes_dir=tmp_path)

    descriptions = writer.planned_path_descriptions([WriterSampleConfig])

    assert descriptions[tmp_path / "writer"] == "Writer test declarations."
    assert descriptions[tmp_path / "writer" / "sample"] == "Writer sample declarations."
    assert descriptions[tmp_path / "writer" / "sample" / "writersampleconfig.toml"] == (
        "Generated inactive example; remove its marker before use."
    )


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
        '# lychd: sample-rune\n# Edit this file, then remove this marker to activate it.\n\nname = "custom"\n'
    )
    assert "required_value" not in content


def test_writer_renders_embedded_config_as_a_valid_toml_inline_table(tmp_path: Path) -> None:
    writer = ConfigWriter(runes_dir=tmp_path)

    writer.initialize_anchors([WriterEmbeddedConfig])
    created = writer.inscribe_samples([WriterEmbeddedConfig])

    content = created[0].read_text(encoding="utf-8")
    assert 'quadlet = { image = "<required:str>" }' in content
    parsed = tomllib.loads(content)
    rune = WriterEmbeddedConfig.model_validate(parsed)
    assert rune.quadlet.image == "<required:str>"


def test_writer_legacy_callbacks_run_at_the_creation_commit_boundary(tmp_path: Path) -> None:
    """Public path callbacks remain compatible while publication owns rollback."""
    writer = ConfigWriter(runes_dir=tmp_path)
    directory_batches: list[tuple[Path, ...]] = []
    samples: list[Path] = []

    directories = writer.initialize_anchors(
        [WriterCustomTemplateConfig],
        on_created=directory_batches.append,
    )
    created_samples = writer.inscribe_samples(
        [WriterCustomTemplateConfig],
        on_created=samples.append,
    )

    assert tuple(path for batch in directory_batches for path in batch) == tuple(directories)
    assert samples == created_samples


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


def test_writer_preserves_and_never_journals_a_peer_sample(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The initial empty-anchor observation cannot adopt a publication racer."""
    anchor = tmp_path / "writer" / "sample"
    anchor.mkdir(parents=True)
    target = anchor / "writersampleconfig.toml"
    journal: list[CreatedResources] = []
    creation = JournaledCreation(on_created=journal.append)
    writer = ConfigWriter(runes_dir=tmp_path, creation=creation)
    raced = False

    def install_peer_then_link(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        del source, src_dir_fd, follow_symlinks
        nonlocal raced
        if not raced:
            raced = True
            descriptor = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=dst_dir_fd,
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write('required_name = "peer"\n')
        raise FileExistsError(destination)

    monkeypatch.setattr(
        "lychd.system.services.publication.os.link",
        install_peer_then_link,
    )

    created = writer.inscribe_samples([WriterSampleConfig])

    assert created == []
    assert journal == []
    assert target.read_text(encoding="utf-8") == 'required_name = "peer"\n'
