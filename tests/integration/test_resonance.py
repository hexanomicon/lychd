import os
from pathlib import Path
from click.testing import CliRunner
import pytest
from lychd.interface.cli.main import cli

def test_cli_bind_resonance_and_targets(tmp_path):
    """
    The Resonance Crucible:
    Verifies that 'lychd bind' generates Systemd Target units and
    correctly handles the 'always_on' resonance flag.
    """
    # 1. Setup Mock Codex (ADR 13 Layout)
    xdg_config = tmp_path / "config"
    runes_dir = xdg_config / "lychd" / "runes"
    units_dir = xdg_config / "containers" / "systemd"
    
    runes_dir.mkdir(parents=True)
    units_dir.mkdir(parents=True)
    
    # 2. Write Mock Runes
    # a) A Titan model (Standard - participating in VRAM wars)
    titan_toml = runes_dir / "animator" / "titan_text.toml"
    titan_toml.parent.mkdir(parents=True, exist_ok=True)
    titan_toml.write_text("model = 'llama3-70b'\nalways_on = false\n", encoding="utf-8")
    
    # b) A Vision model (Standard - conflicting with Titan)
    vision_toml = runes_dir / "animator" / "vision.toml"
    vision_toml.write_text("model = 'phi3-vision'\nalways_on = false\n", encoding="utf-8")
    
    # c) An Embedding model (Always On - The Resonant Ally)
    embed_toml = runes_dir / "animator" / "embedding.toml"
    embed_toml.write_text("model = 'nomic-embed'\nalways_on = true\n", encoding="utf-8")
    
    # 3. Execution via CliRunner
    runner = CliRunner()
    result = runner.invoke(cli, ["bind", "--runes-dir", str(runes_dir), "--units-dir", str(units_dir)])
    
    # 4. Assertions
    if result.exit_code != 0:
        print(result.output)
    assert result.exit_code == 0
    
    # Verify Titan Target & Physical Constraints
    titan_target = units_dir / "lychd-coven-titan_text.target"
    if not titan_target.exists():
        print(result.output)
    assert titan_target.exists(), "Titan Target unit not generated"
    titan_content = titan_target.read_text()
    assert "Description=LychD Coven Target: titan_text" in titan_content
    
    # THE QUADLET PHYSICS: Titan must conflict with Vision, but NOT with the Embedding ally.
    assert "Conflicts=lychd-coven-vision.target" in titan_content
    assert "lychd-coven-embedding.target" not in titan_content, "Always-on unit incorrectly marked as conflict"
    
    # Verify Embedding Target (The Resonance)
    embed_target = units_dir / "lychd-coven-embedding.target"
    assert embed_target.exists(), "Embedding Target unit not generated"
    embed_content = embed_target.read_text()
    # Always-on units bypass the conflict generation entirely
    assert "Conflicts=" not in embed_content
    
    # Verify Quadlet lifecycle binding (PartOf)
    titan_container = units_dir / "lychd-titan_text.container"
    assert titan_container.exists()
    assert "PartOf=lychd-coven-titan_text.target" in titan_container.read_text()

if __name__ == "__main__":
    pytest.main([__file__])
