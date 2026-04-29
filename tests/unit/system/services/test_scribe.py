from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lychd.system.schemas import QuadletContainer, QuadletPod, QuadletTarget
from lychd.system.services.scribe import ScribeService


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    """Create mock templates."""
    d = tmp_path / "templates"
    d.mkdir()
    (d / "container.jinja").write_text("ContainerName={{ container_name }}", encoding="utf-8")
    (d / "pod.jinja").write_text("PodName={{ pod_name }}", encoding="utf-8")
    (d / "target.jinja").write_text("Description={{ description }}", encoding="utf-8")
    return d


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir()
    return d


@pytest.fixture
def scribe(templates_dir: Path, output_dir: Path) -> ScribeService:
    return ScribeService(templates_dir=templates_dir, output_dir=output_dir)


@patch("lychd.system.services.scribe.shutil.which")
@patch("lychd.system.services.scribe.subprocess.run")
def test_scribe_atomic_inscription(
    mock_run: MagicMock,
    mock_which: MagicMock,
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    """Verify that ScribeService performs an atomic swap and git commit."""
    mock_which.return_value = "/usr/bin/git"

    # Define some runes
    pod = QuadletPod(pod_name="lychd")
    container = QuadletContainer(container_name="hermes", image="ollama/ollama", description="desc")
    target = QuadletTarget(name="logic", description="Logic Coven")

    # Perform inscription
    scribe.generate_all([pod, container, target])

    # 1. Verify files exist in output_dir
    assert (output_dir / "lychd.pod").exists()
    assert (output_dir / "hermes.container").exists()
    assert (output_dir / "lychd-coven-logic.target").exists()
    assert "PodName=lychd" in (output_dir / "lychd.pod").read_text()
    assert "ContainerName=hermes" in (output_dir / "hermes.container").read_text()
    assert "Description=Logic Coven" in (output_dir / "lychd-coven-logic.target").read_text()

    # 2. Verify git was called (init and commit)
    assert mock_run.call_count >= 2
    mock_run.assert_any_call(["/usr/bin/git", "init", "-b", "main", str(output_dir)], check=True, capture_output=True)


@patch("lychd.system.services.scribe.shutil.which")
@patch("lychd.system.services.scribe.subprocess.run")
def test_scribe_cleanup_stale_files(
    mock_run: MagicMock,
    mock_which: MagicMock,
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    """Verify that stale quadlet files are removed during atomic swap."""
    mock_which.return_value = None  # Disable git for this test

    stale_file = output_dir / "stale.container"
    stale_file.touch()

    # Non-quadlet file should remain
    non_quadlet = output_dir / "important.txt"
    non_quadlet.touch()

    scribe.generate_all([])

    assert not stale_file.exists()
    assert non_quadlet.exists()
