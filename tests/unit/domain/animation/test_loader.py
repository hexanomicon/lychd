from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

from lychd.domain.animation.schemas import ModelFormat
from lychd.domain.animation.services.loader import AnimatorLoader

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def temp_dirs(tmp_path: Path) -> tuple[Path, Path]:
    """Create temporary directories for testing.

    Returns:
        tuple[Path, Path]: (soulstones_dir, portals_dir)
    """
    soul_dir = tmp_path / "soulstones"
    portal_dir = tmp_path / "portals"
    soul_dir.mkdir()
    portal_dir.mkdir()
    return soul_dir, portal_dir


def test_load_solitary_soulstone(temp_dirs: tuple[Path, Path]) -> None:
    """Test loading a simple, ungrouped soulstone."""
    soul_dir, portal_dir = temp_dirs

    (soul_dir / "hermes.toml").write_text(
        textwrap.dedent("""
        [hermes]
        image = "ghcr.io/ggerganov/llama.cpp:server"
        port = 8080
        model_path = "/models/hermes.gguf"
        model_name = "hermes-v2"
        """),
        encoding="utf-8",
    )

    # Inject empty reserved ports to avoid hitting real settings
    loader = AnimatorLoader(soulstones_path=soul_dir, portals_path=portal_dir, reserved_ports={})
    soulstones, _ = loader.load_all()

    assert len(soulstones) == 1
    stone = soulstones[0]
    assert stone.name == "hermes"
    assert stone.port == 8080


def test_load_explicit_groups_soulstones(temp_dirs: tuple[Path, Path]) -> None:
    """Test explicit 'groups' field in TOML."""
    soul_dir, portal_dir = temp_dirs

    (soul_dir / "logic_cluster.toml").write_text(
        textwrap.dedent("""
        [alpha]
        groups = ["logic"]
        image = "vllm/vllm"
        port = 9001
        model_path = "/models/alpha"
        model_name = "alpha-7b"

        [beta]
        groups = ["logic"]
        image = "vllm/vllm"
        port = 9002
        model_path = "/models/beta"
        model_name = "beta-7b"
        """),
        encoding="utf-8",
    )

    loader = AnimatorLoader(soulstones_path=soul_dir, portals_path=portal_dir, reserved_ports={})
    soulstones, _ = loader.load_all()

    assert len(soulstones) == 2
    soulstones.sort(key=lambda x: x.name)
    alpha, beta = soulstones

    assert alpha.name == "alpha"
    assert alpha.groups == ["logic"]
    assert beta.name == "beta"
    assert beta.groups == ["logic"]


def test_load_mixed_content(temp_dirs: tuple[Path, Path]) -> None:
    """Test a file that contains both solitary and grouped entities."""
    soul_dir, portal_dir = temp_dirs

    (soul_dir / "mixed.toml").write_text(
        textwrap.dedent("""
        [lonewolf]
        # Implicit groups=[]
        image = "img"
        port = 8000
        model_path = "/m"
        model_name = "lone"

        [leader]
        groups = ["pack"]
        image = "img"
        port = 8001
        model_path = "/m"
        model_name = "leader"
        """),
        encoding="utf-8",
    )

    loader = AnimatorLoader(soulstones_path=soul_dir, portals_path=portal_dir, reserved_ports={})
    soulstones, _ = loader.load_all()

    assert len(soulstones) == 2


def test_port_conflict_detection(temp_dirs: tuple[Path, Path]) -> None:
    """Ensure loader raises ValueError when two soulstones claim the same port."""
    soul_dir, portal_dir = temp_dirs

    (soul_dir / "conflict.toml").write_text(
        textwrap.dedent("""
        [hermes]
        image = "img"
        port = 8080
        model_path = "/m"
        model_name = "hermes"

        [zeus]
        image = "img"
        port = 8080
        model_path = "/m"
        model_name = "zeus"
        """),
        encoding="utf-8",
    )

    loader = AnimatorLoader(soulstones_path=soul_dir, portals_path=portal_dir, reserved_ports={})

    with pytest.raises(ValueError, match="conflicts with hermes"):
        loader.load_all()


def test_system_port_conflict(temp_dirs: tuple[Path, Path]) -> None:
    """Ensure loader raises ValueError when a soulstone claims a system port."""
    soul_dir, portal_dir = temp_dirs

    (soul_dir / "bad_port.toml").write_text(
        textwrap.dedent("""
        [rogue]
        image = "img"
        port = 5432
        model_path = "/m"
        model_name = "rogue"
        """),
        encoding="utf-8",
    )

    # Reserve Postgres port (Name -> Port) to match Loader signature
    reserved = {"Postgres": 5432}
    loader = AnimatorLoader(soulstones_path=soul_dir, portals_path=portal_dir, reserved_ports=reserved)

    with pytest.raises(ValueError, match="conflicts with Postgres"):
        loader.load_all()


def test_load_portals(temp_dirs: tuple[Path, Path]) -> None:
    """Test loading portal configurations."""
    soul_dir, portal_dir = temp_dirs

    (portal_dir / "cloud.toml").write_text(
        textwrap.dedent("""
        [openai]
        uri = "https://api.openai.com/v1"
        model_name = "gpt-4"
        provider = "openai"
        api_key_env = "OPENAI_API_KEY"
        """),
        encoding="utf-8",
    )

    loader = AnimatorLoader(soulstones_path=soul_dir, portals_path=portal_dir, reserved_ports={})
    _, portals = loader.load_all()

    assert len(portals) == 1
    assert portals[0].provider == "openai"


def test_resilience_malformed_toml(temp_dirs: tuple[Path, Path]) -> None:
    """Ensure a bad file is skipped and doesn't crash the loader."""
    soul_dir, portal_dir = temp_dirs

    (soul_dir / "broken.toml").write_text("this is not toml", encoding="utf-8")

    loader = AnimatorLoader(soulstones_path=soul_dir, portals_path=portal_dir, reserved_ports={})
    soulstones, _ = loader.load_all()

    assert len(soulstones) == 0


def test_schema_defaults(temp_dirs: tuple[Path, Path]) -> None:
    """Verify default generation parameters."""
    soul_dir, portal_dir = temp_dirs

    (soul_dir / "defaults.toml").write_text(
        textwrap.dedent("""
        [basic]
        image = "img"
        port = 7000
        model_path = "/m"
        model_name = "basic"
        model_format = "GGUF"
        """),
        encoding="utf-8",
    )

    loader = AnimatorLoader(soulstones_path=soul_dir, portals_path=portal_dir, reserved_ports={})
    stones, _ = loader.load_all()

    assert stones[0].temperature == 0.7
    assert stones[0].model_format == ModelFormat.GGUF


def test_api_key_resolution(temp_dirs: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that environment variables are transmuted into SecretStr keys."""
    soul_dir, portal_dir = temp_dirs

    monkeypatch.setenv("MY_SECRET_KEY", "sk-proj-123456")

    (portal_dir / "secure.toml").write_text(
        textwrap.dedent("""
        [secure_portal]
        uri = "https://api.example.com"
        model_name = "gpt-secure"
        api_key_env = "MY_SECRET_KEY"
        """),
        encoding="utf-8",
    )

    loader = AnimatorLoader(soulstones_path=soul_dir, portals_path=portal_dir, reserved_ports={})
    _, portals = loader.load_all()

    assert len(portals) == 1
    assert portals[0].api_key is not None
    assert portals[0].api_key.get_secret_value() == "sk-proj-123456"
