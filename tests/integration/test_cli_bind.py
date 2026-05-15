import os
from pathlib import Path
from click.testing import CliRunner
import pytest
from lychd.interface.cli.main import cli

def test_cli_bind_generates_quadlets_with_conflicts(tmp_path):
    """
    The Transmutation Crucible:
    Verifies that 'lychd bind' generates Podman Quadlet files and
    correctly injects the 'Conflicts=' directive for Titan models.
    """
    # 1. Setup Mock Codex (ADR 13 Layout)
    xdg_config = tmp_path / "config"
    runes_dir = xdg_config / "lychd" / "runes"
    units_dir = xdg_config / "containers" / "systemd"
    
    runes_dir.mkdir(parents=True)
    units_dir.mkdir(parents=True)
    
    # 2. Write Mock Runes
    # a) A Titan text model (filename triggers 'titan' logic in our stub)
    titan_toml = runes_dir / "animator" / "titan_text.toml"
    titan_toml.parent.mkdir(parents=True, exist_ok=True)
    titan_toml.write_text("model = 'llama3-70b-titan'\\n", encoding="utf-8")
    
    # b) A standard vision model
    vision_toml = runes_dir / "animator" / "standard_vision.toml"
    vision_toml.write_text("model = 'phi3-vision'\\n", encoding="utf-8")
    
    # 3. Execution via CliRunner
    runner = CliRunner()
    result = runner.invoke(cli, ["bind", "--runes-dir", str(runes_dir), "--units-dir", str(units_dir)])
    
    # 4. Assertions
    assert result.exit_code == 0
    assert "Forging physical constraints..." in result.output
    
    # Verify Titan Quadlet
    titan_quadlet = units_dir / "lychd-titan_text.container"
    assert titan_quadlet.exists(), f"Titan Quadlet not found at {titan_quadlet}"
    titan_content = titan_quadlet.read_text()
    assert "[Unit]" in titan_content
    assert "Description=LychD Coven: titan_text" in titan_content
    
    # THE QUADLET PHYSICS: Assert that Conflicts= was injected for the Titan
    # This guarantees the Linux kernel kills the vision model when titan-text starts.
    assert "Conflicts=lychd-vision.service" in titan_content
    
    # Verify Vision Quadlet
    vision_quadlet = units_dir / "lychd-standard_vision.container"
    assert vision_quadlet.exists(), f"Vision Quadlet not found at {vision_quadlet}"
    vision_content = vision_quadlet.read_text()
    # Standard models in our stub logic do not trigger the automatic conflict.
    assert "Conflicts=lychd-vision.service" not in vision_content

if __name__ == "__main__":
    pytest.main([__file__])
